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
	"errors"
	"fmt"
	"maps"
	"reflect"
	"sync"

	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/core/api"
	"github.com/firebase/genkit/go/core/status"
	"github.com/firebase/genkit/go/internal/base"
)

// ToolFunc is the function type for tool implementations.
type ToolFunc[In, Out any] = func(ctx *ToolContext, input In) (Out, error)

// MultipartToolFunc is the function type for multipart tool implementations.
// Unlike regular tools that return just an output value, multipart tools
// can return both an output value and additional content parts (like media).
type MultipartToolFunc[In any] = func(ctx *ToolContext, input In) (*MultipartToolResponse, error)

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

// ToolAction is a tool backed by a registry action. It is the concrete type
// returned by [NewTool] and [NewMultipartTool].
// Internally, all tools use the v2 format (returning MultipartToolResponse).
// For regular tools, RunRaw unwraps the Output field for backward compatibility.
//
// It implements [Tool] and [api.Action], so it can be passed anywhere either
// is accepted, including the action slice a plugin returns from Init. Unlike
// the other primitives it holds its action in a named field rather than
// embedding it, so its documented methods are its whole surface.
//
// Interrupts are resolved on [InterruptibleToolAction], the tool type made for
// them, or on the part itself with [Part.ToToolRestart] and
// [Part.ToToolResponse]; the Respond, Restart, RespondWith, and RestartWith
// methods here are deprecated.
type ToolAction[In, Out any] struct {
	toolCore
}

// toolCore is the state and behavior shared by [ToolAction] and
// [InterruptibleToolAction]: the underlying action, how it is registered and
// run, and the definition advertised to models. The verbs that resolve an
// interrupt live on the outer types, which differ there.
type toolCore struct {
	action    api.Action   // The underlying action.
	multipart bool         // Whether this is a multipart-only tool.
	registry  api.Registry // Registry for schema resolution. Set when registered.
}

// Pinned here so that breaking either interface fails the build at the type
// rather than at a call site.
var (
	_ Tool       = (*ToolAction[any, any])(nil)
	_ api.Action = (*ToolAction[any, any])(nil)
)

// ToolDef is the previous name for [ToolAction]. It was renamed because it
// read as a sibling of [ToolDefinition], the wire type a tool advertises to
// the model, which it is not.
//
// Deprecated: use [ToolAction].
type ToolDef[In, Out any] = ToolAction[In, Out]

// Tool is the type-erased view of a tool: what a model can call, what
// [Generate] accepts through [WithTools] and [Hooks.Tools], and what
// [LookupTool] finds by name. The result of every constructor satisfies it:
// [ToolAction] from [NewTool] and [NewMultipartTool], [InterruptibleToolAction]
// from [NewInterruptibleTool], and their [genkit.DefineTool],
// [genkit.DefineMultipartTool], and [genkit.DefineInterruptibleTool]
// counterparts.
//
// A Tool runs; it does not resolve interrupts. Resolve them on the part with
// [Part.ToToolRestart] and [Part.ToToolResponse], which is all a type-erased
// handle could do, or with the typed verbs of an [InterruptibleToolAction].
type Tool interface {
	// Name returns the name of the tool.
	Name() string
	// Definition returns the definition for this tool to be passed to models.
	Definition() *ToolDefinition
	// RunRaw runs this tool using the provided raw input and returns just the output.
	RunRaw(ctx context.Context, input any) (any, error)
	// RunRawMultipart runs this tool and returns the full [MultipartToolResponse].
	RunRawMultipart(ctx context.Context, input any) (*MultipartToolResponse, error)
	// Register registers the tool with the given registry.
	Register(r api.Registry)
}

// IsToolInterruptError reports whether err is an interrupt raised by a tool
// call (see [tool.Interrupt]) and returns the interrupt data as a map. It is
// for code that runs a tool outside of [Generate], such as middleware; inside
// the loop, interrupts surface through [ModelResponse.Interrupts].
func IsToolInterruptError(err error) (bool, map[string]any) {
	var ie *base.ToolInterruptError
	if !errors.As(err, &ie) {
		return false, nil
	}
	m, _ := interruptPayload(ie.Data)
	return true, m
}

// interruptPayload converts interrupt data to the JSON object the wire contract
// requires: nil stays nil (a bare interrupt), a map is returned as is, and any
// other value is converted through JSON. A value that serializes to a JSON
// scalar or array is rejected.
func interruptPayload(data any) (map[string]any, error) {
	switch v := data.(type) {
	case nil:
		return nil, nil
	case map[string]any:
		return v, nil
	default:
		m, err := base.StructToMap(v)
		if err != nil {
			return nil, fmt.Errorf("must serialize to a JSON object (a struct or map), got %T: %w", data, err)
		}
		return m, nil
	}
}

// interruptData converts the metadata carried by an interrupt error into the
// payload for [ToolInterrupt.Data]. A nil map becomes an untyped nil (a bare
// interrupt), not a nil map in an interface.
func interruptData(metadata map[string]any) any {
	if metadata == nil {
		return nil
	}
	return metadata
}

// InterruptOptions provides configuration for tool interruption.
//
// Deprecated: InterruptOptions is the argument of the deprecated
// [ToolContext.Interrupt]. Use [tool.Interrupt] with a struct or a map.
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

// RespondWithOption is a functional option for [ToolAction.RespondWith].
//
// Deprecated: RespondWithOption is the option type of the deprecated
// [ToolAction.RespondWith]; [InterruptibleToolAction.Respond] and
// [Part.ToToolResponse] take none.
type RespondWithOption[Out any] interface {
	applyRespondWith(*RespondOptions)
}

// applyRespondWith applies the option to the respond options. Metadata is a
// single-value slot, so the last [WithResponseMetadata] set wins.
func (o *RespondOptions) applyRespondWith(opts *RespondOptions) {
	if o.Metadata != nil {
		opts.Metadata = o.Metadata
	}
}

