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

// The tracing package provides support for execution traces.
package tracing

import (
	"context"
	"os"
	"sync"

	"github.com/firebase/genkit/go/core/logger"
	"github.com/firebase/genkit/go/internal/base"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/codes"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	"go.opentelemetry.io/otel/trace"
)

var (
	globalProvider     *sdktrace.TracerProvider
	globalProviderOnce sync.Once
)

// GetGlobalTracerProvider returns the global tracer provider, creating it if needed.
func GetGlobalTracerProvider() *sdktrace.TracerProvider {
	globalProviderOnce.Do(func() {
		globalProvider = sdktrace.NewTracerProvider()
		otel.SetTracerProvider(globalProvider)

		// Auto-configure telemetry if environment variable is set
		if telemetryURL := os.Getenv("GENKIT_TELEMETRY_SERVER"); telemetryURL != "" {
			WriteTelemetryImmediate(NewHTTPTelemetryClient(telemetryURL))
		}
	})
	return globalProvider
}

// GetGlobalTracer returns a tracer from the global tracer provider.
func GetGlobalTracer() trace.Tracer {
	return GetGlobalTracerProvider().Tracer("genkit-tracer", trace.WithInstrumentationVersion("v1"))
}

// RegisterSpanProcessor registers a span processor with the global provider.
func RegisterSpanProcessor(sp sdktrace.SpanProcessor) {
	GetGlobalTracerProvider().RegisterSpanProcessor(sp)
}

// WriteTelemetryImmediate adds a telemetry server to the global tracer provider.
// Traces are saved immediately as they are finished.
// Use this for a gtrace.Store with a fast Save method,
// such as one that writes to a file.
func WriteTelemetryImmediate(client TelemetryClient) {
	e := newTraceServerExporter(client)
	// Adding a SimpleSpanProcessor is like using the WithSyncer option.
	RegisterSpanProcessor(sdktrace.NewSimpleSpanProcessor(e))
	// Ignore tracerProvider.Shutdown. It shouldn't be needed when using WithSyncer.
	// Confirmed for OTel packages as of v1.24.0.
	// Also requires traceStoreExporter.Shutdown to be a no-op.
}

// WriteTelemetryBatch adds a telemetry server to the global tracer provider.
// Traces are batched before being sent for processing.
// Use this for a gtrace.Store with a potentially expensive Save method,
// such as one that makes an RPC.
// Callers must invoke the returned function at the end of the program to flush the final batch
// and perform other cleanup.
func WriteTelemetryBatch(client TelemetryClient) (shutdown func(context.Context) error) {
	e := newTraceServerExporter(client)
	// Adding a BatchSpanProcessor is like using the WithBatcher option.
	RegisterSpanProcessor(sdktrace.NewBatchSpanProcessor(e))
	return GetGlobalTracerProvider().Shutdown
}

// The rest of this file contains code translated from js/common/src/tracing/*.ts.

const (
	attrPrefix   = "genkit"
	spanTypeAttr = attrPrefix + ":type"
)

// RunInNewSpan runs f on input in a new span with the given name.
// The attrs map provides the span's initial attributes.
func RunInNewSpan[I, O any](
	ctx context.Context,
	name, spanType string,
	isRoot bool,
	input I,
	f func(context.Context, I) (O, error),
) (O, error) {
	// TODO: support span links.
	log := logger.FromContext(ctx)
	log.Debug("span start", "name", name)
	defer log.Debug("span end", "name", name)
	sm := &spanMetadata{
		Name:   name,
		Input:  input,
		IsRoot: isRoot,
	}
	parentSpanMeta := spanMetaKey.FromContext(ctx)
	var parentPath string
	if parentSpanMeta != nil {
		parentPath = parentSpanMeta.Path
	}
	sm.Path = parentPath + "/" + name
	var opts []trace.SpanStartOption
	if spanType != "" {
		opts = append(opts, trace.WithAttributes(attribute.String(spanTypeAttr, spanType)))
	}
	ctx, span := GetGlobalTracer().Start(ctx, name, opts...)
	defer span.End()
	// At the end, copy some of the spanMetadata to the OpenTelemetry span.
	defer func() { span.SetAttributes(sm.attributes()...) }()
	// Add the spanMetadata to the context, so the function can access it.
	ctx = spanMetaKey.NewContext(ctx, sm)
	// Run the function.
	output, err := f(ctx, input)

	if err != nil {
		sm.State = spanStateError
		span.SetStatus(codes.Error, err.Error())
		span.RecordError(err)
		return base.Zero[O](), err
	}
	// TODO: the typescript code checks if sm.State == error here. Can that happen?
	sm.State = spanStateSuccess
	sm.Output = output
	return output, nil

}

// spanState is the completion status of a span.
// An empty spanState indicates that the span has not ended.
type spanState string

const (
	spanStateSuccess spanState = "success"
	spanStateError   spanState = "error"
)

// spanMetadata holds genkit-specific information about a span.
type spanMetadata struct {
	Name   string
	State  spanState
	IsRoot bool
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
		attribute.String("genkit:name", sm.Name),
		attribute.String("genkit:state", string(sm.State)),
		attribute.String("genkit:input", base.JSONString(sm.Input)),
		attribute.String("genkit:path", sm.Path),
		attribute.String("genkit:output", base.JSONString(sm.Output)),
	}
	if sm.IsRoot {
		kvs = append(kvs, attribute.Bool("genkit:isRoot", sm.IsRoot))
	}
	for k, v := range sm.attrs {
		kvs = append(kvs, attribute.String(attrPrefix+":metadata:"+k, v))
	}
	return kvs
}

// spanMetaKey is for storing spanMetadatas in a context.
var spanMetaKey = base.NewContextKey[*spanMetadata]()

// SetCustomMetadataAttr records a key in the current span metadata.
func SetCustomMetadataAttr(ctx context.Context, key, value string) {
	spanMetaKey.FromContext(ctx).SetAttr(key, value)
}

// SpanPath returns the path as recroding in the current span metadata.
func SpanPath(ctx context.Context) string {
	return spanMetaKey.FromContext(ctx).Path
}
