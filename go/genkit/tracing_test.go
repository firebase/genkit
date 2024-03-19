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
	"slices"
	"strconv"
	"testing"

	"go.opentelemetry.io/otel/attribute"
)

// TODO(jba): add tests that compare tracing data saved to disk with goldens.

func TestSpanMetadata(t *testing.T) {
	const testInput = 17
	sm := &spanMetadata{
		Name:  "name",
		State: SpanStateSuccess,
		Path:  "parent/name",
		Input: testInput,
	}
	sm.SetAttr("key", "value")

	got := sm.attributes()
	want := []attribute.KeyValue{
		attribute.String("genkit:state", "success"),
		attribute.String("genkit:input", strconv.Itoa(testInput)),
		attribute.String("genkit:metadata:key", "value"),
	}
	if !slices.Equal(got, want) {
		t.Errorf("\ngot  %v\nwant %v", got, want)
	}

}