// WithResponseMetadata sets metadata for the response. Repeating this option
// replaces the metadata rather than merging it.
//
// Deprecated: WithResponseMetadata only applies to the deprecated
// [ToolAction.RespondWith]. Set [Part.Metadata] on the part that
// [InterruptibleToolAction.Respond] or [Part.ToToolResponse] returns instead.
func WithResponseMetadata[Out any](meta map[string]any) RespondWithOption[Out] {
	return &RespondOptions{Metadata: meta}
}

// RestartWithOption is a restart option for [Part.ToToolRestart] and
// [InterruptibleToolAction.Restart]. It is
// the same option as [RestartOption], carrying the tool's input type in its
// signature so [WithNewInput] reads as typed at the call site; every
// RestartOption ([WithResume] included) is accepted where one is expected,
// and vice versa.
type RestartWithOption[In any] interface {
	RestartOption
}

// WithNewInput sets a new input value to replace the original tool request input.
// Repeating this option takes the last input set. On an
// [InterruptibleToolAction], the method of the same name checks the input
// against the tool's In type.
func WithNewInput[In any](input In) RestartWithOption[In] {
	return &RestartOptions{ReplaceInput: input}
}

// WithResumedMetadata sets metadata to pass to the resumed tool execution.
// The metadata will be available in the tool's [ToolContext.Resumed] field.
// Repeating this option replaces the metadata rather than merging it.
// [WithResume] is the same option for a typed value.
func WithResumedMetadata[In any](meta map[string]any) RestartWithOption[In] {
	return &RestartOptions{ResumedMetadata: meta}
}

// ToolContext provides context and utility functions for tool execution.
type ToolContext struct {
	context.Context
	// Resumed is optional metadata that can be used to resume the tool execution.
	// Map is not nil only if the tool was interrupted.
	Resumed map[string]any
	// OriginalInput is the original input to the tool if the tool was interrupted, otherwise nil.
	OriginalInput any
}

// Interrupt interrupts the tool execution and returns control to the caller
// with the total model response so far. The provided metadata is preserved
// and passed back via [ToolContext.Resumed] when the tool is restarted.
//
// Deprecated: Use [tool.Interrupt], which works in every tool because
// [ToolContext] embeds [context.Context]. It takes the payload directly, a
// struct or a map, and the caller reads a struct back with [InterruptAs].
func (tc *ToolContext) Interrupt(opts *InterruptOptions) error {
	if opts == nil {
		opts = &InterruptOptions{}
	}
	return &base.ToolInterruptError{Data: interruptData(opts.Metadata)}
}

// InterruptWith is a convenience function to interrupt a tool with a strongly-typed metadata value.
// The metadata is converted to map[string]any via JSON marshaling.
//
// Deprecated: Use [tool.Interrupt], which takes the same typed value and works
// in every tool because [ToolContext] embeds [context.Context].
func InterruptWith[T any](tc *ToolContext, meta T) error {
	m, err := base.StructToMap(meta)
	if err != nil {
		return fmt.Errorf("InterruptWith: failed to convert metadata: %w", err)
	}
	return &base.ToolInterruptError{Data: interruptData(m)}
}

// InterruptAs returns an interrupted tool request's interrupt data as a typed
// value, typically to decide between [Part.ToToolRestart] and
// [Part.ToToolResponse].
// Returns the zero value and false if the part is not an interrupt, the
// interrupt carries no data, or the type doesn't match.
//
// This reads the Data field of the part's [ToolInterrupt] state.
//
//	for _, part := range resp.Interrupts() {
//		req, ok := ai.InterruptAs[TransferInterrupt](part)
//	}
func InterruptAs[T any](p *Part) (T, bool) {
	var zero T
	if p == nil || !p.IsInterrupt() || p.Interrupt.Data == nil {
		return zero, false
	}
	return base.ConvertTo[T](p.Interrupt.Data)
}

// IsResumed returns true if this tool execution is a resumption after an interrupt.
func (tc *ToolContext) IsResumed() bool {
	return tc.Resumed != nil
}

// IsToolResumed reports whether the current context is a resumed tool execution.
// This is intended for use in middleware that needs to distinguish between
// first-time and restarted tool calls.
func IsToolResumed(ctx context.Context) bool {
	return base.ToolResumeKey.FromContext(ctx) != nil
}

// ResumedValue retrieves a typed value from the resumed metadata on ctx.
// Returns the zero value and false if the key doesn't exist or the type doesn't match.
// Accepts either a plain [context.Context] (useful in middleware) or a [*ToolContext],
// which embeds [context.Context].
func ResumedValue[T any](ctx context.Context, key string) (T, bool) {
	var zero T
	m := base.ToolResumeKey.FromContext(ctx)
	if m == nil {
		return zero, false
	}
	v, ok := m[key]
	if !ok {
		return zero, false
	}
	return base.ConvertTo[T](v)
}

// OriginalInputAs returns the original input typed appropriately.
// Returns the zero value and false if not resumed or type doesn't match.
func OriginalInputAs[T any](tc *ToolContext) (T, bool) {
	var zero T
	if tc.OriginalInput == nil {
		return zero, false
	}
	return base.ConvertTo[T](tc.OriginalInput)
}

// toolStrictKey is the metadata key under metadata["tool"] used to carry the
// per-tool strict-schema flag through the action metadata and onto
// [ToolDefinition.Metadata]. Plugins consume this key directly.
const toolStrictKey = "strict"

// applyStrictMetadata sets metadata["tool"][toolStrictKey] = *strict when
// strict is non-nil. A nil value leaves the metadata untouched.
func applyStrictMetadata(metadata map[string]any, strict *bool) {
	if strict == nil {
		return
	}
	toolMeta, _ := metadata["tool"].(map[string]any)
	if toolMeta == nil {
		toolMeta = map[string]any{}
		metadata["tool"] = toolMeta
	}
	toolMeta[toolStrictKey] = *strict
}

