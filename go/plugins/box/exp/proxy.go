// Copyright 2026 Google LLC
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

package exp

import (
	"context"
	"encoding/json"
	"fmt"
	"reflect"

	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/trace"

	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/core/api"
)

// Span attributes that mark a proxied call in the caller's trace. The proxy
// is a real action, so its span is the caller-side half of the call; the box
// records its own trace, linked through boxTraceIDAttr.
const (
	boxAttr        = "genkit:metadata:box"
	boxTraceIDAttr = "genkit:metadata:box:traceId"
)

// ProxyOption configures a proxy built from a name rather than from a real
// action ([NewTool], [NewFlow], and their Define variants).
type ProxyOption func(*proxyOptions)

type proxyOptions struct {
	description  string
	inputSchema  map[string]any
	outputSchema map[string]any
	streamSchema map[string]any
}

// WithDescription sets a flow proxy's description. Tool proxies take theirs
// as an argument, like [ai.NewTool].
func WithDescription(d string) ProxyOption {
	return func(o *proxyOptions) { o.description = d }
}

// WithInputSchema sets the proxy's input schema, for callers that only have
// JSON Schema (config, or the box's [Box.ListActions] metadata). Like
// [ai.WithInputSchema] it stands in for the In type parameter, which must be
// any.
func WithInputSchema(schema map[string]any) ProxyOption {
	return func(o *proxyOptions) { o.inputSchema = schema }
}

// WithOutputSchema sets the proxy's output schema; see [WithInputSchema]. Out
// must be any.
func WithOutputSchema(schema map[string]any) ProxyOption {
	return func(o *proxyOptions) { o.outputSchema = schema }
}

// WithStreamSchema sets a streaming flow proxy's chunk schema; see
// [WithInputSchema]. Stream must be any.
func WithStreamSchema(schema map[string]any) ProxyOption {
	return func(o *proxyOptions) { o.streamSchema = schema }
}

func applyProxyOptions(opts []ProxyOption) *proxyOptions {
	o := &proxyOptions{}
	for _, opt := range opts {
		opt(o)
	}
	return o
}

// requireAny panics unless T is an interface type: an explicit schema stands
// in for the type parameter, and a concrete type would disagree with it.
func requireAny[T any](ctor, name, what string) {
	if reflect.TypeFor[T]().Kind() != reflect.Interface {
		panic(fmt.Errorf("%s %q: %s requires its type parameter to be any, got %v", ctor, name, what, reflect.TypeFor[T]()))
	}
}

// isAny reports whether T is an interface type (in practice any).
func isAny[T any]() bool { return reflect.TypeFor[T]().Kind() == reflect.Interface }

// call runs one proxied call: it marks the caller-side span, dispatches req
// through the box, and records the box's trace id on the span.
func (b *Box) call(ctx context.Context, req *RunActionRequest, opts *RunOptions) (json.RawMessage, error) {
	span := trace.SpanFromContext(ctx)
	span.SetAttributes(attribute.String(boxAttr, b.id))
	if req.Context == nil {
		req.Context = core.FromContext(ctx)
	}
	res, err := b.dispatch(ctx, req, opts)
	if err != nil {
		return nil, err
	}
	if res.TraceID != "" {
		span.SetAttributes(attribute.String(boxTraceIDAttr, res.TraceID))
	}
	return res.Result, nil
}

// decodeJSON decodes raw into a T. Empty or null input yields the zero T.
func decodeJSON[T any](raw json.RawMessage, what string) (T, error) {
	var v T
	if len(raw) == 0 || string(raw) == "null" {
		return v, nil
	}
	if err := json.Unmarshal(raw, &v); err != nil {
		return v, fmt.Errorf("box: decode %s: %w", what, err)
	}
	return v, nil
}

// actionKey is the key of the named action in the box.
func actionKey(t api.ActionType, name string) string {
	return api.KeyFromName(t, name)
}
