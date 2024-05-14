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
	"flag"
	"math"
	"strings"
	"testing"

	"github.com/google/genkit/go/ai"
	"github.com/google/genkit/go/plugins/vertexai"
)

// The tests here only work with a project set to a valid value.
// The user running these tests must be authenticated, for example by
// setting a valid GOOGLE_APPLICATION_CREDENTIALS environment variable.
var projectID = flag.String("projectid", "", "VertexAI project")
var location = flag.String("location", "us-central1", "geographic location")

func TestGenerator(t *testing.T) {
	if *projectID == "" {
		t.Skipf("no -projectid provided")
	}
	ctx := context.Background()
	g, err := vertexai.NewGenerator(ctx, "gemini-1.0-pro", *projectID, *location)
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
	if !strings.Contains(out, "France") {
		t.Errorf("got \"%s\", expecting it would contain \"France\"", out)
	}
	if resp.Request != req {
		t.Error("Request field not set properly")
	}
}

func TestGeneratorTool(t *testing.T) {
	if *projectID == "" {
		t.Skip("no -projectid provided")
	}
	ctx := context.Background()
	g, err := vertexai.NewGenerator(ctx, "gemini-1.0-pro", *projectID, *location)
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
