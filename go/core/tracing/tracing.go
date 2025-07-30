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
	"errors"
	"strings"
	"sync"

	"github.com/firebase/genkit/go/core/logger"
	"github.com/firebase/genkit/go/internal/base"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/codes"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	"go.opentelemetry.io/otel/trace"
)

// markedError wraps an error to track if it's already been marked as a failure source
type markedError struct {
	error
	marked bool
}

func (e *markedError) Error() string {
	return e.error.Error()
}

func (e *markedError) Unwrap() error {
	return e.error
}

// markErrorAsHandled marks an error as already handled for failure source tracking
func markErrorAsHandled(err error) error {
	var me *markedError
	if errors.As(err, &me) {
		me.marked = true
		return me
	}
	// Wrap the error if it's not already a markedError
	return &markedError{error: err, marked: true}
}

// isErrorAlreadyMarked checks if an error has already been marked as a failure source
func isErrorAlreadyMarked(err error) bool {
	var me *markedError
	if errors.As(err, &me) {
		return me.marked
	}
	return false
}

// State holds OpenTelemetry values for creating traces.
type State struct {
	tp     *sdktrace.TracerProvider // references Stores
	tracer trace.Tracer             // returned from tp.Tracer(), cached
}

func NewState() *State {
	tp := sdktrace.NewTracerProvider()
	return &State{
		tp:     tp,
		tracer: tp.Tracer("genkit-tracer", trace.WithInstrumentationVersion("v1")),
	}
}

func (ts *State) RegisterSpanProcessor(sp sdktrace.SpanProcessor) {
	ts.tp.RegisterSpanProcessor(sp)
}

// WriteTelemetryImmediate adds a telemetry server to the tracingState.
// Traces are saved immediately as they are finshed.
// Use this for a gtrace.Store with a fast Save method,
// such as one that writes to a file.
func (ts *State) WriteTelemetryImmediate(client TelemetryClient) {
	e := newTraceServerExporter(client)
	// Adding a SimpleSpanProcessor is like using the WithSyncer option.
	ts.RegisterSpanProcessor(sdktrace.NewSimpleSpanProcessor(e))
	// Ignore tracerProvider.Shutdown. It shouldn't be needed when using WithSyncer.
	// Confirmed for OTel packages as of v1.24.0.
	// Also requires traceStoreExporter.Shutdown to be a no-op.
}

// WriteTelemetryBatch adds a telemetry server to the tracingState.
// Traces are batched before being sent for processing.
// Use this for a gtrace.Store with a potentially expensive Save method,
// such as one that makes an RPC.
// Callers must invoke the returned function at the end of the program to flush the final batch
// and perform other cleanup.
func (ts *State) WriteTelemetryBatch(client TelemetryClient) (shutdown func(context.Context) error) {
	e := newTraceServerExporter(client)
	// Adding a BatchSpanProcessor is like using the WithBatcher option.
	ts.RegisterSpanProcessor(sdktrace.NewBatchSpanProcessor(e))
	return ts.tp.Shutdown
}

// The rest of this file contains code translated from js/common/src/tracing/*.ts.

const (
	attrPrefix   = "genkit"
	spanTypeAttr = attrPrefix + ":type"
)

// SpanMetadata contains metadata information for creating properly annotated spans
type SpanMetadata struct {
	// Name is the span name
	Name string
	// IsRoot indicates if this is a root span
	IsRoot bool
	// Type represents the kind of span (e.g., "action", "flowStep")
	Type string
	// Subtype provides more specific categorization (e.g., "tool", "flow", "model")
	Subtype string
	// TelemetryLabels are arbitrary key-value pairs set directly as span attributes
	// These can have any name (e.g., "genkit:sessionId": "123", "custom.label": "value")
	// This matches TypeScript's telemetryLabels concept
	TelemetryLabels map[string]string
	// Metadata are genkit-specific metadata that get "genkit:metadata:" prefix
	// (e.g., "subtype": "tool" becomes "genkit:metadata:subtype": "tool")
	Metadata map[string]string
}

