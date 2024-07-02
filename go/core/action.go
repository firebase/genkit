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

package core

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/firebase/genkit/go/core/logger"
	"github.com/firebase/genkit/go/core/tracing"
	"github.com/firebase/genkit/go/internal"
	"github.com/firebase/genkit/go/internal/atype"
	"github.com/firebase/genkit/go/internal/common"
	"github.com/firebase/genkit/go/internal/metrics"
	"github.com/firebase/genkit/go/internal/registry"
	"github.com/invopop/jsonschema"
)

// Func is the type of function that Actions and Flows execute.
// It takes an input of type Int and returns an output of type Out, optionally
// streaming values of type Stream incrementally by invoking a callback.
// If the StreamingCallback is non-nil and the function supports streaming, it should
// stream the results by invoking the callback periodically, ultimately returning
// with a final return value. Otherwise, it should ignore the StreamingCallback and
// just return a result.
type Func[In, Out, Stream any] func(context.Context, In, func(context.Context, Stream) error) (Out, error)

// TODO(jba): use a generic type alias for the above when they become available?

// An Action is a named, observable operation.
// It consists of a function that takes an input of type I and returns an output
// of type O, optionally streaming values of type S incrementally by invoking a callback.
// It optionally has other metadata, like a description
// and JSON Schemas for its input and output.
//
// Each time an Action is run, it results in a new trace span.
type Action[In, Out, Stream any] struct {
	name         string
	atype        atype.ActionType
	fn           Func[In, Out, Stream]
	tstate       *tracing.State
	inputSchema  *jsonschema.Schema
	outputSchema *jsonschema.Schema
	// optional
	description string
	metadata    map[string]any
}

type noStream = func(context.Context, struct{}) error

// See js/core/src/action.ts

// DefineAction creates a new non-streaming Action and registers it.
func DefineAction[In, Out any](
	provider, name string,
	atype atype.ActionType,
	metadata map[string]any,
	fn func(context.Context, In) (Out, error),
) *Action[In, Out, struct{}] {
	return DefineActionInRegistry(registry.Global, provider, name, atype, metadata, nil,
		func(ctx context.Context, in In, _ noStream) (Out, error) {
			return fn(ctx, in)
		})
}

// DefineStreamingAction creates a new streaming action and registers it.
func DefineStreamingAction[In, Out, Stream any](
	provider, name string,
	atype atype.ActionType,
	metadata map[string]any,
	fn Func[In, Out, Stream],
) *Action[In, Out, Stream] {
	return DefineActionInRegistry(registry.Global, provider, name, atype, metadata, nil, fn)
}

// DefineCustomAction defines a streaming action with type Custom.
func DefineCustomAction[In, Out, Stream any](provider, name string, metadata map[string]any, fn Func[In, Out, Stream]) *Action[In, Out, Stream] {
	return DefineStreamingAction(provider, name, atype.Custom, metadata, fn)
}

// DefineActionWithInputSchema creates a new Action and registers it.
// This differs from DefineAction in that the input schema is
// defined dynamically; the static input type is "any".
// This is used for prompts.
func DefineActionWithInputSchema[Out any](
	provider, name string,
	atype atype.ActionType,
	metadata map[string]any,
	inputSchema *jsonschema.Schema,
	fn func(context.Context, any) (Out, error),
) *Action[any, Out, struct{}] {
	return DefineActionInRegistry(registry.Global, provider, name, atype, metadata, inputSchema,
		func(ctx context.Context, in any, _ noStream) (Out, error) {
			return fn(ctx, in)
		})
}

// DefineActionInRegistry creates an action and registers it with the given Registry.
// For use by the Genkit module only.
func DefineActionInRegistry[In, Out, Stream any](
	r *registry.Registry,
	provider, name string,
	atype atype.ActionType,
	metadata map[string]any,
	inputSchema *jsonschema.Schema,
	fn Func[In, Out, Stream],
) *Action[In, Out, Stream] {
	fullName := name
	if provider != "" {
		fullName = provider + "/" + name
	}
	a := newAction(fullName, atype, metadata, inputSchema, fn)
	r.RegisterAction(atype, a)
	return a
}

