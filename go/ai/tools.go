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

package ai

import (
	"context"
	"encoding/json"
	"fmt"

	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/internal/action"
	"github.com/firebase/genkit/go/internal/atype"
	"github.com/firebase/genkit/go/internal/base"
	"github.com/firebase/genkit/go/internal/registry"
)

// ToolRef is a reference to a tool.
type ToolRef interface {
	Name() string
}

// ToolName is a distinct type for a tool name.
// It is meant to be passed where a ToolRef is expected but no Tool is had.
type ToolName string

// Name returns the name of the tool.
func (t ToolName) Name() string {
	return (string)(t)
}

// A ToolDef is an implementation of a single tool.
type ToolDef[In, Out any] core.ActionDef[In, Out, struct{}]

// tool is genericless version of ToolDef. It's required to make [LookupTool] possible.
type tool struct {
	// action is the underlying internal action. It's needed for the descriptor.
	action action.Action
}

// Tool represents an instance of a tool.
type Tool interface {
	// Name returns the name of the tool.
	Name() string
	// Definition returns ToolDefinition for for this tool.
	Definition() *ToolDefinition
	// RunRaw runs this tool using the provided raw input.
	RunRaw(ctx context.Context, input any) (any, error)
}

// ToolInterruptError represents an intentional interruption of tool execution.
type ToolInterruptError struct {
	Metadata map[string]any
}

func (e *ToolInterruptError) Error() string {
	return "tool execution interrupted"
}

// InterruptOptions provides configuration for tool interruption.
type InterruptOptions struct {
	Metadata map[string]any
}

// ToolContext provides context and utility functions for tool execution.
type ToolContext struct {
	context.Context
	// Interrupt is a function that can be used to interrupt the tool execution.
	// Interrupting tool execution returns the control to the caller with the
	// total model response so far.
	Interrupt func(opts *InterruptOptions) error
}

// DefineTool defines a tool function with interrupt capability
func DefineTool[In, Out any](r *registry.Registry, name, description string,
	fn func(ctx *ToolContext, input In) (Out, error)) Tool {
	metadata := make(map[string]any)
	metadata["type"] = "tool"
	metadata["name"] = name
	metadata["description"] = description

	wrappedFn := func(ctx context.Context, input In) (Out, error) {
		toolCtx := &ToolContext{
			Context: ctx,
			Interrupt: func(opts *InterruptOptions) error {
				return &ToolInterruptError{
					Metadata: opts.Metadata,
				}
			},
		}
		return fn(toolCtx, input)
	}

	toolAction := core.DefineAction(r, "", name, atype.Tool, metadata, wrappedFn)

	return &tool{action: toolAction}
}

// Name returns the name of the tool.
func (ta *tool) Name() string {
	return ta.Definition().Name
}

// Name returns the name of the tool.
func (t *ToolDef[In, Out]) Name() string {
	return t.Definition().Name
}

// Definition returns [ToolDefinition] for for this tool.
func (t *ToolDef[In, Out]) Definition() *ToolDefinition {
	return definition((*core.ActionDef[In, Out, struct{}])(t).Desc())
}

// Definition returns [ToolDefinition] for for this tool.
func (t *tool) Definition() *ToolDefinition {
	return definition(t.action.Desc())
}

func definition(desc action.Desc) *ToolDefinition {
	td := &ToolDefinition{
		Name:        desc.Metadata["name"].(string),
		Description: desc.Metadata["description"].(string),
	}
	if desc.InputSchema != nil {
		td.InputSchema = base.SchemaAsMap(desc.InputSchema)
	}
	if desc.OutputSchema != nil {
		td.OutputSchema = base.SchemaAsMap(desc.OutputSchema)
	}
	return td
}

// RunRaw runs this tool using the provided raw map format data (JSON parsed
// as map[string]any).
func (t *tool) RunRaw(ctx context.Context, input any) (any, error) {
	return runAction(ctx, t.Definition(), t.action, input)
}

// RunRaw runs this tool using the provided raw map format data (JSON parsed
// as map[string]any).
func (t *ToolDef[In, Out]) RunRaw(ctx context.Context, input any) (any, error) {
	return runAction(ctx, t.Definition(), (*core.ActionDef[In, Out, struct{}])(t), input)
}

// runAction runs the given action with the provided raw input and returns the output in raw format.
func runAction(ctx context.Context, def *ToolDefinition, action core.Action, input any) (any, error) {
	mi, err := json.Marshal(input)
	if err != nil {
		return nil, fmt.Errorf("error marshalling tool input for %v: %v", def.Name, err)
	}
	output, err := action.RunJSON(ctx, mi, nil)
	if err != nil {
		return nil, fmt.Errorf("error calling tool %v: %w", def.Name, err)
	}

	var uo any
	err = json.Unmarshal(output, &uo)
	if err != nil {
		return nil, fmt.Errorf("error parsing tool output for %v: %v", def.Name, err)
	}
	return uo, nil
}

// LookupTool looks up the tool in the registry by provided name and returns it.
func LookupTool(r *registry.Registry, name string) Tool {
	if name == "" {
		return nil
	}

	action := r.LookupAction(fmt.Sprintf("/%s/%s", atype.Tool, name))
	if action == nil {
		return nil
	}
	return &tool{action: action}
}
