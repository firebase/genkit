// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package genkit

import (
	"context"
	"errors"
	"fmt"

	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/core/tracing"
	"github.com/firebase/genkit/go/internal/atype"
	"github.com/firebase/genkit/go/internal/base"
)

// streamingCallback is the type of streaming callbacks.
type streamingCallback[Stream any] func(context.Context, Stream) error

type noStream = func(context.Context, struct{}) error

// A Flow is a user-defined Action. A Flow[In, Out, Stream] represents a function from In to Out. The Stream parameter is for flows that support streaming: providing their results incrementally.
type Flow[In, Out, Stream any] struct {
	action *core.Action[In, Out, Stream]
}

// StreamFlowValue is either a streamed value or a final output of a flow.
type StreamFlowValue[Out, Stream any] struct {
	Done   bool
	Output Out    // valid if Done is true
	Stream Stream // valid if Done is false
}

// flowContextKey is a context key that indicates whether the current context is a flow context.
var flowContextKey = base.NewContextKey[*flowContext]()

// flowContext is a context that contains the tracing state for a flow.
type flowContext struct {
	tracingState *tracing.State
}

// DefineFlow creates a Flow that runs fn, and registers it as an action. fn takes an input of type In and returns an output of type Out.
func DefineFlow[In, Out any](
	g *Genkit,
	name string,
	fn func(context.Context, In) (Out, error),
) *Flow[In, Out, struct{}] {
	a := core.DefineAction(g.reg, "", name, atype.Flow, nil, func(ctx context.Context, input In) (Out, error) {
		fc := &flowContext{tracingState: g.reg.TracingState()}
		return fn(flowContextKey.NewContext(ctx, fc), input)
	})
	return &Flow[In, Out, struct{}]{action: a}
}

// DefineStreamingFlow creates a streaming Flow that runs fn, and registers it as an action.
//
// fn takes an input of type In and returns an output of type Out, optionally
// streaming values of type Stream incrementally by invoking a callback.
//
// If the function supports streaming and the callback is non-nil, it should
// stream the results by invoking the callback periodically, ultimately returning
// with a final return value that includes all the streamed data.
// Otherwise, it should ignore the callback and just return a result.
func DefineStreamingFlow[In, Out, Stream any](
	g *Genkit,
	name string,
	fn func(context.Context, In, func(context.Context, Stream) error) (Out, error),
) *Flow[In, Out, Stream] {
	a := core.DefineStreamingAction(g.reg, "", name, atype.Flow, nil, func(ctx context.Context, input In, cb func(context.Context, Stream) error) (Out, error) {
		fc := &flowContext{tracingState: g.reg.TracingState()}
		return fn(flowContextKey.NewContext(ctx, fc), input, cb)
	})
	return &Flow[In, Out, Stream]{action: a}
}

// Run runs the function f in the context of the current flow
// and returns what f returns.
// It returns an error if no flow is active.
//
// Each call to Run results in a new step in the flow.
// A step has its own span in the trace, and its result is cached so that if the flow
// is restarted, f will not be called a second time.
func Run[Out any](ctx context.Context, name string, f func() (Out, error)) (Out, error) {
	fc := flowContextKey.FromContext(ctx)
	if fc == nil {
		var z Out
		return z, fmt.Errorf("flow.Run(%q): must be called from a flow", name)
	}
	return tracing.RunInNewSpan(ctx, fc.tracingState, name, "flowStep", false, nil, func(ctx context.Context, _ any) (Out, error) {
		tracing.SetCustomMetadataAttr(ctx, "genkit:name", name)
		tracing.SetCustomMetadataAttr(ctx, "genkit:type", "flowStep")
		o, err := f()
		if err != nil {
			return base.Zero[Out](), err
		}
		return o, nil
	})
}

// Run runs the flow in the context of another flow.
func (f *Flow[In, Out, Stream]) Run(ctx context.Context, input In) (Out, error) {
	return f.action.Run(ctx, input, nil)
}

// Stream runs the flow in the context of another flow and streams the output.
// It returns a function whose argument function (the "yield function") will be repeatedly
// called with the results.
//
// If the yield function is passed a non-nil error, the flow has failed with that
// error; the yield function will not be called again.
//
// If the yield function's [StreamFlowValue] argument has Done == true, the value's
// Output field contains the final output; the yield function will not be called
// again.
//
// Otherwise the Stream field of the passed [StreamFlowValue] holds a streamed result.
func (f *Flow[In, Out, Stream]) Stream(ctx context.Context, input In) func(func(*StreamFlowValue[Out, Stream], error) bool) {
	return func(yield func(*StreamFlowValue[Out, Stream], error) bool) {
		cb := func(ctx context.Context, s Stream) error {
			if ctx.Err() != nil {
				return ctx.Err()
			}
			if !yield(&StreamFlowValue[Out, Stream]{Stream: s}, nil) {
				return errStop
			}
			return nil
		}
		output, err := f.action.Run(ctx, input, cb)
		if err != nil {
			yield(nil, err)
		} else {
			yield(&StreamFlowValue[Out, Stream]{Done: true, Output: output}, nil)
		}
	}
}

var errStop = errors.New("stop")
