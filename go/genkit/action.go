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
)

// An Action is a function with a name.
// It optionally has other metadata, like a description
// and JSON Schemas for its input and output.
//
// Each time an Action is run, it results in a new trace span.
type Action[I, O any] struct {
	name string
	fn   func(context.Context, I) (O, error)
	// optional
	Description string
	Metadata    map[string]any
	// TODO?: JSON schemas for input and output types.
	// JSONSchema can represent additional constraints beyond what the Go type system
	// can express, so we should use them to validate inputs and outputs.
}

// See js/common/src/types.ts

// NewAction creates a new Action with the given name and function.
func NewAction[I, O any](name string, fn func(context.Context, I) (O, error)) *Action[I, O] {
	return &Action[I, O]{
		name: name,
		fn:   fn,
	}
}

// Name returns the Action's name.
func (a *Action[I, O]) Name() string { return a.name }

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
	return runInNewSpan(ctx, a.name, "action", input, a.fn)
}

func (a *Action[I, O]) runJSON(ctx context.Context, input []byte) ([]byte, error) {
	var in I
	if err := json.Unmarshal(input, &in); err != nil {
		return nil, err
	}
	out, err := a.Run(ctx, in)
	if err != nil {
		return nil, err
	}
	return json.Marshal(out)
}

// action is the type that all Action[I, O] have in common.
type action interface {
	Name() string

	// runJSON uses encoding/json to unmarshal the input,
	// calls Action.Run, then returns the marshaled result.
	runJSON(ctx context.Context, input []byte) ([]byte, error)
}
