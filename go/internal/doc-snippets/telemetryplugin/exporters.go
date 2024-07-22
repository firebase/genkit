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

package telemetryplugin

import (
	"context"
	"log/slog"

	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/sdk/metric"
	"go.opentelemetry.io/otel/sdk/metric/metricdata"
	"go.opentelemetry.io/otel/sdk/trace"
)

type YourCustomSpanExporter struct{}

func (e YourCustomSpanExporter) Shutdown(ctx context.Context) error {
	panic("unimplemented")
}

func (e YourCustomSpanExporter) ExportSpans(ctx context.Context, spans []trace.ReadOnlySpan) error {
	panic("unimplemented")
}

type YourCustomMetricExporter struct{}

func (m YourCustomMetricExporter) Aggregation(metric.InstrumentKind) metric.Aggregation {
	panic("unimplemented")
}

func (m YourCustomMetricExporter) Export(context.Context, *metricdata.ResourceMetrics) error {
	panic("unimplemented")
}

func (m YourCustomMetricExporter) ForceFlush(context.Context) error {
	panic("unimplemented")
}

func (m YourCustomMetricExporter) Shutdown(context.Context) error {
	panic("unimplemented")
}

func (m YourCustomMetricExporter) Temporality(metric.InstrumentKind) metricdata.Temporality {
	panic("unimplemented")
}

type YourCustomHandler struct {
	Options *slog.HandlerOptions
}

// Enabled implements slog.Handler.
func (y YourCustomHandler) Enabled(context.Context, slog.Level) bool {
	panic("unimplemented")
}

// Handle implements slog.Handler.
func (y YourCustomHandler) Handle(context.Context, slog.Record) error {
	panic("unimplemented")
}

// WithAttrs implements slog.Handler.
func (y YourCustomHandler) WithAttrs(attrs []slog.Attr) slog.Handler {
	panic("unimplemented")
}

// WithGroup implements slog.Handler.
func (y YourCustomHandler) WithGroup(name string) slog.Handler {
	panic("unimplemented")
}

// [START redactpii]
type redactingSpanExporter struct {
	trace.SpanExporter
}

func (e *redactingSpanExporter) ExportSpans(ctx context.Context, spanData []trace.ReadOnlySpan) error {
	var redacted []trace.ReadOnlySpan
	for _, s := range spanData {
		redacted = append(redacted, redactedSpan{s})
	}
	return e.SpanExporter.ExportSpans(ctx, redacted)
}

func (e *redactingSpanExporter) Shutdown(ctx context.Context) error {
	return e.SpanExporter.Shutdown(ctx)
}

type redactedSpan struct {
	trace.ReadOnlySpan
}

func (s redactedSpan) Attributes() []attribute.KeyValue {
	// Omit input and output, which may contain PII.
	var ts []attribute.KeyValue
	for _, a := range s.ReadOnlySpan.Attributes() {
		if a.Key == "genkit:input" || a.Key == "genkit:output" {
			continue
		}
		ts = append(ts, a)
	}
	return ts
}
// [END redactpii]
