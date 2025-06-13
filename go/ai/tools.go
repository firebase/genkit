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
	"maps"

	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/internal/base"
	"github.com/firebase/genkit/go/internal/registry"
	"github.com/invopop/jsonschema"
)

var resumedCtxKey = base.NewContextKey[map[string]any]()
var origInputCtxKey = base.NewContextKey[any]()

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

// tool is the internal implementation of the Tool interface.
// It holds the underlying core action and allows looking up tools
// by name without knowing their specific input/output types.
type tool struct {
	core.Action
}

// Tool represents an instance of a tool.
type Tool interface {
	// Name returns the name of the tool.
	Name() string
	// Definition returns ToolDefinition for for this tool.
	Definition() *ToolDefinition
	// RunRaw runs this tool using the provided raw input.
	RunRaw(ctx context.Context, input any) (any, error)
	// Register sets the tracing state on the action and registers it with the registry.
	Register(r *registry.Registry)
	// Respond constructs a *Part with a ToolResponse for a given interrupted tool request.
	Respond(toolReq *Part, outputData any, opts *RespondOptions) *Part
	// Restart constructs a *Part with a new ToolRequest to re-trigger a tool,
	// potentially with new input and metadata.
	Restart(toolReq *Part, opts *RestartOptions) *Part
}

// toolInterruptError represents an intentional interruption of tool execution.
type toolInterruptError struct {
	Metadata map[string]any
}

func (e *toolInterruptError) Error() string {
	return "tool execution interrupted"
}

// InterruptOptions provides configuration for tool interruption.
type InterruptOptions struct {
	Metadata map[string]any
}

// RestartOptions provides configuration options for restarting a tool.
type RestartOptions struct {
	// ReplaceInput allows replacing the existing input arguments to the tool with different ones,
	// for example if the user revised an action before confirming. When input is replaced,
	// the existing tool request will be amended in the message history.
	ReplaceInput any
	// ResumedMetadata is the metadata you want to provide to the tool to aide in reprocessing.
	// Defaults to true if none is supplied.
	ResumedMetadata any
}

// RespondOptions provides configuration options for responding to a tool request.
type RespondOptions struct {
	// Metadata is additional metadata to include in the response.
	Metadata map[string]any
}

// ToolContext provides context and utility functions for tool execution.
type ToolContext struct {
	context.Context
	// Interrupt is a function that can be used to interrupt the tool execution.
	// Interrupting tool execution returns the control to the caller with the
	// total model response so far.
	Interrupt func(opts *InterruptOptions) error
	// Resumed is optional metadata that can be used to resume the tool execution.
	// Map is not nil only if the tool was interrupted.
	Resumed map[string]any
	// OriginalInput is the original input to the tool if the tool was interrupted, otherwise nil.
	OriginalInput any
}

// DefineTool defines a tool.
func DefineTool[In, Out any](r *registry.Registry, name, description string,
	fn func(ctx *ToolContext, input In) (Out, error)) Tool {
	metadata, wrappedFn := implementTool(name, description, fn)
	toolAction := core.DefineAction(r, "", name, core.ActionTypeTool, metadata, wrappedFn)
	return &tool{Action: toolAction}
}

// DefineToolWithInputSchema defines a tool function with a custom input schema.
func DefineToolWithInputSchema[Out any](r *registry.Registry, name, description string,
	inputSchema *jsonschema.Schema,
	fn func(ctx *ToolContext, input any) (Out, error)) Tool {
	metadata, wrappedFn := implementTool(name, description, fn)
	toolAction := core.DefineActionWithInputSchema(r, "", name, core.ActionTypeTool, metadata, inputSchema, wrappedFn)
	return &tool{Action: toolAction}
}

