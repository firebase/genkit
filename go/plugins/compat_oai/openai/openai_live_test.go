package openai_test

import (
	"context"
	"os"
	"strings"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/compat_oai/openai"
	"github.com/openai/openai-go/option"
)

func TestPlugin(t *testing.T) {
	apiKey := os.Getenv("OPENAI_API_KEY")
	if apiKey == "" {
		t.Skip("Skipping test: OPENAI_API_KEY environment variable not set")
	}

	ctx := context.Background()

	// Initialize genkit with GPT-4o-min as default model
	g, err := genkit.Init(context.Background(), genkit.WithDefaultModel("openai/gpt-4o-mini"))
	if err != nil {
		t.Fatal(err)
	}
	t.Log("genkit initialized")

	// Initialize the OpenAI plugin
	apiKeyOption := option.WithAPIKey(apiKey)
	err = openai.OpenAI(ctx, g, apiKeyOption)
	if err != nil {
		t.Fatal(err)
	}
	t.Log("openai plugin initialized")

	t.Run("embedder", func(t *testing.T) {
		embedder := openai.Embedder(g, "text-embedding-3-small")
		res, err := ai.Embed(ctx, embedder, ai.WithEmbedText("yellow banana"))
		if err != nil {
			t.Fatal(err)
		}
		out := res.Embeddings[0].Embedding
		// There's not a whole lot we can test about the result.
		// Just do a few sanity checks.
		if len(out) < 100 {
			t.Errorf("embedding vector looks too short: len(out)=%d", len(out))
		}
		var normSquared float32
		for _, x := range out {
			normSquared += x * x
		}
		if normSquared < 0.9 || normSquared > 1.1 {
			t.Errorf("embedding vector not unit length: %f", normSquared)
		}
	})

	t.Run("basic completion", func(t *testing.T) {
		t.Log("generating basic completion response")
		resp, err := genkit.Generate(ctx, g,
			ai.WithTextPrompt("What is the capital of France?"),
		)
		if err != nil {
			t.Fatal("error generating basic completion response: ", err)
		}
		t.Logf("basic completion response: %+v", resp)

		out := resp.Message.Content[0].Text
		if !strings.Contains(strings.ToLower(out), "paris") {
			t.Errorf("got %q, expecting it to contain 'Paris'", out)
		}

		// Verify usage statistics are present
		if resp.Usage == nil || resp.Usage.TotalTokens == 0 {
			t.Error("Expected non-zero usage statistics")
		}
	})

	t.Run("streaming", func(t *testing.T) {
		var streamedOutput string
		chunks := 0

		final, err := genkit.Generate(ctx, g,
			ai.WithTextPrompt("Write a short paragraph about artificial intelligence."),
			ai.WithStreaming(func(ctx context.Context, chunk *ai.ModelResponseChunk) error {
				chunks++
				for _, content := range chunk.Content {
					streamedOutput += content.Text
				}
				return nil
			}))
		if err != nil {
			t.Fatal(err)
		}

		// Verify streaming worked
		if chunks <= 1 {
			t.Error("Expected multiple chunks for streaming")
		}

		// Verify final output matches streamed content
		finalOutput := ""
		for _, content := range final.Message.Content {
			finalOutput += content.Text
		}
		if streamedOutput != finalOutput {
			t.Errorf("Streaming output doesn't match final output\nStreamed: %s\nFinal: %s",
				streamedOutput, finalOutput)
		}

		t.Logf("streaming response: %+v", finalOutput)
	})

	t.Run("tool usage", func(t *testing.T) {
		// TODO: Implement tool usage
		t.Log("skipping tool usage")
	})

	t.Run("system message", func(t *testing.T) {
		resp, err := genkit.Generate(ctx, g,
			ai.WithTextPrompt("What are you?"),
			ai.WithSystemPrompt("You are a helpful math tutor who loves numbers."),
		)
		if err != nil {
			t.Fatal(err)
		}

		out := resp.Message.Content[0].Text
		if !strings.Contains(strings.ToLower(out), "math") {
			t.Errorf("got %q, expecting response to mention being a math tutor", out)
		}

		t.Logf("system message response: %+v", out)
	})

	t.Run("multi-turn conversation", func(t *testing.T) {
		// TODO: Implement multi-turn conversation
		t.Log("skipping multi-turn conversation")
	})
}
