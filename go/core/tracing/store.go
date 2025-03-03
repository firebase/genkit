// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package tracing

// Data is information about a trace.
type Data struct {
	TraceID     string               `json:"traceId"`
	DisplayName string               `json:"displayName"`
	StartTime   Milliseconds         `json:"startTime"`
	EndTime     Milliseconds         `json:"endTime"`
	Spans       map[string]*SpanData `json:"spans"`
}

// SpanData is information about a trace span.
// Most of this information comes from OpenTelemetry.
// See https://pkg.go.dev/go.opentelemetry.io/otel/sdk/trace#ReadOnlySpan.
// SpanData can be passed to json.Marshal, whereas most of the OpenTelemetry
// types make no claims about JSON serializability.
type SpanData struct {
	SpanID                 string                 `json:"spanId"`
	TraceID                string                 `json:"traceId,omitempty"`
	ParentSpanID           string                 `json:"parentSpanId,omitempty"`
	StartTime              Milliseconds           `json:"startTime"`
	EndTime                Milliseconds           `json:"endTime"`
	Attributes             map[string]any         `json:"attributes,omitempty"`
	DisplayName            string                 `json:"displayName"`
	Links                  []*Link                `json:"links,omitempty"`
	InstrumentationLibrary InstrumentationLibrary `json:"instrumentationLibrary,omitempty"`
	SpanKind               string                 `json:"spanKind"` // trace.SpanKind as a string
	// This bool is in a separate struct, to match the js (and presumably the OTel) formats.
	SameProcessAsParentSpan BoolValue  `json:"sameProcessAsParentSpan"`
	Status                  Status     `json:"status"`
	TimeEvents              TimeEvents `json:"timeEvents,omitempty"`
}

type TimeEvents struct {
	TimeEvent []TimeEvent `json:"timeEvent,omitempty"`
}

type BoolValue struct {
	Value bool `json:"value,omitempty"`
}

type TimeEvent struct {
	Time       Milliseconds `json:"time,omitempty"`
	Annotation Annotation   `json:"annotation,omitempty"`
}

type Annotation struct {
	Attributes  map[string]any `json:"attributes,omitempty"`
	Description string         `json:"description,omitempty"`
}

// A SpanContext contains identifying trace information about a Span.
type SpanContext struct {
	TraceID    string `json:"traceId,omitempty"`
	SpanID     string `json:"spanId"`
	IsRemote   bool   `json:"isRemote"`
	TraceFlags int    `json:"traceFlags"`
}

// A Link describes the relationship between two Spans.
type Link struct {
	SpanContext            SpanContext    `json:"spanContext,omitempty"`
	Attributes             map[string]any `json:"attributes,omitempty"`
	DroppedAttributesCount int            `json:"droppedAttributesCount"`
}

// InstrumentationLibrary is a copy of [go.opentelemetry.io/otel/sdk/instrumentation.Library],
// with added struct tags to match the javascript JSON field names.
type InstrumentationLibrary struct {
	Name      string `json:"name"`
	Version   string `json:"version"`
	SchemaURL string `json:"schemaUrl,omitempty"`
}

// Status is a copy of [go.opentelemetry.io/otel/sdk/trace.Status],
// with added struct tags to match the javascript JSON field names.
type Status struct {
	Code        uint32 `json:"code"` // avoid the MarshalJSON method on codes.Code
	Description string `json:"description,omitempty"`
}