// applyToolOutputSchema records a custom output schema as the tool's
// advertised (original) output schema. The action's own output type stays the
// multipart envelope; [ToolAction.Definition] surfaces the original schema to the
// model and the Dev UI.
func applyToolOutputSchema(metadata map[string]any, schema map[string]any) {
	if schema != nil {
		metadata["originalOutputSchema"] = schema
	}
}

// requireAnyTypeParam panics unless the type parameter T is an interface type
// (in practice 'any'). The tool constructors call it before honoring an
// explicit schema option: the custom schema stands in for a type parameter of
// 'any', and a concrete T would silently disagree with the advertised schema.
// The requirement argument is the leading clause of the panic message, e.g.
// "WithInputSchema requires In".
func requireAnyTypeParam[T any](ctor, name, requirement string) {
	if typ := reflect.TypeFor[T](); typ.Kind() != reflect.Interface {
		panic(fmt.Errorf("%s %q: %s to be of type 'any', but got %v", ctor, name, requirement, typ))
	}
}

// NewTool creates a new [ToolAction]. It can be passed directly to [Generate].
// Use [WithInputSchema] or [WithOutputSchema] to provide custom JSON schemas
// instead of inferring them from the type parameters. Inside the function,
// [tool.AttachParts] adds content parts (e.g. media) to the response and
// [tool.SendPartial] streams progress, neither of which changes the signature.
func NewTool[In, Out any](name, description string, fn ToolFunc[In, Out], opts ...ToolOption) *ToolAction[In, Out] {
	c := newToolCore("ai.NewTool", name, description, opts, func(ctx context.Context, input In) (Out, error) {
		return fn(newToolContext(ctx), input)
	})
	return &ToolAction[In, Out]{toolCore: c}
}

// NewToolWithInputSchema creates a new [ToolAction] with a custom input schema. It can be passed directly to [Generate].
//
// Deprecated: Use [NewTool] with [WithInputSchema] instead.
func NewToolWithInputSchema[Out any](name, description string, inputSchema map[string]any, fn ToolFunc[any, Out]) *ToolAction[any, Out] {
	return NewTool(name, description, fn, WithInputSchema(inputSchema))
}

// NewMultipartTool creates a new multipart [ToolAction]. It can be passed directly to [Generate].
// Multipart tools can return both output data and additional content parts (like media).
// Use [WithInputSchema] to provide a custom JSON schema instead of inferring from the type parameter.
// Use [WithOutputSchema] or [WithOutputSchemaName] to advertise the logical
// output the tool produces (the envelope's output field); the wire format
// stays the multipart response envelope.
//
// Deprecated: Use [NewTool] and attach content parts with [tool.AttachParts],
// which keeps the output type (and therefore the advertised output schema).
func NewMultipartTool[In any](name, description string, fn MultipartToolFunc[In], opts ...ToolOption) *ToolAction[In, *MultipartToolResponse] {
	toolOpts := &toolOptions{}
	for _, opt := range opts {
		opt.applyTool(toolOpts)
	}

	// Out is fixed to the multipart envelope, so only In can disagree with an
	// explicit schema. WithOutputSchema describes the envelope's output field
	// and carries no such constraint.
	if toolOpts.InputSchema != nil {
		requireAnyTypeParam[In]("ai.NewMultipartTool", name, "WithInputSchema requires In")
	}

	metadata := toolMetadata(name, description, true, nil)
	applyToolOutputSchema(metadata, toolOpts.OutputSchema)
	applyStrictMetadata(metadata, toolOpts.StrictSchema)
	wrapped := func(ctx context.Context, input In) (*MultipartToolResponse, error) {
		return runToolFunc(ctx, name, func(ctx context.Context) (*MultipartToolResponse, error) {
			return fn(newToolContext(ctx), input)
		})
	}
	action := core.NewActionOf(api.ActionTypeToolV2, name, &core.ActionOptions{Metadata: metadata, InputSchema: toolOpts.InputSchema}, wrapped)
	return &ToolAction[In, *MultipartToolResponse]{toolCore: toolCore{action: action, multipart: true}}
}

// newToolCore builds the action behind a tool whose function returns Out:
// it applies the options, records Out's schema as the output the tool
// advertises, and wraps run in the multipart envelope every tool speaks
// internally. ctor names the constructor in panic messages.
func newToolCore[In, Out any](ctor, name, description string, opts []ToolOption, run func(ctx context.Context, input In) (Out, error)) toolCore {
	toolOpts := &toolOptions{}
	for _, opt := range opts {
		opt.applyTool(toolOpts)
	}

	if toolOpts.InputSchema != nil {
		requireAnyTypeParam[In](ctor, name, "WithInputSchema requires In")
	}
	if toolOpts.OutputSchema != nil {
		requireAnyTypeParam[Out](ctor, name, "WithOutputSchema and WithOutputSchemaName require Out")
	}

	metadata := toolMetadata(name, description, false, inferOutputSchema[Out]())
	applyToolOutputSchema(metadata, toolOpts.OutputSchema)
	applyStrictMetadata(metadata, toolOpts.StrictSchema)
	wrapped := func(ctx context.Context, input In) (*MultipartToolResponse, error) {
		return runToolFunc(ctx, name, func(ctx context.Context) (*MultipartToolResponse, error) {
			output, err := run(ctx, input)
			if err != nil {
				return nil, err
			}
			return &MultipartToolResponse{Output: output}, nil
		})
	}
	action := core.NewActionOf(api.ActionTypeToolV2, name, &core.ActionOptions{Metadata: metadata, InputSchema: toolOpts.InputSchema}, wrapped)
	return toolCore{action: action}
}

