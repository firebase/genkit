// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package vertexai_test

import (
	"context"
	"flag"
	"math"
	"strings"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/vertexai"
)

// The tests here only work with a project set to a valid value.
// The user running these tests must be authenticated, for example by
// setting a valid GOOGLE_APPLICATION_CREDENTIALS environment variable.
var projectID = flag.String("projectid", "", "VertexAI project")
var location = flag.String("location", "us-central1", "geographic location")

func TestLive(t *testing.T) {
	if *projectID == "" {
		t.Skipf("no -projectid provided")
	}
	ctx := context.Background()
	g, err := genkit.Init(context.Background(), genkit.WithDefaultModel("vertexai/gemini-1.5-flash"))
	if err != nil {
		t.Fatal(err)
	}
	err = vertexai.Init(ctx, g, &vertexai.Config{ProjectID: *projectID, Location: *location})
	if err != nil {
		t.Fatal(err)
	}
	embedder := vertexai.Embedder(g, "textembedding-gecko@003")

	gablorkenTool := genkit.DefineTool(g, "gablorken", "use when need to calculate a gablorken",
		func(ctx *ai.ToolContext, input struct {
			Value float64
			Over  float64
		}) (float64, error) {
			return math.Pow(input.Value, input.Over), nil
		},
	)
	t.Run("model", func(t *testing.T) {
		resp, err := genkit.Generate(ctx, g, ai.WithTextPrompt("Which country was Napoleon the emperor of?"))
		if err != nil {
			t.Fatal(err)
		}
		out := resp.Message.Content[0].Text
		if !strings.Contains(out, "France") {
			t.Errorf("got \"%s\", expecting it would contain \"France\"", out)
		}
		if resp.Request == nil {
			t.Error("Request field not set properly")
		}
		if resp.Usage.InputTokens == 0 || resp.Usage.OutputTokens == 0 || resp.Usage.TotalTokens == 0 {
			t.Errorf("Empty usage stats %#v", *resp.Usage)
		}
	})
	t.Run("streaming", func(t *testing.T) {
		out := ""
		parts := 0
		final, err := genkit.Generate(ctx, g,
			ai.WithTextPrompt("Write one paragraph about the Golden State Warriors."),
			ai.WithStreaming(func(ctx context.Context, c *ai.ModelResponseChunk) error {
				parts++
				for _, p := range c.Content {
					out += p.Text
				}
				return nil
			}))
		if err != nil {
			t.Fatal(err)
		}
		out2 := ""
		for _, p := range final.Message.Content {
			out2 += p.Text
		}
		if out != out2 {
			t.Errorf("streaming and final should contain the same text.\nstreaming:%s\nfinal:%s", out, out2)
		}
		const want = "Golden"
		if !strings.Contains(out, want) {
			t.Errorf("got %q, expecting it to contain %q", out, want)
		}
		if parts == 1 {
			// Check if streaming actually occurred.
			t.Errorf("expecting more than one part")
		}
		if final.Usage.InputTokens == 0 || final.Usage.OutputTokens == 0 || final.Usage.TotalTokens == 0 {
			// TODO: vertexai client doesn't return stats in streaming mode.
			//t.Errorf("Empty usage stats %#v", *final.Usage)
		}
	})
	t.Run("tool", func(t *testing.T) {
		resp, err := genkit.Generate(ctx, g,
			ai.WithTextPrompt("what is a gablorken of 2 over 3.5?"),
			ai.WithTools(gablorkenTool))
		if err != nil {
			t.Fatal(err)
		}

		out := resp.Message.Content[0].Text
		if !strings.Contains(out, "12.25") {
			t.Errorf("got %s, expecting it to contain \"12.25\"", out)
		}
	})
	t.Run("embedder", func(t *testing.T) {
		res, err := ai.Embed(ctx, embedder, ai.WithEmbedDocs(
			ai.DocumentFromText("time flies like an arrow", nil),
			ai.DocumentFromText("fruit flies like a banana", nil),
		))
		if err != nil {
			t.Fatal(err)
		}

		// There's not a whole lot we can test about the result.
		// Just do a few sanity checks.
		for _, de := range res.Embeddings {
			out := de.Embedding
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
		}
	})
}
