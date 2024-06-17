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

package vertexai_test

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"math"
	"strings"
	"testing"

	"github.com/firebase/genkit/go/ai"
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
	const modelName = "gemini-1.0-pro"
	const embedderName = "textembedding-gecko"
	err := vertexai.Init(ctx, vertexai.Config{
		ProjectID: *projectID,
		Location:  *location,
		Models:    []string{modelName},
		Embedders: []string{embedderName},
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
	t.Run("model", func(t *testing.T) {
		req := &ai.GenerateRequest{
			Candidates: 1,
			Messages: []*ai.Message{
				&ai.Message{
					Content: []*ai.Part{ai.NewTextPart("Which country was Napoleon the emperor of?")},
					Role:    ai.RoleUser,
				},
			},
		}

		resp, err := ai.Generate(ctx, vertexai.Model(modelName), req, nil)
		if err != nil {
			t.Fatal(err)
		}
		out := resp.Candidates[0].Message.Content[0].Text
		if !strings.Contains(out, "France") {
			t.Errorf("got \"%s\", expecting it would contain \"France\"", out)
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
		model := vertexai.Model(modelName)
		final, err := ai.Generate(ctx, model, req, func(ctx context.Context, c *ai.GenerateResponseChunk) error {
			parts++
			for _, p := range c.Content {
				out += p.Text
			}
			return nil
		})
		if err != nil {
			t.Fatal(err)
		}
		out2 := ""
		for _, p := range final.Candidates[0].Message.Content {
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

		resp, err := ai.Generate(ctx, vertexai.Model(modelName), req, nil)
		if err != nil {
			t.Fatal(err)
		}

		out := resp.Candidates[0].Message.Content[0].Text
		if !strings.Contains(out, "12.25") {
			t.Errorf("got %s, expecting it to contain \"12.25\"", out)
		}
	})
	t.Run("embedder", func(t *testing.T) {
		out, err := ai.Embed(ctx, vertexai.Embedder(embedderName), &ai.EmbedRequest{
			Document: ai.DocumentFromText("time flies like an arrow", nil),
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
}
