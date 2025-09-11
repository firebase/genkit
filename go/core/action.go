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
	"strings"
	"time"

	"github.com/firebase/genkit/go/core/logger"
	"github.com/firebase/genkit/go/core/tracing"
	"github.com/firebase/genkit/go/internal/base"
	"github.com/firebase/genkit/go/internal/metrics"
	"github.com/firebase/genkit/go/internal/registry"
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
	// Register registers the action with the given registry.
	Register(r *registry.Registry)
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
	ActionTypeResource         ActionType = "resource"
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
	fn   StreamingFunc[In, Out, Stream] // Function that is called during runtime. May not actually support streaming.
	desc *ActionDesc                    // Descriptor of the action.
}

// ActionDesc is a descriptor of an action.
type ActionDesc struct {
	Type         ActionType     `json:"type"`         // Type of the action.
	Key          string         `json:"key"`          // Key of the action.
	Name         string         `json:"name"`         // Name of the action.
	Description  string         `json:"description"`  // Description of the action.
	InputSchema  map[string]any `json:"inputSchema"`  // JSON schema to validate against the action's input.
	OutputSchema map[string]any `json:"outputSchema"` // JSON schema to validate against the action's output.
	Metadata     map[string]any `json:"metadata"`     // Metadata for the action.
}

type noStream = func(context.Context, struct{}) error

// NewAction creates a new non-streaming [Action] without registering it.
// If inputSchema is nil, it is inferred from the function's input type.
func NewAction[In, Out any](
	name string,
	atype ActionType,
	metadata map[string]any,
	inputSchema map[string]any,
	fn Func[In, Out],
) *ActionDef[In, Out, struct{}] {
	return newAction(name, atype, metadata, inputSchema,
		func(ctx context.Context, in In, cb noStream) (Out, error) {
			return fn(ctx, in)
		})
}

// NewStreamingAction creates a new streaming [Action] without registering it.
// If inputSchema is nil, it is inferred from the function's input type.
func NewStreamingAction[In, Out, Stream any](
	name string,
	atype ActionType,
	metadata map[string]any,
	inputSchema map[string]any,
	fn StreamingFunc[In, Out, Stream],
) *ActionDef[In, Out, Stream] {
	return newAction(name, atype, metadata, inputSchema, fn)
}

// DefineAction creates a new non-streaming Action and registers it.
// If inputSchema is nil, it is inferred from the function's input type.
func DefineAction[In, Out any](
	r *registry.Registry,
	name string,
	atype ActionType,
	metadata map[string]any,
	inputSchema map[string]any,
	fn Func[In, Out],
) *ActionDef[In, Out, struct{}] {
	return defineAction(r, name, atype, metadata, inputSchema,
		func(ctx context.Context, in In, cb noStream) (Out, error) {
			return fn(ctx, in)
		})
}

// DefineStreamingAction creates a new streaming action and registers it.
// If inputSchema is nil, it is inferred from the function's input type.
func DefineStreamingAction[In, Out, Stream any](
	r *registry.Registry,
	name string,
	atype ActionType,
	metadata map[string]any,
	inputSchema map[string]any,
	fn StreamingFunc[In, Out, Stream],
) *ActionDef[In, Out, Stream] {
	return defineAction(r, name, atype, metadata, inputSchema, fn)
}

// defineAction creates an action and registers it with the given Registry.
func defineAction[In, Out, Stream any](
	r *registry.Registry,
	name string,
	atype ActionType,
	metadata map[string]any,
	inputSchema map[string]any,
	fn StreamingFunc[In, Out, Stream],
) *ActionDef[In, Out, Stream] {
	a := newAction(name, atype, metadata, inputSchema, fn)
	provider, id := ParseName(name)
	key := NewKey(atype, provider, id)
	r.RegisterAction(key, a)
	return a
}

