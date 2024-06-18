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

// Package genkit provides Genkit functionality for application developers.
package genkit

import (
	"context"
	"errors"
	"net/http"

	"github.com/firebase/genkit/go/core"
)

// DefineFlow creates a Flow that runs fn, and registers it as an action.
//
// fn takes an input of type In and returns an output of type Out.
func DefineFlow[In, Out any](
	name string,
	fn func(ctx context.Context, input In) (Out, error),
) *core.Flow[In, Out, struct{}] {
	return core.InternalDefineFlow(name, core.Func[In, Out, struct{}](func(ctx context.Context, input In, cb func(ctx context.Context, _ struct{}) error) (Out, error) {
		return fn(ctx, input)
	}))
}

// DefineStreamingFlow creates a streaming Flow that runs fn, and registers it as an action.
//
// fn takes an input of type In and returns an output of type Out, optionally
// streaming values of type Stream incrementally by invoking a callback.
// Pass [NoStream] for functions that do not support streaming.
//
// If the function supports streaming and the callback is non-nil, it should
// stream the results by invoking the callback periodically, ultimately returning
// with a final return value. Otherwise, it should ignore the callback and
// just return a result.
func DefineStreamingFlow[In, Out, Stream any](
	name string,
	fn func(ctx context.Context, input In, callback func(context.Context, Stream) error) (Out, error),
) *core.Flow[In, Out, Stream] {
	return core.InternalDefineFlow(name, core.Func[In, Out, Stream](fn))
}

// Run runs the function f in the context of the current flow
// and returns what f returns.
// It returns an error if no flow is active.
//
// Each call to Run results in a new step in the flow.
// A step has its own span in the trace, and its result is cached so that if the flow
// is restarted, f will not be called a second time.
func Run[Out any](ctx context.Context, name string, f func() (Out, error)) (Out, error) {
	return core.InternalRun(ctx, name, f)
}

// RunFlow runs flow in the context of another flow. The flow must run to completion when started
// (that is, it must not have interrupts).
func RunFlow[In, Out, Stream any](ctx context.Context, flow *core.Flow[In, Out, Stream], input In) (Out, error) {
	return core.InternalRunFlow(ctx, flow, input)
}

// StreamFlowValue is either a streamed value or a final output of a flow.
type StreamFlowValue[Out, Stream any] struct {
	Done   bool
	Output Out    // valid if Done is true
	Stream Stream // valid if Done is false
}

// StreamFlow runs flow on input and delivers both the streamed values and the final output.
// It returns a function whose argument function (the "yield function") will be repeatedly
// called with the results.
//
// If the yield function is passed a non-nil error, the flow has failed with that
// error; the yield function will not be called again. An error is also passed if
// the flow fails to complete (that is, it has an interrupt).
// Genkit Go does not yet support interrupts.
//
// If the yield function's [StreamFlowValue] argument has Done == true, the value's
// Output field contains the final output; the yield function will not be called
// again.
//
// Otherwise the Stream field of the passed [StreamFlowValue] holds a streamed result.
func StreamFlow[In, Out, Stream any](ctx context.Context, flow *core.Flow[In, Out, Stream], input In) func(func(*StreamFlowValue[Out, Stream], error) bool) {
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
		output, err := core.InternalStreamFlow(ctx, flow, input, cb)
		if err != nil {
			yield(nil, err)
		} else {
			yield(&StreamFlowValue[Out, Stream]{Done: true, Output: output}, nil)
		}
	}
}

var errStop = errors.New("stop")

// StartFlowServer starts a server serving the routes described in [NewFlowServeMux].
// It listens on addr, or if empty, the value of the PORT environment variable,
// or if that is empty, ":3400".
//
// In development mode (if the environment variable GENKIT_ENV=dev), it also starts
// a dev server.
//
// StartFlowServer always returns a non-nil error, the one returned by http.ListenAndServe.
func StartFlowServer(addr string) error {
	return core.StartFlowServer(addr)
}

// NewFlowServeMux constructs a [net/http.ServeMux] where each defined flow is a route.
// All routes take a single query parameter, "stream", which if true will stream the
// flow's results back to the client. (Not all flows support streaming, however.)
//
// To use the returned ServeMux as part of a server with other routes, either add routes
// to it, or install it as part of another ServeMux, like so:
//
//	mainMux := http.NewServeMux()
//	mainMux.Handle("POST /flow/", http.StripPrefix("/flow/", NewFlowServeMux()))
func NewFlowServeMux() *http.ServeMux {
	return core.NewFlowServeMux()
}
