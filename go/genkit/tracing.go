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
	"path"
	"sync"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/codes"
	"go.opentelemetry.io/otel/trace"
)

// This file contains code translated from js/common/src/tracing/*.ts.

// tracer is an OpenTelemetry object that creates traces.
// Use the same one for the lifetime of the process.
var tracer = otel.Tracer("genkit-tracer")

const (
	attrPrefix   = "genkit"
	spanTypeAttr = attrPrefix + ":type"
)

// runInNewSpan runs f on input in a new span with the given name.
// The attrs map provides the span's initial attributes.
func runInNewSpan[I, O any](
	ctx context.Context,
	name, spanType string,
	input I,
	f func(context.Context, I) (O, error),
) (O, error) {
	// TODO(jba): support span links
	log := logger(ctx)
	log.Debug("span start", "name", name)
	defer log.Debug("span end", "name", name)
	sm := &spanMetadata{
		Name:  name,
		Input: input,
	}
	// TODO(jba): Determine whether this span is an immediate child of the root, and understand why it matters.
	parentSpanMeta := spanMetaKey.fromContext(ctx)
	var parentPath string
	if parentSpanMeta != nil {
		parentPath = parentSpanMeta.Path
	}
	sm.Path = path.Join(parentPath, name)
	ctx, span := tracer.Start(ctx, name, trace.WithAttributes(attribute.String(spanTypeAttr, spanType)))
	defer span.End()
	// At the end, copy some of the spanMetadata to the OpenTelemetry span.
	defer func() { span.SetAttributes(sm.attributes()...) }()
	// Add the spanMetadata to the context, so the function can access it.
	ctx = spanMetaKey.newContext(ctx, sm)

	// Run the function.
	output, err := f(ctx, input)

	if err != nil {
		sm.State = SpanStateError
		span.SetStatus(codes.Error, err.Error())
		return zero[O](), err
	}
	// TODO(jba): the typescript code checks if sm.State == error here. Can that happen?
	sm.State = SpanStateSuccess
	sm.Output = output
	return output, nil

}

// SpanState is the completion status of a span.
// An empty SpanState indicates that the span has not ended.
type SpanState string

const (
	SpanStateSuccess SpanState = "success"
	SpanStateError   SpanState = "error"
)

// spanMetadata holds genkit-specific information about a span.
type spanMetadata struct {
	Name   string
	State  SpanState
	Input  any
	Output any
	Path   string // slash-separated list of names from the root span to the current one
	mu     sync.Mutex
	attrs  map[string]string // additional information, as key-value pairs
}

// SetAttr sets an attribute, overwriting whatever is there.
func (sm *spanMetadata) SetAttr(k, v string) {
	if sm == nil {
		return
	}
	sm.mu.Lock()
	defer sm.mu.Unlock()
	if sm.attrs == nil {
		sm.attrs = map[string]string{}
	}
	sm.attrs[k] = v
}

// attributes returns some information about the spanMetadata
// as a slice of OpenTelemetry attributes.
func (sm *spanMetadata) attributes() []attribute.KeyValue {
	sm.mu.Lock()
	defer sm.mu.Unlock()
	kvs := []attribute.KeyValue{
		attribute.String("genkit:state", string(sm.State)),
		attribute.String("genkit:input", jsonString(sm.Input)),
		// TODO(jba): the ts code includes the input but not the output. Why?
		// attribute.String("genkit:output", jsonString(sm.Output))),
	}
	for k, v := range sm.attrs {
		kvs = append(kvs, attribute.String(attrPrefix+":metadata:"+k, v))
	}
	return kvs
}

// spanMetaKey is for storing spanMetadatas in a context.
var spanMetaKey = newContextKey[*spanMetadata]()