// newAction creates a new Action with the given name and arguments.
// If inputSchema is nil, it is inferred from In.
func newAction[In, Out, Stream any](
	name string,
	atype atype.ActionType,
	metadata map[string]any,
	inputSchema *jsonschema.Schema,
	fn Func[In, Out, Stream],
) *Action[In, Out, Stream] {
	var i In
	var o Out
	if inputSchema == nil {
		inputSchema = internal.InferJSONSchema(i)
	}
	return &Action[In, Out, Stream]{
		name:  name,
		atype: atype,
		fn: func(ctx context.Context, input In, sc func(context.Context, Stream) error) (Out, error) {
			tracing.SetCustomMetadataAttr(ctx, "subtype", string(atype))
			return fn(ctx, input, sc)
		},
		inputSchema:  inputSchema,
		outputSchema: internal.InferJSONSchema(o),
		metadata:     metadata,
	}
}

// Name returns the Action's Name.
func (a *Action[In, Out, Stream]) Name() string { return a.name }

// setTracingState sets the action's tracing.State.
func (a *Action[In, Out, Stream]) SetTracingState(tstate *tracing.State) { a.tstate = tstate }

// Run executes the Action's function in a new trace span.
func (a *Action[In, Out, Stream]) Run(ctx context.Context, input In, cb func(context.Context, Stream) error) (output Out, err error) {
	logger.FromContext(ctx).Debug("Action.Run",
		"name", a.Name,
		"input", fmt.Sprintf("%#v", input))
	defer func() {
		logger.FromContext(ctx).Debug("Action.Run",
			"name", a.Name,
			"output", fmt.Sprintf("%#v", output),
			"err", err)
	}()
	tstate := a.tstate
	if tstate == nil {
		// This action has probably not been registered.
		tstate = registry.Global.TracingState()
	}
	return tracing.RunInNewSpan(ctx, tstate, a.name, "action", false, input,
		func(ctx context.Context, input In) (Out, error) {
			start := time.Now()
			var err error
			if err = internal.ValidateValue(input, a.inputSchema); err != nil {
				err = fmt.Errorf("invalid input: %w", err)
			}
			var output Out
			if err == nil {
				output, err = a.fn(ctx, input, cb)
				if err == nil {
					if err = internal.ValidateValue(output, a.outputSchema); err != nil {
						err = fmt.Errorf("invalid output: %w", err)
					}
				}
			}
			latency := time.Since(start)
			if err != nil {
				metrics.WriteActionFailure(ctx, a.name, latency, err)
				return internal.Zero[Out](), err
			}
			metrics.WriteActionSuccess(ctx, a.name, latency)
			return output, nil
		})
}

// RunJSON runs the action with a JSON input, and returns a JSON result.
func (a *Action[In, Out, Stream]) RunJSON(ctx context.Context, input json.RawMessage, cb func(context.Context, json.RawMessage) error) (json.RawMessage, error) {
	// Validate input before unmarshaling it because invalid or unknown fields will be discarded in the process.
	if err := internal.ValidateJSON(input, a.inputSchema); err != nil {
		return nil, err
	}
	var in In
	if err := json.Unmarshal(input, &in); err != nil {
		return nil, err
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
func (a *Action[I, O, S]) Desc() common.ActionDesc {
	ad := common.ActionDesc{
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
func LookupActionFor[In, Out, Stream any](typ atype.ActionType, provider, name string) *Action[In, Out, Stream] {
	key := fmt.Sprintf("/%s/%s/%s", typ, provider, name)
	a := registry.Global.LookupAction(key)
	if a == nil {
		return nil
	}
	return a.(*Action[In, Out, Stream])
}
