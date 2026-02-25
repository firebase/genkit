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
	"fmt"
	"maps"
	"slices"

	"github.com/firebase/genkit/go/ai"
)

const toolApprovalSource = "toolApproval"

// ToolApprovalInterrupt is the typed interrupt metadata emitted by the
// [ToolApproval] middleware when a tool call is blocked for approval.
//
// Use [IsToolApprovalInterrupt] to check whether an interrupt came from this
// middleware and extract the metadata in one step.
type ToolApprovalInterrupt struct {
	// Source identifies this interrupt as coming from the ToolApproval middleware.
	Source string `json:"source"`
	// Tool is the name of the tool that requires approval.
	Tool string `json:"tool"`
}

// IsToolApprovalInterrupt reports whether an interrupt [ai.Part] was emitted
// by the [ToolApproval] middleware. If so, it returns the typed metadata.
func IsToolApprovalInterrupt(p *ai.Part) (ToolApprovalInterrupt, bool) {
	meta, ok := ai.InterruptAs[ToolApprovalInterrupt](p)
	if !ok || meta.Source != toolApprovalSource {
		return ToolApprovalInterrupt{}, false
	}
	return meta, true
}

// ApproveInterrupt creates a restart [ai.Part] for a tool call that was
// blocked by [ToolApproval]. Pass the returned Part to [ai.WithToolRestarts]
// to re-execute the tool.
//
// Returns nil if p is not a tool request.
func ApproveInterrupt(p *ai.Part) *ai.Part {
	if p == nil || !p.IsToolRequest() {
		return nil
	}
	newMeta := maps.Clone(p.Metadata)
	if newMeta == nil {
		newMeta = make(map[string]any)
	}
	newMeta["resumed"] = true
	delete(newMeta, "interrupt")

	part := ai.NewToolRequestPart(&ai.ToolRequest{
		Name:  p.ToolRequest.Name,
		Ref:   p.ToolRequest.Ref,
		Input: p.ToolRequest.Input,
	})
	part.Metadata = newMeta
	return part
}

// DenyInterrupt creates a response [ai.Part] for a tool call that was blocked
// by [ToolApproval] and denied by the user. Pass the returned Part to
// [ai.WithToolResponses] to provide the denial message as the tool's output.
//
// Returns nil if p is not a tool request.
func DenyInterrupt(p *ai.Part, message string) *ai.Part {
	if p == nil || !p.IsToolRequest() {
		return nil
	}
	resp := ai.NewResponseForToolRequest(p, message)
	resp.Metadata = map[string]any{
		"interruptResponse": true,
	}
	return resp
}

// ToolApproval is a middleware that requires explicit approval for tool execution.
//
// AllowedTools and DeniedTools are mutually exclusive and control the default behavior:
//
//   - AllowedTools: deny-by-default; only listed tools run, all others interrupt.
//   - DeniedTools: allow-by-default; all tools run except listed ones, which interrupt.
//   - Neither set: all tools interrupt (deny-all).
//
// Usage:
//
//	resp, err := ai.Generate(ctx, r,
//	    ai.WithModel(m),
//	    ai.WithPrompt("do something"),
//	    ai.WithTools(toolA, toolB, toolC),
//	    ai.WithUse(&middleware.ToolApproval{AllowedTools: []string{"toolA"}}),
//	)
//	// toolA runs automatically; toolB and toolC trigger interrupts.
//	// Use resp.Interrupts() + WithToolRestarts() to approve and re-execute.
type ToolApproval struct {
	ai.BaseMiddleware
	// AllowedTools is the list of tool names that are pre-approved to run
	// without interruption. Tools not in this list will trigger an interrupt.
	// Mutually exclusive with DeniedTools.
	AllowedTools []string `json:"allowedTools,omitempty"`
	// DeniedTools is the list of tool names that will trigger an interrupt.
	// Tools not in this list run immediately.
	// Mutually exclusive with AllowedTools.
	DeniedTools []string `json:"deniedTools,omitempty"`
}

func (t *ToolApproval) Name() string { return provider + "/toolApproval" }

func (t *ToolApproval) New() ai.Middleware {
	return &ToolApproval{
		AllowedTools: t.AllowedTools,
		DeniedTools:  t.DeniedTools,
	}
}

func (t *ToolApproval) WrapTool(ctx context.Context, params *ai.ToolParams, next ai.ToolNext) (*ai.ToolResponse, error) {
	if len(t.AllowedTools) > 0 && len(t.DeniedTools) > 0 {
		return nil, fmt.Errorf("toolApproval: AllowedTools and DeniedTools are mutually exclusive")
	}

	// Resumed (restarted) tool calls have already been approved by the caller.
	if ai.IsToolResumed(ctx) {
		return next(ctx, params)
	}

	name := params.Tool.Name()

	interrupt := map[string]any{
		"source": toolApprovalSource,
		"tool":   name,
	}

	if len(t.DeniedTools) > 0 {
		if slices.Contains(t.DeniedTools, name) {
			return nil, ai.NewToolInterruptError(interrupt)
		}
		return next(ctx, params)
	}

	// AllowedTools mode (or neither set — deny all).
	if slices.Contains(t.AllowedTools, name) {
		return next(ctx, params)
	}
	return nil, ai.NewToolInterruptError(interrupt)
}
