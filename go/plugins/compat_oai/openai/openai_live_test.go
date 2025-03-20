package openai_test

import (
	"context"
	"flag"
	"strings"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/compat_oai/openai"
)

var (
	apiKey = flag.String("apikey", "", "OpenAI API key")
)

func TestLive(t *testing.T) {
	if *apiKey == "" {
		t.Skip("no -apikey provided")
	}

	ctx := context.Background()

	// Initialize genkit with GPT-4o-min as default model
	g, err := genkit.Init(context.Background(), genkit.WithDefaultModel("openai/gpt-4o-mini"))
	if err != nil {
		t.Fatal(err)
	}

	// Initialize the OpenAI plugin
	err = openai.Init(ctx, g, &openai.Config{APIKey: *apiKey})
	if err != nil {
		t.Fatal(err)
	}

	t.Run("basic completion", func(t *testing.T) {
		resp, err := genkit.Generate(ctx, g,
			ai.WithTextPrompt("What is the capital of France?"),
		)
		if err != nil {
			t.Fatal(err)
		}

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
	})

	t.Run("tool usage", func(t *testing.T) {
		// TODO: Implement tool usage
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
	})

	t.Run("multi-turn conversation", func(t *testing.T) {
		// TODO: Implement multi-turn conversation
	})
}
