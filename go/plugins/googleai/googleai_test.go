// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package googleai_test

import (
	"context"
	"flag"
	"fmt"
	"log"
	"math"
	"net/http"
	"net/http/httptest"
	"os"
	"regexp"
	"strings"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/internal"
	"github.com/firebase/genkit/go/plugins/googleai"
)

// The tests here only work with an API key set to a valid value.
var (
	apiKey = flag.String("key", "", "Gemini API key")
	cache  = flag.String("cache", "", "Local file to cache (large text document)")
)

var header = flag.Bool("header", false, "run test for x-goog-client-api header")

// We can't test the DefineAll functions along with the other tests because
// we get duplicate definitions of models.
var testAll = flag.Bool("all", false, "test DefineAllXXX functions")

func TestLive(t *testing.T) {
	if *apiKey == "" {
		t.Skipf("no -key provided")
	}
	if *testAll {
		t.Skip("-all provided")
	}
	g, err := genkit.Init(context.Background(), genkit.WithDefaultModel("googleai/gemini-1.5-flash"))
	if err != nil {
		log.Fatal(err)
	}
	ctx := context.Background()
	err = googleai.Init(ctx, g, &googleai.Config{APIKey: *apiKey})
	if err != nil {
		t.Fatal(err)
	}
	embedder := googleai.Embedder(g, "embedding-001")
	if err != nil {
		t.Fatal(err)
	}
	gablorkenTool := genkit.DefineTool(g, "gablorken", "use when need to calculate a gablorken",
		func(ctx *ai.ToolContext, input struct {
			Value int
			Over  float64
		},
		) (float64, error) {
			return math.Pow(float64(input.Value), input.Over), nil
		},
	)
	t.Run("embedder", func(t *testing.T) {
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
	t.Run("generate", func(t *testing.T) {
		resp, err := genkit.Generate(ctx, g, ai.WithPromptText("Which country was Napoleon the emperor of? Name the country, nothing else"))
		if err != nil {
			t.Fatal(err)
		}
		out := strings.ReplaceAll(resp.Message.Content[0].Text, "\n", "")
		const want = "France"
		if out != want {
			t.Errorf("got %q, expecting %q", out, want)
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
			ai.WithPromptText("Write one paragraph about the North Pole."),
			ai.WithStreaming(func(ctx context.Context, c *ai.ModelResponseChunk) error {
				parts++
				out += c.Content[0].Text
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
		const want = "North"
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
			ai.WithPromptText("what is a gablorken of 2 over 3.5?"),
			ai.WithTools(gablorkenTool))
		if err != nil {
			t.Fatal(err)
		}

		out := resp.Message.Content[0].Text
		const want = "11.31"
		if !strings.Contains(out, want) {
			t.Errorf("got %q, expecting it to contain %q", out, want)
		}
	})
	t.Run("avoid tool", func(t *testing.T) {
		resp, err := genkit.Generate(ctx, g,
			ai.WithPromptText("what is a gablorken of 2 over 3.5?"),
			ai.WithTools(gablorkenTool),
			ai.WithToolChoice(ai.ToolChoiceNone))
		if err != nil {
			t.Fatal(err)
		}

		out := resp.Message.Content[0].Text
		const doNotWant = "11.31"
		if strings.Contains(out, doNotWant) {
			t.Errorf("got %q, expecting it NOT to contain %q", out, doNotWant)
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
			ai.WithPromptText("write a summary of the content"),
			ai.WithConfig(&ai.GenerationCommonConfig{
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
			ai.WithConfig(&ai.GenerationCommonConfig{
				Version: "gemini-1.5-flash-001",
			}),
			ai.WithMessages(resp.History()...),
			ai.WithPromptText("rewrite the previous summary but now talking like a pirate, say Ahoy a lot of times"),
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
}

func TestCacheHelper(t *testing.T) {
	t.Run("cache metadata", func(t *testing.T) {
		req := ai.ModelRequest{
			Messages: []*ai.Message{
				ai.NewUserMessage(
					ai.NewTextPart(("this is just a test")),
				),
				ai.NewModelMessage(
					ai.NewTextPart("oh really? is it?")).WithCacheTTL(100),
			},
		}

		for _, m := range req.Messages {
			if m.Role == ai.RoleModel {
				metadata := m.Metadata
				if len(metadata) == 0 {
					t.Fatal("expected metadata with contents, got empty")
				}
				cache, ok := metadata["cache"].(map[string]any)
				if !ok {
					t.Fatal("cache should be a map")
				}
				if cache["ttlSeconds"] != 100 {
					t.Fatalf("expecting ttlSeconds to be 100s, got: %q", cache["ttlSeconds"])
				}
			}
		}
	})
	t.Run("cache metadata overwrite", func(t *testing.T) {
		m := ai.NewModelMessage(ai.NewTextPart("foo bar")).WithCacheTTL(100)
		metadata := m.Metadata
		if len(metadata) == 0 {
			t.Fatal("expected metadata with contents, got empty")
		}
		cache, ok := metadata["cache"].(map[string]any)
		if !ok {
			t.Fatal("cache should be a map")
		}
		if cache["ttlSeconds"] != 100 {
			t.Fatalf("expecting ttlSeconds to be 100s, got: %q", cache["ttlSeconds"])
		}

		m.Metadata["foo"] = "bar"
		m.WithCacheTTL(50)

		metadata = m.Metadata
		cache, ok = metadata["cache"].(map[string]any)
		if !ok {
			t.Fatal("cache should be a map")
		}
		if cache["ttlSeconds"] != 50 {
			t.Fatalf("expecting ttlSeconds to be 50s, got: %d", cache["ttlSeconds"])
		}
		_, ok = metadata["foo"]
		if !ok {
			t.Fatal("metadata contents were altered, expecting foo key")
		}
		bar, ok := metadata["foo"].(string)
		if !ok {
			t.Fatalf(`metadata["foo"] contents got altered, expecting string, got: %T`, bar)
		}
		if bar != "bar" {
			t.Fatalf("expecting to be bar but got: %q", bar)
		}
	})
}

func TestHeader(t *testing.T) {
	g, err := genkit.Init(context.Background(), genkit.WithDefaultModel("googleai/gemini-1.5-flash"))
	if err != nil {
		log.Fatal(err)
	}
	if !*header {
		t.Skip("skipped; to run, pass -header and don't run the live test")
	}
	ctx := context.Background()
	var header http.Header
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		header = r.Header
		http.Error(w, "test", http.StatusServiceUnavailable)
	}))
	defer server.Close()

	if err := googleai.Init(ctx, g, &googleai.Config{APIKey: "x"}); err != nil {
		t.Fatal(err)
	}
	_, _ = genkit.Generate(ctx, g, ai.WithPromptText("hi"))
	got := header.Get("x-goog-api-client")
	want := regexp.MustCompile(fmt.Sprintf(`\bgenkit-go/%s\b`, internal.Version))
	if !want.MatchString(got) {
		t.Errorf("got x-goog-api-client header value\n%s\nwanted it to match regexp %s", got, want)
	}
}