// toolMetadata builds the action metadata every tool constructor records. The
// action's own output schema is the multipart envelope, so the schema the tool
// advertises to models rides in originalOutputSchema, where [ToolAction.Definition]
// reads it; nil leaves it unset.
func toolMetadata(name, description string, multipart bool, originalOutputSchema map[string]any) map[string]any {
	metadata := map[string]any{
		"type":        api.ActionTypeToolV2,
		"name":        name,
		"description": description,
		"tool":        map[string]any{"multipart": multipart},
		"dynamic":     true,
	}
	if originalOutputSchema != nil {
		metadata["originalOutputSchema"] = originalOutputSchema
	}
	return metadata
}

// inferOutputSchema returns the JSON schema for the Out type parameter, or nil
// when Out carries no schema (e.g. any).
func inferOutputSchema[Out any]() map[string]any {
	var zero Out
	if reflect.TypeOf(zero) == nil {
		return nil
	}
	return core.InferSchemaMap(zero)
}

// newToolContext builds the [ToolContext] a tool function written against it
// receives, lifting the restart state off the context.
func newToolContext(ctx context.Context) *ToolContext {
	return &ToolContext{
		Context:       ctx,
		Resumed:       base.ToolResumeKey.FromContext(ctx),
		OriginalInput: base.ToolOriginalInputKey.FromContext(ctx),
	}
}

// runToolFunc runs one tool invocation: it installs the part sink that
// [tool.AttachParts] writes to, runs the function, folds the attached parts
// into the response, and validates an interrupt's payload where the tool ran
// rather than later in the generate loop.
func runToolFunc(ctx context.Context, name string, run func(ctx context.Context) (*MultipartToolResponse, error)) (*MultipartToolResponse, error) {
	// The sink may be called from goroutines the tool function spawns
	// (mirroring tool.SendPartial, which is also safe for concurrent use), so
	// guard the slice.
	var partsMu sync.Mutex
	var parts []*Part
	ctx = base.ToolPartSinkKey.NewContext(ctx, func(part any) {
		if p, ok := part.(*Part); ok {
			partsMu.Lock()
			parts = append(parts, p)
			partsMu.Unlock()
		}
	})

	resp, err := run(ctx)
	if err != nil {
		var ie *base.ToolInterruptError
		if errors.As(err, &ie) {
			if vErr := validateInterruptPayload(ie.Data, "interrupt data"); vErr != nil {
				return nil, fmt.Errorf("tool %q: %w", name, vErr)
			}
		}
		return nil, err
	}

	partsMu.Lock()
	defer partsMu.Unlock()
	if len(parts) > 0 {
		resp.Content = append(resp.Content, parts...)
	}
	return resp, nil
}

// Name returns the name of the tool.
func (t *toolCore) Name() string {
	return t.action.Name()
}

// Definition returns [ToolDefinition] for for this tool.
func (t *toolCore) Definition() *ToolDefinition {
	desc := t.action.Desc()

	// Resolve the input schema if it contains a $ref.
	inputSchema := desc.InputSchema
	if t.registry != nil {
		if resolved, err := core.ResolveSchema(t.registry, inputSchema); err == nil {
			inputSchema = resolved
		}
	}

	// Every tool function is wrapped in the multipart envelope, so the action's
	// own output schema describes that envelope, never the tool's real output.
	// Advertise the schema recorded at construction time from the output type
	// (or from an explicit [WithOutputSchema]), and nothing at all when the
	// output type carries no schema, e.g. any: an unconstrained output is
	// described by no schema, not by the envelope's.
	var outputSchema map[string]any
	if origSchema, ok := desc.Metadata["originalOutputSchema"].(map[string]any); ok {
		outputSchema = origSchema
	}

	// Resolve the output schema if it contains a $ref.
	if t.registry != nil && outputSchema != nil {
		if resolved, err := core.ResolveSchema(t.registry, outputSchema); err == nil {
			outputSchema = resolved
		}
	}

	metadata := map[string]any{
		"multipart": t.multipart,
	}
	if toolMeta, ok := desc.Metadata["tool"].(map[string]any); ok {
		if s, ok := toolMeta[toolStrictKey].(bool); ok {
			metadata[toolStrictKey] = s
		}
	}

	return &ToolDefinition{
		Name:         desc.Name,
		Description:  desc.Description,
		InputSchema:  inputSchema,
		OutputSchema: outputSchema,
		Metadata:     metadata,
	}
}

// Register registers the tool with the given registry.
func (t *toolCore) Register(r api.Registry) {
	t.registry = r
	t.action.Register(r)
	if !t.multipart {
		// Also register under the "tool" key for backward compatibility.
		provider, id := api.ParseName(t.action.Name())
		r.RegisterAction(api.NewKey(api.ActionTypeTool, provider, id), t.action)
	}
}

// Desc returns the tool's action descriptor: its name, schemas, and metadata.
func (t *toolCore) Desc() api.ActionDesc { return t.action.Desc() }

// runRawMultipart runs the tool on raw input (JSON parsed as map[string]any)
// and returns the full multipart response. The exported run methods live on
// the outer types, so that a nil tool value, typically a package-level
// variable used before it was defined, gets an error instead of a panic.
func (t *toolCore) runRawMultipart(ctx context.Context, input any) (*MultipartToolResponse, error) {
	mi, err := json.Marshal(input)
	if err != nil {
		return nil, status.Errorf(status.ErrInvalidInput, "marshalling input for tool %q: %w", t.Name(), err)
	}
	output, err := t.action.RunJSON(ctx, mi, nil)
	if err != nil {
		return nil, fmt.Errorf("error calling tool %v: %w", t.Name(), err)
	}

	var resp MultipartToolResponse
	if err := json.Unmarshal(output, &resp); err != nil {
		return nil, status.Errorf(status.ErrInvalidOutput, "parsing output of tool %q: %w", t.Name(), err)
	}
	return &resp, nil
}

