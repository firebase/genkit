package alloydb

import (
	"context"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestRetriever_Fail_WrongTypeOfOption(t *testing.T) {
	ds := docStore{}
	res, err := ds.Retrieve(context.Background(), &ai.RetrieverRequest{Options: struct{}{}})
	require.Nil(t, res)
	require.Error(t, err)
	assert.ErrorContains(t, err, "postgres.Retrieve options have type")
}

func TestRetriever_Fail_EmbedReturnError(t *testing.T) {
	ds := docStore{
		config: &Config{Embedder: mockEmbedderFail{}},
	}
	res, err := ds.Retrieve(context.Background(), &ai.RetrieverRequest{})
	require.Nil(t, res)
	require.Error(t, err)
}
