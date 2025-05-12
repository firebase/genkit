package postgresql

import (
	"context"
	"testing"

	"github.com/firebase/genkit/go/genkit"
)

func TestInit_AlreadyCalled(t *testing.T) {
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
	_ = gcsp.Init(ctx, &genkit.Genkit{})

}
