package postgresql

import (
	"context"
	"encoding/json"
	"fmt"
	"slices"
	"strconv"
	"strings"

	"github.com/firebase/genkit/go/ai"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
)

type docStore struct {
	engine PostgresEngine

	tableName             string
	schemaName            string
	idColumn              string
	metadataJSONColumn    string
	contentColumn         string
	embeddingColumn       string
	metadataColumns       []string
	ignoreMetadataColumns []string

	embedder        ai.Embedder
	embedderOptions any
}

// newDocStore instantiate a docStore
func newDocStore(ctx context.Context, p *Postgres, cfg Config) (*docStore, error) {
	p.mu.Lock()
	defer p.mu.Unlock()
	if !p.initted {
		panic("postgres.Init not called")
	}
	if cfg.Name == "" {
		return nil, fmt.Errorf("name is empty")
	}
	if cfg.Embedder == nil {
		return nil, fmt.Errorf("embedder is required")
	}

	if cfg.SchemaName == "" {
		cfg.SchemaName = defaultSchemaName
	}

	if cfg.TableName == "" {
		cfg.TableName = defaultTable
	}

	return &docStore{
		engine: p.engine,

		tableName:             cfg.TableName,
		schemaName:            cfg.SchemaName,
		idColumn:              cfg.IDColumn,
		metadataJSONColumn:    cfg.MetadataJsonColumn,
		contentColumn:         cfg.ContentColumn,
		embeddingColumn:       cfg.EmbeddingColumn,
		metadataColumns:       cfg.MetadataColumns,
		ignoreMetadataColumns: cfg.IgnoreMetadataColumns,

		embedder:        cfg.Embedder,
		embedderOptions: cfg.EmbedderOptions,
	}, nil
}