// errNilTool is the error the run methods return when called on a nil tool
// value, typically a package-level tool variable used before it was defined.
func errNilTool(method string) error {
	return status.Errorf(status.ErrInvalidArgument, "ai.Tool.%s: tool called on a nil tool; check that all tools are defined", method)
}

// RunJSON runs the tool on JSON-encoded input and returns the JSON-encoded
// multipart response envelope, which is what the registry serves for this
// tool. Prefer [ToolAction.RunRaw], which unwraps the envelope's output for a
// regular tool.
func (t *ToolAction[In, Out]) RunJSON(ctx context.Context, input json.RawMessage, cb core.StreamCallback[json.RawMessage]) (json.RawMessage, error) {
	if t == nil {
		return nil, errNilTool("RunJSON")
	}
	return t.action.RunJSON(ctx, input, cb)
}

// RunJSONWithTelemetry is [ToolAction.RunJSON] with the run's telemetry
// returned alongside the output.
func (t *ToolAction[In, Out]) RunJSONWithTelemetry(ctx context.Context, input json.RawMessage, cb core.StreamCallback[json.RawMessage]) (*api.ActionRunResult[json.RawMessage], error) {
	if t == nil {
		return nil, errNilTool("RunJSONWithTelemetry")
	}
	return t.action.RunJSONWithTelemetry(ctx, input, cb)
}

// RunRaw runs this tool using the provided raw map format data (JSON parsed as map[string]any).
func (t *ToolAction[In, Out]) RunRaw(ctx context.Context, input any) (any, error) {
	resp, err := t.RunRawMultipart(ctx, input)
	if err != nil {
		return nil, err
	}
	return resp.Output, nil
}

// RunRawMultipart runs this tool using the provided raw map format data (JSON parsed as map[string]any).
// It returns the full multipart response.
func (t *ToolAction[In, Out]) RunRawMultipart(ctx context.Context, input any) (*MultipartToolResponse, error) {
	if t == nil {
		return nil, errNilTool("RunRawMultipart")
	}
	return t.runRawMultipart(ctx, input)
}

// LookupTool looks up the tool in the registry by provided name and returns it.
// It checks for "tool.v2" first, then falls back to "tool" for legacy compatibility.
// Since the types are not known at lookup time, it returns a type-erased tool;
// interrupts it raises are resolved on the part, with [Part.ToToolRestart] and
// [Part.ToToolResponse].
func LookupTool(r api.Registry, name string) Tool {
	if name == "" {
		return nil
	}
	provider, id := api.ParseName(name)

	// First try tool.v2 (all new tools are registered here)
	key := api.NewKey(api.ActionTypeToolV2, provider, id)
	action := r.ResolveAction(key)

	// Fall back to tool for legacy compatibility
	if action == nil {
		key = api.NewKey(api.ActionTypeTool, provider, id)
		action = r.ResolveAction(key)
	}

	if action == nil {
		return nil
	}

	desc := action.Desc()
	multipart := false
	if toolMeta, ok := desc.Metadata["tool"].(map[string]any); ok {
		if mp, ok := toolMeta["multipart"].(bool); ok {
			multipart = mp
		}
	}

	return &ToolAction[any, any]{toolCore: toolCore{action: action, multipart: multipart, registry: r}}
}

// IsMultipart returns true if the tool is a multipart tool (tool.v2 only).
func (t *toolCore) IsMultipart() bool {
	return t.multipart
}

// Respond creates a part for [WithToolResponses] to provide a resolved response for an interrupted tool call.
// Returns nil if the part is not a tool request.
//
// Deprecated: Use [Part.ToToolResponse], or define the tool with
// [genkit.DefineInterruptibleTool] and use [InterruptibleToolAction.Respond].
func (t *ToolAction[In, Out]) Respond(toolReq *Part, output any, opts *RespondOptions) *Part {
	if toolReq == nil || !toolReq.IsToolRequest() {
		return nil
	}

	if opts == nil {
		opts = &RespondOptions{}
	}

	return newResponsePart(toolReq, output, opts.Metadata)
}

// Restart creates a part for [WithToolRestarts] to re-execute an interrupted tool call with additional context.
// Returns nil if the part is not a tool request or the resume data does not
// serialize to a JSON object.
//
// Deprecated: Use [Part.ToToolRestart], or define the tool with
// [genkit.DefineInterruptibleTool] and use [InterruptibleToolAction.Restart].
func (t *ToolAction[In, Out]) Restart(p *Part, opts *RestartOptions) *Part {
	if p == nil || !p.IsToolRequest() {
		return nil
	}

	if opts == nil {
		opts = &RestartOptions{}
	}

	restart, err := newRestartPart("ai.Restart", p, []RestartOption{opts})
	if err != nil {
		return nil
	}
	return restart
}

// RespondWith creates a part for [WithToolResponses] to provide a resolved response for an interrupted tool call.
//
// Example:
//
//	part, err := myTool.RespondWith(toolReq, output, WithResponseMetadata[MyOutput](meta))
//
// Deprecated: Define the tool with [genkit.DefineInterruptibleTool] and use
// [InterruptibleToolAction.Respond], or answer the part directly with
// [Part.ToToolResponse].
func (t *ToolAction[In, Out]) RespondWith(toolReq *Part, output Out, opts ...RespondWithOption[Out]) (*Part, error) {
	if toolReq == nil {
		return nil, status.Errorf(status.ErrInvalidArgument, "ai.RespondWith: toolReq is nil")
	}
	if !toolReq.IsToolRequest() {
		return nil, status.Errorf(ErrInvalidPart, "ai.RespondWith: part is not a tool request")
	}
	if toolReq.ToolRequest.Name != t.Name() {
		return nil, status.Errorf(status.ErrInvalidArgument, "ai.RespondWith: tool request is for %q, not %q", toolReq.ToolRequest.Name, t.Name())
	}

	cfg := &RespondOptions{}
	for _, opt := range opts {
		opt.applyRespondWith(cfg)
	}

	return newResponsePart(toolReq, output, cfg.Metadata), nil
}

