// Copyright 2026 Google LLC
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

package exp

import (
	"context"
	"encoding/json"
	"strings"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
)

func TestToolFromCopiesDefinition(t *testing.T) {
	g := newTestGenkit()
	real := genkit.DefineTool(g, "shout", "Shouts.", func(_ *ai.ToolContext, in shoutIn) (string, error) {
		return strings.ToUpper(in.Text), nil
	})
	proxy := NewToolFrom(New(g, newFakeRunner(nil)), real)
	want, got := real.Definition(), proxy.Definition()
	if got.Name != want.Name || got.Description != want.Description {
		t.Errorf("definition = %q/%q, want %q/%q", got.Name, got.Description, want.Name, want.Description)
	}
	if mustJSON(t, got.InputSchema) != mustJSON(t, want.InputSchema) || mustJSON(t, got.OutputSchema) != mustJSON(t, want.OutputSchema) {
		t.Errorf("schemas = %v / %v, want %v / %v", got.InputSchema, got.OutputSchema, want.InputSchema, want.OutputSchema)
	}
}

func TestDefineToolFromRenamesAndCallsOriginal(t *testing.T) {
	ctx := context.Background()
	g := newTestGenkit()
	r := newFakeRunner(nil)
	real := ai.NewTool("shout", "", func(_ *ai.ToolContext, in shoutIn) (shoutIn, error) { return in, nil })
	DefineToolFrom(New(g, r), real, "boxedShout")
	registered := genkit.LookupTool(g, "boxedShout")
	if registered == nil {
		t.Fatal("boxedShout not registered")
	}
	if _, err := registered.RunRaw(ctx, map[string]any{"text": "x"}); err != nil {
		t.Fatal(err)
	}
	if _, _, calls := r.snapshot(); calls[0].req.Key != "/tool.v2/shout" {
		t.Errorf("box key = %q, want the original /tool.v2/shout", calls[0].req.Key)
	}
	defer func() {
		if recover() == nil {
			t.Error("DefineToolFrom with the original name did not panic")
		}
	}()
	DefineToolFrom(New(g, r), real, "shout")
}

func TestToolJSONSchemaSpec(t *testing.T) {
	schema := map[string]any{"type": "object", "properties": map[string]any{"q": map[string]any{"type": "string"}}}
	tool := NewTool[any, any](New(newTestGenkit(), newFakeRunner(nil)), "search", "Search.", WithInputSchema(schema))
	if tool.Definition().InputSchema["properties"] == nil {
		t.Errorf("input schema = %v, want the explicit one", tool.Definition().InputSchema)
	}
	defer func() {
		if recover() == nil {
			t.Error("WithInputSchema on a typed In did not panic")
		}
	}()
	NewTool[shoutIn, any](New(newTestGenkit(), newFakeRunner(nil)), "bad", "", WithInputSchema(schema))
}

func TestToolForwardsAttachedParts(t *testing.T) {
	r := newFakeRunner(func(context.Context, *RunActionRequest, *RunOptions) (any, error) {
		return map[string]any{
			"output":  "done",
			"content": []*ai.Part{ai.NewMediaPart("image/png", "data:image/png;base64,AAAA")},
		}, nil
	})
	tool := NewTool[shoutIn, string](New(newTestGenkit(), r), "draw", "")
	resp, err := tool.RunRawMultipart(context.Background(), map[string]any{"text": "x"})
	if err != nil {
		t.Fatal(err)
	}
	if resp.Output != "done" || len(resp.Content) != 1 || !resp.Content[0].IsMedia() {
		t.Errorf("response = %+v, want output done plus one media part", resp)
	}
}

func TestProxyToolInGenerate(t *testing.T) {
	ctx := context.Background()
	g := newTestGenkit()
	tool := NewTool[shoutIn, shoutIn](New(g, newFakeRunner(nil)), "shout", "Shouts.")
	turn := 0
	model := genkit.DefineModel(g, "test/caller", &ai.ModelOptions{Supports: &ai.ModelSupports{Tools: true, Multiturn: true}},
		func(_ context.Context, req *ai.ModelRequest, _ ai.ModelStreamCallback) (*ai.ModelResponse, error) {
			turn++
			if turn == 1 {
				return &ai.ModelResponse{Message: ai.NewModelMessage(ai.NewToolRequestPart(&ai.ToolRequest{
					Name: "shout", Input: map[string]any{"text": "hey"},
				}))}, nil
			}
			last := req.Messages[len(req.Messages)-1]
			return &ai.ModelResponse{Message: ai.NewModelTextMessage(mustJSON(t, last.Content[0].ToolResponse.Output))}, nil
		})
	resp, err := genkit.Generate(ctx, g, ai.WithModel(model), ai.WithPrompt("go"), ai.WithTools(tool))
	if err != nil {
		t.Fatal(err)
	}
	if resp.Text() != `{"text":"hey"}` {
		t.Errorf("text = %q, want the boxed tool's output", resp.Text())
	}
}

func mustJSON(t *testing.T, v any) string {
	t.Helper()
	b, err := json.Marshal(v)
	if err != nil {
		t.Fatal(err)
	}
	return string(b)
}
