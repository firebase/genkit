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

package telemetryplugin

import (
	"context"
	"log/slog"

	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/sdk/metric"
	"go.opentelemetry.io/otel/sdk/metric/metricdata"
	"go.opentelemetry.io/otel/sdk/trace"
)

// [START pattern1simple]
// Simple direct export - use existing exporters from your telemetry provider

func createYourTraceExporter() (trace.SpanExporter, error) {
	// TODO: Replace with your actual telemetry provider's exporter
	// Examples:
	// - Jaeger: jaeger.New(jaeger.WithCollectorEndpoint("http://localhost:14268/api/traces"))
	// - OTLP: otlptrace.New(ctx, otlptrace.WithEndpoint("http://localhost:4318"))
	// - Datadog: datadog.NewExporter(datadog.WithService("my-service"))

	// For this example, return a simple implementation
	return &simpleTraceExporter{}, nil
}

func createYourMetricExporter() (metric.Exporter, error) {
	// TODO: Replace with your actual telemetry provider's exporter
	// Examples:
	// - Prometheus: prometheus.New()
	// - OTLP: otlpmetric.New(ctx, otlpmetric.WithEndpoint("http://localhost:4318"))
	// - Datadog: datadog.NewMetricExporter(datadog.WithService("my-service"))

	// For this example, return a simple implementation
	return &simpleMetricExporter{}, nil
}

// Simple implementations (replace with real exporters from your provider)
type simpleTraceExporter struct{}

func (e *simpleTraceExporter) ExportSpans(ctx context.Context, spans []trace.ReadOnlySpan) error {
	// TODO: Send spans to your telemetry backend
	return nil
}
func (e *simpleTraceExporter) Shutdown(ctx context.Context) error { return nil }

type simpleMetricExporter struct{}

func (e *simpleMetricExporter) Export(ctx context.Context, rm *metricdata.ResourceMetrics) error {
	// TODO: Send metrics to your telemetry backend
	return nil
}
func (e *simpleMetricExporter) ForceFlush(ctx context.Context) error { return nil }
func (e *simpleMetricExporter) Shutdown(ctx context.Context) error   { return nil }
func (e *simpleMetricExporter) Aggregation(ik metric.InstrumentKind) metric.Aggregation {
	return metric.DefaultAggregationSelector(ik)
}
func (e *simpleMetricExporter) Temporality(ik metric.InstrumentKind) metricdata.Temporality {
	return metricdata.CumulativeTemporality
}

// [END pattern1simple]

// [START pattern2advanced]
// Advanced wrapper with custom processing

// YourAdjustingTraceExporter wraps a real exporter and adds custom processing
type YourAdjustingTraceExporter struct {
	exporter trace.SpanExporter // The real exporter (Jaeger, Datadog, etc.)
}

func (e *YourAdjustingTraceExporter) ExportSpans(ctx context.Context, spans []trace.ReadOnlySpan) error {
	// STEP 1: Your custom processing here
	// Examples:
	// - Filter out sensitive data (like Google Cloud does)
	// - Extract business metrics from spans (like Google Cloud does)
	// - Add custom attributes for your company
	// - Send copies to multiple backends

	processedSpans := e.processSpans(spans)

	// STEP 2: Forward to your real exporter
	return e.exporter.ExportSpans(ctx, processedSpans)
}

func (e *YourAdjustingTraceExporter) processSpans(spans []trace.ReadOnlySpan) []trace.ReadOnlySpan {
	// TODO: Add your custom span processing logic here
	// This is where you'd implement features like:
	// - PII redaction
	// - Custom attributes
	return spans
}

func (e *YourAdjustingTraceExporter) Shutdown(ctx context.Context) error {
	return e.exporter.Shutdown(ctx)
}

func (e *YourAdjustingTraceExporter) ForceFlush(ctx context.Context) error {
	if flusher, ok := e.exporter.(interface{ ForceFlush(context.Context) error }); ok {
		return flusher.ForceFlush(ctx)
	}
	return nil
}

// [END pattern2advanced]

// [START loghandler]
type YourCustomHandler struct {
	Options *slog.HandlerOptions
}

// Enabled implements slog.Handler.
func (y YourCustomHandler) Enabled(ctx context.Context, level slog.Level) bool {
	// TODO: Implement log level filtering
	return level >= slog.LevelInfo
}

// Handle implements slog.Handler.
func (y YourCustomHandler) Handle(ctx context.Context, record slog.Record) error {
	// TODO: Send log to your telemetry provider
	return nil
}

// WithAttrs implements slog.Handler.
func (y YourCustomHandler) WithAttrs(attrs []slog.Attr) slog.Handler {
	// TODO: Return new handler with additional attributes
	return y
}

// WithGroup implements slog.Handler.
func (y YourCustomHandler) WithGroup(name string) slog.Handler {
	// TODO: Return new handler with group name
	return y
}

// [END loghandler]

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