// RestartWith creates a part for [WithToolRestarts] to re-execute an interrupted tool call with additional context.
//
// Example:
//
//	part, err := myTool.RestartWith(toolReq, WithNewInput(newInput), WithResumedMetadata[MyInput](meta))
//
// Deprecated: Define the tool with [genkit.DefineInterruptibleTool] and use
// [InterruptibleToolAction.Restart], or restart the part directly with
// [Part.ToToolRestart].
func (t *ToolAction[In, Out]) RestartWith(toolReq *Part, opts ...RestartWithOption[In]) (*Part, error) {
	if toolReq == nil {
		return nil, status.Errorf(status.ErrInvalidArgument, "ai.RestartWith: toolReq is nil")
	}
	if !toolReq.IsToolRequest() {
		return nil, status.Errorf(ErrInvalidPart, "ai.RestartWith: part is not a tool request")
	}
	if toolReq.ToolRequest.Name != t.Name() {
		return nil, status.Errorf(status.ErrInvalidArgument, "ai.RestartWith: tool request is for %q, not %q", toolReq.ToolRequest.Name, t.Name())
	}

	restartOpts := make([]RestartOption, len(opts))
	for i, opt := range opts {
		restartOpts[i] = opt
	}
	return newRestartPart("ai.RestartWith", toolReq, restartOpts)
}

// --- Interruptible tools ---

// InterruptibleToolFunc is the function type for tools created with
// [NewInterruptibleTool]. It receives a plain [context.Context]: the resume
// parameter carries everything [ToolContext] exists for. It is nil on the
// first call and non-nil when the tool is being re-executed after an
// interrupt, holding the data the caller passed when restarting (the zero
// value of Res for a bare restart).
type InterruptibleToolFunc[In, Out, Res any] = func(ctx context.Context, input In, resume *Res) (Out, error)

// InterruptibleToolAction is a tool that supports typed interrupt/resume. The
// Res type parameter is the type of data the caller sends back when resuming
// the tool after an interrupt. Create one with [NewInterruptibleTool] or
// [genkit.DefineInterruptibleTool].
//
// Inside the function, [tool.Interrupt] pauses execution with typed data that
// the caller reads with [InterruptAs]. The caller then re-executes the tool
// with [InterruptibleToolAction.Restart], passing
// [InterruptibleToolAction.WithResume] to deliver a Res (and
// [InterruptibleToolAction.WithNewInput] to revise the input), or answers the
// call outright with [InterruptibleToolAction.Respond]. Both check that the
// interrupted part belongs to this tool.
//
// It is a [Tool] and an [api.Action], so it goes wherever either is accepted:
// [WithTools], [Hooks.Tools], or a plugin's action list. Callers that hold
// only the part, such as an application resolving an interrupt raised by a
// middleware's tool, use [Part.ToToolRestart] and [Part.ToToolResponse].
type InterruptibleToolAction[In, Out, Res any] struct {
	toolCore
}

// Pinned here so that breaking either interface fails the build at the type
// rather than at a call site.
var (
	_ Tool       = (*InterruptibleToolAction[any, any, any])(nil)
	_ api.Action = (*InterruptibleToolAction[any, any, any])(nil)
)

// NewInterruptibleTool creates a new unregistered [InterruptibleToolAction].
// It can be passed directly to [Generate], which registers it for the duration
// of the call. Use [WithInputSchema] or [WithOutputSchema] to provide custom
// JSON schemas instead of inferring them from the type parameters.
//
// The resume payload must serialize to a JSON object (a struct or a map), since
// it is carried on the restart part; a payload that does not decode into Res
// fails the resumed call rather than silently arriving as a zero value.
func NewInterruptibleTool[In, Out, Res any](name, description string, fn InterruptibleToolFunc[In, Out, Res], opts ...ToolOption) *InterruptibleToolAction[In, Out, Res] {
	c := newToolCore("ai.NewInterruptibleTool", name, description, opts, func(ctx context.Context, input In) (Out, error) {
		var resume *Res
		if v := base.ToolResumeKey.FromContext(ctx); v != nil {
			r, err := base.MapToStruct[Res](v)
			if err != nil {
				var zero Out
				return zero, fmt.Errorf("tool %q: failed to convert resume data: %w", name, err)
			}
			resume = &r
		}
		return fn(ctx, input, resume)
	})
	return &InterruptibleToolAction[In, Out, Res]{toolCore: c}
}

// RunJSON runs the tool on JSON-encoded input and returns the JSON-encoded
// multipart response envelope, which is what the registry serves for this
// tool. Prefer [InterruptibleToolAction.RunRaw], which unwraps the envelope's
// output.
func (t *InterruptibleToolAction[In, Out, Res]) RunJSON(ctx context.Context, input json.RawMessage, cb core.StreamCallback[json.RawMessage]) (json.RawMessage, error) {
	if t == nil {
		return nil, errNilTool("RunJSON")
	}
	return t.action.RunJSON(ctx, input, cb)
}

// RunJSONWithTelemetry is [InterruptibleToolAction.RunJSON] with the run's
// telemetry returned alongside the output.
func (t *InterruptibleToolAction[In, Out, Res]) RunJSONWithTelemetry(ctx context.Context, input json.RawMessage, cb core.StreamCallback[json.RawMessage]) (*api.ActionRunResult[json.RawMessage], error) {
	if t == nil {
		return nil, errNilTool("RunJSONWithTelemetry")
	}
	return t.action.RunJSONWithTelemetry(ctx, input, cb)
}

