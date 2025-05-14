package postgresql

import (
	"context"
	"errors"

	"github.com/firebase/genkit/go/ai"
)

type mockEmbedderFail struct{}

func (m mockEmbedderFail) Name() string { return "mock" }
func (m mockEmbedderFail) Embed(ctx context.Context, req *ai.EmbedRequest) (*ai.EmbedResponse, error) {
	return nil, errors.New("mock fail")
}
