package alloydb

import (
	"context"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/stretchr/testify/require"
)

func TestIndex_Success_NoDocuments(t *testing.T) {
	ds := docStore{}
	err := ds.Index(context.Background(), &ai.IndexerRequest{})
	require.NoError(t, err)

}

func TestIndex_Fail_EmbedReturnError(t *testing.T) {
	ds := docStore{
		config: &Config{Embedder: mockEmbedderFail{}},
	}
	req := &ai.IndexerRequest{
		Documents: []*ai.Document{{
			Content: []*ai.Part{{
				Kind:        ai.PartText,
				ContentType: "text/plain",
				Text:        "This is a test",
			}},
			Metadata: nil,
		}},
		Options: nil}

	err := ds.Index(context.Background(), req)
	require.Error(t, err)
}
