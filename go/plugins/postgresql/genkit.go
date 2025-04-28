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

type docStore struct {
	engine          PostgresEngine
	embedder        ai.Embedder
	embedderOptions any
}

// Config provides configuration options for [DefineIndexer] and [DefineRetriever].
type Config struct {
	Name            string
	TableName       string
	SchemaName      string
	ContentColumn   string
	EmbeddingColumn string
	MetadataColumns []string
	Embedder        ai.Embedder // Embedder to use. Required.
	EmbedderOptions any         // Options to pass to the embedder.
}

// newDocStore instantiate a docStore
func (p *Postgres) newDocStore(ctx context.Context, cfg Config) (*docStore, error) {
	p.mu.Lock()
	defer p.mu.Unlock()
	if !p.initted {
		panic("postgres.Init not called")
	}
	if cfg.Name == "" {
		return nil, errors.New("name is empty")
	}
	if cfg.Embedder == nil {
		return nil, errors.New("embedder is required")
	}

	if cfg.SchemaName == "" {
		cfg.SchemaName = defaultSchemaName
	}

	if cfg.TableName == "" {
		return nil, errors.New("table name is required")
	}

	return &docStore{
		engine:          p.engine,
		embedder:        cfg.Embedder,
		embedderOptions: cfg.EmbedderOptions,
	}, nil
}

// DefineRetriever defines a Retriever with the given configuration.
func DefineRetriever(ctx context.Context, g *genkit.Genkit, cfg Config) (ai.Retriever, error) {
	gcsp := genkit.LookupPlugin(g, provider).(*Postgres)
	if gcsp == nil {
		return nil, errors.New("google cloud sql for postgres plugin not found; did you call genkit.Init with the google cloud sql for postgres plugin?")
	}

	ds, err := gcsp.newDocStore(ctx, cfg)
	if err != nil {
		return nil, err
	}
	return genkit.DefineRetriever(g, provider, cfg.Name, ds.Retrieve), nil
}

func (ds *docStore) Retrieve(ctx context.Context, req *ai.RetrieverRequest) (*ai.RetrieverResponse, error) {
	//TODO: implement method
	return nil, nil
}

func DefineIndexer(ctx context.Context, g *genkit.Genkit, cfg Config) (ai.Indexer, error) {
	gcsp := genkit.LookupPlugin(g, provider).(*Postgres)
	if gcsp == nil {
		return nil, errors.New(" google cloud sql for postgres plugin not found; did you call genkit.Init with the google cloud sql for postgres plugin?")
	}

	ds, err := gcsp.newDocStore(ctx, cfg)
	if err != nil {
		return nil, err
	}
	return genkit.DefineIndexer(g, provider, cfg.Name, ds.Index), nil
}

// Index implements the genkit Retriever.Index method.
func (ds *docStore) Index(ctx context.Context, req *ai.IndexerRequest) error {
	if len(req.Documents) == 0 {
		return nil
	}
	//TODO: implement method
	return nil
}

// Indexer returns the indexer with the given index name.
func Indexer(g *genkit.Genkit, name string) ai.Indexer {
	return genkit.LookupIndexer(g, provider, name)
}

// Retriever returns the retriever with the given index name.
func Retriever(g *genkit.Genkit, name string) ai.Retriever {
	return genkit.LookupRetriever(g, provider, name)
}
