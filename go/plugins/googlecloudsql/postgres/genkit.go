package postgres

import (
	"context"
	"errors"
	"fmt"
	"sync"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
)

// The provider used in the registry.
const provider = "googlecloudsql-postgres"

// GoogleCloudSQLPostgres holds the current plugin state.
type GoogleCloudSQLPostgres struct {
	Config      EngineConfig
	mu          sync.Mutex
	initialized bool
	engine      *engine
}

func (gcsp *GoogleCloudSQLPostgres) Name() string {
	return provider
}

// Init initialize the Cloud SQL for PostgreSQL
func (gcsp *GoogleCloudSQLPostgres) Init(ctx context.Context, g *genkit.Genkit) error {
	gcsp.mu.Lock()
	defer gcsp.mu.Unlock()
	if gcsp.initialized {
		panic("googlecloudsql.postgres.Init already initialized")
	}

	e, err := newEngine(ctx, gcsp.Config)
	if err != nil {
		return fmt.Errorf("googlecloudsql.postgres.Init failed to populate config %v", err)
	}

	gcsp.engine = e
	gcsp.initialized = true
	return nil

}

type docStore struct {
	engine          *engine
	embedder        ai.Embedder
	embedderOptions any
}

// newDocStore instantiate a docStore
func (gcsp *GoogleCloudSQLPostgres) newDocStore(ctx context.Context, cfg Config) (*docStore, error) {
	gcsp.mu.Lock()
	defer gcsp.mu.Unlock()
	if !gcsp.initialized {
		panic("googlecloudsql.postgres.Init not called")
	}
	if cfg.Name == "" {
		return nil, errors.New("name is empty")
	}
	if cfg.Embedder == nil {
		return nil, errors.New("embedder is required")
	}

	return &docStore{
		engine:          gcsp.engine,
		embedder:        cfg.Embedder,
		embedderOptions: cfg.EmbedderOptions,
	}, nil
}

// Config provides configuration options for [DefineIndexer] and [DefineRetriever].
type Config struct {
	Name            string      // Name to use.
	Embedder        ai.Embedder // Embedder to use. Required.
	EmbedderOptions any         // Options to pass to the embedder.
}

// DefineRetriever defines a Retriever with the given configuration.
func DefineRetriever(ctx context.Context, g *genkit.Genkit, cfg Config) (ai.Retriever, error) {
	gcsp := genkit.LookupPlugin(g, provider).(*GoogleCloudSQLPostgres)
	if gcsp == nil {
		return nil, errors.New("google cloud sql for postgres plugin not found; did you call genkit.Init with the pinecone plugin?")
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
	gcsp := genkit.LookupPlugin(g, provider).(*GoogleCloudSQLPostgres)
	if gcsp == nil {
		return nil, errors.New("google cloud sql for postgres plugin not found; did you call genkit.Init with the pinecone plugin?")
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
