package postgresql

import (
	"context"

	"github.com/firebase/genkit/go/ai"
)

// RetrieverOptions options for retriever
type RetrieverOptions struct {
}

// Retrieve returns the result of the query
func (p *Postgres) Retrieve(ctx context.Context, req *ai.RetrieverRequest) (*ai.RetrieverResponse, error) {
	// TODO: implement
	return nil, nil
}
