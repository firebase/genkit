// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package tracing

import (
	"slices"
	"strconv"
	"testing"

	"go.opentelemetry.io/otel/attribute"
)

// TODO: add tests that compare tracing data saved to disk with goldens.

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
