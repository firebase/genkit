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

package genkit

import (
	"context"
	"encoding/json"
	"fmt"
	"maps"
	"reflect"

	"github.com/invopop/jsonschema"
)

// An Action is a function with a name.
// It optionally has other metadata, like a description
// and JSON Schemas for its input and output.
//
// Each time an Action is run, it results in a new trace span.
type Action[I, O any] struct {
	name         string
	fn           func(context.Context, I) (O, error)
	tstate       *tracingState
	inputSchema  *jsonschema.Schema
	outputSchema *jsonschema.Schema
	// optional
	Description string
	Metadata    map[string]any
}

// See js/common/src/types.ts

// NewAction creates a new Action with the given name and function.
func NewAction[I, O any](name string, fn func(context.Context, I) (O, error)) *Action[I, O] {
	var i I
	var o O
	return &Action[I, O]{
		name:         name,
		fn:           fn,
		inputSchema:  inferJSONSchema(i),
		outputSchema: inferJSONSchema(o),
	}
}

// Name returns the Action's name.
func (a *Action[I, O]) Name() string { return a.name }

// setTracingState sets the action's tracingState.
func (a *Action[I, O]) setTracingState(tstate *tracingState) { a.tstate = tstate }

// Run executes the Action's function in a new span.
func (a *Action[I, O]) Run(ctx context.Context, input I) (output O, err error) {
	// TODO: validate input against JSONSchema for I.
	// TODO: validate output against JSONSchema for O.
	logger(ctx).Debug("Action.Run",
		"name", a.name,
		"input", fmt.Sprintf("%#v", input))
	defer func() {
		logger(ctx).Debug("Action.Run",
			"name", a.name,
			"output", fmt.Sprintf("%#v", output),
			"err", err)
	}()
	tstate := a.tstate
	if tstate == nil {
		// This action has probably not been registered.
		tstate = globalRegistry.tstate
	}
	return runInNewSpan(ctx, tstate, a.name, "action", false, input, a.fn)
}

func (a *Action[I, O]) runJSON(ctx context.Context, input json.RawMessage) (json.RawMessage, error) {
	var in I
	if err := json.Unmarshal(input, &in); err != nil {
		return nil, err
	}
	out, err := a.Run(ctx, in)
	if err != nil {
		return nil, err
	}
	bytes, err := json.Marshal(out)
	if err != nil {
		return nil, err
	}
	return json.RawMessage(bytes), nil
}

// action is the type that all Action[I, O] have in common.
type action interface {
	Name() string

	// runJSON uses encoding/json to unmarshal the input,
	// calls Action.Run, then returns the marshaled result.
	runJSON(ctx context.Context, input json.RawMessage) (json.RawMessage, error)

	// desc returns a description of the action.
	// It should set all fields of actionDesc except Key, which
	// the registry will set.
	desc() actionDesc

	// setTracingState set's the action's tracingState.
	setTracingState(*tracingState)
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

func (a *Action[I, O]) desc() actionDesc {
	ad := actionDesc{
		Name:         a.name,
		Description:  a.Description,
		Metadata:     a.Metadata,
		InputSchema:  a.inputSchema,
		OutputSchema: a.outputSchema,
	}
	// Required by genkit UI:
	if ad.Metadata == nil {
		ad.Metadata = map[string]any{}
	}
	ad.Metadata["inputSchema"] = nil
	ad.Metadata["outputSchema"] = nil
	return ad
}

func inferJSONSchema(x any) *jsonschema.Schema {
	var r jsonschema.Reflector
	// If x is a struct, put its definition at the "top level" of the schema,
	// instead of nested inside a "$defs" object.
	if reflect.TypeOf(x).Kind() == reflect.Struct {
		r.ExpandedStruct = true
	}
	return r.Reflect(x)
}
