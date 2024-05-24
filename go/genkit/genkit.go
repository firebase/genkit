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

// Run the npm script that generates JSON Schemas from the zod types
// in the *.ts files. It writes the result to genkit-tools/genkit-schema.json
//go:generate npm --prefix ../../genkit-tools run export:schemas

// Run the Go code generator on the file just created.
//go:generate go run ../internal/cmd/jsonschemagen -outdir .. -config schemas.config ../../genkit-tools/genkit-schema.json genkit

// Package genkit provides Genkit functionality for application developers.
package genkit

import (
	"context"
	"errors"
	"net/http"

	"github.com/firebase/genkit/go/core"
)

// DefineFlow creates a Flow that runs fn, and registers it as an action.
func DefineFlow[I, O, S any](name string, fn core.Func[I, O, S]) *core.Flow[I, O, S] {
	return core.DefineFlow(name, fn)
}

// Run runs the function f in the context of the current flow.
// It returns an error if no flow is active.
//
// Each call to Run results in a new step in the flow.
// A step has its own span in the trace, and its result is cached so that if the flow
// is restarted, f will not be called a second time.
func Run[T any](ctx context.Context, name string, f func() (T, error)) (T, error) {
	return core.Run(ctx, name, f)
}

// RunFlow runs flow in the context of another flow. The flow must run to completion when started
// (that is, it must not have interrupts).
func RunFlow[I, O, S any](ctx context.Context, flow *core.Flow[I, O, S], input I) (O, error) {
	return core.RunFlow(ctx, flow, input)
}

type NoStream = core.NoStream

// StreamFlowValue is either a streamed value or a final output of a flow.
type StreamFlowValue[O, S any] struct {
	Done   bool
	Output O // valid if Done is true
	Stream S // valid if Done is false
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
func StreamFlow[I, O, S any](ctx context.Context, flow *core.Flow[I, O, S], input I) func(func(*StreamFlowValue[O, S], error) bool) {
	return func(yield func(*StreamFlowValue[O, S], error) bool) {
		cb := func(ctx context.Context, s S) error {
			if ctx.Err() != nil {
				return ctx.Err()
			}
			if !yield(&StreamFlowValue[O, S]{Stream: s}, nil) {
				return errStop
			}
			return nil
		}
		output, err := core.InternalStreamFlow(ctx, flow, input, cb)
		if err != nil {
			yield(nil, err)
		} else {
			yield(&StreamFlowValue[O, S]{Done: true, Output: output}, nil)
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
