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

package middleware

import (
	"context"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/core/api"
	"github.com/firebase/genkit/go/internal/registry"
)

func defineToolModel(t *testing.T, r *registry.Registry, name string, fn ai.ModelFunc) ai.Model {
	t.Helper()
	return ai.DefineModel(r, name, &ai.ModelOptions{
		Supports: &ai.ModelSupports{Multiturn: true, SystemRole: true, Tools: true},
	}, fn)
}

func defineTool(t *testing.T, r api.Registry, name string) ai.Tool {
	t.Helper()
	return ai.DefineTool(r, name, "test tool",
		func(ctx *ai.ToolContext, input struct {
			V string `json:"v"`
		}) (string, error) {
			return "result:" + input.V, nil
		})
}

// twoToolModelHandler returns a model handler that requests two tools on the first call,
// then returns a final text response when it sees tool responses.
func twoToolModelHandler(tool1, tool2 string) ai.ModelFunc {
	return func(ctx context.Context, req *ai.ModelRequest, cb ai.ModelStreamCallback) (*ai.ModelResponse, error) {
		// Check if we already have tool responses
		for _, msg := range req.Messages {
			for _, part := range msg.Content {
				if part.IsToolResponse() {
					return &ai.ModelResponse{
						Request: req,
						Message: ai.NewModelTextMessage("done"),
					}, nil
				}
			}
		}
		// First call — request both tools
		return &ai.ModelResponse{
			Request: req,
			Message: &ai.Message{
				Role: ai.RoleModel,
				Content: []*ai.Part{
					ai.NewToolRequestPart(&ai.ToolRequest{Name: tool1, Input: map[string]any{"v": "1"}}),
					ai.NewToolRequestPart(&ai.ToolRequest{Name: tool2, Input: map[string]any{"v": "2"}}),
				},
			},
		}, nil
	}
}

func TestToolApprovalAllowsApprovedTools(t *testing.T) {
	r := newTestRegistry(t)

	m := defineToolModel(t, r, "test/twotools", twoToolModelHandler("allowed", "alsoAllowed"))
	allowed := defineTool(t, r, "allowed")
	alsoAllowed := defineTool(t, r, "alsoAllowed")

	ta := &ToolApproval{AllowedTools: []string{"allowed", "alsoAllowed"}}
	ai.DefineMiddleware(r, "toolApproval", ta)

	resp, err := ai.Generate(ctx, r,
		ai.WithModel(m),
		ai.WithPrompt("go"),
		ai.WithTools(allowed, alsoAllowed),
		ai.WithUse(ta),
	)
	if err != nil {
		t.Fatal(err)
	}
	// Both tools approved → no interrupt, model returns "done"
	if resp.Text() != "done" {
		t.Errorf("got %q, want %q", resp.Text(), "done")
	}
	if resp.FinishReason == "interrupted" {
		t.Error("did not expect interrupted finish reason")
	}
}

func TestToolApprovalInterruptsUnapprovedTools(t *testing.T) {
	r := newTestRegistry(t)

	m := defineToolModel(t, r, "test/twotools", twoToolModelHandler("safe", "dangerous"))
	safe := defineTool(t, r, "safe")
	dangerous := defineTool(t, r, "dangerous")

	ta := &ToolApproval{AllowedTools: []string{"safe"}}
	ai.DefineMiddleware(r, "toolApproval", ta)

	resp, err := ai.Generate(ctx, r,
		ai.WithModel(m),
		ai.WithPrompt("go"),
		ai.WithTools(safe, dangerous),
		ai.WithUse(ta),
	)
	if err != nil {
		t.Fatal(err)
	}
	if resp.FinishReason != "interrupted" {
		t.Errorf("got finish reason %q, want %q", resp.FinishReason, "interrupted")
	}

	interrupts := resp.Interrupts()
	if len(interrupts) == 0 {
		t.Fatal("expected at least one interrupt")
	}

	// Find the interrupt for "dangerous" using the typed helper.
	found := false
	for _, p := range interrupts {
		meta, ok := IsToolApprovalInterrupt(p)
		if !ok {
			continue
		}
		if meta.Tool == "dangerous" {
			found = true
		}
	}
	if !found {
		t.Error("expected interrupt for 'dangerous' tool")
	}
}

func TestToolApprovalEmptyListInterruptsAll(t *testing.T) {
	r := newTestRegistry(t)

	// Model requests a single tool
	singleToolHandler := func(ctx context.Context, req *ai.ModelRequest, cb ai.ModelStreamCallback) (*ai.ModelResponse, error) {
		for _, msg := range req.Messages {
			for _, part := range msg.Content {
				if part.IsToolResponse() {
					return &ai.ModelResponse{Request: req, Message: ai.NewModelTextMessage("done")}, nil
				}
			}
		}
		return &ai.ModelResponse{
			Request: req,
			Message: &ai.Message{
				Role: ai.RoleModel,
				Content: []*ai.Part{
					ai.NewToolRequestPart(&ai.ToolRequest{Name: "myTool", Input: map[string]any{"v": "1"}}),
				},
			},
		}, nil
	}

	m := defineToolModel(t, r, "test/singletool", singleToolHandler)
	myTool := defineTool(t, r, "myTool")

	ta := &ToolApproval{} // empty allowed list
	ai.DefineMiddleware(r, "toolApproval", ta)

	resp, err := ai.Generate(ctx, r,
		ai.WithModel(m),
		ai.WithPrompt("go"),
		ai.WithTools(myTool),
		ai.WithUse(ta),
	)
	if err != nil {
		t.Fatal(err)
	}
	if resp.FinishReason != "interrupted" {
		t.Errorf("got finish reason %q, want %q", resp.FinishReason, "interrupted")
	}
}

