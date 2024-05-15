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
	"flag"
	"math"
	"strings"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/plugins/googleai"
)

// The tests here only work with an API key set to a valid value.
var apiKey = flag.String("key", "", "Gemini API key")

func TestEmbedder(t *testing.T) {
	if *apiKey == "" {
		t.Skipf("no -key provided")
	}
	ctx := context.Background()
	e, err := googleai.NewEmbedder(ctx, "embedding-001", *apiKey)
	if err != nil {
		t.Fatal(err)
	}
	out, err := e.Embed(ctx, &ai.EmbedRequest{
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
}

func TestGenerator(t *testing.T) {
	if *apiKey == "" {
		t.Skipf("no -key provided")
	}
	ctx := context.Background()
	g, err := googleai.NewGenerator(ctx, "gemini-1.0-pro", *apiKey)
	if err != nil {
		t.Fatal(err)
	}
	req := &ai.GenerateRequest{
		Candidates: 1,
		Messages: []*ai.Message{
			&ai.Message{
				Content: []*ai.Part{ai.NewTextPart("Which country was Napoleon the emperor of?")},
				Role:    ai.RoleUser,
			},
		},
	}

	resp, err := g.Generate(ctx, req, nil)
	if err != nil {
		t.Fatal(err)
	}
	out := resp.Candidates[0].Message.Content[0].Text()
	if out != "France" {
		t.Errorf("got \"%s\", expecting \"France\"", out)
	}
	if resp.Request != req {
		t.Error("Request field not set properly")
	}
}

func TestGeneratorStreaming(t *testing.T) {
	if *apiKey == "" {
		t.Skipf("no -key provided")
	}
	ctx := context.Background()
	g, err := googleai.NewGenerator(ctx, "gemini-1.0-pro", *apiKey)
	if err != nil {
		t.Fatal(err)
	}
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
	_, err = g.Generate(ctx, req, func(ctx context.Context, c *ai.Candidate) error {
		parts++
		out += c.Message.Content[0].Text()
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(out, "San Francisco") {
		t.Errorf("got \"%s\", expecting it to contain \"San Francisco\"", out)
	}
	if parts == 1 {
		// Check if streaming actually occurred.
		t.Errorf("expecting more than one part")
	}
}

func TestGeneratorTool(t *testing.T) {
	if *apiKey == "" {
		t.Skipf("no -key provided")
	}
	ctx := context.Background()
	g, err := googleai.NewGenerator(ctx, "gemini-1.0-pro", *apiKey)
	if err != nil {
		t.Fatal(err)
	}
	req := &ai.GenerateRequest{
		Candidates: 1,
		Messages: []*ai.Message{
			&ai.Message{
				Content: []*ai.Part{ai.NewTextPart("what is 3.5 squared? Use the tool provided.")},
				Role:    ai.RoleUser,
			},
		},
		Tools: []*ai.ToolDefinition{
			&ai.ToolDefinition{
				Name:         "exponentiation",
				InputSchema:  map[string]any{"base": "float64", "exponent": "int"},
				OutputSchema: map[string]any{"output": "float64"},
			},
		},
	}

	resp, err := g.Generate(ctx, req, nil)
	if err != nil {
		t.Fatal(err)
	}
	p := resp.Candidates[0].Message.Content[0]
	if !p.IsToolRequest() {
		t.Fatalf("tool not requested")
	}
	toolReq := p.ToolRequest()
	if toolReq.Name != "exponentiation" {
		t.Errorf("tool name is %q, want \"exponentiation\"", toolReq.Name)
	}
	if toolReq.Input["base"] != 3.5 {
		t.Errorf("base is %f, want 3.5", toolReq.Input["base"])
	}
	if toolReq.Input["exponent"] != 2 && toolReq.Input["exponent"] != 2.0 {
		// Note: 2.0 is wrong given the schema, but Gemini returns a float anyway.
		t.Errorf("exponent is %f, want 2", toolReq.Input["exponent"])
	}

	// Update our conversation with the tool request the model made and our tool response.
	// (Our "tool" is just math.Pow.)
	req.Messages = append(req.Messages,
		resp.Candidates[0].Message,
		&ai.Message{
			Content: []*ai.Part{ai.NewToolResponsePart(&ai.ToolResponse{
				Name:   "exponentiation",
				Output: map[string]any{"output": math.Pow(3.5, 2)},
			})},
			Role: ai.RoleTool,
		},
	)

	// Issue our request again.
	resp, err = g.Generate(ctx, req, nil)
	if err != nil {
		t.Fatal(err)
	}

	// Check final response.
	out := resp.Candidates[0].Message.Content[0].Text()
	if !strings.Contains(out, "12.25") {
		t.Errorf("got %s, expecting it to contain \"12.25\"", out)
	}
}
