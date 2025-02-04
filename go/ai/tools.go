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
	Context   context.Context
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
func (ta *toolAction) RunRaw(ctx context.Context, input any) (any, error) {
	return runAction(ctx, ta, input)

}

// RunRaw runs this tool using the provided raw map format data (JSON parsed
// as map[string]any).
func (ta *ToolDef[In, Out]) RunRaw(ctx context.Context, input any) (any, error) {
	return runAction(ctx, ta, input)
}

func runAction(ctx context.Context, action Tool, input any) (any, error) {
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
		return nil, fmt.Errorf("error parsing tool output for %v: %v", action.Definition().Name, err)
	}
	return uo, nil
}

// LookupTool looks up the tool in the registry by provided name and returns it.
func LookupTool(r *registry.Registry, name string) Tool {
	return &toolAction{action: r.LookupAction(fmt.Sprintf("/tool/local/%s", name))}
}
