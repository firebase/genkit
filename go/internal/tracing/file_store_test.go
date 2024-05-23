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

package tracing

import (
	"context"
	"errors"
	"testing"
	"time"

	"github.com/google/go-cmp/cmp"
)

func TestFileStore(t *testing.T) {
	ctx := context.Background()
	td1 := &Data{
		DisplayName: "td1",
		StartTime:   10,
		EndTime:     20,
		Spans: map[string]*SpanData{
			"s1": {SpanID: "sid1"},
			"s2": {SpanID: "sid2"},
		},
	}
	ts, err := NewFileStore(t.TempDir())
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
	td2 := &Data{
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
	want := &Data{
		TraceID:     "id1",
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
	td3 := &Data{DisplayName: "td3"}
	time.Sleep(50 * time.Millisecond) // force different mtimes
	if err := ts.Save(ctx, "id3", td3); err != nil {
		t.Fatal(err)
	}

	gotTDs, gotCT, err := ts.List(ctx, nil)
	// All the Datas, in the expected order.
	wantTDs := []*Data{td3, want}
	if diff := cmp.Diff(wantTDs, gotTDs); diff != "" {
		t.Errorf("mismatch (-want, +got):\n%s", diff)
	}
	if gotCT != "" {
		t.Errorf("continuation token: got %q, want %q", gotCT, "")
	}
}

func TestListRange(t *testing.T) {
	// These tests assume the default limit is 10.
	total := 20
	for _, test := range []struct {
		q                  *Query
		wantStart, wantEnd int
		wantErr            bool
	}{
		{nil, 0, 10, false},
		{
			&Query{Limit: 1},
			0, 1, false,
		},
		{
			&Query{Limit: 5, ContinuationToken: "1"},
			1, 6, false,
		},
		{
			&Query{ContinuationToken: "5"},
			5, 15, false,
		},
		{&Query{Limit: -1}, 0, 0, true},               // negative limit
		{&Query{ContinuationToken: "x"}, 0, 0, true},  // not a number
		{&Query{ContinuationToken: "-1"}, 0, 0, true}, // too small
		{&Query{ContinuationToken: "21"}, 0, 0, true}, // too large
	} {
		gotStart, gotEnd, err := listRange(test.q, total)
		if test.wantErr {
			if !errors.Is(err, ErrBadQuery) {
				t.Errorf("%+v: got err %v, want errBadQuery", test.q, err)
			}
		} else if gotStart != test.wantStart || gotEnd != test.wantEnd || err != nil {
			t.Errorf("%+v: got (%d, %d, %v), want (%d, %d, nil)",
				test.q, gotStart, gotEnd, err, test.wantStart, test.wantEnd)
		}
	}
}