// RunInNewSpan runs f on input in a new span with the provided metadata.
// The metadata contains all span configuration including name, type, labels, etc.
func RunInNewSpan[I, O any](
	ctx context.Context,
	tstate *State,
	metadata *SpanMetadata,
	input I,
	f func(context.Context, I) (O, error),
) (O, error) {
	// TODO: support span links.
	log := logger.FromContext(ctx)
	log.Debug("span start", "name", metadata.Name)
	defer log.Debug("span end", "name", metadata.Name)

	// Ensure metadata exists
	if metadata == nil {
		metadata = &SpanMetadata{}
	}

	sm := &spanMetadata{
		Name:     metadata.Name,
		Input:    input,
		IsRoot:   metadata.IsRoot,
		Type:     metadata.Type,
		Subtype:  metadata.Subtype,
		Metadata: metadata.Metadata,
		mu:       sync.Mutex{},
	}

	// Get parent span path from context
	var parentPath string
	if parentSM := spanMetaKey.FromContext(ctx); parentSM != nil {
		parentPath = parentSM.Path
	}

	// Build path with type annotations like JS: /{name,t:type}
	sm.Path = buildAnnotatedPath(metadata.Name, parentPath, metadata.Type)

	// Add subtype decoration if subtype is specified
	if metadata.Subtype != "" {
		sm.Path = decoratePathWithSubtype(sm.Path, metadata.Subtype)
	}

	var opts []trace.SpanStartOption
	// Add arbitrary attributes
	if metadata.TelemetryLabels != nil {
		var attrs []attribute.KeyValue
		for k, v := range metadata.TelemetryLabels {
			attrs = append(attrs, attribute.String(k, v))
		}
		opts = append(opts, trace.WithAttributes(attrs...))
	}

	ctx, span := tstate.tracer.Start(ctx, metadata.Name, opts...)
	defer span.End()
	// At the end, copy some of the spanMetadata to the OpenTelemetry span.
	defer func() {
		span.SetAttributes(sm.attributes()...)
	}()

	ctx = spanMetaKey.NewContext(ctx, sm)
	output, err := f(ctx, input)
	if err != nil {
		sm.State = spanStateError

		// Add genkit:isFailureSource logic like TypeScript
		// Mark the first failing span as the source of failure. Prevent parent
		// spans that catch re-thrown exceptions from also claiming to be the source.
		if !isErrorAlreadyMarked(err) {
			// Set isFailureSource directly on span at runtime
			span.SetAttributes(attribute.String("genkit:isFailureSource", "true"))
			err = markErrorAsHandled(err) // Mark error to prevent parent spans from claiming failure source
		}

		span.SetStatus(codes.Error, err.Error())
	} else {
		sm.State = spanStateSuccess
		sm.Output = output
	}
	return output, err
}

// buildAnnotatedPath creates a path with type annotations
// e.g., /{chatFlow,t:flow}/{generateResponse,t:action}
func buildAnnotatedPath(name, parentPath, spanType string) string {
	pathSegment := name
	if spanType != "" {
		pathSegment = name + ",t:" + spanType
	}
	// Always wrap in braces for hierarchical path format
	pathSegment = "{" + pathSegment + "}"
	return parentPath + "/" + pathSegment
}

// decoratePathWithSubtype adds subtype annotation to the final path segment
// e.g., /{flow,t:action}/{step,t:action} -> /{flow,t:action,s:flow}/{step,t:action,s:tool}
func decoratePathWithSubtype(path string, subtype string) string {
	if path == "" || subtype == "" {
		return path
	}

	// Find the last opening brace to locate the final path segment
	lastBraceIndex := strings.LastIndex(path, "{")
	if lastBraceIndex == -1 {
		return path // No braces found, nothing to decorate
	}

	// Find the closing brace after the last opening brace
	closingBraceIndex := strings.Index(path[lastBraceIndex:], "}")
	if closingBraceIndex == -1 {
		return path // No closing brace found
	}
	closingBraceIndex += lastBraceIndex

	// Extract the content of the last segment (without braces)
	segmentContent := path[lastBraceIndex+1 : closingBraceIndex]

	// Add subtype annotation
	decoratedContent := segmentContent + ",s:" + subtype

	// Rebuild the path with the decorated last segment
	return path[:lastBraceIndex+1] + decoratedContent + path[closingBraceIndex:]
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
	Name     string
	State    spanState
	IsRoot   bool
	Input    any
	Output   any
	Path     string            // annotated path with type information
	Type     string            // span type (action, flow, model, etc.)
	Subtype  string            // span subtype (tool, model, flow, etc.)
	Metadata map[string]string // additional custom metadata
	mu       sync.Mutex
}

// attributes returns some information about the spanMetadata
// as a slice of OpenTelemetry attributes that genkit telemetry plugins expect.
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

	// Add genkit:type if specified
	if sm.Type != "" {
		kvs = append(kvs, attribute.String("genkit:type", sm.Type))
	}

	// Add genkit:metadata:subtype if specified
	if sm.Subtype != "" {
		kvs = append(kvs, attribute.String("genkit:metadata:subtype", sm.Subtype))
	}

	if sm.IsRoot {
		kvs = append(kvs, attribute.Bool("genkit:isRoot", sm.IsRoot))
	}

	// Add custom metadata attributes
	if sm.Metadata != nil {
		for k, v := range sm.Metadata {
			kvs = append(kvs, attribute.String(attrPrefix+":metadata:"+k, v))
		}
	}

	return kvs
}

// spanMetaKey is for storing spanMetadatas in a context.
var spanMetaKey = base.NewContextKey[*spanMetadata]()

// SpanPath returns the path as recorded in the current span metadata.
func SpanPath(ctx context.Context) string {
	return spanMetaKey.FromContext(ctx).Path
}