// NewTool creates a tool but does not register it in the registry. It can be passed directly to [Generate].
func NewTool[In, Out any](name, description string,
	fn func(ctx *ToolContext, input In) (Out, error)) Tool {
	metadata, wrappedFn := implementTool(name, description, fn)
	metadata["dynamic"] = true
	toolAction := core.NewAction("", name, core.ActionTypeTool, metadata, wrappedFn)
	return &tool{Action: toolAction}
}

// implementTool creates the metadata and wrapped function common to both DefineTool and NewTool.
func implementTool[In, Out any](name, description string, fn func(ctx *ToolContext, input In) (Out, error)) (map[string]any, func(context.Context, In) (Out, error)) {
	metadata := map[string]any{
		"type":        core.ActionTypeTool,
		"name":        name,
		"description": description,
	}
	wrappedFn := func(ctx context.Context, input In) (Out, error) {
		toolCtx := &ToolContext{
			Context: ctx,
			Interrupt: func(opts *InterruptOptions) error {
				return &toolInterruptError{
					Metadata: opts.Metadata,
				}
			},
			Resumed:       resumedCtxKey.FromContext(ctx),
			OriginalInput: origInputCtxKey.FromContext(ctx),
		}
		return fn(toolCtx, input)
	}

	return metadata, wrappedFn
}

// Name returns the name of the tool.
func (t *tool) Name() string {
	return t.Action.Name()
}

// Definition returns [ToolDefinition] for for this tool.
func (t *tool) Definition() *ToolDefinition {
	desc := t.Action.Desc()
	td := &ToolDefinition{
		Name:        desc.Name,
		Description: desc.Description,
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
	return runAction(ctx, t.Definition(), t.Action, input)
}

// Register sets the tracing state on the action and registers it with the registry.
func (t *tool) Register(r *registry.Registry) {
	t.Action.SetTracingState(r.TracingState())
	r.RegisterAction(fmt.Sprintf("/%s/%s", core.ActionTypeTool, t.Action.Name()), t.Action)
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

	action := r.LookupAction(fmt.Sprintf("/%s/%s", core.ActionTypeTool, name))
	if action == nil {
		return nil
	}
	return &tool{Action: action.(core.Action)}
}

// Respond creates a tool response for an interrupted tool call to pass to the [WithToolResponses] option to [Generate].
// If the part provided is not a tool request, it returns nil.
func (t *tool) Respond(toolReq *Part, output any, opts *RespondOptions) *Part {
	if toolReq == nil || !toolReq.IsToolRequest() {
		return nil
	}

	if opts == nil {
		opts = &RespondOptions{}
	}

	newToolResp := NewResponseForToolRequest(toolReq, output)
	newToolResp.Metadata = map[string]any{
		"interruptResponse": true,
	}
	if opts.Metadata != nil {
		newToolResp.Metadata["interruptResponse"] = opts.Metadata
	}

	return newToolResp
}

// Restart creates a tool request for an interrupted tool call to pass to the [WithToolRestarts] option to [Generate].
// If the part provided is not a tool request, it returns nil.
func (t *tool) Restart(p *Part, opts *RestartOptions) *Part {
	if p == nil || !p.IsToolRequest() {
		return nil
	}

	if opts == nil {
		opts = &RestartOptions{}
	}

	newInput := p.ToolRequest.Input
	var originalInput any

	if opts.ReplaceInput != nil {
		originalInput = newInput
		newInput = opts.ReplaceInput
	}

	newMeta := maps.Clone(p.Metadata)
	if newMeta == nil {
		newMeta = make(map[string]any)
	}

	newMeta["resumed"] = true
	if opts.ResumedMetadata != nil {
		newMeta["resumed"] = opts.ResumedMetadata
	}

	if originalInput != nil {
		newMeta["replacedInput"] = originalInput
	}

	delete(newMeta, "interrupt")

	newToolReq := NewToolRequestPart(&ToolRequest{
		Name:  p.ToolRequest.Name,
		Ref:   p.ToolRequest.Ref,
		Input: newInput,
	})
	newToolReq.Metadata = newMeta

	return newToolReq
}
