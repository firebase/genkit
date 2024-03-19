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

// Types related to storing trace information.

import (
	"context"
	"time"
)

// A TraceStore stores trace information.
// Every trace has a unique ID.
type TraceStore interface {
	// Save saves the TraceData to the store. If a TraceData with the id already exists,
	// the two are merged.
	Save(ctx context.Context, id string, td *TraceData) error
	// Load reads the TraceData with the given ID from the store.
	// It returns an error that is fs.ErrNotExist if there isn't one.
	Load(ctx context.Context, id string) (*TraceData, error)
	// List returns all the TraceDatas in the store that satisfy q,
	// sorted by ID.
	List(ctx context.Context, q *TraceQuery) ([]*TraceData, error)
}

// A TraceQuery filters the result of [TraceStore.List].
type TraceQuery struct {
	Limit int // maximum number of traces to return
}

// Microseconds represents a time as the number of microseconds since the Unix epoch.
type Microseconds float64

func timeToMicroseconds(t time.Time) Microseconds {
	nsec := t.UnixNano()
	return Microseconds(float64(nsec) / 1e3)
}

func (m Microseconds) time() time.Time {
	sec := int64(m / 1e6)
	nsec := int64((float64(m) - float64(sec*1e6)) * 1e3)
	return time.Unix(sec, nsec)
}

// TraceData is information about a trace.
type TraceData struct {
	DisplayName string               `json:"displayName"`
	StartTime   Microseconds         `json:"startTime"`
	EndTime     Microseconds         `json:"endTime"`
	Spans       map[string]*SpanData `json:"spans"`
}

// SpanData is information about a trace span.
// Most of this information comes from OpenTelemetry.
// See https://pkg.go.dev/go.opentelemetry.io/otel/sdk/trace#ReadOnlySpan.
// SpanData can be passed to json.Marshal, whereas most of the OpenTelemetry
// types make no claims about JSON serializability.
type SpanData struct {
	SpanID                  string                 `json:"spanId"`
	TraceID                 string                 `json:"traceId,omitempty"`
	ParentSpanID            string                 `json:"parentSpanId,omitempty"`
	StartTime               Microseconds           `json:"startTime"`
	EndTime                 Microseconds           `json:"endTime"`
	Attributes              map[string]any         `json:"attributes"`
	DisplayName             string                 `json:"displayName"`
	Links                   []*Link                `json:"links"`
	InstrumentationLibrary  InstrumentationLibrary `json:"instrumentationLibrary"`
	SpanKind                string                 `json:"spanKind"` // trace.SpanKind as a string
	SameProcessAsParentSpan struct {
		Value bool `json:"value"`
	} `json:"sameProcessAsParentSpan"`
	Status     Status `json:"status"`
	TimeEvents struct {
		TimeEvent []TimeEvent `json:"timeEvent"`
	} `json:"timeEvents"`
}

type TimeEvent struct {
	Time       Microseconds `json:"time"`
	Annotation struct {
		Attributes  map[string]any `json:"attributes"`
		Description string         `json:"description"`
	} `json:"annotation"`
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
	SpanContext            SpanContext    `json:"spanContext"`
	Attributes             map[string]any `json:"attributes"`
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
