// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package core

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"reflect"
	"time"

	"github.com/firebase/genkit/go/core/logger"
	"github.com/firebase/genkit/go/core/tracing"
	"github.com/firebase/genkit/go/internal/action"
	"github.com/firebase/genkit/go/internal/atype"
	"github.com/firebase/genkit/go/internal/base"
	"github.com/firebase/genkit/go/internal/metrics"
	"github.com/firebase/genkit/go/internal/registry"
	"github.com/invopop/jsonschema"
)

// Func is an alias for non-streaming functions with input of type In and output of type Out.
type Func[In, Out any] = func(context.Context, In) (Out, error)

// StreamingFunc is an alias for streaming functions with input of type In, output of type Out, and streaming chunk of type Stream.
type StreamingFunc[In, Out, Stream any] = func(context.Context, In, StreamCallback[Stream]) (Out, error)

// StreamCallback is a function that is called during streaming to return the next chunk of the stream.
type StreamCallback[Stream any] = func(context.Context, Stream) error

// Action is the interface that all Genkit primitives (e.g. flows, models, tools) have in common.
type Action interface {
	// Name returns the name of the action.
	Name() string
	// RunJSON runs the action with the given JSON input and streaming callback and returns the output as JSON.
	RunJSON(ctx context.Context, input json.RawMessage, cb func(context.Context, json.RawMessage) error) (json.RawMessage, error)
}

// An ActionDef is a named, observable operation that underlies all Genkit primitives.
// It consists of a function that takes an input of type I and returns an output
// of type O, optionally streaming values of type S incrementally by invoking a callback.
// It optionally has other metadata, like a description and JSON Schemas for its input and
// output which it validates against.
//
// Each time an ActionDef is run, it results in a new trace span.
type ActionDef[In, Out, Stream any] struct {
	name         string                         // Name of the action.
	description  string                         // Description of the action. Optional.
	atype        atype.ActionType               // Type of the action (e.g. flow, model, tool).
	fn           StreamingFunc[In, Out, Stream] // Function that is called during runtime. May not actually support streaming.
	tstate       *tracing.State                 // Collects and writes traces during runtime.
	inputSchema  *jsonschema.Schema             // JSON schema to validate against the action's input.
	outputSchema *jsonschema.Schema             // JSON schema to validate against the action's output.
	metadata     map[string]any                 // Metadata for the action.
}

type noStream = func(context.Context, struct{}) error

// DefineAction creates a new non-streaming Action and registers it.
func DefineAction[In, Out any](
	r *registry.Registry,
	provider, name string,
	atype atype.ActionType,
	metadata map[string]any,
	fn Func[In, Out],
) *ActionDef[In, Out, struct{}] {
	return defineAction(r, provider, name, atype, metadata, nil,
		func(ctx context.Context, in In, cb noStream) (Out, error) {
			return fn(ctx, in)
		})
}

// DefineStreamingAction creates a new streaming action and registers it.
func DefineStreamingAction[In, Out, Stream any](
	r *registry.Registry,
	provider, name string,
	atype atype.ActionType,
	metadata map[string]any,
	fn StreamingFunc[In, Out, Stream],
) *ActionDef[In, Out, Stream] {
	return defineAction(r, provider, name, atype, metadata, nil, fn)
}

// DefineActionWithInputSchema creates a new Action and registers it.
// This differs from DefineAction in that the input schema is
// defined dynamically; the static input type is "any".
// This is used for prompts.
func DefineActionWithInputSchema[Out any](
	r *registry.Registry,
	provider, name string,
	atype atype.ActionType,
	metadata map[string]any,
	inputSchema *jsonschema.Schema,
	fn Func[any, Out],
) *ActionDef[any, Out, struct{}] {
	return defineAction(r, provider, name, atype, metadata, inputSchema,
		func(ctx context.Context, in any, _ noStream) (Out, error) {
			return fn(ctx, in)
		})
}

// defineAction creates an action and registers it with the given Registry.
func defineAction[In, Out, Stream any](
	r *registry.Registry,
	provider, name string,
	atype atype.ActionType,
	metadata map[string]any,
	inputSchema *jsonschema.Schema,
	fn StreamingFunc[In, Out, Stream],
) *ActionDef[In, Out, Stream] {
	fullName := name
	if provider != "" {
		fullName = provider + "/" + name
	}
	a := newAction(r, fullName, atype, metadata, inputSchema, fn)
	r.RegisterAction(atype, a)
	return a
}

