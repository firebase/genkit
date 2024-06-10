// Copyright 2024 Google LLC
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

package googleai_test

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"math"
	"strings"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/plugins/googleai"
)

// The tests here only work with an API key set to a valid value.
var apiKey = flag.String("key", "", "Gemini API key")

const (
	embeddingModel  = "embedding-001"
	generativeModel = "gemini-1.0-pro"
)

func TestLive(t *testing.T) {
	if *apiKey == "" {
		t.Skipf("no -key provided")
	}
	ctx := context.Background()
	_, _, err := googleai.Init(ctx, googleai.Config{
		APIKey:    *apiKey,
		Embedders: []string{embeddingModel},
		Models:    []string{generativeModel},
	})
	if err != nil {
		t.Fatal(err)
	}
	toolDef := &ai.ToolDefinition{
		Name:         "exponentiation",
		InputSchema:  map[string]any{"base": "float64", "exponent": "int"},
		OutputSchema: map[string]any{"output": "float64"},
	}
	ai.DefineTool(toolDef, nil,
		func(ctx context.Context, input map[string]any) (map[string]any, error) {
			baseAny, ok := input["base"]
			if !ok {
				return nil, errors.New("exponentiation tool: missing base")
			}
			base, ok := baseAny.(float64)
			if !ok {
				return nil, fmt.Errorf("exponentiation tool: base is %T, want %T", baseAny, float64(0))
			}

			expAny, ok := input["exponent"]
			if !ok {
				return nil, errors.New("exponentiation tool: missing exponent")
			}
			exp, ok := expAny.(float64)
			if !ok {
				expInt, ok := expAny.(int)
				if !ok {
					return nil, fmt.Errorf("exponentiation tool: exponent is %T, want %T or %T", expAny, float64(0), int(0))
				}
				exp = float64(expInt)
			}

			r := map[string]any{"output": math.Pow(base, exp)}
			return r, nil
		},
	)
	t.Run("embedder", func(t *testing.T) {
		out, err := ai.Embed(ctx, googleai.Embedder(embeddingModel), &ai.EmbedRequest{
			Document: ai.DocumentFromText("yellow banana", nil),
		})
		if err != nil {
			t.Fatal(err)
		}

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
		g := googleai.Model(generativeModel)
		req := &ai.GenerateRequest{
			Candidates: 1,
			Messages: []*ai.Message{
				&ai.Message{
					Content: []*ai.Part{ai.NewTextPart("Which country was Napoleon the emperor of?")},
					Role:    ai.RoleUser,
				},
			},
		}

		resp, err := ai.Generate(ctx, g, req, nil)
		if err != nil {
			t.Fatal(err)
		}
		out := resp.Candidates[0].Message.Content[0].Text
		const want = "France"
		if out != want {
			t.Errorf("got %q, expecting %q", out, want)
		}
		if resp.Request != req {
			t.Error("Request field not set properly")
		}
	})
	t.Run("streaming", func(t *testing.T) {
		req := &ai.GenerateRequest{
			Candidates: 1,
			Messages: []*ai.Message{
				&ai.Message{
					Content: []*ai.Part{ai.NewTextPart("Write one paragraph about the Golden State Warriors.")},
					Role:    ai.RoleUser,
				},
			},
		}

		out := ""
		parts := 0
		g := googleai.Model(generativeModel)
		_, err = ai.Generate(ctx, g, req, func(ctx context.Context, c *ai.GenerateResponseChunk) error {
			parts++
			out += c.Content[0].Text
			return nil
		})
		if err != nil {
			t.Fatal(err)
		}
		const want = "Golden"
		if !strings.Contains(out, want) {
			t.Errorf("got %q, expecting it to contain %q", out, want)
		}
		if parts == 1 {
			// Check if streaming actually occurred.
			t.Errorf("expecting more than one part")
		}
	})
	t.Run("tool", func(t *testing.T) {
		req := &ai.GenerateRequest{
			Candidates: 1,
			Messages: []*ai.Message{
				&ai.Message{
					Content: []*ai.Part{ai.NewTextPart("what is 3.5 squared? Use the tool provided.")},
					Role:    ai.RoleUser,
				},
			},
			Tools: []*ai.ToolDefinition{toolDef},
		}

		resp, err := ai.Generate(ctx, googleai.Model(generativeModel), req, nil)
		if err != nil {
			t.Fatal(err)
		}

		out := resp.Candidates[0].Message.Content[0].Text
		const want = "12.25"
		if !strings.Contains(out, want) {
			t.Errorf("got %q, expecting it to contain %q", out, want)
		}
	})
}
