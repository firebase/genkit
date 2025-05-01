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

func NewPostgres(engine PostgresEngine) *Postgres {
	return &Postgres{
		engine: engine,
	}
}

func (p *Postgres) Name() string {
	return provider
}

// Init initialize the Cloud SQL for PostgreSQL
func (p *Postgres) Init(ctx context.Context, g *genkit.Genkit) error {
	p.mu.Lock()
	defer p.mu.Unlock()
	if p.initted {
		panic("postgres.Init already initted")
	}

	// TODO: add validation

	p.initted = true
	return nil

}

// Config provides configuration options for [DefineIndexer] and [DefineRetriever].
type Config struct {
	Name string

	TableName             string
	SchemaName            string
	IDColumn              string
	ContentColumn         string
	EmbeddingColumn       string
	MetadataJsonColumn    string
	MetadataColumns       []string
	IgnoreMetadataColumns []string

	Embedder        ai.Embedder // Embedder to use. Required.
	EmbedderOptions any         // Options to pass to the embedder.
}

// DefineRetriever defines a Retriever with the given configuration.
func DefineRetriever(ctx context.Context, g *genkit.Genkit, cfg Config) (ai.Retriever, error) {
	gcsp := genkit.LookupPlugin(g, provider).(*Postgres)
	if gcsp == nil {
		return nil, errors.New(" google cloud sql for postgres plugin not found; did you call genkit.Init with the google cloud sql for postgres plugin?")
	}

	ds, err := newDocStore(ctx, gcsp, cfg)
	if err != nil {
		return nil, err
	}
	return genkit.DefineRetriever(g, provider, cfg.Name, ds.Retrieve), nil
}

func DefineIndexer(ctx context.Context, g *genkit.Genkit, cfg Config) (ai.Indexer, error) {
	gcsp := genkit.LookupPlugin(g, provider).(*Postgres)
	if gcsp == nil {
		return nil, errors.New(" google cloud sql for postgres plugin not found; did you call genkit.Init with the google cloud sql for postgres plugin?")
	}

	ds, err := newDocStore(ctx, gcsp, cfg)
	if err != nil {
		return nil, err
	}
	return genkit.DefineIndexer(g, provider, cfg.Name, ds.Index), nil
}

// Indexer returns the indexer with the given index name.
func Indexer(g *genkit.Genkit, name string) ai.Indexer {
	return genkit.LookupIndexer(g, provider, name)
}

// Retriever returns the retriever with the given index name.
func Retriever(g *genkit.Genkit, name string) ai.Retriever {
	return genkit.LookupRetriever(g, provider, name)
}
