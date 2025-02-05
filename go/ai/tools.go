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
	action *core.Action[In, Out, struct{}]
}

// toolAction is genericless version of ToolDef. It's required to make
// LookupTool possible.
type toolAction struct {
	action action.Action
}

// Tool represents an instance of a tool.
type Tool interface {
	// Definition returns ToolDefinition for for this tool.
	Definition() *ToolDefinition
	// Action returns the action instance that backs this tools.
	Action() action.Action
	// RunRaw runs this tool using the provided raw map format data (JSON parsed
	// as map[string]any).
	RunRaw(ctx context.Context, input map[string]any) (any, error)
}

// DefineTool defines a tool function.
func DefineTool[In, Out any](r *registry.Registry, name, description string, fn func(ctx context.Context, input In) (Out, error)) *ToolDef[In, Out] {
	metadata := make(map[string]any)
	metadata["type"] = "tool"
	metadata["name"] = name
	metadata["description"] = description

	toolAction := core.DefineAction(r, provider, name, atype.Tool, metadata, fn)

	return &ToolDef[In, Out]{
		action: toolAction,
	}
}

// Action returns the action instance that backs this tools.
func (ta *ToolDef[In, Out]) Action() action.Action {
	return ta.action
}

// Action returns the action instance that backs this tools.
func (ta *toolAction) Action() action.Action {
	return ta.action
}

// Definition returns ToolDefinition for for this tool.
func (ta *ToolDef[In, Out]) Definition() *ToolDefinition {
	return definition(ta)
}

// Definition returns ToolDefinition for for this tool.
func (ta *toolAction) Definition() *ToolDefinition {
	return definition(ta)
}

func definition(ta Tool) *ToolDefinition {
	return &ToolDefinition{
		Name:         ta.Action().Desc().Metadata["name"].(string),
		Description:  ta.Action().Desc().Metadata["description"].(string),
		InputSchema:  base.SchemaAsMap(ta.Action().Desc().InputSchema),
		OutputSchema: base.SchemaAsMap(ta.Action().Desc().OutputSchema),
	}
}

// RunRaw runs this tool using the provided raw map format data (JSON parsed
// as map[string]any).
func (ta *toolAction) RunRaw(ctx context.Context, input map[string]any) (any, error) {
	return runAction(ctx, ta, input)

}

// RunRaw runs this tool using the provided raw map format data (JSON parsed
// as map[string]any).
func (ta *ToolDef[In, Out]) RunRaw(ctx context.Context, input map[string]any) (any, error) {
	return runAction(ctx, ta, input)
}

func runAction(ctx context.Context, action Tool, input map[string]any) (any, error) {
	mi, err := json.Marshal(input)
	if err != nil {
		return nil, fmt.Errorf("error marshalling tool input for %v: %v", action.Definition().Name, err)
	}
	output, err := action.Action().RunJSON(ctx, mi, nil)
	if err != nil {
		return nil, fmt.Errorf("error calling tool %v: %v", action.Definition().Name, err)
	}

	var uo any
	err = json.Unmarshal(output, &uo)
	if err != nil {
		return nil, fmt.Errorf("error parsing tool input for %v: %v", action.Definition().Name, err)
	}
	return uo, nil
}

// LookupTool looks up the tool in the registry by provided name and returns it.
func LookupTool(r *registry.Registry, name string) Tool {
	return &toolAction{action: r.LookupAction(fmt.Sprintf("/tool/local/%s", name))}
}
