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

	"github.com/firebase/genkit/go/core/api"
	"github.com/firebase/genkit/go/core/logger"
	"github.com/firebase/genkit/go/core/tracing"
	"github.com/firebase/genkit/go/internal/base"
	"github.com/firebase/genkit/go/internal/metrics"
)

// Func is an alias for non-streaming functions with input of type In and output of type Out.
type Func[In, Out any] = func(context.Context, In) (Out, error)

// StreamingFunc is an alias for streaming functions with input of type In, output of type Out, and streaming chunk of type Stream.
type StreamingFunc[In, Out, Stream any] = func(context.Context, In, StreamCallback[Stream]) (Out, error)

// StreamCallback is a function that is called during streaming to return the next chunk of the stream.
type StreamCallback[Stream any] = func(context.Context, Stream) error

// An ActionDef is a named, observable operation that underlies all Genkit primitives.
// It consists of a function that takes an input of type I and returns an output
// of type O, optionally streaming values of type S incrementally by invoking a callback.
// It optionally has other metadata, like a description and JSON Schemas for its input and
// output which it validates against.
//
// Each time an ActionDef is run, it results in a new trace span.
type ActionDef[In, Out, Stream any] struct {
	fn   StreamingFunc[In, Out, Stream] // Function that is called during runtime. May not actually support streaming.
	desc *api.ActionDesc                // Descriptor of the action.
}

type noStream = func(context.Context, struct{}) error

