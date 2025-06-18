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

package core

import (
	"context"
	"encoding/json"
	"fmt"
	"reflect"
	"time"

	"github.com/firebase/genkit/go/core/logger"
	"github.com/firebase/genkit/go/core/tracing"
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
	// Desc returns a descriptor of the action.
	Desc() ActionDesc
	// SetTracingState sets the tracing state on the action.
	SetTracingState(tstate *tracing.State)
}

// An ActionType is the kind of an action.
type ActionType string

const (
	ActionTypeRetriever        ActionType = "retriever"
	ActionTypeIndexer          ActionType = "indexer"
	ActionTypeEmbedder         ActionType = "embedder"
	ActionTypeEvaluator        ActionType = "evaluator"
	ActionTypeFlow             ActionType = "flow"
	ActionTypeModel            ActionType = "model"
	ActionTypeExecutablePrompt ActionType = "executable-prompt"
	ActionTypeTool             ActionType = "tool"
	ActionTypeUtil             ActionType = "util"
	ActionTypeCustom           ActionType = "custom"
)

// An ActionDef is a named, observable operation that underlies all Genkit primitives.
// It consists of a function that takes an input of type I and returns an output
// of type O, optionally streaming values of type S incrementally by invoking a callback.
// It optionally has other metadata, like a description and JSON Schemas for its input and
// output which it validates against.
//
// Each time an ActionDef is run, it results in a new trace span.
type ActionDef[In, Out, Stream any] struct {
	fn     StreamingFunc[In, Out, Stream] // Function that is called during runtime. May not actually support streaming.
	desc   *ActionDesc                    // Descriptor of the action.
	tstate *tracing.State                 // Collects and writes traces during runtime.
}

// ActionDesc is a descriptor of an action.
type ActionDesc struct {
	Type         ActionType         `json:"type"`         // Type of the action.
	Key          string             `json:"key"`          // Key of the action.
	Name         string             `json:"name"`         // Name of the action.
	Description  string             `json:"description"`  // Description of the action.
	InputSchema  *jsonschema.Schema `json:"inputSchema"`  // JSON schema to validate against the action's input.
	OutputSchema *jsonschema.Schema `json:"outputSchema"` // JSON schema to validate against the action's output.
	Metadata     map[string]any     `json:"metadata"`     // Metadata for the action.
}

type noStream = func(context.Context, struct{}) error

// DefineAction creates a new non-streaming Action and registers it.
func DefineAction[In, Out any](
	r *registry.Registry,
	provider, name string,
	atype ActionType,
	metadata map[string]any,
	fn Func[In, Out],
) *ActionDef[In, Out, struct{}] {
	return defineAction(r, provider, name, atype, metadata, nil,
		func(ctx context.Context, in In, cb noStream) (Out, error) {
			return fn(ctx, in)
		})
}

// NewAction creates a new non-streaming Action without registering it.
func NewAction[In, Out any](
	provider, name string,
	atype ActionType,
	metadata map[string]any,
	fn Func[In, Out],
) *ActionDef[In, Out, struct{}] {
	fullName := name
	if provider != "" {
		fullName = provider + "/" + name
	}
	return newAction(nil, fullName, atype, metadata, nil,
		func(ctx context.Context, in In, cb noStream) (Out, error) {
			return fn(ctx, in)
		})
}

// DefineStreamingAction creates a new streaming action and registers it.
func DefineStreamingAction[In, Out, Stream any](
	r *registry.Registry,
	provider, name string,
	atype ActionType,
	metadata map[string]any,
	fn StreamingFunc[In, Out, Stream],
) *ActionDef[In, Out, Stream] {
	return defineAction(r, provider, name, atype, metadata, nil, fn)
}

// DefineActionWithInputSchema creates a new Action and registers it.
// This differs from DefineAction in that the input schema is
// defined dynamically; the static input type is "any".
// This is used for prompts and tools that need custom input validation.
func DefineActionWithInputSchema[Out any](
	r *registry.Registry,
	provider, name string,
	atype ActionType,
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
	atype ActionType,
	metadata map[string]any,
	inputSchema *jsonschema.Schema,
	fn StreamingFunc[In, Out, Stream],
) *ActionDef[In, Out, Stream] {
	fullName := name
	if provider != "" {
		fullName = provider + "/" + name
	}
	a := newAction(r, fullName, atype, metadata, inputSchema, fn)
	key := fmt.Sprintf("/%s/%s", atype, fullName)
	r.RegisterAction(key, a)
	return a
}