func TestToolApprovalDeniedToolsInterruptsDenied(t *testing.T) {
	r := newTestRegistry(t)

	m := defineToolModel(t, r, "test/twotools", twoToolModelHandler("safe", "dangerous"))
	safe := defineTool(t, r, "safe")
	dangerous := defineTool(t, r, "dangerous")

	ta := &ToolApproval{DeniedTools: []string{"dangerous"}}
	ai.DefineMiddleware(r, "toolApproval", ta)

	resp, err := ai.Generate(ctx, r,
		ai.WithModel(m),
		ai.WithPrompt("go"),
		ai.WithTools(safe, dangerous),
		ai.WithUse(ta),
	)
	if err != nil {
		t.Fatal(err)
	}
	if resp.FinishReason != "interrupted" {
		t.Errorf("got finish reason %q, want %q", resp.FinishReason, "interrupted")
	}

	interrupts := resp.Interrupts()
	if len(interrupts) == 0 {
		t.Fatal("expected at least one interrupt")
	}

	found := false
	for _, p := range interrupts {
		meta, ok := IsToolApprovalInterrupt(p)
		if !ok {
			continue
		}
		if meta.Tool == "dangerous" {
			found = true
		}
		if meta.Tool == "safe" {
			t.Error("did not expect interrupt for 'safe' tool")
		}
	}
	if !found {
		t.Error("expected interrupt for 'dangerous' tool")
	}
}

func TestToolApprovalDeniedToolsAllowsOthers(t *testing.T) {
	r := newTestRegistry(t)

	m := defineToolModel(t, r, "test/twotools", twoToolModelHandler("allowed1", "allowed2"))
	allowed1 := defineTool(t, r, "allowed1")
	allowed2 := defineTool(t, r, "allowed2")

	ta := &ToolApproval{DeniedTools: []string{"somethingElse"}}
	ai.DefineMiddleware(r, "toolApproval", ta)

	resp, err := ai.Generate(ctx, r,
		ai.WithModel(m),
		ai.WithPrompt("go"),
		ai.WithTools(allowed1, allowed2),
		ai.WithUse(ta),
	)
	if err != nil {
		t.Fatal(err)
	}
	if resp.Text() != "done" {
		t.Errorf("got %q, want %q", resp.Text(), "done")
	}
	if resp.FinishReason == "interrupted" {
		t.Error("did not expect interrupted finish reason")
	}
}

func TestToolApprovalMutualExclusionErrors(t *testing.T) {
	r := newTestRegistry(t)

	m := defineToolModel(t, r, "test/twotools", twoToolModelHandler("a", "b"))
	a := defineTool(t, r, "a")
	b := defineTool(t, r, "b")

	ta := &ToolApproval{
		AllowedTools: []string{"a"},
		DeniedTools:  []string{"b"},
	}
	ai.DefineMiddleware(r, "toolApproval", ta)

	_, err := ai.Generate(ctx, r,
		ai.WithModel(m),
		ai.WithPrompt("go"),
		ai.WithTools(a, b),
		ai.WithUse(ta),
	)
	if err == nil {
		t.Fatal("expected error when both AllowedTools and DeniedTools are set")
	}
}

func TestToolApprovalApproveAndDenyHelpers(t *testing.T) {
	r := newTestRegistry(t)

	m := defineToolModel(t, r, "test/twotools", twoToolModelHandler("approvable", "deniable"))
	approvable := defineTool(t, r, "approvable")
	deniable := defineTool(t, r, "deniable")

	ta := &ToolApproval{} // deny all
	ai.DefineMiddleware(r, "toolApproval", ta)

	resp, err := ai.Generate(ctx, r,
		ai.WithModel(m),
		ai.WithPrompt("go"),
		ai.WithTools(approvable, deniable),
		ai.WithUse(ta),
	)
	if err != nil {
		t.Fatal(err)
	}
	if resp.FinishReason != "interrupted" {
		t.Fatalf("got finish reason %q, want %q", resp.FinishReason, "interrupted")
	}

	var restarts, responses []*ai.Part
	for _, interrupt := range resp.Interrupts() {
		meta, ok := IsToolApprovalInterrupt(interrupt)
		if !ok {
			t.Fatal("expected tool approval interrupt")
		}
		switch meta.Tool {
		case "approvable":
			restarts = append(restarts, ApproveInterrupt(interrupt))
		case "deniable":
			responses = append(responses, DenyInterrupt(interrupt, "denied by user"))
		}
	}

	if len(restarts) != 1 {
		t.Fatalf("expected 1 restart, got %d", len(restarts))
	}
	if len(responses) != 1 {
		t.Fatalf("expected 1 response, got %d", len(responses))
	}

	// Resume with the approved and denied tools.
	resp, err = ai.Generate(ctx, r,
		ai.WithModel(m),
		ai.WithMessages(resp.History()...),
		ai.WithTools(approvable, deniable),
		ai.WithToolRestarts(restarts...),
		ai.WithToolResponses(responses...),
		ai.WithUse(ta),
	)
	if err != nil {
		t.Fatal(err)
	}
	if resp.Text() != "done" {
		t.Errorf("got %q, want %q", resp.Text(), "done")
	}
}