// NewAction creates a new non-streaming [Action] without registering it.
// If inputSchema is nil, it is inferred from the function's input api.
func NewAction[In, Out any](
	name string,
	atype api.ActionType,
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
// If inputSchema is nil, it is inferred from the function's input api.
func NewStreamingAction[In, Out, Stream any](
	name string,
	atype api.ActionType,
	metadata map[string]any,
	inputSchema map[string]any,
	fn StreamingFunc[In, Out, Stream],
) *ActionDef[In, Out, Stream] {
	return newAction(name, atype, metadata, inputSchema, fn)
}

// DefineAction creates a new non-streaming Action and registers it.
// If inputSchema is nil, it is inferred from the function's input api.
func DefineAction[In, Out any](
	r api.Registry,
	name string,
	atype api.ActionType,
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
// If inputSchema is nil, it is inferred from the function's input api.
func DefineStreamingAction[In, Out, Stream any](
	r api.Registry,
	name string,
	atype api.ActionType,
	metadata map[string]any,
	inputSchema map[string]any,
	fn StreamingFunc[In, Out, Stream],
) *ActionDef[In, Out, Stream] {
	return defineAction(r, name, atype, metadata, inputSchema, fn)
}

// defineAction creates an action and registers it with the given Registry.
func defineAction[In, Out, Stream any](
	r api.Registry,
	name string,
	atype api.ActionType,
	metadata map[string]any,
	inputSchema map[string]any,
	fn StreamingFunc[In, Out, Stream],
) *ActionDef[In, Out, Stream] {
	a := newAction(name, atype, metadata, inputSchema, fn)
	provider, id := api.ParseName(name)
	key := api.NewKey(atype, provider, id)
	r.RegisterAction(key, a)
	return a
}

// newAction creates a new Action with the given name and arguments.
// If registry is nil, tracing state is left nil to be set later.
// If inputSchema is nil, it is inferred from In.
func newAction[In, Out, Stream any](
	name string,
	atype api.ActionType,
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
			return fn(ctx, input, cb)
		},
		desc: &api.ActionDesc{
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
	r, err := a.runWithTelemetry(ctx, input, cb)
	if err != nil {
		return base.Zero[Out](), err
	}
	return r.Result, nil
}

// Run executes the Action's function in a new trace span.
func (a *ActionDef[In, Out, Stream]) runWithTelemetry(ctx context.Context, input In, cb StreamCallback[Stream]) (output api.ActionRunResult[Out], err error) {
	inputBytes, _ := json.Marshal(input)
	logger.FromContext(ctx).Debug("Action.Run",
		"name", a.Name(),
		"input", inputBytes)
	defer func() {
		outputBytes, _ := json.Marshal(output)
		logger.FromContext(ctx).Debug("Action.Run",
			"name", a.Name(),
			"output", outputBytes,
			"err", err)
	}()

	// Create span metadata and inject flow name if we're in a flow context
	spanMetadata := &tracing.SpanMetadata{
		Name:    a.desc.Name,
		Type:    "action",
		Subtype: string(a.desc.Type), // The actual action type becomes the subtype
		// IsRoot will be automatically determined in tracing.go based on parent span presence
	}

	// Auto-inject flow name if we're in a flow context
	if flowName := FlowNameFromContext(ctx); flowName != "" {
		if spanMetadata.Metadata == nil {
			spanMetadata.Metadata = make(map[string]string)
		}
		spanMetadata.Metadata["flow:name"] = flowName
	}

	var traceID string
	var spanID string
	o, err := tracing.RunInNewSpan(ctx, spanMetadata, input,
		func(ctx context.Context, input In) (Out, error) {
			traceInfo := tracing.SpanTraceInfo(ctx)
			traceID = traceInfo.TraceID
			spanID = traceInfo.SpanID

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
	return api.ActionRunResult[Out]{
		Result:  o,
		TraceId: traceID,
		SpanId:  spanID,
	}, err
}

// RunJSON runs the action with a JSON input, and returns a JSON result.
func (a *ActionDef[In, Out, Stream]) RunJSON(ctx context.Context, input json.RawMessage, cb StreamCallback[json.RawMessage]) (json.RawMessage, error) {
	r, err := a.RunJSONWithTelemetry(ctx, input, cb)
	if err != nil {
		return nil, err
	}
	return r.Result, nil
}

// RunJSON runs the action with a JSON input, and returns a JSON result along with telemetry info.
func (a *ActionDef[In, Out, Stream]) RunJSONWithTelemetry(ctx context.Context, input json.RawMessage, cb StreamCallback[json.RawMessage]) (*api.ActionRunResult[json.RawMessage], error) {
	var i In
	if len(input) > 0 {
		// First unmarshal input into a generic value to handle unknown fields and null values which
		// would be discard and/or converted into zero values if unmarshaled directly into the In type.
		var rawData any
		if err := json.Unmarshal(input, &rawData); err != nil {
			return nil, NewError(INTERNAL, "failed to unmarshal input: %v", err)
		}

		normalized, err := base.NormalizeInput(rawData, a.desc.InputSchema)
		if err != nil {
			return nil, NewError(INVALID_ARGUMENT, "invalid input: %v", err)
		}

		if err := base.ValidateValue(normalized, a.desc.InputSchema); err != nil {
			return nil, NewError(INVALID_ARGUMENT, err.Error())
		}

		normalizedBytes, err := json.Marshal(normalized)
		if err != nil {
			return nil, NewError(INTERNAL, "failed to marshal normalized input: %v", err)
		}

		if err := json.Unmarshal(normalizedBytes, &i); err != nil {
			return nil, NewError(INTERNAL, "failed to unmarshal normalized input: %v", err)
		}
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

	r, err := a.runWithTelemetry(ctx, i, scb)
	if err != nil {
		return &api.ActionRunResult[json.RawMessage]{
			TraceId: r.TraceId,
			SpanId:  r.SpanId,
		}, err
	}

	bytes, err := json.Marshal(r.Result)
	if err != nil {
		return nil, err
	}

	return &api.ActionRunResult[json.RawMessage]{
		Result:  json.RawMessage(bytes),
		TraceId: r.TraceId,
		SpanId:  r.SpanId,
	}, nil
}

// Desc returns a descriptor of the action.
func (a *ActionDef[In, Out, Stream]) Desc() api.ActionDesc {
	return *a.desc
}

// Register registers the action with the given registry.
func (a *ActionDef[In, Out, Stream]) Register(r api.Registry) {
	r.RegisterAction(a.desc.Key, a)
}

// ResolveActionFor returns the action for the given key in the global registry,
// or nil if there is none.
// It panics if the action is of the wrong api.
func ResolveActionFor[In, Out, Stream any](r api.Registry, atype api.ActionType, name string) *ActionDef[In, Out, Stream] {
	provider, id := api.ParseName(name)
	key := api.NewKey(atype, provider, id)
	a := r.ResolveAction(key)
	if a == nil {
		return nil
	}
	return a.(*ActionDef[In, Out, Stream])
}

// LookupActionFor returns the action for the given key in the global registry,
// or nil if there is none.
// It panics if the action is of the wrong api.
//
// Deprecated: Use ResolveActionFor.
func LookupActionFor[In, Out, Stream any](r api.Registry, atype api.ActionType, name string) *ActionDef[In, Out, Stream] {
	provider, id := api.ParseName(name)
	key := api.NewKey(atype, provider, id)
	a := r.LookupAction(key)
	if a == nil {
		return nil
	}
	return a.(*ActionDef[In, Out, Stream])
}
