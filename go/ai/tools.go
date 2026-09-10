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

// InterruptibleToolFunc is the function type for tools created with
// [NewInterruptibleTool]. It receives a plain [context.Context]: the resume
// parameter carries everything [ToolContext] exists for. It is nil on the
// first call and non-nil when the tool is being re-executed after an
// interrupt, holding the data the caller passed when restarting (the zero
// value of Res for a bare restart).
type InterruptibleToolFunc[In, Out, Res any] = func(ctx context.Context, input In, resume *Res) (Out, error)

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

// InterruptibleToolAction is a tool backed by a registry action, the concrete
// type behind every tool constructor. In is the input the model fills in, Out
// is what the tool returns, and Res is what the tool is restarted with after
// it interrupts. [ToolAction] is the same type with Res fixed to a map, for
// tools that do not declare a resume type.
//
// It implements [Tool] and [api.Action], so it goes wherever either is
// accepted: [WithTools], [Hooks.Tools], or the action slice a plugin returns
// from Init. Unlike the other primitives it holds its action in a named field
// rather than embedding it, so its documented methods are its whole surface.
//
// An interrupt the tool raises comes back as a part in
// [ModelResponse.Interrupts]. [InterruptibleToolAction.Interrupted] claims
// the part for this tool and returns an [InterruptedCall], whose typed verbs
// build the part that resumes generation through [WithResume]:
//
//	for _, part := range resp.Interrupts() {
//		if call, ok := transferMoney.Interrupted(part); ok {
//			approved := askHuman(call.Input.Amount, call.Input.ToAccount)
//			parts = append(parts, call.Restart(Confirmation{Approved: approved}))
//		}
//	}
type InterruptibleToolAction[In, Out, Res any] struct {
	action   api.Action   // The underlying action.
	registry api.Registry // Registry for schema resolution. Set when registered.
}

// ToolAction is the tool type [NewTool] and [LookupTool] return: an
// [InterruptibleToolAction] whose resume payload is an untyped map,
// the map a tool written against [ToolContext] reads from
// [ToolContext.Resumed]. Every method of [InterruptibleToolAction] is
// available on it, with [InterruptedCall.Restart] taking a map[string]any.
type ToolAction[In, Out any] = InterruptibleToolAction[In, Out, map[string]any]

// Pinned here so that breaking either interface fails the build at the type
// rather than at a call site.
var (
	_ Tool       = (*InterruptibleToolAction[any, any, any])(nil)
	_ api.Action = (*InterruptibleToolAction[any, any, any])(nil)
)

// ToolDef is the previous name for [ToolAction]. It was renamed because it
// read as a sibling of [ToolDefinition], the wire type a tool advertises to
// the model, which it is not.
//
// Deprecated: use [ToolAction].
type ToolDef[In, Out any] = ToolAction[In, Out]

// Tool is the type-erased view of a tool: what a model can call, what
// [Generate] accepts through [WithTools] and [Hooks.Tools], and what
// [LookupTool] finds by name. The result of every constructor satisfies it.
//
// A Tool runs. An interrupt it raised is resolved on the part, with
// [Part.ToToolRestart] and [Part.ToToolResponse], or with the typed verbs of
// the tool value when it is in scope (see
// [InterruptibleToolAction.Interrupted]). The Respond and Restart methods here
// are deprecated.
type Tool interface {
	// Name returns the name of the tool.
	Name() string
	// Definition returns the definition for this tool to be passed to models.
	Definition() *ToolDefinition
	// RunRaw runs this tool using the provided raw input and returns just the output.
	RunRaw(ctx context.Context, input any) (any, error)
	// RunRawMultipart runs this tool and returns the full [MultipartToolResponse].
	RunRawMultipart(ctx context.Context, input any) (*MultipartToolResponse, error)
	// Respond creates a part that answers an interrupted tool request.
	//
	// Deprecated: Use [Part.ToToolResponse].
	Respond(toolReq *Part, outputData any, opts *RespondOptions) *Part
	// Restart creates a part that re-executes an interrupted tool request.
	//
	// Deprecated: Use [Part.ToToolRestart].
	Restart(toolReq *Part, opts *RestartOptions) *Part
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
	m, _ := objectPayload(ie.Data, "interrupt data")
	return true, m
}

