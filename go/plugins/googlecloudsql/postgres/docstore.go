package postgres

import (
	"context"
	"errors"
	"fmt"
	"github.com/firebase/genkit/go/ai"
	"slices"
	"strconv"
	"strings"
)

type docStore struct {
	engine          *engine
	embedder        ai.Embedder
	embedderOptions any
}

type Criteria struct {
	filter           any
	count            int
	distanceStrategy DistanceStrategy
}

type SimilaritySearch struct {
	vectorStore *VectorStore
	criteria    *Criteria
}

func NewSimilaritySearch(vectorStore *VectorStore, criteria *Criteria) *SimilaritySearch {
	return &SimilaritySearch{
		vectorStore: vectorStore,
		criteria:    criteria,
	}
}

func (ss SimilaritySearch) buildQuery(embedding []float32) string {

	vectorToString := func(v []float32) string {
		stringArray := make([]string, len(v))
		for i, val := range v {
			stringArray[i] = strconv.FormatFloat(float64(val), 'f', -1, 32)
		}
		return "[" + strings.Join(stringArray, ", ") + "]"
	}

	operator := ss.criteria.distanceStrategy.operator()
	searchFunction := ss.criteria.distanceStrategy.similaritySearchFunction()
	vs := ss.vectorStore
	columns := append(vs.metadataColumns, vs.contentColumn)
	if ss.vectorStore.metadataJsonColumn != "" {
		columns = append(columns, ss.vectorStore.metadataJsonColumn)
	}
	columnNames := strings.Join(columns, `, `)
	whereClause := ""
	if ss.criteria.filter != nil {
		whereClause = fmt.Sprintf("WHERE %s", ss.criteria.filter)
	}
	stmt := fmt.Sprintf(`
        SELECT %s, %s(%s, '%s') AS distance FROM "%s"."%s" %s ORDER BY %s %s '%s' LIMIT %d;`,
		columnNames, searchFunction, vs.embeddingColumn, vectorToString(embedding), vs.schemaName, vs.tableName,
		whereClause, vs.embeddingColumn, operator, vectorToString(embedding), ss.criteria.count)

	return stmt
}

func (ds *docStore) query(ctx context.Context, ss SimilaritySearch, embbeding []float32) (*ai.RetrieverResponse, error) {
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

		meta := make(map[string]any, ss.criteria.count)
		var content []*ai.Part
		for i, col := range columnNames {
			if (len(ss.vectorStore.metadataColumns) > 0 && !slices.Contains(ss.vectorStore.metadataColumns, col)) &&
				ss.vectorStore.contentColumn != col &&
				ss.vectorStore.metadataJsonColumn != col {
				continue
			}

			if ss.vectorStore.contentColumn == col {
				content = append(content, ai.NewTextPart(values[i].(string)))
			}

			if ss.vectorStore.metadataJsonColumn == col {
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

// newDocStore instantiate a docStore
func newDocStore(ctx context.Context, engine *engine, cfg Config) (*docStore, error) {

	if cfg.Name == "" {
		return nil, errors.New("name is empty")
	}
	if cfg.Embedder == nil {
		return nil, errors.New("embedder is required")
	}

	return &docStore{
		engine:          engine,
		embedder:        cfg.Embedder,
		embedderOptions: cfg.EmbedderOptions,
	}, nil
}

type RetrieverOptions struct {
	SimilaritySearch SimilaritySearch
}

func (ds *docStore) Retrieve(ctx context.Context, req *ai.RetrieverRequest) (*ai.RetrieverResponse, error) {
	if req.Options == nil {
		vs, _ := NewVectorStore()
		crt := &Criteria{
			filter:           "",
			count:            defaultCount,
			distanceStrategy: defaultDistanceStrategy,
		}
		req.Options = &RetrieverOptions{SimilaritySearch: SimilaritySearch{vectorStore: vs, criteria: crt}}
	}

	ropt, ok := req.Options.(*RetrieverOptions)
	if !ok {
		return nil, fmt.Errorf("googlecloudsql.postgres.Retrieve options have type %T, want %T", req.Options, &RetrieverOptions{})
	}

	if ropt.SimilaritySearch.vectorStore == nil {
		vs, _ := NewVectorStore()
		ropt.SimilaritySearch.vectorStore = vs
	}

	if ropt.SimilaritySearch.criteria == nil {
		ropt.SimilaritySearch.criteria = &Criteria{
			filter:           "",
			count:            defaultCount,
			distanceStrategy: defaultDistanceStrategy,
		}
	}

	ereq := &ai.EmbedRequest{
		Documents: []*ai.Document{req.Query},
		Options:   ds.embedderOptions,
	}
	eres, err := ds.embedder.Embed(ctx, ereq)
	if err != nil {
		return nil, fmt.Errorf("googlecloudsql.postgres.Retrieve retrieve embedding failed: %v", err)
	}
	res, err := ds.query(ctx, ropt.SimilaritySearch, eres.Embeddings[0].Embedding)
	if err != nil {
		return nil, fmt.Errorf("googlecloudsql.postgres.Retrieve failed to execute the query: %v", err)
	}
	return res, nil
}

// Index implements the genkit Retriever.Index method.
func (ds *docStore) Index(ctx context.Context, req *ai.IndexerRequest) error {
	if len(req.Documents) == 0 {
		return nil
	}
	//TODO: implement method
	return nil
}
