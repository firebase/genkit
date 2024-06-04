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
	"maps"
	"time"

	"github.com/firebase/genkit/go/core/logger"
	"github.com/firebase/genkit/go/core/tracing"
	"github.com/firebase/genkit/go/internal"
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

// NoStream indicates that the action or flow does not support streaming.
// A Func[I, O, NoStream] will ignore its streaming callback.
// Such a function corresponds to a Flow[I, O, struct{}].
type NoStream = func(context.Context, struct{}) error

type streamingCallback[Stream any] func(context.Context, Stream) error

// An Action is a named, observable operation.
// It consists of a function that takes an input of type I and returns an output
// of type O, optionally streaming values of type S incrementally by invoking a callback.
// It optionally has other metadata, like a description
// and JSON Schemas for its input and output.
//
// Each time an Action is run, it results in a new trace span.
type Action[In, Out, Stream any] struct {
	name         string
	atype        ActionType
	fn           Func[In, Out, Stream]
	tstate       *tracing.State
	inputSchema  *jsonschema.Schema
	outputSchema *jsonschema.Schema
	// optional
	Description string
	Metadata    map[string]any
}

// See js/core/src/action.ts

// DefineAction creates a new Action and registers it.
func DefineAction[In, Out any](provider, name string, atype ActionType, metadata map[string]any, fn func(context.Context, In) (Out, error)) *Action[In, Out, struct{}] {
	return defineAction(globalRegistry, provider, name, atype, metadata, fn)
}

func defineAction[In, Out any](r *registry, provider, name string, atype ActionType, metadata map[string]any, fn func(context.Context, In) (Out, error)) *Action[In, Out, struct{}] {
	a := NewAction(name, atype, metadata, fn)
	r.registerAction(provider, a)
	return a
}

func DefineStreamingAction[In, Out, Stream any](provider, name string, atype ActionType, metadata map[string]any, fn Func[In, Out, Stream]) *Action[In, Out, Stream] {
	return defineStreamingAction(globalRegistry, provider, name, atype, metadata, fn)
}

func defineStreamingAction[In, Out, Stream any](r *registry, provider, name string, atype ActionType, metadata map[string]any, fn Func[In, Out, Stream]) *Action[In, Out, Stream] {
	a := NewStreamingAction(name, atype, metadata, fn)
	r.registerAction(provider, a)
	return a
}

// NewAction creates a new Action with the given name and non-streaming function.
func NewAction[In, Out any](name string, atype ActionType, metadata map[string]any, fn func(context.Context, In) (Out, error)) *Action[In, Out, struct{}] {
	return NewStreamingAction(name, atype, metadata, func(ctx context.Context, in In, cb NoStream) (Out, error) {
		return fn(ctx, in)
	})
}

// NewStreamingAction creates a new Action with the given name and streaming function.
func NewStreamingAction[In, Out, Stream any](name string, atype ActionType, metadata map[string]any, fn Func[In, Out, Stream]) *Action[In, Out, Stream] {
	var i In
	var o Out
	return &Action[In, Out, Stream]{
		name:  name,
		atype: atype,
		fn: func(ctx context.Context, input In, sc func(context.Context, Stream) error) (Out, error) {
			tracing.SetCustomMetadataAttr(ctx, "subtype", string(atype))
			return fn(ctx, input, sc)
		},
		inputSchema:  inferJSONSchema(i),
		outputSchema: inferJSONSchema(o),
		Metadata:     metadata,
	}
}

// Name returns the Action's name.
func (a *Action[In, Out, Stream]) Name() string { return a.name }

func (a *Action[In, Out, Stream]) actionType() ActionType { return a.atype }

// setTracingState sets the action's tracing.State.
func (a *Action[In, Out, Stream]) setTracingState(tstate *tracing.State) { a.tstate = tstate }

// Run executes the Action's function in a new trace span.
func (a *Action[In, Out, Stream]) Run(ctx context.Context, input In, cb func(context.Context, Stream) error) (output Out, err error) {
	logger.FromContext(ctx).Debug("Action.Run",
		"name", a.name,
		"input", fmt.Sprintf("%#v", input))
	defer func() {
		logger.FromContext(ctx).Debug("Action.Run",
			"name", a.name,
			"output", fmt.Sprintf("%#v", output),
			"err", err)
	}()
	tstate := a.tstate
	if tstate == nil {
		// This action has probably not been registered.
		tstate = globalRegistry.tstate
	}
	return tracing.RunInNewSpan(ctx, tstate, a.name, "action", false, input,
		func(ctx context.Context, input In) (Out, error) {
			start := time.Now()
			var err error
			if err = ValidateValue(input, a.inputSchema); err != nil {
				err = fmt.Errorf("invalid input: %w", err)
			}
			var output Out
			if err == nil {
				output, err = a.fn(ctx, input, cb)
				if err == nil {
					if err = ValidateValue(output, a.outputSchema); err != nil {
						err = fmt.Errorf("invalid output: %w", err)
					}
				}
			}
			latency := time.Since(start)
			if err != nil {
				writeActionFailure(ctx, a.name, latency, err)
				return internal.Zero[Out](), err
			}
			writeActionSuccess(ctx, a.name, latency)
			return output, nil
		})
}

func (a *Action[In, Out, Stream]) runJSON(ctx context.Context, input json.RawMessage, cb func(context.Context, json.RawMessage) error) (json.RawMessage, error) {
	// Validate input before unmarshaling it because invalid or unknown fields will be discarded in the process.
	if err := ValidateJSON(input, a.inputSchema); err != nil {
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

// action is the type that all Action[I, O, S] have in common.
type action interface {
	Name() string
	actionType() ActionType

	// runJSON uses encoding/json to unmarshal the input,
	// calls Action.Run, then returns the marshaled result.
	runJSON(ctx context.Context, input json.RawMessage, cb func(context.Context, json.RawMessage) error) (json.RawMessage, error)

	// desc returns a description of the action.
	// It should set all fields of actionDesc except Key, which
	// the registry will set.
	desc() actionDesc

	// setTracingState set's the action's tracing.State.
	setTracingState(*tracing.State)
}

// An actionDesc is a description of an Action.
// It is used to provide a list of registered actions.
type actionDesc struct {
	Key          string             `json:"key"` // full key from the registry
	Name         string             `json:"name"`
	Description  string             `json:"description"`
	Metadata     map[string]any     `json:"metadata"`
	InputSchema  *jsonschema.Schema `json:"inputSchema"`
	OutputSchema *jsonschema.Schema `json:"outputSchema"`
}

func (d1 actionDesc) equal(d2 actionDesc) bool {
	return d1.Key == d2.Key &&
		d1.Name == d2.Name &&
		d1.Description == d2.Description &&
		maps.Equal(d1.Metadata, d2.Metadata)
}

func (a *Action[I, O, S]) desc() actionDesc {
	ad := actionDesc{
		Name:         a.name,
		Description:  a.Description,
		Metadata:     a.Metadata,
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

func inferJSONSchema(x any) (s *jsonschema.Schema) {
	r := jsonschema.Reflector{
		DoNotReference: true,
	}
	s = r.Reflect(x)
	// TODO: Unwind this change once Monaco Editor supports newer than JSON schema draft-07.
	s.Version = ""
	return s
}