// objectPayload converts an interrupt or resume payload to the JSON object the
// wire contract requires: nil stays nil (a bare interrupt or restart), a map
// is returned as is, and any other value is converted through JSON. A value
// that serializes to a JSON scalar or array is rejected; what names the
// payload in the error.
func objectPayload(data any, what string) (map[string]any, error) {
	switch v := data.(type) {
	case nil:
		return nil, nil
	case map[string]any:
		return v, nil
	}
	if err := checkObjectPayload(data, what); err != nil {
		return nil, err
	}
	m, err := base.StructToMap(data)
	if err != nil {
		return nil, fmt.Errorf("%s must serialize to a JSON object (a struct or map), got %T: %w", what, data, err)
	}
	return m, nil
}

// checkObjectPayload is the check half of [objectPayload], for the verbs that
// only need to know that a payload will serialize as a JSON object and can
// leave the conversion to the reader: it costs a type inspection, not a JSON
// round trip. nil passes, as a bare interrupt or restart.
func checkObjectPayload(data any, what string) error {
	if data == nil || objectValue(data) {
		return nil
	}
	return fmt.Errorf("%s must serialize to a JSON object (a struct or map), got %T", what, data)
}

// objectValue reports whether v is a Go value that serializes to a JSON object
// by construction: a struct, possibly behind pointers, or a map with string
// keys. Scalars, slices and arrays are not, and neither is nil.
func objectValue(v any) bool {
	t := reflect.TypeOf(v)
	for t != nil && t.Kind() == reflect.Pointer {
		t = t.Elem()
	}
	if t == nil {
		return false
	}
	switch t.Kind() {
	case reflect.Struct:
		return true
	case reflect.Map:
		return t.Key().Kind() == reflect.String
	}
	return false
}

// InterruptOptions provides configuration for tool interruption.
//
// Deprecated: InterruptOptions is the argument of the deprecated
// [ToolContext.Interrupt]. Use [tool.Interrupt] with a struct or a map.
type InterruptOptions struct {
	Metadata map[string]any
}

// RestartOptions provides configuration options for restarting a tool.
//
// Deprecated: RestartOptions is the argument of the deprecated
// [ToolAction.Restart] and the value behind the deprecated [RestartWithOption]
// constructors. Use [InterruptedCall.Restart] and
// [InterruptedCall.RestartWithInput], or [Part.ToToolRestart] and
// [Part.ToToolRestartWithInput], which take the resume data and the new input
// directly.
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
//
// Deprecated: RespondOptions is the argument of the deprecated
// [ToolAction.Respond] and the value behind the deprecated
// [WithResponseMetadata]. Set [Part.Metadata] on the part that
// [InterruptedCall.Respond] or [Part.ToToolResponse] returns instead.
type RespondOptions struct {
	// Metadata is additional metadata to include in the response.
	Metadata map[string]any
}

// RespondWithOption is a functional option for [ToolAction.RespondWith].
//
// Deprecated: RespondWithOption is the option type of the deprecated
// [ToolAction.RespondWith]; [InterruptedCall.Respond] and
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
// [InterruptedCall.Respond] or [Part.ToToolResponse] returns instead.
func WithResponseMetadata[Out any](meta map[string]any) RespondWithOption[Out] {
	return &RespondOptions{Metadata: meta}
}

// RestartWithOption is a functional option for [ToolAction.RestartWith].
//
// Deprecated: RestartWithOption is the option type of the deprecated
// [ToolAction.RestartWith]. [InterruptedCall.Restart] and
// [InterruptedCall.RestartWithInput] take the resume data and the new input
// directly.
type RestartWithOption[In any] interface {
	applyRestartWith(*RestartOptions)
}

