// Copyright 2025 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// SPDX-License-Identifier: Apache-2.0

package googlegenai_test

import (
	"context"
	"flag"
	"math"
	"os"
	"strings"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/googlegenai"
)

// The tests here only work with a project set to a valid value.
// The user running these tests must be authenticated, for example by
// setting a valid GOOGLE_APPLICATION_CREDENTIALS environment variable.
var (
	projectID = flag.String("projectid", "", "VertexAI project")
	location  = flag.String("location", "us-central1", "geographic location")
)

func TestVertexAILive(t *testing.T) {
	if *projectID == "" {
		t.Skipf("no -projectid provided")
	}
	ctx := context.Background()
	g, err := genkit.Init(context.Background(), genkit.WithDefaultModel("vertexai/gemini-1.5-flash"))
	if err != nil {
		t.Fatal(err)
	}
	err = (&googlegenai.VertexAI{ProjectID: *projectID, Location: *location}).Init(ctx, g)
	if err != nil {
		t.Fatal(err)
	}
	embedder := googlegenai.VertexAIEmbedder(g, "textembedding-gecko@003")

	gablorkenTool := genkit.DefineTool(g, "gablorken", "use this tool when the user asks to calculate a gablorken",
		func(ctx *ai.ToolContext, input struct {
			Value float64
			Over  float64
		},
		) (float64, error) {
			return math.Pow(input.Value, input.Over), nil
		},
	)
	t.Run("model", func(t *testing.T) {
		resp, err := genkit.Generate(ctx, g, ai.WithPrompt("Which country was Napoleon the emperor of?"))
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
			ai.WithPrompt("Write one paragraph about the Golden State Warriors."),
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
			t.Errorf("Empty usage stats %#v", *final.Usage)
		}
	})
	t.Run("tool", func(t *testing.T) {
		resp, err := genkit.Generate(ctx, g,
			ai.WithPrompt("what is a gablorken of 2 over 3.5?"),
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
		res, err := ai.Embed(ctx, embedder,
			ai.WithTextDocs("time flies like an arrow", "fruit flies like a banana"),
		)
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
	t.Run("cache", func(t *testing.T) {
		if *cache == "" {
			t.Skip("no cache contents provided, use -cache flag")
		}
		textContent, err := os.ReadFile(*cache)
		if err != nil {
			t.Fatal(err)
		}
		resp, err := genkit.Generate(ctx, g,
			ai.WithMessages(
				ai.NewUserTextMessage(string(textContent)).WithCacheTTL(360),
			),
			ai.WithPrompt("write a summary of the content"),
			ai.WithConfig(&googlegenai.GeminiConfig{
				Version: "gemini-1.5-flash-001",
			}))
		if err != nil {
			t.Fatal(err)
		}
		// inspect metadata just to make sure the cache was created
		m := resp.Message.Metadata
		cacheName := ""
		if cache, ok := m["cache"].(map[string]any); ok {
			if n, ok := cache["name"].(string); ok {
				if n == "" {
					t.Fatal("expecting a cache name, but got nothing")
				}
				cacheName = n
			} else {
				t.Fatalf("cache name should be a string but got %T", n)
			}
		} else {
			t.Fatalf("cache name should be a map but got %T", cache)
		}
		resp, err = genkit.Generate(ctx, g,
			ai.WithConfig(&googlegenai.GeminiConfig{
				Version: "gemini-1.5-flash-001",
			}),
			ai.WithMessages(resp.History()...),
			ai.WithPrompt("rewrite the previous summary but now talking like a pirate, say Ahoy a lot of times"),
		)
		if err != nil {
			t.Fatal(err)
		}
		text := resp.Text()
		if !strings.Contains(text, "Ahoy") {
			t.Fatalf("expecting a response as a pirate but got %v", text)
		}
		// cache metadata should have not changed...
		if cache, ok := m["cache"].(map[string]any); ok {
			if n, ok := cache["name"].(string); ok {
				if n == "" {
					t.Fatal("expecting a cache name, but got nothing")
				}
				if cacheName != n {
					t.Fatalf("cache name mismatch, want: %s, got: %s", cacheName, n)
				}
			} else {
				t.Fatalf("cache name should be a string but got %T", n)
			}
		} else {
			t.Fatalf("cache name should be a map but got %T", cache)
		}
	})
	t.Run("media content (unstructured data)", func(t *testing.T) {
		i, err := fetchImgAsBase64()
		if err != nil {
			t.Fatal(err)
		}
		resp, err := genkit.Generate(ctx, g,
			ai.WithSystem("You are a pirate expert in TV Shows, your response should include the name of the character in the image provided"),
			ai.WithMessages(
				ai.NewUserMessage(
					ai.NewTextPart("do you know who's in the image?"),
					ai.NewDataPart("data:image/png;base64,"+i),
				),
			),
		)
		if err != nil {
			t.Fatal(err)
		}
		if !strings.Contains(resp.Text(), "Bluey") {
			t.Fatalf("image detection failed, want: Bluey, got: %s", resp.Text())
		}
	})
	t.Run("media content", func(t *testing.T) {
		resp, err := genkit.Generate(ctx, g,
			ai.WithMessages(
				ai.NewUserMessage(
					ai.NewTextPart("do you know what's the video about?"),
					ai.NewMediaPart("video/mp4", `https://www.youtube.com/watch?v=_6FYhqGgel8`),
				),
			),
		)
		if err != nil {
			t.Fatal(err)
		}
		if !strings.Contains(resp.Text(), "Mario Kart") {
			t.Fatalf("image detection failed, want: Mario Kart, got: %s", resp.Text())
		}
	})
	t.Run("constrained generation", func(t *testing.T) {
		type outFormat struct {
			Country string
		}
		resp, err := genkit.Generate(ctx, g,
			ai.WithPrompt("Which country was Napoleon the emperor of?"),
			ai.WithOutputType(outFormat{}),
		)
		if err != nil {
			t.Fatal(err)
		}

		var ans outFormat
		err = resp.Output(&ans)
		if err != nil {
			t.Fatal(err)
		}
		const want = "France"
		if ans.Country != want {
			t.Errorf("got %q, expecting %q", ans.Country, want)
		}
		if resp.Request == nil {
			t.Error("Request field not set properly")
		}
		if resp.Usage.InputTokens == 0 || resp.Usage.OutputTokens == 0 || resp.Usage.TotalTokens == 0 {
			t.Errorf("Empty usage stats %#v", *resp.Usage)
		}
	})
}
