// Copyright 2024 Google LLC
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

const provider = "local"

// A ToolDef is an implementation of a single tool.
type ToolDef[In, Out any] struct {
	action *core.ActionDef[In, Out, struct{}]
}

// toolAction is genericless version of ToolDef. It's required to make
// LookupTool possible.
type toolAction struct {
	// action is the underlying internal action. It's needed for the descriptor.
	action action.Action
}

// Tool represents an instance of a tool.
type Tool interface {
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
	Interrupt func(opts *InterruptOptions) error
}

// DefineTool defines a tool function with interrupt capability
func DefineTool[In, Out any](r *registry.Registry, name, description string,
	fn func(ctx *ToolContext, input In) (Out, error)) *ToolDef[In, Out] {

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

	toolAction := core.DefineAction(r, provider, name, atype.Tool, metadata, wrappedFn)
	return &ToolDef[In, Out]{
		action: toolAction,
	}
}

// Definition returns ToolDefinition for for this tool.
func (ta *ToolDef[In, Out]) Definition() *ToolDefinition {
	return definition(ta.action.Desc())
}

// Definition returns ToolDefinition for for this tool.
func (ta *toolAction) Definition() *ToolDefinition {
	return definition(ta.action.Desc())
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
func (ta *toolAction) RunRaw(ctx context.Context, input any) (any, error) {
	return runAction(ctx, ta.Definition(), ta.action, input)

}

// RunRaw runs this tool using the provided raw map format data (JSON parsed
// as map[string]any).
func (ta *ToolDef[In, Out]) RunRaw(ctx context.Context, input any) (any, error) {
	return runAction(ctx, ta.Definition(), ta.action, input)
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
	return &toolAction{action: r.LookupAction(fmt.Sprintf("/tool/local/%s", name))}
}