// applyRestartWith applies the option to the restart options. The replacement
// input and the resumed metadata are independent single-value slots, so the
// last option to set each one wins.
func (o *RestartOptions) applyRestartWith(opts *RestartOptions) {
	if o.ReplaceInput != nil {
		opts.ReplaceInput = o.ReplaceInput
	}
	if o.ResumedMetadata != nil {
		opts.ResumedMetadata = o.ResumedMetadata
	}
}

// WithNewInput sets a new input value to replace the original tool request input.
// Repeating this option takes the last input set.
//
// Deprecated: WithNewInput only applies to the deprecated
// [ToolAction.RestartWith]. Use [InterruptedCall.RestartWithInput], which
// checks the input against the tool's In type, or
// [Part.ToToolRestartWithInput].
func WithNewInput[In any](input In) RestartWithOption[In] {
	return &RestartOptions{ReplaceInput: input}
}

// WithResumedMetadata sets metadata to pass to the resumed tool execution.
// The metadata will be available in the tool's [ToolContext.Resumed] field.
// Repeating this option replaces the metadata rather than merging it.
//
// Deprecated: WithResumedMetadata only applies to the deprecated
// [ToolAction.RestartWith]. Use [InterruptedCall.Restart], which checks the
// data against the tool's Res type, or [Part.ToToolRestart].
func WithResumedMetadata[In any](meta map[string]any) RestartWithOption[In] {
	return &RestartOptions{ResumedMetadata: meta}
}

// ToolContext provides context and utility functions for tool execution.
type ToolContext struct {
	context.Context
	// Resumed is the resume payload of a restarted call, as a map, and nil on
	// a first call. A tool created with [NewInterruptibleTool] receives the
	// payload typed, as its resume parameter, instead.
	Resumed map[string]any
	// OriginalInput is the input the tool was first called with when the
	// caller restarted it with a new one (see
	// [InterruptedCall.RestartWithInput]), otherwise nil.
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
	return &base.ToolInterruptError{Data: opts.Metadata}
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
	return &base.ToolInterruptError{Data: m}
}