// RunRaw runs this tool using the provided raw map format data (JSON parsed as
// map[string]any) and returns just the output.
func (t *InterruptibleToolAction[In, Out, Res]) RunRaw(ctx context.Context, input any) (any, error) {
	resp, err := t.RunRawMultipart(ctx, input)
	if err != nil {
		return nil, err
	}
	return resp.Output, nil
}

// RunRawMultipart runs this tool using the provided raw map format data (JSON
// parsed as map[string]any) and returns the full multipart response.
func (t *InterruptibleToolAction[In, Out, Res]) RunRawMultipart(ctx context.Context, input any) (*MultipartToolResponse, error) {
	if t == nil {
		return nil, errNilTool("RunRawMultipart")
	}
	return t.runRawMultipart(ctx, input)
}

// Restart creates a part for [WithToolRestarts] that re-executes this tool's
// interrupted call. Pass [InterruptibleToolAction.WithResume] to deliver the
// answer to the tool's resume parameter and
// [InterruptibleToolAction.WithNewInput] to revise the input. The part must be
// an unresolved interrupt for this tool; [Part.ToToolRestart] is the same verb
// for a part whose tool is not in scope.
func (t *InterruptibleToolAction[In, Out, Res]) Restart(interruptPart *Part, opts ...RestartOption) (*Part, error) {
	const fnName = "ai.InterruptibleToolAction.Restart"
	part, err := t.ownedInterrupt(fnName, interruptPart)
	if err != nil {
		return nil, err
	}
	return newRestartPart(fnName, part, opts)
}

// Respond creates a part for [WithToolResponses] that answers this tool's
// interrupted call with output, without re-executing the tool. The output is
// validated against the tool's output schema when generation resumes. The part
// must be an unresolved interrupt for this tool; [Part.ToToolResponse] is the
// same verb for a part whose tool is not in scope.
func (t *InterruptibleToolAction[In, Out, Res]) Respond(interruptPart *Part, output Out) (*Part, error) {
	part, err := t.ownedInterrupt("ai.InterruptibleToolAction.Respond", interruptPart)
	if err != nil {
		return nil, err
	}
	return newResponsePart(part, output, nil), nil
}

// WithResume returns a restart option carrying data to this tool's resume
// parameter, checked against the tool's Res type at the call site. See
// [WithResume] for the semantics.
func (t *InterruptibleToolAction[In, Out, Res]) WithResume(resume Res) RestartOption {
	return WithResume(resume)
}

// WithNewInput returns a restart option providing a new input for this tool
// when it re-executes, checked against the tool's In type at the call site.
// See [WithNewInput] for the semantics.
func (t *InterruptibleToolAction[In, Out, Res]) WithNewInput(input In) RestartOption {
	return WithNewInput(input)
}

// ownedInterrupt checks that p is an unresolved interrupt addressed to this
// tool and returns it with its interrupt state in typed form (see
// interruptPartOf), for the verbs that resolve an interrupt on the tool value.
func (t *toolCore) ownedInterrupt(fnName string, p *Part) (*Part, error) {
	if p == nil {
		return nil, status.Errorf(status.ErrInvalidArgument, "%s: part is nil", fnName)
	}
	p, ok := interruptPartOf(p)
	if !ok {
		return nil, status.Errorf(ErrInvalidPart, "%s: part is not an interrupted tool request", fnName)
	}
	if p.ToolRequest.Name != t.Name() {
		return nil, status.Errorf(status.ErrInvalidArgument, "%s: tool request is for %q, not %q", fnName, p.ToolRequest.Name, t.Name())
	}
	return p, nil
}

// --- Resolving an interrupt ---

// RestartOption configures the restart part built by [Part.ToToolRestart].
// [WithResume], [WithNewInput], and [WithResumedMetadata] are the options.
type RestartOption interface {
	applyRestart(*restartOptions)
}

// restartOptions holds the resolved configuration for a restart part.
type restartOptions struct {
	resume   any
	newInput any
}

// applyRestart applies the option to the restart options. The last value set
// for a field wins.
func (o *RestartOptions) applyRestart(opts *restartOptions) {
	if o.ResumedMetadata != nil {
		opts.resume = o.ResumedMetadata
	}
	if o.ReplaceInput != nil {
		opts.newInput = o.ReplaceInput
	}
}

// WithResume delivers data to the restarted tool when it re-executes: the
// resume parameter of an interruptible tool, or [ToolContext.Resumed] and
// [ResumedValue] for a tool written against [ToolContext]. Without it, the tool
// re-executes with an empty resume payload, so restarting is itself the
// approval for tools that key on the presence of a resume.
//
// The data must serialize to a JSON object (a struct or a map): it lands on the
// restart part as [ToolRestart] data, which the wire protocol encodes as a JSON
// object in the part's metadata.
func WithResume(resume any) RestartOption {
	return &RestartOptions{ResumedMetadata: resume}
}

// ToToolRestart converts this interrupted tool request into a restart [Part]
// that re-executes the tool, for use with [WithToolRestarts]. The receiver
// must be an interrupted tool request, as received via
// [ModelResponse.Interrupts]. Use [WithResume] to deliver data to the
// restarted tool, and [WithNewInput] to provide a new input.
//
//	for _, part := range resp.Interrupts() {
//		restart, err := part.ToToolRestart(ai.WithResume(Confirmation{Approved: true}))
//	}
func (p *Part) ToToolRestart(opts ...RestartOption) (*Part, error) {
	p, ok := interruptPartOf(p)
	if !ok {
		return nil, status.Errorf(ErrInvalidPart, "ai.Part.ToToolRestart: part is not an interrupted tool request")
	}
	return newRestartPart("ai.Part.ToToolRestart", p, opts)
}

