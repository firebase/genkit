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
	"slices"
	"strconv"
	"testing"

	"go.opentelemetry.io/otel/attribute"
)

// TODO(jba): add tests that compare tracing data saved to disk with goldens.

func TestSpanMetadata(t *testing.T) {
	const (
		testInput  = 17
		testOutput = 18
	)
	sm := &spanMetadata{
		Name:   "name",
		State:  spanStateSuccess,
		Path:   "parent/name",
		Input:  testInput,
		Output: testOutput,
	}
	sm.SetAttr("key", "value")

	got := sm.attributes()
	want := []attribute.KeyValue{
		attribute.String("genkit:name", "name"),
		attribute.String("genkit:state", "success"),
		attribute.String("genkit:input", strconv.Itoa(testInput)),
		attribute.String("genkit:path", "parent/name"),
		attribute.String("genkit:output", strconv.Itoa(testOutput)),
		attribute.String("genkit:metadata:key", "value"),
	}
	if !slices.Equal(got, want) {
		t.Errorf("\ngot  %v\nwant %v", got, want)
	}
}

func TestTracing(t *testing.T) {
	ctx := context.Background()
	const actionName = "TestTracing-inc"
	a := NewAction(actionName, nil, inc)
	if _, err := a.Run(context.Background(), 3, nil); err != nil {
		t.Fatal(err)
	}
	// The dev TraceStore is registered by Init, called from TestMain.
	ts := globalRegistry.lookupTraceStore(EnvironmentDev)
	tds, _, err := ts.List(ctx, nil)
	if err != nil {
		t.Fatal(err)
	}
	// The same trace store is used for all tests, so there might be several traces.
	// Look for this one, which has a unique name.
	for _, td := range tds {
		if td.DisplayName == actionName {
			// Spot check: expect a single span.
			if g, w := len(td.Spans), 1; g != w {
				t.Errorf("got %d spans, want %d", g, w)
			}
			return
		}
	}
	t.Fatalf("did not find trace named %q", actionName)
}
