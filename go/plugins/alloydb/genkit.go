package alloydb

import (
	"context"
	"fmt"
	"sync"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
)

// The provider used in the registry.
const provider = "postgres"

// Postgres holds the current plugin state.
type Postgres struct {
	mu      sync.Mutex
	initted bool
	engine  *PostgresEngine
}

func (p *Postgres) Name() string {
	return provider
}

// Init initialize the PostgreSQL
func (p *Postgres) Init(ctx context.Context, g *genkit.Genkit) error {
	p.mu.Lock()
	defer p.mu.Unlock()
	if p.initted {
		panic("postgres.Init already initted")
	}

	if p.engine == nil {
		panic("postgres.Init engine is nil")
	}

	if p.engine.Pool == nil {
		panic("postgres.Init engine has no pool")
	}
	p.initted = true
	return nil

}

// Config provides configuration options for [DefineIndexer] and [DefineRetriever].
type Config struct {
	TableName             string
	SchemaName            string
	ContentColumn         string
	EmbeddingColumn       string
	MetadataColumns       []string
	IDColumn              string
	MetadataJSONColumn    string
	IgnoreMetadataColumns []string

	Embedder        ai.Embedder // Embedder to use. Required.
	EmbedderOptions any         // Options to pass to the embedder.
}

// DefineRetriever defines a Retriever with the given configuration.
func DefineRetriever(ctx context.Context, g *genkit.Genkit, p *Postgres, cfg *Config) (ai.Retriever, error) {
	ds, err := newDocStore(ctx, p, cfg)
	if err != nil {
		return nil, err
	}

	return genkit.DefineRetriever(g, provider, ds.config.TableName, ds.Retrieve), nil
}

// DefineIndexer defines an Indexer with the given configuration.
func DefineIndexer(ctx context.Context, g *genkit.Genkit, p *Postgres, cfg *Config) (ai.Indexer, error) {
	ds, err := newDocStore(ctx, p, cfg)
	if err != nil {
		return nil, err
	}

	return genkit.DefineIndexer(g, provider, ds.config.TableName, ds.Index), nil
}

// Indexer returns the indexer with the given index name.
func Indexer(g *genkit.Genkit, name string) ai.Indexer {
	return genkit.LookupIndexer(g, provider, name)
}

// Retriever returns the retriever with the given index name.
func Retriever(g *genkit.Genkit, name string) ai.Retriever {
	return genkit.LookupRetriever(g, provider, name)
}

/* +++++++++++++++++++++++
		Advance methods
 +++++++++++++++++++++++++ */

// ApplyVectorIndex creates an index in the table of the embeddings.
func (p *Postgres) ApplyVectorIndex(ctx context.Context, config *Config, index BaseIndex, name string, concurrently bool) error {
	if !p.initted {
		panic("postgres.ApplyVectorIndex not initted")
	}

	if index.indexType == "exactnearestneighbor" {
		return p.DropVectorIndex(ctx, config, name)
	}

	filter := ""
	if len(index.partialIndexes) > 0 {
		filter = fmt.Sprintf("WHERE %s", index.partialIndexes)
	}
	optsString := index.indexOptions()
	params := fmt.Sprintf("WITH %s", optsString)

	if name == "" {
		if index.name == "" {
			index.name = config.TableName + defaultIndexNameSuffix
		}
		name = index.name
	}

	concurrentlyStr := ""
	if concurrently {
		concurrentlyStr = "CONCURRENTLY"
	}

	function := index.distanceStrategy.searchFunction()
	stmt := fmt.Sprintf(`CREATE INDEX %s %s ON "%s"."%s" USING %s (%s %s) %s %s`,
		concurrentlyStr, name, config.SchemaName, config.TableName, index.indexType, config.EmbeddingColumn, function, params, filter)

	_, err := p.engine.Pool.Exec(ctx, stmt)
	if err != nil {
		return fmt.Errorf("failed to execute creation of index: %w", err)
	}

	return nil
}

// ReIndex recreates the index on the table.
func (p *Postgres) ReIndex(ctx context.Context, config *Config) error {
	if !p.initted {
		panic("postgres.ApplyVectorIndex not initted")
	}
	indexName := config.TableName + defaultIndexNameSuffix
	return p.ReIndexWithName(ctx, indexName)
}

// ReIndexWithName recreates the index on the table by name.
func (p *Postgres) ReIndexWithName(ctx context.Context, indexName string) error {
	if !p.initted {
		panic("postgres.ApplyVectorIndex not initted")
	}
	query := fmt.Sprintf("REINDEX INDEX %s;", indexName)
	_, err := p.engine.Pool.Exec(ctx, query)
	if err != nil {
		return fmt.Errorf("failed to reindex: %w", err)
	}

	return nil
}

// DropVectorIndex drops the vector index from the table.
func (p *Postgres) DropVectorIndex(ctx context.Context, config *Config, indexName string) error {
	if !p.initted {
		panic("postgres.ApplyVectorIndex not initted")
	}
	if indexName == "" {
		indexName = config.TableName + defaultIndexNameSuffix
	}
	query := fmt.Sprintf("DROP INDEX IF EXISTS %s;", indexName)
	_, err := p.engine.Pool.Exec(ctx, query)
	if err != nil {
		return fmt.Errorf("failed to drop vector index: %w", err)
	}

	return nil
}

// IsValidIndex checks if index exists in the table.
func (p *Postgres) IsValidIndex(ctx context.Context, config *Config, indexName string) (bool, error) {
	if !p.initted {
		panic("postgres.ApplyVectorIndex not initted")
	}
	if indexName == "" {
		indexName = config.TableName + defaultIndexNameSuffix
	}
	query := fmt.Sprintf("SELECT tablename, indexname  FROM pg_indexes WHERE tablename = '%s' AND schemaname = '%s' AND indexname = '%s';",
		config.TableName, config.SchemaName, indexName)
	var tableName, indexNameFromDB string
	if err := p.engine.Pool.QueryRow(ctx, query).Scan(&tableName, &indexNameFromDB); err != nil {
		return false, fmt.Errorf("failed to check if index exists: %w", err)
	}

	return indexNameFromDB == indexName, nil
}