// InterruptAs returns the data an interrupted tool request carries, decoded
// into T. A tool sends that data with [tool.Interrupt]; it is what the tool
// chose to say about the pause, e.g. why it needs approval. The input the
// model provided is on [InterruptedCall.Input] instead, typed by the tool.
// Returns the zero value and false if the part is not an interrupt, the
// interrupt carries no data, or the data does not decode into T.
//
//	for _, part := range resp.Interrupts() {
//		reason, ok := ai.InterruptAs[TransferInterrupt](part)
//	}
func InterruptAs[T any](p *Part) (T, bool) {
	var zero T
	it := p.interruptState()
	if it == nil || it.Resolved || it.Data == nil {
		return zero, false
	}
	return base.ConvertTo[T](it.Data)
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

// requireObjectTypeParam panics unless the type parameter T is a struct or a
// map with string keys, the Go types that serialize to a JSON object.
// [NewInterruptibleTool] calls it for Res: the resume payload rides on the
// restart part as a JSON object, and checking the type once at definition is
// what lets [InterruptedCall.Restart] build that part without an error to
// return. what names the type parameter in the panic message.
func requireObjectTypeParam[T any](ctor, name, what string) {
	typ := reflect.TypeFor[T]()
	if typ.Kind() == reflect.Struct || (typ.Kind() == reflect.Map && typ.Key().Kind() == reflect.String) {
		return
	}
	panic(fmt.Errorf("%s %q: %s must be a struct or a map with string keys, so that it serializes to a JSON object, but got %v", ctor, name, what, typ))
}

// NewTool creates a new [ToolAction]. It can be passed directly to [Generate].
// The options it accepts are listed on [ToolOption]. Inside the function,
// [tool.AttachParts] adds content parts (e.g. media) to the response and
// [tool.SendPartial] streams progress, neither of which changes the signature.
//
// The tool can pause with [tool.Interrupt]; it then reads what the caller sent
// on restart from [ToolContext.Resumed], untyped. A tool that expects a typed
// answer is better made with [NewInterruptibleTool].
func NewTool[In, Out any](name, description string, fn ToolFunc[In, Out], opts ...ToolOption) *ToolAction[In, Out] {
	return newTool[In, Out, map[string]any]("ai.NewTool", name, description, opts, func(ctx context.Context, input In) (Out, error) {
		return fn(newToolContext(ctx), input)
	})
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
	// Out is fixed to the multipart envelope, so only In can disagree with an
	// explicit schema. WithOutputSchema describes the envelope's output field
	// and carries no such constraint.
	toolOpts := applyToolOptions[In]("ai.NewMultipartTool", name, opts)
	metadata := toolMetadata(name, description, true, nil)
	applyToolOutputSchema(metadata, toolOpts.OutputSchema)
	applyStrictMetadata(metadata, toolOpts.StrictSchema)
	wrapped := func(ctx context.Context, input In) (*MultipartToolResponse, error) {
		return runToolFunc(ctx, func(ctx context.Context) (*MultipartToolResponse, error) {
			return fn(newToolContext(ctx), input)
		})
	}
	action := core.NewActionOf(api.ActionTypeToolV2, name, &core.ActionOptions{Metadata: metadata, InputSchema: toolOpts.InputSchema}, wrapped)
	return &ToolAction[In, *MultipartToolResponse]{action: action}
}

// NewInterruptibleTool creates a new unregistered [InterruptibleToolAction].
// It can be passed directly to [Generate], which registers it for the duration
// of the call. The options it accepts are listed on [ToolOption].
//
// Inside the function, [tool.Interrupt] pauses generation; the resume
// parameter is nil on that first call and set to what the caller sent when
// the tool re-executes. Res must be a struct or a map with string keys, so
// that the payload serializes to a JSON object on the restart part; any other
// type panics here, at definition. A payload that does not decode into Res
// fails the resumed call rather than silently arriving as a zero value.
func NewInterruptibleTool[In, Out, Res any](name, description string, fn InterruptibleToolFunc[In, Out, Res], opts ...ToolOption) *InterruptibleToolAction[In, Out, Res] {
	const ctor = "ai.NewInterruptibleTool"
	requireObjectTypeParam[Res](ctor, name, "the resume type Res")
	return newTool[In, Out, Res](ctor, name, description, opts, func(ctx context.Context, input In) (Out, error) {
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
}

// newTool builds the action behind a tool whose function returns Out: it
// applies the options, records Out's schema as the output the tool
// advertises, and wraps run in the multipart envelope every tool speaks
// internally. ctor names the constructor in panic messages.
func newTool[In, Out, Res any](ctor, name, description string, opts []ToolOption, run func(ctx context.Context, input In) (Out, error)) *InterruptibleToolAction[In, Out, Res] {
	toolOpts := applyToolOptions[In](ctor, name, opts)
	if toolOpts.OutputSchema != nil {
		requireAnyTypeParam[Out](ctor, name, "WithOutputSchema and WithOutputSchemaName require Out")
	}

	metadata := toolMetadata(name, description, false, base.SchemaMapFor[Out]())
	applyToolOutputSchema(metadata, toolOpts.OutputSchema)
	applyStrictMetadata(metadata, toolOpts.StrictSchema)
	wrapped := func(ctx context.Context, input In) (*MultipartToolResponse, error) {
		return runToolFunc(ctx, func(ctx context.Context) (*MultipartToolResponse, error) {
			output, err := run(ctx, input)
			if err != nil {
				return nil, err
			}
			return &MultipartToolResponse{Output: output}, nil
		})
	}
	action := core.NewActionOf(api.ActionTypeToolV2, name, &core.ActionOptions{Metadata: metadata, InputSchema: toolOpts.InputSchema}, wrapped)
	return &InterruptibleToolAction[In, Out, Res]{action: action}
}

// applyToolOptions applies opts and checks that an explicit input schema comes
// with an In of any, since the schema stands in for the type parameter. ctor
// names the constructor in the panic message.
func applyToolOptions[In any](ctor, name string, opts []ToolOption) *toolOptions {
	toolOpts := &toolOptions{}
	for _, opt := range opts {
		opt.applyTool(toolOpts)
	}
	if toolOpts.InputSchema != nil {
		requireAnyTypeParam[In](ctor, name, "WithInputSchema requires In")
	}
	return toolOpts
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
// [tool.AttachParts] writes to, runs the function, and folds the attached
// parts into the response.
func runToolFunc(ctx context.Context, run func(ctx context.Context) (*MultipartToolResponse, error)) (*MultipartToolResponse, error) {
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
		return nil, err
	}

	// A multipart function may return a nil response with no error, which
	// the envelope treats as an empty one, so attached parts still have a
	// response to land on.
	if resp == nil {
		resp = &MultipartToolResponse{}
	}

	partsMu.Lock()
	defer partsMu.Unlock()
	if len(parts) > 0 {
		resp.Content = append(resp.Content, parts...)
	}
	return resp, nil
}

// Name returns the name of the tool.
func (t *InterruptibleToolAction[In, Out, Res]) Name() string {
	return t.action.Name()
}

// Definition returns [ToolDefinition] for for this tool.
func (t *InterruptibleToolAction[In, Out, Res]) Definition() *ToolDefinition {
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

	toolMeta := toolMetaOf(desc)
	metadata := map[string]any{
		"multipart": toolMeta["multipart"] == true,
	}
	if s, ok := toolMeta[toolStrictKey].(bool); ok {
		metadata[toolStrictKey] = s
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
func (t *InterruptibleToolAction[In, Out, Res]) Register(r api.Registry) {
	t.registry = r
	t.action.Register(r)
	if !t.IsMultipart() {
		// Also register under the "tool" key for backward compatibility.
		provider, id := api.ParseName(t.action.Name())
		r.RegisterAction(api.NewKey(api.ActionTypeTool, provider, id), t.action)
	}
}

// Desc returns the tool's action descriptor: its name, schemas, and metadata.
func (t *InterruptibleToolAction[In, Out, Res]) Desc() api.ActionDesc { return t.action.Desc() }

// IsMultipart returns true if the tool is a multipart tool (tool.v2 only).
func (t *InterruptibleToolAction[In, Out, Res]) IsMultipart() bool {
	return toolMetaOf(t.action.Desc())["multipart"] == true
}

// toolMetaOf returns the "tool" map of an action's metadata, where
// [toolMetadata] records the per-tool flags; nil when absent, so lookups on
// it are safe.
func toolMetaOf(desc api.ActionDesc) map[string]any {
	m, _ := desc.Metadata["tool"].(map[string]any)
	return m
}

// errNilTool is the error the run methods return when called on a nil tool
// value, typically a package-level tool variable used before it was defined.
func errNilTool(method string) error {
	return status.Errorf(status.ErrInvalidArgument, "ai.Tool.%s: tool called on a nil tool; check that all tools are defined", method)
}

// RunJSON runs the tool on JSON-encoded input and returns the JSON-encoded
// multipart response envelope, which is what the registry serves for this
// tool. Prefer [InterruptibleToolAction.RunRaw], which unwraps the envelope's
// output for a regular tool.
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

// RunRaw runs this tool using the provided raw map format data (JSON parsed as map[string]any).
func (t *InterruptibleToolAction[In, Out, Res]) RunRaw(ctx context.Context, input any) (any, error) {
	resp, err := t.RunRawMultipart(ctx, input)
	if err != nil {
		return nil, err
	}
	return resp.Output, nil
}

// RunRawMultipart runs this tool using the provided raw map format data (JSON parsed as map[string]any).
// It returns the full multipart response.
func (t *InterruptibleToolAction[In, Out, Res]) RunRawMultipart(ctx context.Context, input any) (*MultipartToolResponse, error) {
	if t == nil {
		return nil, errNilTool("RunRawMultipart")
	}
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

// LookupTool looks up the tool in the registry by provided name and returns it.
// It checks for "tool.v2" first, then falls back to "tool" for legacy compatibility.
// Since the types are not known at lookup time, it returns a type-erased tool;
// an interrupt it raised is resolved on the part, with [Part.ToToolRestart] and
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
	return &ToolAction[any, any]{action: action, registry: r}
}

// --- Resolving an interrupt ---

// InterruptedCall is a typed view of an interrupted call to one tool: the part
// as received, the input decoded to the tool's In type, and the verbs that
// resolve the interrupt. [InterruptibleToolAction.Interrupted] returns one
// only for a part that is an unresolved interrupt of that tool, and Res is
// checked at definition to serialize as a JSON object, so nothing here can
// fail: each verb returns the part that resumes generation through
// [WithResume].
//
// Read the data the tool sent when it paused, if any, with [InterruptAs] on
// Part.
type InterruptedCall[In, Out, Res any] struct {
	// Part is the interrupted tool request, as received.
	Part *Part
	// Input is the tool's input, as the model provided it.
	Input In
}

// Interrupted claims part for this tool: it reports whether part is an
// unresolved interrupt of this tool and, when it is, returns the call with
// its input decoded. A nil part, a part of another kind, an interrupt already
// resolved, an interrupt of another tool, or an input that no longer decodes
// as In all report false. Iterate [ModelResponse.Interrupts] and claim each
// part with the tools that could have raised it:
//
//	for _, part := range resp.Interrupts() {
//		if call, ok := transferMoney.Interrupted(part); ok {
//			parts = append(parts, call.Respond(&TransferOutput{Status: "declined"}))
//		}
//	}
func (t *InterruptibleToolAction[In, Out, Res]) Interrupted(part *Part) (*InterruptedCall[In, Out, Res], bool) {
	if t == nil || !part.IsInterrupt() || part.ToolRequest.Name != t.Name() {
		return nil, false
	}
	input, err := base.ConvertToExact[In](part.ToolRequest.Input)
	if err != nil {
		return nil, false
	}
	return &InterruptedCall[In, Out, Res]{Part: part, Input: input}, true
}

// Restart returns the part that re-executes the tool with resume delivered to
// its resume parameter (or to [ToolContext.Resumed], for a tool written
// against [ToolContext]). Pass the zero value, or nil for a map, for a bare
// restart: the tool then re-executes with an empty payload, so restarting is
// itself the approval for a tool that keys on the presence of a resume.
func (c *InterruptedCall[In, Out, Res]) Restart(resume Res) *Part {
	return buildRestartPart(c.Part, resume, nil)
}

// RestartWithInput is [InterruptedCall.Restart] with the tool's input replaced
// by input, for a person who revised the request before approving it. The
// tool re-executes with the new input and the original stays on
// [ToolRestart.OriginalInput], where [tool.OriginalInput] reads it.
func (c *InterruptedCall[In, Out, Res]) RestartWithInput(input In, resume Res) *Part {
	return buildRestartPart(c.Part, resume, input)
}

// Respond returns the part that answers the call with output, without
// re-executing the tool: the model sees output as the tool's result. The
// output is validated against the tool's output schema when generation
// resumes.
func (c *InterruptedCall[In, Out, Res]) Respond(output Out) *Part {
	return newResponsePart(c.Part, output, nil)
}

// ToToolRestart converts this interrupted tool request into the restart [Part]
// that re-executes the tool, for [WithResume]. It is the verb for code
// that holds only the part, such as a handler resolving an interrupt raised by
// a middleware's tool; with the tool value in scope,
// [InterruptibleToolAction.Interrupted] gives the same verb typed.
//
// resume is delivered to the tool's resume parameter, or to
// [ToolContext.Resumed]. It must serialize to a JSON object (a struct or a
// map); nil is a bare restart, so restarting is itself the approval for a
// tool that keys on the presence of a resume.
//
//	for _, part := range resp.Interrupts() {
//		restart, err := part.ToToolRestart(map[string]any{"toolApproved": true})
//	}
func (p *Part) ToToolRestart(resume any) (*Part, error) {
	return p.toToolRestart("ai.Part.ToToolRestart", resume, nil)
}

// ToToolRestartWithInput is [Part.ToToolRestart] with the tool's input
// replaced by input. The original input stays on [ToolRestart.OriginalInput].
func (p *Part) ToToolRestartWithInput(input, resume any) (*Part, error) {
	return p.toToolRestart("ai.Part.ToToolRestartWithInput", resume, input)
}

// toToolRestart checks p and resume for the exported restart verbs, which
// differ only in the name they report and in whether newInput replaces the
// tool's input.
func (p *Part) toToolRestart(fnName string, resume, newInput any) (*Part, error) {
	if !p.IsInterrupt() {
		return nil, status.Errorf(ErrInvalidPart, "%s: part is not an interrupted tool request", fnName)
	}
	if _, err := objectPayload(resume, "resume data"); err != nil {
		return nil, status.Errorf(status.ErrInvalidArgument, "%s: %w", fnName, err)
	}
	return buildRestartPart(p, resume, newInput), nil
}

// ToToolResponse converts this interrupted tool request into the tool response
// [Part] that answers it with output, for [WithResume], without
// re-executing the tool. The output is validated against the tool's output
// schema when generation resumes. With the tool value in scope,
// [InterruptibleToolAction.Interrupted] gives the same verb typed.
func (p *Part) ToToolResponse(output any) (*Part, error) {
	if !p.IsInterrupt() {
		return nil, status.Errorf(ErrInvalidPart, "ai.Part.ToToolResponse: part is not an interrupted tool request")
	}
	return newResponsePart(p, output, nil), nil
}

// Respond creates a part for [WithToolResponses] to provide a resolved response for an interrupted tool call.
// Returns nil if the part is not a tool request.
//
// Deprecated: Use [Part.ToToolResponse], or claim the part with
// [InterruptibleToolAction.Interrupted] and use [InterruptedCall.Respond].
func (t *InterruptibleToolAction[In, Out, Res]) Respond(toolReq *Part, output any, opts *RespondOptions) *Part {
	if !toolReq.IsToolRequest() {
		return nil
	}
	if opts == nil {
		opts = &RespondOptions{}
	}
	return newResponsePart(toolReq, output, opts.Metadata)
}

// Restart creates a part for [WithToolRestarts] to re-execute an interrupted tool call with additional context.
// Returns nil if the part is not a tool request. The resume data is carried as
// given: a value that is not a JSON object resumes the tool with an empty
// payload, the way a peer runtime's marker would.
//
// Deprecated: Use [Part.ToToolRestart], or claim the part with
// [InterruptibleToolAction.Interrupted] and use [InterruptedCall.Restart].
func (t *InterruptibleToolAction[In, Out, Res]) Restart(p *Part, opts *RestartOptions) *Part {
	if !p.IsToolRequest() {
		return nil
	}
	if opts == nil {
		opts = &RestartOptions{}
	}
	return buildRestartPart(p, opts.ResumedMetadata, opts.ReplaceInput)
}

// RespondWith creates a part for [WithToolResponses] to provide a resolved response for an interrupted tool call.
//
// Deprecated: Claim the part with [InterruptibleToolAction.Interrupted] and
// use [InterruptedCall.Respond], or answer the part directly with
// [Part.ToToolResponse].
func (t *InterruptibleToolAction[In, Out, Res]) RespondWith(toolReq *Part, output Out, opts ...RespondWithOption[Out]) (*Part, error) {
	if err := t.checkToolRequest("ai.RespondWith", toolReq); err != nil {
		return nil, err
	}
	cfg := &RespondOptions{}
	for _, opt := range opts {
		opt.applyRespondWith(cfg)
	}
	return newResponsePart(toolReq, output, cfg.Metadata), nil
}

// RestartWith creates a part for [WithToolRestarts] to re-execute an interrupted tool call with additional context.
//
// Deprecated: Claim the part with [InterruptibleToolAction.Interrupted] and
// use [InterruptedCall.Restart] or [InterruptedCall.RestartWithInput], or
// restart the part directly with [Part.ToToolRestart].
func (t *InterruptibleToolAction[In, Out, Res]) RestartWith(toolReq *Part, opts ...RestartWithOption[In]) (*Part, error) {
	const fnName = "ai.RestartWith"
	if err := t.checkToolRequest(fnName, toolReq); err != nil {
		return nil, err
	}
	cfg := &RestartOptions{}
	for _, opt := range opts {
		opt.applyRestartWith(cfg)
	}
	if _, err := objectPayload(cfg.ResumedMetadata, "resume data"); err != nil {
		return nil, status.Errorf(status.ErrInvalidArgument, "%s: %w", fnName, err)
	}
	return buildRestartPart(toolReq, cfg.ResumedMetadata, cfg.ReplaceInput), nil
}

// checkToolRequest is the guard the deprecated RespondWith and RestartWith
// share: toolReq must be a tool request for this tool. fnName names the verb
// in the error.
func (t *InterruptibleToolAction[In, Out, Res]) checkToolRequest(fnName string, toolReq *Part) error {
	if toolReq == nil {
		return status.Errorf(status.ErrInvalidArgument, "%s: toolReq is nil", fnName)
	}
	if !toolReq.IsToolRequest() {
		return status.Errorf(ErrInvalidPart, "%s: part is not a tool request", fnName)
	}
	if toolReq.ToolRequest.Name != t.Name() {
		return status.Errorf(status.ErrInvalidArgument, "%s: tool request is for %q, not %q", fnName, toolReq.ToolRequest.Name, t.Name())
	}
	return nil
}

// buildRestartPart builds the tool request [Part] that re-executes an
// interrupted call. The new part keeps the interrupted part's metadata, less
// its interrupt state. resume is the payload delivered to the tool, already
// validated to serialize as a JSON object, or nil for a bare restart; a nil
// map or pointer is a bare restart too. A non-nil newInput replaces the input
// the tool re-executes with, and the original is preserved on
// [ToolRestart.OriginalInput].
func buildRestartPart(interruptPart *Part, resume, newInput any) *Part {
	toolReq := interruptPart.ToolRequest
	input, originalInput := toolReq.Input, any(nil)
	if newInput != nil {
		input, originalInput = newInput, input
	}

	restartPart := NewToolRequestPart(&ToolRequest{
		Name:  toolReq.Name,
		Ref:   toolReq.Ref,
		Input: input,
	})
	restartPart.Metadata = stripWireKeys(maps.Clone(interruptPart.Metadata))
	restartPart.Restart = &ToolRestart{Resume: bareIfNil(resume), OriginalInput: originalInput}
	return restartPart
}

// bareIfNil normalizes an interrupt or resume payload: an untyped nil, a nil
// map, or a nil pointer all mean a bare interrupt or restart, so they become
// an untyped nil rather than a typed nil inside the interface, which would
// serialize as JSON null instead of the bare marker.
func bareIfNil(v any) any {
	if base.IsNil(v) {
		return nil
	}
	return v
}

// newResponsePart builds the tool response [Part] that resolves an interrupted
// call with a pre-computed output. The interruptResponse marker tells the
// generate loop to resolve the interrupt instead of re-executing the tool;
// metadata, when non-nil, replaces the bare marker.
func newResponsePart(interruptPart *Part, output any, metadata map[string]any) *Part {
	resp := NewResponseForToolRequest(interruptPart, output)
	resp.Metadata = map[string]any{metaInterruptResponse: true}
	if metadata != nil {
		resp.Metadata[metaInterruptResponse] = metadata
	}
	return resp
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
