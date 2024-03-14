package genkit

import (
	"context"
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
	logger(ctx).Debug("Action.Run", "input", fmt.Sprintf("%#v", input))
	defer func() {
		logger(ctx).Debug("Action.Run", "output", fmt.Sprintf("%#v", output), "err", err)
	}()
	// TODO: run the function in a new tracing span.
	return a.fn(ctx, input)
}