// ToToolResponse converts this interrupted tool request into a tool response
// [Part], for use with [WithToolResponses]. Instead of re-executing the tool
// (as [Part.ToToolRestart] does), this provides a pre-computed result directly.
// The output is validated against the tool's output schema when generation
// resumes.
func (p *Part) ToToolResponse(output any) (*Part, error) {
	p, ok := interruptPartOf(p)
	if !ok {
		return nil, status.Errorf(ErrInvalidPart, "ai.Part.ToToolResponse: part is not an interrupted tool request")
	}
	return newResponsePart(p, output, nil), nil
}

// interruptPartOf returns p with its interrupt state in typed form and reports
// whether it is an unresolved interrupt. Parts built by the loop or read off
// the wire carry the typed state already and are returned as is. A part a
// caller hand-assembled with the JS "interrupt" metadata key is lifted on a
// copy, so the caller's map is untouched and the key does not ride along onto
// the part built from it. This keeps the part verbs as lenient as the
// type-erased tool verbs they replace.
func interruptPartOf(p *Part) (*Part, bool) {
	if p == nil {
		return nil, false
	}
	if p.Interrupt == nil && p.Metadata != nil {
		if _, ok := p.Metadata[base.ToolMetaInterrupt]; ok {
			lifted := p.Clone()
			lifted.liftWireMetadata()
			p = lifted
		}
	}
	return p, p.IsInterrupt()
}

// newRestartPart builds the tool request [Part] that re-executes an interrupted
// call, applying the given restart options. fnName is woven into error
// messages. The new part keeps the interrupted part's metadata but not its
// interrupt state; when a new input is provided, the original is preserved on
// [ToolRestart.OriginalInput].
func newRestartPart(fnName string, interruptPart *Part, opts []RestartOption) (*Part, error) {
	cfg := &restartOptions{}
	for _, opt := range opts {
		opt.applyRestart(cfg)
	}
	if err := validateInterruptPayload(cfg.resume, "resume data"); err != nil {
		return nil, status.Errorf(status.ErrInvalidArgument, "%s: %w", fnName, err)
	}

	toolReq := interruptPart.ToolRequest
	input := toolReq.Input
	var originalInput any
	if cfg.newInput != nil {
		originalInput = input
		input = cfg.newInput
	}

	restartPart := NewToolRequestPart(&ToolRequest{
		Name:  toolReq.Name,
		Ref:   toolReq.Ref,
		Input: input,
	})
	restartPart.Metadata = maps.Clone(interruptPart.Metadata)
	restartPart.Restart = &ToolRestart{Resume: cfg.resume, OriginalInput: originalInput}
	return restartPart, nil
}

// newResponsePart builds the tool response [Part] that resolves an interrupted
// call with a pre-computed output. The interruptResponse marker tells the
// generate loop to resolve the interrupt instead of re-executing the tool;
// metadata, when non-nil, replaces the bare marker.
func newResponsePart(interruptPart *Part, output any, metadata map[string]any) *Part {
	resp := NewResponseForToolRequest(interruptPart, output)
	resp.Metadata = map[string]any{base.ToolMetaInterruptResponse: true}
	if metadata != nil {
		resp.Metadata[base.ToolMetaInterruptResponse] = metadata
	}
	return resp
}

// restartStateOf returns a restart part's typed state, tolerating a part whose
// state is still in raw wire metadata. Parts built by [Part.ToToolRestart] and
// friends, and parts read off the wire, carry the typed state; a part a caller
// hand-assembled with the JS metadata keys is lifted here (on a copy, so the
// caller's map is untouched) rather than silently restarting with no resume
// data.
func restartStateOf(p *Part) *ToolRestart {
	if p == nil {
		return nil
	}
	if p.Restart != nil {
		return p.Restart
	}
	lifted := p.Clone()
	lifted.liftWireMetadata()
	return lifted.Restart
}

// resumePayload converts a restart's resume data to the map the tool sees on
// its context. A payload set in process is typically a struct, so it is
// converted the same way a JSON round trip through another runtime would; a
// bare restart yields an empty map, which still marks the call as a resumption.
func resumePayload(resume any) (map[string]any, error) {
	switch v := resume.(type) {
	case nil:
		return map[string]any{}, nil
	case map[string]any:
		return v, nil
	default:
		m, err := base.StructToMap(v)
		if err != nil {
			return nil, fmt.Errorf("resume data must serialize to a JSON object (a struct or map), got %T: %w", resume, err)
		}
		return m, nil
	}
}

// validateInterruptPayload checks that an interrupt or resume payload
// serializes to a JSON object, as the wire contract requires (an object, or
// bare when the payload is nil). what names the payload in the error message.
func validateInterruptPayload(data any, what string) error {
	if data == nil {
		return nil
	}
	if _, ok := data.(map[string]any); ok {
		return nil
	}
	if _, err := base.StructToMap(data); err != nil {
		return fmt.Errorf("%s must serialize to a JSON object (a struct or map), got %T: %w", what, data, err)
	}
	return nil
}

// resolveUniqueTools resolves the list of tool refs to a list of all tool names and new tools that must be registered.
// Returns an error if there are tool refs with duplicate names.
func resolveUniqueTools(r api.Registry, toolRefs []ToolRef) (toolNames []string, newTools []Tool, err error) {
	toolMap := make(map[string]bool)

	for _, toolRef := range toolRefs {
		name := toolRef.Name()

		if toolMap[name] {
			return nil, nil, status.Errorf(status.ErrInvalidArgument, "duplicate tool %q", name)
		}
		toolMap[name] = true
		toolNames = append(toolNames, name)

		if LookupTool(r, name) == nil {
			if tool, ok := toolRef.(Tool); ok {
				newTools = append(newTools, tool)
			}
		}
	}

	return toolNames, newTools, nil
}
