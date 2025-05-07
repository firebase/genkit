package postgresql

import (
	"context"
	"errors"
	"fmt"
	"strings"
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
	config  Config
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

	if p.engine.Pool == nil {
		panic("postgres.Init engine has no pool")
	}

	if strings.TrimSpace(p.config.TableName) == "" {
		panic("table name must be defined")
	}

	if p.config.SchemaName == "" {
		p.config.SchemaName = defaultSchemaName
	}
	if p.config.SchemaName == "" {
		p.config.SchemaName = defaultSchemaName
	}
	if p.config.IDColumn == "" {
		p.config.IDColumn = defaultIDColumn
	}
	if p.config.MetadataJSONColumn == "" {
		p.config.MetadataJSONColumn = defaultMetadataJsonColumn
	}
	if p.config.ContentColumn == "" {
		p.config.ContentColumn = defaultContentColumn
	}
	if p.config.EmbeddingColumn == "" {
		p.config.EmbeddingColumn = defaultEmbeddingColumn
	}

	if p.config.Embedder == nil {
		return fmt.Errorf("embedder is required")
	}

	if err := p.validate(ctx); err != nil {
		return err
	}

	p.initted = true
	return nil

}

func (p *Postgres) validate(ctx context.Context) error {
	stmt := fmt.Sprintf("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '%s' AND table_schema = '%s'", p.config.TableName, p.config.SchemaName)
	rows, err := p.engine.Pool.Query(ctx, stmt)
	if err != nil {
		return err
	}

	mapColumnNameDataType := make(map[string]string)

	for rows.Next() {
		var columnName, dataType string
		if err := rows.Scan(&columnName, &dataType); err != nil {
			return err
		}
		mapColumnNameDataType[columnName] = dataType
	}

	if _, ok := mapColumnNameDataType[p.config.IDColumn]; !ok {
		return fmt.Errorf("id column '%s' does not exist", p.config.IDColumn)
	}

	ccdt, ok := mapColumnNameDataType[p.config.ContentColumn]
	if !ok {
		return fmt.Errorf("content column '%s' does not exist", p.config.ContentColumn)
	}

	if ccdt != "text" && strings.Contains(ccdt, "char") {
		return fmt.Errorf("content column '%s' is type '%s'. must be a type of character string", p.config.ContentColumn, ccdt)
	}

	ecdt, ok := mapColumnNameDataType[p.config.EmbeddingColumn]
	if !ok {
		return fmt.Errorf("content column '%s' does not exist", p.config.ContentColumn)
	}

	if ecdt != "USER-DEFINED" {
		return fmt.Errorf("content column '%s' must be a type vector", p.config.ContentColumn)
	}

	for _, mc := range p.config.MetadataColumns {
		if _, ok = mapColumnNameDataType[mc]; !ok {
			return fmt.Errorf("metadata column '%s' does not exist", mc)
		}
	}

	return nil

}

// Config provides configuration options for [DefineIndexer] and [DefineRetriever].
type Config struct {
	TableName          string
	SchemaName         string
	ContentColumn      string
	EmbeddingColumn    string
	MetadataColumns    []string
	IDColumn           string
	MetadataJSONColumn string

	Embedder        ai.Embedder // Embedder to use. Required.
	EmbedderOptions any         // Options to pass to the embedder.
}

// DefineRetriever defines a Retriever with the given configuration.
func DefineRetriever(ctx context.Context, g *genkit.Genkit) (ai.Retriever, error) {
	p := genkit.LookupPlugin(g, provider).(*Postgres)
	if p == nil {
		return nil, errors.New("google cloud sql for postgres plugin not found; call genkit.Init with the google cloud sql for postgres plugin")
	}
	return genkit.DefineRetriever(g, provider, p.config.TableName, p.Retrieve), nil
}

func DefineIndexer(ctx context.Context, g *genkit.Genkit) (ai.Indexer, error) {
	p := genkit.LookupPlugin(g, provider).(*Postgres)
	if p == nil {
		return nil, errors.New("google cloud sql for postgres plugin not found; call genkit.Init with the google cloud sql for postgres plugin")
	}

	return genkit.DefineIndexer(g, provider, p.config.TableName, p.Index), nil
}

// Indexer returns the indexer with the given index name.
func Indexer(g *genkit.Genkit, name string) ai.Indexer {
	return genkit.LookupIndexer(g, provider, name)
}

// Retriever returns the retriever with the given index name.
func Retriever(g *genkit.Genkit, name string) ai.Retriever {
	return genkit.LookupRetriever(g, provider, name)
}
