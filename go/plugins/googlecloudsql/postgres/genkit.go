package postgres

import (
	"context"
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
		return nil, fmt.Errorf("google cloud sql for postgres plugin not found. call genkit.Init with the googlecloudsql-postgres plugin")
	}

	ds, err := newDocStore(ctx, gcsp.engine, cfg)
	if err != nil {
		return nil, err
	}
	return genkit.DefineRetriever(g, provider, cfg.Name, ds.Retrieve), nil
}

func DefineIndexer(ctx context.Context, g *genkit.Genkit, cfg Config) (ai.Indexer, error) {
	gcsp := genkit.LookupPlugin(g, provider).(*GoogleCloudSQLPostgres)
	if gcsp == nil {
		return nil, fmt.Errorf("google cloud sql for postgres plugin not found. call genkit.Init with the googlecloudsql-postgres plugin")
	}

	ds, err := newDocStore(ctx, gcsp.engine, cfg)
	if err != nil {
		return nil, err
	}
	return genkit.DefineIndexer(g, provider, cfg.Name, ds.Index), nil
}