// newAction creates a new Action with the given name and arguments.
// If registry is nil, tracing state is left nil to be set later.
// If inputSchema is nil, it is inferred from In.
func newAction[In, Out, Stream any](
	name string,
	atype ActionType,
	metadata map[string]any,
	inputSchema map[string]any,
	fn StreamingFunc[In, Out, Stream],
) *ActionDef[In, Out, Stream] {
	if inputSchema == nil {
		var i In
		if reflect.ValueOf(i).Kind() != reflect.Invalid {
			inputSchema = InferSchemaMap(i)
		}
	}

	var o Out
	var outputSchema map[string]any
	if reflect.ValueOf(o).Kind() != reflect.Invalid {
		outputSchema = InferSchemaMap(o)
	}

	var description string
	if desc, ok := metadata["description"].(string); ok {
		description = desc
	}

	return &ActionDef[In, Out, Stream]{
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

	return tracing.RunInNewSpan(ctx, a.desc.Name, "action", false, input,
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

	var i In
	if err := json.Unmarshal(input, &i); err != nil {
		return nil, NewError(INVALID_ARGUMENT, "invalid input: %v", err)
	}

	// Adhere to the input schema if the number type is ambiguous and the input type is an any.
	converted, err := base.ConvertJSONNumbers(i, a.desc.InputSchema)
	if err != nil {
		return nil, NewError(INVALID_ARGUMENT, "invalid input: %v", err)
	}

	if result, ok := converted.(In); ok {
		i = result
	}

	var scb StreamCallback[Stream]
	if cb != nil {
		scb = func(ctx context.Context, s Stream) error {
			bytes, err := json.Marshal(s)
			if err != nil {
				return err
			}
			return cb(ctx, json.RawMessage(bytes))
		}
	}

	out, err := a.Run(ctx, i, scb)
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

// Register registers the action with the given registry.
func (a *ActionDef[In, Out, Stream]) Register(r *registry.Registry) {
	r.RegisterAction(a.desc.Key, a)
}

// ResolveActionFor returns the action for the given key in the global registry,
// or nil if there is none.
// It panics if the action is of the wrong type.
func ResolveActionFor[In, Out, Stream any](r *registry.Registry, atype ActionType, name string) *ActionDef[In, Out, Stream] {
	provider, id := ParseName(name)
	key := NewKey(atype, provider, id)
	a := r.ResolveAction(key)
	if a == nil {
		return nil
	}
	return a.(*ActionDef[In, Out, Stream])
}

// LookupActionFor returns the action for the given key in the global registry,
// or nil if there is none.
// It panics if the action is of the wrong type.
func LookupActionFor[In, Out, Stream any](r *registry.Registry, atype ActionType, name string) *ActionDef[In, Out, Stream] {
	provider, id := ParseName(name)
	key := NewKey(atype, provider, id)
	a := r.LookupAction(key)
	if a == nil {
		return nil
	}
	return a.(*ActionDef[In, Out, Stream])
}

// NewKey creates a new action key for the given type, provider, and name.
func NewKey(typ ActionType, provider, id string) string {
	if provider != "" {
		return fmt.Sprintf("/%s/%s/%s", typ, provider, id)
	}
	return fmt.Sprintf("/%s/%s", typ, id)
}

// ParseKey parses an action key into a type, provider, and name.
func ParseKey(key string) (ActionType, string, string) {
	parts := strings.Split(key, "/")
	if len(parts) < 4 || parts[0] != "" {
		// Return empty values if the key doesn't have the expected format
		return "", "", ""
	}
	name := strings.Join(parts[3:], "/")
	return ActionType(parts[1]), parts[2], name
}

// NewName creates a new action name for the given provider and id.
func NewName(provider, id string) string {
	if provider != "" {
		return fmt.Sprintf("%s/%s", provider, id)
	}
	return id
}

// ParseName parses an action name into a provider and id.
func ParseName(name string) (string, string) {
	parts := strings.Split(name, "/")
	if len(parts) < 2 {
		return "", name
	}
	id := strings.Join(parts[1:], "/")
	return parts[0], id
}
