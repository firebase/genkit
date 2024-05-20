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
	"crypto/md5"
	"fmt"
	"os"
	"path/filepath"
	"sync"

	"github.com/firebase/genkit/go/internal"
	gtrace "github.com/firebase/genkit/go/trace"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/codes"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	"go.opentelemetry.io/otel/trace"
)

// tracingState holds OpenTelemetry values for creating traces.
type tracingState struct {
	tp     *sdktrace.TracerProvider // references TraceStores
	tracer trace.Tracer             // returned from tp.Tracer(), cached
}

func newTracingState() *tracingState {
	tp := sdktrace.NewTracerProvider()
	return &tracingState{
		tp:     tp,
		tracer: tp.Tracer("genkit-tracer", trace.WithInstrumentationVersion("v1")),
	}
}

func (ts *tracingState) registerSpanProcessor(sp sdktrace.SpanProcessor) {
	ts.tp.RegisterSpanProcessor(sp)
}

// addTraceStoreImmediate adds tstore to the tracingState.
// Traces are saved immediately as they are finshed.
// Use this for a trace.Store with a fast Save method,
// such as one that writes to a file.
func (ts *tracingState) addTraceStoreImmediate(tstore gtrace.Store) {
	e := newTraceStoreExporter(tstore)
	// Adding a SimpleSpanProcessor is like using the WithSyncer option.
	ts.registerSpanProcessor(sdktrace.NewSimpleSpanProcessor(e))
	// Ignore tracerProvider.Shutdown. It shouldn't be needed when using WithSyncer.
	// Confirmed for OTel packages as of v1.24.0.
	// Also requires traceStoreExporter.Shutdown to be a no-op.
}

// addTraceStoreBatch adds ts to the tracingState.
// Traces are batched before being sent for processing.
// Use this for a trace.Store with a potentially expensive Save method,
// such as one that makes an RPC.
// Callers must invoke the returned function at the end of the program to flush the final batch
// and perform other cleanup.
func (ts *tracingState) addTraceStoreBatch(tstore gtrace.Store) (shutdown func(context.Context) error) {
	e := newTraceStoreExporter(tstore)
	// Adding a BatchSpanProcessor is like using the WithBatcher option.
	ts.registerSpanProcessor(sdktrace.NewBatchSpanProcessor(e))
	return ts.tp.Shutdown
}

func newDevTraceStore() (gtrace.Store, error) {
	programName := filepath.Base(os.Args[0])
	rootHash := fmt.Sprintf("%02x", md5.Sum([]byte(programName)))
	dir := filepath.Join(os.TempDir(), ".genkit", rootHash, "traces")
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return nil, err
	}
	// Don't remove the temp directory, for post-mortem debugging.
	return gtrace.NewFileStore(dir)
}

// The rest of this file contains code translated from js/common/src/tracing/*.ts.

const (
	attrPrefix   = "genkit"
	spanTypeAttr = attrPrefix + ":type"
)

// runInNewSpan runs f on input in a new span with the given name.
// The attrs map provides the span's initial attributes.
func runInNewSpan[I, O any](
	ctx context.Context,
	tstate *tracingState,
	name, spanType string,
	isRoot bool,
	input I,
	f func(context.Context, I) (O, error),
) (O, error) {
	// TODO(jba): support span links.
	log := logger(ctx)
	log.Debug("span start", "name", name)
	defer log.Debug("span end", "name", name)
	sm := &spanMetadata{
		Name:   name,
		Input:  input,
		IsRoot: isRoot,
	}
	parentSpanMeta := spanMetaKey.fromContext(ctx)
	var parentPath string
	if parentSpanMeta != nil {
		parentPath = parentSpanMeta.Path
	}
	sm.Path = parentPath + "/" + name
	var opts []trace.SpanStartOption
	if spanType != "" {
		opts = append(opts, trace.WithAttributes(attribute.String(spanTypeAttr, spanType)))
	}
	ctx, span := tstate.tracer.Start(ctx, name, opts...)
	defer span.End()
	// At the end, copy some of the spanMetadata to the OpenTelemetry span.
	defer func() { span.SetAttributes(sm.attributes()...) }()
	// Add the spanMetadata to the context, so the function can access it.
	ctx = spanMetaKey.newContext(ctx, sm)
	// Run the function.
	output, err := f(ctx, input)

	if err != nil {
		sm.State = spanStateError
		span.SetStatus(codes.Error, err.Error())
		return internal.Zero[O](), err
	}
	// TODO(jba): the typescript code checks if sm.State == error here. Can that happen?
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
		attribute.String("genkit:input", internal.JSONString(sm.Input)),
		attribute.String("genkit:path", sm.Path),
		attribute.String("genkit:output", internal.JSONString(sm.Output)),
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
var spanMetaKey = newContextKey[*spanMetadata]()

// SetCustomMetadataAttr records a key in the current span metadata.
func SetCustomMetadataAttr(ctx context.Context, key, value string) {
	spanMetaKey.fromContext(ctx).SetAttr(key, value)
}