func (ds *docStore) query(ctx context.Context, ss *SimilaritySearch, embbeding []float32) (*ai.RetrieverResponse, error) {
	res := &ai.RetrieverResponse{}

	query := ss.buildQuery(embbeding)
	rows, err := ds.engine.Pool.Query(ctx, query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	fieldDescriptions := rows.FieldDescriptions()
	columnNames := make([]string, len(fieldDescriptions))

	for i, fieldDescription := range fieldDescriptions {
		columnNames[i] = fieldDescription.Name
	}

	for rows.Next() {
		values := make([]interface{}, len(columnNames))
		valuesPrt := make([]interface{}, len(columnNames))

		for i := range columnNames {
			valuesPrt[i] = &values[i]
		}
		if err := rows.Scan(valuesPrt...); err != nil {
			return nil, fmt.Errorf("scan row failed: %v", err)
		}

		meta := make(map[string]any, ss.k)
		var content []*ai.Part
		for i, col := range columnNames {
			if (len(ss.metadataColumns) > 0 && !slices.Contains(ss.metadataColumns, col)) &&
				ss.contentColumn != col &&
				ss.metadataJsonColumn != col {
				continue
			}

			if ss.contentColumn == col {
				content = append(content, ai.NewTextPart(values[i].(string)))
			}

			if ss.metadataJsonColumn == col {
				content = append(content, ai.NewJSONPart(values[i].(string)))
				continue
			}

			meta[col] = values[i]
		}

		doc := &ai.Document{
			Metadata: meta,
			Content:  content,
		}

		res.Documents = append(res.Documents, doc)
	}

	return res, nil
}

type RetrieverOptions struct {
	SimilaritySearch *SimilaritySearch
}

func (ds *docStore) Retrieve(ctx context.Context, req *ai.RetrieverRequest) (*ai.RetrieverResponse, error) {
	if req.Options == nil {
		ss := NewSimilaritySearch()
		req.Options = &RetrieverOptions{SimilaritySearch: ss}
	}

	ropt, ok := req.Options.(*RetrieverOptions)
	if !ok {
		return nil, fmt.Errorf("postgres.Retrieve options have type %T, want %T", req.Options, &RetrieverOptions{})
	}

	if ropt.SimilaritySearch == nil {
		ss := NewSimilaritySearch()
		ropt.SimilaritySearch = ss
	}

	ereq := &ai.EmbedRequest{
		Documents: []*ai.Document{req.Query},
		Options:   ds.embedderOptions,
	}
	eres, err := ds.embedder.Embed(ctx, ereq)
	if err != nil {
		return nil, fmt.Errorf("postgres.Retrieve retrieve embedding failed: %v", err)
	}
	res, err := ds.query(ctx, ropt.SimilaritySearch, eres.Embeddings[0].Embedding)
	if err != nil {
		return nil, fmt.Errorf("googlecloudsql.postgres.Retrieve failed to execute the query: %v", err)
	}
	return res, nil
}

type IndexerOptions struct {
	VectorStore *VectorStore
}

// Index implements the genkit  Indexer method.
func (ds *docStore) Index(ctx context.Context, req *ai.IndexerRequest) error {
	if len(req.Documents) == 0 {
		return nil
	}

	/*if req.Options == nil {
		vs, _ := NewVectorStore()

		req.Options = &IndexerOptions{VectorStore: vs}
	}

	iopt, ok := req.Options.(*IndexerOptions)
	if !ok {
		return fmt.Errorf("postgres.Indexer options have type %T, want %T", req.Options, &IndexerOptions{})
	}*/

	ereq := &ai.EmbedRequest{
		Documents: req.Documents,
		Options:   ds.embedderOptions,
	}
	eres, err := ds.embedder.Embed(ctx, ereq)
	if err != nil {
		return fmt.Errorf("postgres.Indexer index embedding failed: %v", err)
	}
	for _, doc := range req.Documents {
		// if no metadata provided, initialize with empty map
		if doc.Metadata == nil {
			doc.Metadata = make(map[string]any)
		}

		// generate the id if it's not defined
		if _, ok := doc.Metadata[ds.idColumn].(string); !ok {
			doc.Metadata[ds.idColumn] = uuid.New().String()
		}
	}

	return ds.index(ctx, eres.Embeddings, req.Documents)
}

func (ds *docStore) index(ctx context.Context, documentEmbeddings []*ai.DocumentEmbedding, documents []*ai.Document) error {
	b := &pgx.Batch{}

	for i, doc := range documents {
		embeddingString := vectorToString(documentEmbeddings[i].Embedding)
		query, values, err := ds.generateAddDocumentsQuery(
			doc.Metadata[ds.idColumn].(string), doc.Metadata[ds.contentColumn].(string), embeddingString, doc.Metadata)
		if err != nil {
			return err
		}
		b.Queue(query, values)
	}

	batchResults := ds.engine.Pool.SendBatch(ctx, b)
	if err := batchResults.Close(); err != nil {
		return fmt.Errorf("failed to execute batch: %w", err)
	}

	return nil

}

func vectorToString(v []float32) string {
	stringArray := make([]string, len(v))
	for i, val := range v {
		stringArray[i] = strconv.FormatFloat(float64(val), 'f', -1, 32)
	}
	return "[" + strings.Join(stringArray, ", ") + "]"
}

func (ds *docStore) generateAddDocumentsQuery(id, content, embedding string, metadata map[string]any) (string, []any, error) {
	// Construct metadata column names if present
	metadataColNames := ""
	if len(ds.metadataColumns) > 0 {
		metadataColNames = ", " + strings.Join(ds.metadataColumns, ", ")
	}

	if ds.metadataJSONColumn != "" {
		metadataColNames += ", " + ds.metadataJSONColumn
	}

	insertStmt := fmt.Sprintf(`INSERT INTO %q.%q (%s, %s, %s%s)`,
		ds.schemaName, ds.tableName, ds.idColumn, ds.contentColumn, ds.embeddingColumn, metadataColNames)
	valuesStmt := "VALUES ($1, $2, $3"
	values := []any{id, content, embedding}

	// Add metadata
	for _, metadataColumn := range ds.metadataColumns {
		if val, ok := metadata[metadataColumn]; ok {
			valuesStmt += fmt.Sprintf(", $%d", len(values)+1)
			values = append(values, val)
			delete(metadata, metadataColumn)
		} else {
			valuesStmt += ", NULL"
		}
	}
	// Add JSON column and/or close statement
	if ds.metadataJSONColumn != "" {
		valuesStmt += fmt.Sprintf(", $%d", len(values)+1)
		metadataJSON, err := json.Marshal(metadata)
		if err != nil {
			return "", nil, fmt.Errorf("failed to transform metadata to json: %w", err)
		}
		values = append(values, metadataJSON)
	}
	valuesStmt += ")"
	query := insertStmt + valuesStmt
	return query, values, nil
}

/* +++++++++++++++++++++++
		Advance methods
 +++++++++++++++++++++++++ */

// ApplyVectorIndex creates an index in the table of the embeddings.
func (ds *docStore) ApplyVectorIndex(ctx context.Context, index BaseIndex, name string, concurrently bool) error {
	if index.indexType == "exactnearestneighbor" {
		return ds.DropVectorIndex(ctx, name)
	}

	filter := ""
	if len(index.partialIndexes) > 0 {
		filter = fmt.Sprintf("WHERE %s", index.partialIndexes)
	}
	optsString := index.indexOptions()
	params := fmt.Sprintf("WITH %s", optsString)

	if name == "" {
		if index.name == "" {
			index.name = ds.tableName + defaultIndexNameSuffix
		}
		name = index.name
	}

	concurrentlyStr := ""
	if concurrently {
		concurrentlyStr = "CONCURRENTLY"
	}

	function := index.distanceStrategy.searchFunction()
	stmt := fmt.Sprintf(`CREATE INDEX %s %s ON "%s"."%s" USING %s (%s %s) %s %s`,
		concurrentlyStr, name, ds.schemaName, ds.tableName, index.indexType, ds.embeddingColumn, function, params, filter)

	_, err := ds.engine.Pool.Exec(ctx, stmt)
	if err != nil {
		return fmt.Errorf("failed to execute creation of index: %w", err)
	}

	return nil
}

// ReIndex recreates the index on the table.
func (ds *docStore) ReIndex(ctx context.Context) error {
	indexName := ds.tableName + defaultIndexNameSuffix
	return ds.ReIndexWithName(ctx, indexName)
}

// ReIndexWithName recreates the index on the table by name.
func (ds *docStore) ReIndexWithName(ctx context.Context, indexName string) error {
	query := fmt.Sprintf("REINDEX INDEX %s;", indexName)
	_, err := ds.engine.Pool.Exec(ctx, query)
	if err != nil {
		return fmt.Errorf("failed to reindex: %w", err)
	}

	return nil
}

// DropVectorIndex drops the vector index from the table.
func (ds *docStore) DropVectorIndex(ctx context.Context, indexName string) error {
	if indexName == "" {
		indexName = ds.tableName + defaultIndexNameSuffix
	}
	query := fmt.Sprintf("DROP INDEX IF EXISTS %s;", indexName)
	_, err := ds.engine.Pool.Exec(ctx, query)
	if err != nil {
		return fmt.Errorf("failed to drop vector index: %w", err)
	}

	return nil
}

// IsValidIndex checks if index exists in the table.
func (ds *docStore) IsValidIndex(ctx context.Context, indexName string) (bool, error) {
	if indexName == "" {
		indexName = ds.tableName + defaultIndexNameSuffix
	}
	query := fmt.Sprintf("SELECT tablename, indexname  FROM pg_indexes WHERE tablename = '%s' AND schemaname = '%s' AND indexname = '%s';",
		ds.tableName, ds.schemaName, indexName)
	var tableName, indexNameFromDB string
	err := ds.engine.Pool.QueryRow(ctx, query).Scan(&tableName, &indexNameFromDB)
	if err != nil {
		return false, fmt.Errorf("failed to check if index exists: %w", err)
	}

	return indexNameFromDB == indexName, nil
}

func (ds *docStore) NewBaseIndex(indexName, indexType string, strategy DistanceStrategy, partialIndexes []string, opts Index) BaseIndex {
	return BaseIndex{
		name:             indexName,
		indexType:        indexType,
		distanceStrategy: strategy,
		partialIndexes:   partialIndexes,
		options:          opts,
	}
}
