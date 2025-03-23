package openai_test

import (
	"context"
	"os"
	"strings"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/plugins/compat_oai/openai"
	openaiClient "github.com/openai/openai-go"
	"github.com/openai/openai-go/option"
	"github.com/stretchr/testify/assert"
)

const defaultModel = "gpt-4o-mini"

func setupTestClient(t *testing.T) *openai.ModelGenerator {
	apiKey := os.Getenv("OPENAI_API_KEY")
	if apiKey == "" {
		t.Skip("Skipping test: OPENAI_API_KEY environment variable not set")
	}

	client := openaiClient.NewClient(option.WithAPIKey(apiKey))
	return openai.NewModelGenerator(client, defaultModel)
}

func TestGenerator_Complete(t *testing.T) {
	g := setupTestClient(t)

	// define case with user and model messages
	messages := []*ai.Message{
		{
			Role: ai.RoleUser,
			Content: []*ai.Part{
				ai.NewTextPart("Tell me a joke"),
			},
		},
		{
			Role: ai.RoleModel,
			Content: []*ai.Part{
				ai.NewTextPart("Why did the scarecrow win an award?"),
			},
		},
		{
			Role: ai.RoleUser,
			Content: []*ai.Part{
				ai.NewTextPart("Why?"),
			},
		},
	}

	resp, err := g.WithMessages(messages).Generate(context.Background(), nil)
	assert.NoError(t, err)
	assert.NotEmpty(t, resp.Message.Content)
	assert.Equal(t, ai.RoleModel, resp.Message.Role)

	t.Log("\n=== Simple Completion Response ===")
	for _, part := range resp.Message.Content {
		t.Logf("Content: %s", part.Text)
	}
}

func TestGenerator_Stream(t *testing.T) {
	g := setupTestClient(t)

	messages := []*ai.Message{
		{
			Role: ai.RoleUser,
			Content: []*ai.Part{
				ai.NewTextPart("Count from 1 to 3"),
			},
		},
	}

	var chunks []string
	handleChunk := func(ctx context.Context, chunk *ai.ModelResponseChunk) error {
		for _, part := range chunk.Content {
			chunks = append(chunks, part.Text)

			// log each chunk as it arrives
			t.Logf("Chunk: %s", part.Text)
		}
		return nil
	}

	_, err := g.WithMessages(messages).Generate(context.Background(), handleChunk)
	assert.NoError(t, err)
	assert.NotEmpty(t, chunks)

	// Verify we got the full response
	fullText := strings.Join(chunks, "")
	assert.Contains(t, fullText, "1")
	assert.Contains(t, fullText, "2")
	assert.Contains(t, fullText, "3")

	t.Log("\n=== Full Streaming Response ===")
	t.Log(strings.Join(chunks, ""))
}