// newAction creates a new Action with the given name and arguments.
// If registry is nil, tracing state is left nil to be set later.
// If inputSchema is nil, it is inferred from In.
func newAction[In, Out, Stream any](
	r *registry.Registry,
	name string,
	atype ActionType,
	metadata map[string]any,
	inputSchema *jsonschema.Schema,
	fn StreamingFunc[In, Out, Stream],
) *ActionDef[In, Out, Stream] {
	if inputSchema == nil {
		var i In
		if reflect.ValueOf(i).Kind() != reflect.Invalid {
			inputSchema = base.InferJSONSchema(i)
		}
	}

	var o Out
	var outputSchema *jsonschema.Schema
	if reflect.ValueOf(o).Kind() != reflect.Invalid {
		outputSchema = base.InferJSONSchema(o)
	}

	var description string
	if desc, ok := metadata["description"].(string); ok {
		description = desc
	}

	var tstate *tracing.State
	if r != nil {
		tstate = r.TracingState()
	}

	return &ActionDef[In, Out, Stream]{
		tstate: tstate,
		fn: func(ctx context.Context, input In, cb StreamCallback[Stream]) (Out, error) {
			tracing.SetCustomMetadataAttr(ctx, "subtype", string(atype))
			return fn(ctx, input, cb)
		},
		desc: &ActionDesc{
			Type:         atype,
			Key:          fmt.Sprintf("/%s/%s", atype, name),
			Name:         name,
			Description:  description,
			InputSchema:  inputSchema,
			OutputSchema: outputSchema,
			Metadata:     metadata,
		},
	}
}

// Name returns the Action's Name.
func (a *ActionDef[In, Out, Stream]) Name() string { return a.desc.Name }

// SetTracingState sets the tracing state on the action. This is used when an action
// created without a registry needs to have its tracing state set later.
func (a *ActionDef[In, Out, Stream]) SetTracingState(tstate *tracing.State) {
	a.tstate = tstate
}

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

	return tracing.RunInNewSpan(ctx, a.tstate, a.desc.Name, "action", false, input,
		func(ctx context.Context, input In) (Out, error) {
			start := time.Now()
			var err error
			if err = base.ValidateValue(input, a.desc.InputSchema); err != nil {
				err = fmt.Errorf("invalid input: %w", err)
			}
			var output Out
			if err == nil {
				output, err = a.fn(ctx, input, cb)
				if err == nil {
					if err = base.ValidateValue(output, a.desc.OutputSchema); err != nil {
						err = fmt.Errorf("invalid output: %w", err)
					}
				}
			}
			latency := time.Since(start)
			if err != nil {
				metrics.WriteActionFailure(ctx, a.desc.Name, latency, err)
				return base.Zero[Out](), err
			}
			metrics.WriteActionSuccess(ctx, a.desc.Name, latency)

			return output, nil
		})
}

// RunJSON runs the action with a JSON input, and returns a JSON result.
func (a *ActionDef[In, Out, Stream]) RunJSON(ctx context.Context, input json.RawMessage, cb StreamCallback[json.RawMessage]) (json.RawMessage, error) {
	// Validate input before unmarshaling it because invalid or unknown fields will be discarded in the process.
	if err := base.ValidateJSON(input, a.desc.InputSchema); err != nil {
		return nil, NewError(INVALID_ARGUMENT, err.Error())
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

// Desc returns a descriptor of the action.
func (a *ActionDef[In, Out, Stream]) Desc() ActionDesc {
	return *a.desc
}

// LookupActionFor returns the action for the given key in the global registry,
// or nil if there is none.
// It panics if the action is of the wrong type.
func LookupActionFor[In, Out, Stream any](r *registry.Registry, typ ActionType, provider, name string) *ActionDef[In, Out, Stream] {
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
