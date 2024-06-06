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

package tests

import (
	"cmp"
	"context"
	"flag"
	"fmt"
	"net/http"
	"path/filepath"
	"slices"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/core/tracing"
	"github.com/firebase/genkit/go/internal"
	"github.com/firebase/genkit/go/plugins/googleai"
	gocmp "github.com/google/go-cmp/cmp"
	"github.com/google/go-cmp/cmp/cmpopts"
	"github.com/jba/xltest/go/xltest"
	"google.golang.org/api/option"
)

var update = flag.Bool("update", false, "update golden files with results")

func TestGoogleAI(t *testing.T) {
	ctx := context.Background()
	err := googleai.Init(ctx, googleai.Config{
		ClientOptions: []option.ClientOption{option.WithHTTPClient(mockClient())},
		Models:        []string{"gemini-1.5-pro"},
		Embedders:     []string{"embedding-001"},
	})
	if err != nil {
		t.Fatal(err)
	}

	t.Run("embed", func(t *testing.T) {
		test, err := xltest.ReadFile(filepath.Join("testdata", "googleai-embedder.yaml"))
		if err != nil {
			t.Fatal(err)
		}
		valfunc := validateEmbedder
		if *update {
			valfunc = updateEmbedder
		}
		test.Run(t, func(text string) (embedderResult, error) {
			ts := &testTraceStore{}
			remove := core.SetDevTraceStore(ts)
			defer remove()
			vals, err := ai.Embed(ctx, googleai.Embedder("embedding-001"), &ai.EmbedRequest{Document: ai.DocumentFromText(text, nil)})
			if err != nil {
				return embedderResult{}, err
			}
			return embedderResult{vals, ts.td}, nil
		}, valfunc)
	})
}

type embedderResult struct {
	values []float32
	trace  *tracing.Data
}

// validateEmbedder compares the results from running an embedder with
// the desired results. The latter are taken from a YAML file and so are in raw
// unmarshalled form.
func validateEmbedder(got embedderResult, rawWant map[string]any) error {
	var want embedderResult
	rawVals := rawWant["values"].([]any)
	f32s := make([]float32, len(rawVals))
	for i, v := range rawVals {
		f32s[i] = float32(v.(float64))
	}
	want.values = f32s
	traceFile := rawWant["traceFile"].(string)
	if err := internal.ReadJSONFile(filepath.Join("testdata", traceFile), &want.trace); err != nil {
		return err
	}
	return compareEmbedderResults(got, want)
}

func compareEmbedderResults(got, want embedderResult) error {
	if !slices.Equal(got.values, want.values) {
		return fmt.Errorf("values: got %v, want %v", got.values, want.values)
	}
	renameSpans(got.trace)
	renameSpans(want.trace)
	opts := []gocmp.Option{
		cmpopts.IgnoreFields(tracing.Data{}, "TraceID", "StartTime", "EndTime"),
		cmpopts.IgnoreFields(tracing.SpanData{}, "TraceID", "StartTime", "EndTime"),
	}
	if diff := gocmp.Diff(want.trace, got.trace, opts...); diff != "" {
		return fmt.Errorf("traces: %s", diff)
	}
	return nil
}

// renameSpans changes the keys of td.Spans to s0, s1, ... in order of the span start time,
// as well as references to those IDs within the spans.
// This makes it possible to compare two span maps with different span IDs.
func renameSpans(td *tracing.Data) {
	type item struct {
		id string
		t  tracing.Milliseconds
	}

	var items []item
	startTimes := map[tracing.Milliseconds]bool{}
	for id, span := range td.Spans {
		if startTimes[span.StartTime] {
			panic("duplicate start times")
		}
		startTimes[span.StartTime] = true
		items = append(items, item{id, span.StartTime})
	}
	slices.SortFunc(items, func(i1, i2 item) int {
		return cmp.Compare(i1.t, i2.t)
	})
	oldIDToNew := map[string]string{}
	for i, item := range items {
		oldIDToNew[item.id] = fmt.Sprintf("s%03d", i)
	}
	// Re-create the span map with the new span IDs.
	m := map[string]*tracing.SpanData{}
	for oldID, span := range td.Spans {
		newID := oldIDToNew[oldID]
		if newID == "" {
			panic(fmt.Sprintf("missing id: %q", oldID))
		}
		m[newID] = span
		// A span references it own span ID and possibly its parent's.
		span.SpanID = oldIDToNew[span.SpanID]
		if span.ParentSpanID != "" {
			span.ParentSpanID = oldIDToNew[span.ParentSpanID]
		}
	}
	td.Spans = m
}

func updateEmbedder(got embedderResult, rawWant map[string]any) error {
	filename := rawWant["traceFile"].(string)
	fmt.Printf("writing %s\n", filename)
	return internal.WriteJSONFile(filename, got.trace)
}

func mockClient() *http.Client {
	mrt := &MockRoundTripper{}
	mrt.Handle("POST /v1beta/models/embedding-001:embedContent", http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprint(w, `{"embedding": {"values": [0.25, 0.25, 0.5]}}`)
	}))
	return &http.Client{Transport: mrt}
}

type testTraceStore struct {
	tracing.Store
	td *tracing.Data
}

func (ts *testTraceStore) Save(ctx context.Context, id string, td *tracing.Data) error {
	ts.td = td
	return nil
}
