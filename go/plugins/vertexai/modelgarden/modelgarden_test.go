// Copyright 2025 Google LLC
// SPDX-License-Identifier: Apache-2.0

package modelgarden_test

import (
	"context"
	"flag"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/vertexai/modelgarden"
)

var (
	projectID = flag.String("projectid", "", "Modelgarden project")
	location  = flag.String("location", "us-central1", "Geographic location")
)

func TestModelGarden(t *testing.T) {
	if *projectID == "" {
		t.Skipf("no -projectid provided")
	}

	ctx := context.Background()
	g, err := genkit.New(nil)
	if err != nil {
		t.Fatal(err)
	}

	err = modelgarden.Init(ctx, g, &modelgarden.ModelGardenOptions{
		ProjectID: *projectID,
		Region:    *location,
		Models:    []string{"claude-3-5-sonnet-v2"},
	})
	if err != nil {
		t.Fatal(err)
	}

	t.Run("invalid model", func(t *testing.T) {
		m := modelgarden.Model(g, modelgarden.AnthropicProvider, "claude-not-valid-v2")
		if m != nil {
			t.Fatal("model should have been invalid")
		}
	})

	t.Run("model version ok", func(t *testing.T) {
		m := modelgarden.Model(g, modelgarden.AnthropicProvider, "claude-3-5-sonnet-v2")
		_, err := genkit.Generate(ctx, g,
			ai.WithConfig(&ai.GenerationCommonConfig{
				Temperature: 1,
				Version:     "claude-3-5-sonnet-v2@20241022",
			}),
			ai.WithModel(m),
		)
		if err != nil {
			t.Fatal(err)
		}
	})

	t.Run("model version nok", func(t *testing.T) {
		m := modelgarden.Model(g, modelgarden.AnthropicProvider, "claude-3-5-sonnet-v2")
		_, err := genkit.Generate(ctx, g,
			ai.WithConfig(&ai.GenerationCommonConfig{
				Temperature: 1,
				Version:     "foo",
			}),
			ai.WithModel(m),
		)
		if err == nil {
			t.Fatal("should have failed due wrong model version")
		}
	})

	t.Run("model", func(t *testing.T) {
		m := modelgarden.Model(g, modelgarden.AnthropicProvider, "claude-3-5-sonnet-v2")
		resp, err := genkit.Generate(ctx, g, ai.WithTextPrompt("What's your name?"), ai.WithModel(m))
		if err != nil {
			t.Fatal(err)
		}
		t.Fatal(resp.Message.Content[0].Text)
	})

	t.Run("streaming", func(t *testing.T) {
		m := modelgarden.Model(g, modelgarden.AnthropicProvider, "claude-3-5-sonnet-v2")
		out := ""
		parts := 0

		final, err := genkit.Generate(ctx, g,
			ai.WithTextPrompt("Tell me a short story about a frog and a princess"),
			ai.WithModel(m),
			ai.WithStreaming(func(ctx context.Context, c *ai.ModelResponseChunk) error {
				parts++
				out += c.Content[0].Text
				return nil
			}),
		)
		if err != nil {
			t.Fatal(err)
		}

		out2 := ""
		for _, p := range final.Message.Content {
			out2 += p.Text
		}

		if out != out2 {
			t.Fatalf("streaming and final should containt the same text.\nstreaming: %s\nfinal:%s\n", out, out2)
		}
		if final.Usage.InputTokens == 0 || final.Usage.OutputTokens == 0 || final.Usage.TotalTokens == 0 {
			t.Fatalf("empty usage stats: %#v", *final.Usage)
		}
	})
}
