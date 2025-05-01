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
