package postgresql

import (
	"context"
	"errors"
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
	engine  PostgresEngine
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
func DefineRetriever(ctx context.Context, g *genkit.Genkit, cfg *Config) (ai.Retriever, error) {
	p := genkit.LookupPlugin(g, provider).(*Postgres)
	if p == nil {
		return nil, errors.New("postgres plugin not found; call genkit.Init with postgres plugin")
	}

	ds, err := newDocStore(ctx, p, cfg)
	if err != nil {
		return nil, err
	}

	return genkit.DefineRetriever(g, provider, ds.config.TableName, ds.Retrieve), nil
}

// DefineIndexer defines an Indexer with the given configuration.
func DefineIndexer(ctx context.Context, g *genkit.Genkit, cfg *Config) (ai.Indexer, error) {
	p := genkit.LookupPlugin(g, provider).(*Postgres)
	if p == nil {
		return nil, errors.New(" postgres plugin not found; call genkit.Init with postgres plugin")
	}
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
