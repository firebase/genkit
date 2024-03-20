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
	"fmt"
	"testing"
	"time"

	"github.com/google/go-cmp/cmp"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/codes"
	"go.opentelemetry.io/otel/sdk/instrumentation"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	"go.opentelemetry.io/otel/sdk/trace/tracetest"
	"go.opentelemetry.io/otel/trace"
)

func TestConvertSpan(t *testing.T) {
	traceID := "1234567890abcdef1234567890abcdef"
	spanID1 := "1234567890abcdef"
	spanID2 := "abcdef1234567890"
	tid, err := trace.TraceIDFromHex(traceID)
	if err != nil {
		t.Fatal(err)
	}
	sid1, err := trace.SpanIDFromHex(spanID1)
	if err != nil {
		t.Fatal(err)
	}
	sid2, err := trace.SpanIDFromHex(spanID2)
	if err != nil {
		t.Fatal(err)
	}
	scfg := trace.SpanContextConfig{
		TraceID:    tid,
		SpanID:     sid1,
		TraceFlags: 1,
		TraceState: trace.TraceState{},
		Remote:     true,
	}
	sc1 := trace.NewSpanContext(scfg)
	scfg.SpanID = sid2
	sc2 := trace.NewSpanContext(scfg)
	ss := tracetest.SpanStub{
		Name:        "name",
		SpanContext: sc1,
		Parent:      sc2,
		SpanKind:    trace.SpanKindInternal,
		StartTime:   time.Unix(1, 0),
		EndTime:     time.Unix(2, 0),
		Attributes:  []attribute.KeyValue{attribute.String("k", "v")},
		Events: []sdktrace.Event{
			{
				Name:       "ename",
				Time:       time.Unix(3, 0),
				Attributes: []attribute.KeyValue{attribute.String("k2", "v2")},
			},
		},
		Links: []sdktrace.Link{{
			SpanContext:           sc1,
			Attributes:            []attribute.KeyValue{attribute.String("k3", "v3")},
			DroppedAttributeCount: 1,
		}},
		Status: sdktrace.Status{
			Code:        codes.Ok,
			Description: "desc",
		},
		InstrumentationLibrary: instrumentation.Library{
			Name:      "iname",
			Version:   "version",
			SchemaURL: "surl",
		},
	}
	want := &SpanData{
		DisplayName:  "name",
		TraceID:      traceID,
		SpanID:       spanID1,
		ParentSpanID: spanID2,
		SpanKind:     "internal",
		StartTime:    Microseconds(1e6),
		EndTime:      Microseconds(2e6),
		Attributes:   map[string]any{"k": "v"},
		TimeEvents: timeEvents{TimeEvent: []TimeEvent{{
			Time: Microseconds(3e6),
			Annotation: annotation{
				Attributes:  map[string]any{"k2": "v2"},
				Description: "ename",
			},
		}}},
		Links: []*Link{{
			SpanContext: SpanContext{
				TraceID:    traceID,
				SpanID:     spanID1,
				IsRemote:   true,
				TraceFlags: 1,
			},
			Attributes:             map[string]any{"k3": "v3"},
			DroppedAttributesCount: 1,
		}},
		Status: Status{2, "desc"},
		InstrumentationLibrary: InstrumentationLibrary{
			Name:      "iname",
			Version:   "version",
			SchemaURL: "surl",
		},
	}

	got := convertSpan(ss.Snapshot())
	diff := cmp.Diff(want, got)
	fmt.Println(diff)
}
