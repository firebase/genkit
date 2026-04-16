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
	"slices"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/core/tracing"
)

// ToolApproval is a middleware that interrupts tool execution unless the tool
// is in [AllowedTools] or the call has been resumed after approval.
//
// Usage:
//
//	resp, err := ai.Generate(ctx, r,
//	    ai.WithModel(m),
//	    ai.WithPrompt("do something"),
//	    ai.WithTools(toolA, toolB),
//	    ai.WithUse(&middleware.ToolApproval{AllowedTools: []string{"toolA"}}),
//	)
//	// toolA runs; toolB triggers an interrupt.
//	// Resume with ai.WithToolRestarts to approve and re-execute.
type ToolApproval struct {
	ai.BaseMiddleware
	// AllowedTools is the list of tool names pre-approved to run without
	// interruption. Tools not in this list trigger an interrupt. An empty
	// list interrupts all tools.
	AllowedTools []string `json:"allowedTools,omitempty"`
}

func (t *ToolApproval) Name() string { return provider + "/toolApproval" }

func (t *ToolApproval) New() ai.Middleware {
	return &ToolApproval{AllowedTools: t.AllowedTools}
}

func (t *ToolApproval) WrapTool(ctx context.Context, params *ai.ToolParams, next ai.ToolNext) (*ai.ToolResponse, error) {
	// Resumed tool calls have already been approved by the caller.
	if ai.IsToolResumed(ctx) {
		return next(ctx, params)
	}

	name := params.Tool.Name()
	if slices.Contains(t.AllowedTools, name) {
		return next(ctx, params)
	}

	// Emit a tool-shaped span so the interrupt is attributed to the tool in traces,
	// mirroring the span that core/action.go would create if the tool had run.
	spanMeta := &tracing.SpanMetadata{
		Name:     name,
		Type:     "action",
		Subtype:  "tool",
		Metadata: map[string]string{},
	}
	if flowName := core.FlowNameFromContext(ctx); flowName != "" {
		spanMeta.Metadata["flow:name"] = flowName
	}
	_, err := tracing.RunInNewSpan(ctx, spanMeta, params.Request.Input,
		func(ctx context.Context, _ any) (any, error) {
			return nil, ai.NewToolInterruptError(map[string]any{
				"message": "Tool not in approved list: " + name,
			})
		})
	return nil, err
}