// newAction creates a new Action with the given name and arguments.
// If inputSchema is nil, it is inferred from In.
func newAction[In, Out, Stream any](
	r *registry.Registry,
	name string,
	atype atype.ActionType,
	metadata map[string]any,
	inputSchema *jsonschema.Schema,
	fn StreamingFunc[In, Out, Stream],
) *ActionDef[In, Out, Stream] {
	var i In
	var o Out
	if inputSchema == nil {
		if reflect.ValueOf(i).Kind() != reflect.Invalid {
			inputSchema = base.InferJSONSchemaNonReferencing(i)
		}
	}
	var outputSchema *jsonschema.Schema
	if reflect.ValueOf(o).Kind() != reflect.Invalid {
		outputSchema = base.InferJSONSchemaNonReferencing(o)
	}
	return &ActionDef[In, Out, Stream]{
		name:   name,
		atype:  atype,
		tstate: r.TracingState(),
		fn: func(ctx context.Context, input In, cb StreamCallback[Stream]) (Out, error) {
			tracing.SetCustomMetadataAttr(ctx, "subtype", string(atype))
			return fn(ctx, input, cb)
		},
		inputSchema:  inputSchema,
		outputSchema: outputSchema,
		metadata:     metadata,
	}
}

// Name returns the Action's Name.
func (a *ActionDef[In, Out, Stream]) Name() string { return a.name }

// Run executes the Action's function in a new trace span.
func (a *ActionDef[In, Out, Stream]) Run(ctx context.Context, input In, cb StreamCallback[Stream]) (output Out, err error) {
	logger.FromContext(ctx).Debug("Action.Run",
		"name", a.Name,
		"input", fmt.Sprintf("%#v", input))
	defer func() {
		logger.FromContext(ctx).Debug("Action.Run",
			"name", a.Name,
			"output", fmt.Sprintf("%#v", output),
			"err", err)
	}()

	return tracing.RunInNewSpan(ctx, a.tstate, a.name, "action", false, input,
		func(ctx context.Context, input In) (Out, error) {
			start := time.Now()
			var err error
			if err = base.ValidateValue(input, a.inputSchema); err != nil {
				err = fmt.Errorf("invalid input: %w", err)
			}
			var output Out
			if err == nil {
				output, err = a.fn(ctx, input, cb)
				if err == nil {
					if err = base.ValidateValue(output, a.outputSchema); err != nil {
						err = fmt.Errorf("invalid output: %w", err)
					}
				}
			}
			latency := time.Since(start)
			if err != nil {
				metrics.WriteActionFailure(ctx, a.name, latency, err)
				return base.Zero[Out](), err
			}
			metrics.WriteActionSuccess(ctx, a.name, latency)

			return output, nil
		})
}

// RunJSON runs the action with a JSON input, and returns a JSON result.
func (a *ActionDef[In, Out, Stream]) RunJSON(ctx context.Context, input json.RawMessage, cb StreamCallback[json.RawMessage]) (json.RawMessage, error) {
	// Validate input before unmarshaling it because invalid or unknown fields will be discarded in the process.
	if err := base.ValidateJSON(input, a.inputSchema); err != nil {
		return nil, &base.HTTPError{Code: http.StatusBadRequest, Err: err}
	}
	var in In
	if input != nil {
		if err := json.Unmarshal(input, &in); err != nil {
			return nil, err
		}
	}
	var callback func(context.Context, Stream) error
	if cb != nil {
		callback = func(ctx context.Context, s Stream) error {
			bytes, err := json.Marshal(s)
			if err != nil {
				return err
			}
			return cb(ctx, json.RawMessage(bytes))
		}
	}
	out, err := a.Run(ctx, in, callback)
	if err != nil {
		return nil, err
	}
	bytes, err := json.Marshal(out)
	if err != nil {
		return nil, err
	}
	return json.RawMessage(bytes), nil
}

// Desc returns a description of the action.
func (a *ActionDef[In, Out, Stream]) Desc() action.Desc {
	ad := action.Desc{
		Name:         a.name,
		Description:  a.description,
		Metadata:     a.metadata,
		InputSchema:  a.inputSchema,
		OutputSchema: a.outputSchema,
	}
	// Required by genkit UI:
	if ad.Metadata == nil {
		ad.Metadata = map[string]any{
			"inputSchema":  nil,
			"outputSchema": nil,
		}
	}
	return ad
}

// LookupActionFor returns the action for the given key in the global registry,
// or nil if there is none.
// It panics if the action is of the wrong type.
func LookupActionFor[In, Out, Stream any](r *registry.Registry, typ atype.ActionType, provider, name string) *ActionDef[In, Out, Stream] {
	var key string
	if provider != "" {
		key = fmt.Sprintf("/%s/%s/%s", typ, provider, name)
	} else {
		key = fmt.Sprintf("/%s/%s", typ, name)
	}
	a := r.LookupAction(key)
	if a == nil {
		return nil
	}
	return a.(*ActionDef[In, Out, Stream])
}
