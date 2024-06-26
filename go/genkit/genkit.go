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
	"net/http"

	"github.com/firebase/genkit/go/core"
)

// Options are options to [Init].
type Options struct {
	// If "-", do not start a FlowServer.
	// Otherwise, start a FlowServer on the given address, or the
	// default of ":3400" if empty.
	FlowAddr string
	// The names of flows to serve.
	// If empty, all registered flows are served.
	Flows []string
}

// Init initializes Genkit.
// After it is called, no further actions can be defined.
//
// Init starts servers depending on the value of the GENKIT_ENV
// environment variable and the provided options.
//
// If GENKIT_ENV = "dev", a development server is started
// in a separate goroutine at the address in opts.DevAddr, or the default
// of ":3100" if empty.
//
// If opts.FlowAddr is a value other than "-", a flow server is started (see [StartFlowServer])
// and the call to Init waits for the server to shut down.
// If opts.FlowAddr == "-", no flow server is started and Init returns immediately.
//
// Thus Init(nil) will start a dev server in the "dev" environment, will always start
// a flow server, and will pause execution until the flow server terminates.
func Init(opts *Options) error {
	return core.InternalInit((*core.Options)(opts))
}

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

// StartFlowServer starts a server serving the routes described in [NewFlowServeMux].
// It listens on addr, or if empty, the value of the PORT environment variable,
// or if that is empty, ":3400".
//
// In development mode (if the environment variable GENKIT_ENV=dev), it also starts
// a dev server.
//
// StartFlowServer always returns a non-nil error, the one returned by http.ListenAndServe.
func StartFlowServer(addr string, flows []string) error {
	return core.StartFlowServer(addr, flows)
}

// NewFlowServeMux constructs a [net/http.ServeMux].
// If flows is non-empty, the each of the named flows is registered as a route.
// Otherwise, all defined flows are registered.
// All routes take a single query parameter, "stream", which if true will stream the
// flow's results back to the client. (Not all flows support streaming, however.)
//
// To use the returned ServeMux as part of a server with other routes, either add routes
// to it, or install it as part of another ServeMux, like so:
//
//	mainMux := http.NewServeMux()
//	mainMux.Handle("POST /flow/", http.StripPrefix("/flow/", NewFlowServeMux()))
func NewFlowServeMux(flows []string) *http.ServeMux {
	return core.NewFlowServeMux(flows)
}
