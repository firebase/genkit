package postgresql

import (
	"context"
	"flag"
	"strings"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/internal/fakeembedder"
)

var testUsername = flag.String("test-postgres_user", "", "postgres username for tests")
var testPassword = flag.String("test-postgres_password", "", "postgres password  for tests")
var testDatabase = flag.String("test-postgres-database", "", "postgres database")
var testProjectID = flag.String("test-postgres-project-id", "", "postgres project id  for tests")
var testRegion = flag.String("test-postgres-region", "", "postgres region for tests")
var testInstance = flag.String("test-postgres-instance", "", "postgres instance for tests")
var testIAMEmail = flag.String("test-postgres-iam-email", "", "postgres instance for tests")

func TestInit_NoConnectionPool(t *testing.T) {
	ctx := context.Background()
	cfg := engineConfig{}
	engine := &PostgresEngine{Pool: cfg.connPool}
	defer func() {
		if r := recover(); r == nil {
			t.Error("panic not called")
		}
	}()
	gcsp := &Postgres{engine: engine}
	_ = gcsp.Init(ctx, &genkit.Genkit{})
}

func TestInit_AlreadyCalled(t *testing.T) {
	ctx := context.Background()

	pEngine, err := NewPostgresEngine(ctx,
		WithUser(*testUsername),
		WithPassword(*testPassword),
		WithCloudSQLInstance(*testProjectID, *testRegion, *testInstance),
		WithDatabase(*testDatabase),
		WithIAMAccountEmail(*testIAMEmail))

	if err != nil {
		t.Fatal(err)
	}

	defer func() {
		if r := recover(); r == nil {
			t.Error("panic not called")
		}
	}()

	g := &genkit.Genkit{}

	gcsp := &Postgres{engine: pEngine}
	g, err = genkit.Init(ctx, genkit.WithPlugins(gcsp))

	err = gcsp.Init(ctx, g)
	if err == nil {
		t.Fatal("must fail if init is called twice")
	}

}

func TestPostgres(t *testing.T) {
	if !areValidFlags() {
		t.Skip("no valid postgres flags")
	}

	ctx := context.Background()

	//embedder := newFakeEmbedder()

	pEngine, err := NewPostgresEngine(ctx,
		WithUser(*testUsername),
		WithPassword(*testPassword),
		WithCloudSQLInstance(*testProjectID, *testRegion, *testInstance),
		WithDatabase(*testDatabase),
		WithIAMAccountEmail(*testIAMEmail))

	if err != nil {
		t.Fatal(err)
	}

	postgres := &Postgres{
		engine: pEngine,
	}

	g, err := genkit.Init(ctx, genkit.WithPlugins(postgres))
	if err != nil {
		t.Fatal(err)
	}

	cfg := &Config{
		TableName:             "my-documents",
		SchemaName:            "public",
		ContentColumn:         "content",
		EmbeddingColumn:       "embedding",
		MetadataColumns:       []string{"source", "category"},
		IDColumn:              "custom_id",
		MetadataJSONColumn:    "metadata",
		IgnoreMetadataColumns: []string{"created_at", "updated_at"},
		Embedder:              nil,
		EmbedderOptions:       nil,
	}

	indexer, err := DefineIndexer(ctx, g, cfg)
	if err != nil {
		t.Fatal(err)
	}

	indexer.Name()

	retriever, err := DefineRetriever(ctx, g, cfg)
	if err != nil {
		t.Fatal(err)
	}

	retriever.Name()

}

/** ***************
Helper functions
************** */

func newFakeEmbedder() *fakeembedder.Embedder {
	const dim = 768

	v1 := make([]float32, dim)
	v2 := make([]float32, dim)
	v3 := make([]float32, dim)
	for i := range v1 {
		v1[i] = float32(i)
		v2[i] = float32(i)
		v3[i] = float32(dim - i)
	}
	v2[0] = 1

	d1 := ai.DocumentFromText("hello1", map[string]any{"name": "hello1"})
	d2 := ai.DocumentFromText("hello2", map[string]any{"name": "hello2"})
	d3 := ai.DocumentFromText("goodbye", map[string]any{"name": "goodbye"})

	embedder := fakeembedder.New()
	embedder.Register(d1, v1)
	embedder.Register(d2, v2)
	embedder.Register(d3, v3)

	return embedder
}

func areValidFlags() bool {
	isBasicAuth := testUsername != nil && strings.TrimSpace(*testUsername) != "" &&
		testPassword != nil && strings.TrimSpace(*testPassword) != ""

	isIAMAuth := testIAMEmail != nil && strings.TrimSpace(*testIAMEmail) != ""

	isPostgresEnv := testDatabase != nil && strings.TrimSpace(*testDatabase) != "" &&
		testProjectID != nil && strings.TrimSpace(*testProjectID) != "" &&
		testRegion != nil && strings.TrimSpace(*testRegion) != "" &&
		testInstance != nil && strings.TrimSpace(*testInstance) != ""

	return (isBasicAuth || isIAMAuth) && isPostgresEnv
}
