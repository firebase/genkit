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
	"testing"

	"github.com/google/go-cmp/cmp"
)

func TestFileTraceStore(t *testing.T) {
	ctx := context.Background()
	td1 := &TraceData{
		DisplayName: "td1",
		StartTime:   10,
		EndTime:     20,
		Spans: map[string]*SpanData{
			"s1": {SpanID: "sid1"},
			"s2": {SpanID: "sid2"},
		},
	}
	ts, err := NewFileTraceStore(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	if err := ts.Save(ctx, "id1", td1); err != nil {
		t.Fatal(err)
	}
	got, err := ts.Load(ctx, "id1")
	if err != nil {
		t.Fatal(err)
	}
	if diff := cmp.Diff(td1, got); diff != "" {
		t.Errorf("mismatch (-want, +got):\n%s", diff)
	}

	// Saving a span with the same ID merges spans and overrides the other
	// fields.
	td2 := &TraceData{
		DisplayName: "td2",
		StartTime:   30,
		EndTime:     40,
		Spans: map[string]*SpanData{
			"s3": {SpanID: "sid3"},
		},
	}
	if err := ts.Save(ctx, "id1", td2); err != nil {
		t.Fatal(err)
	}
	want := &TraceData{
		DisplayName: "td2",
		StartTime:   30,
		EndTime:     40,
		Spans: map[string]*SpanData{
			"s1": {SpanID: "sid1"},
			"s2": {SpanID: "sid2"},
			"s3": {SpanID: "sid3"},
		},
	}
	got, err = ts.Load(ctx, "id1")
	if err != nil {
		t.Fatal(err)
	}
	if diff := cmp.Diff(want, got); diff != "" {
		t.Errorf("mismatch (-want, +got):\n%s", diff)
	}

	// Test List.
	td3 := &TraceData{DisplayName: "td3"}
	if err := ts.Save(ctx, "id3", td3); err != nil {
		t.Fatal(err)
	}
	gotl, err := ts.List(ctx, nil)
	if err != nil {
		t.Fatal(err)
	}
	wantl := []*TraceData{want, td3}
	if diff := cmp.Diff(wantl, gotl); diff != "" {
		t.Errorf("mismatch (-want, +got):\n%s", diff)
	}
}
