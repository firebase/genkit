package postgres

import (
	"context"
	"github.com/firebase/genkit/go/genkit"
	"testing"
)

func TestInit_AlreadyCalled(t *testing.T) {
	t.Skip("for local test. work in progress")
	ctx := context.Background()
	cfg := EngineConfig{}

	defer func() {
		if r := recover(); r == nil {
			t.Error("panic not called")
		}
	}()
	gcsp := &GoogleCloudSQLPostgres{Config: cfg}
	_ = gcsp.Init(ctx, &genkit.Genkit{})
	_ = gcsp.Init(ctx, &genkit.Genkit{})

}
