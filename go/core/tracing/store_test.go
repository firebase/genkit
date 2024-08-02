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
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	"github.com/google/go-cmp/cmp"
)

func TestTraceJSON(t *testing.T) {
	// We want to compare a JSON trace produced by the genkit javascript code,
	// in testdata/trace.json, with our own JSON output.
	// If we just compared the text of the file, it would probably fail because
	// the order in which fields of a JSON object are written could differ.
	// We can't just read back in what we wrote; that only proves that our
	// implementation is consistent, not that it matches the js one.
	// So we unmarshal the JSON into a map, and compare the maps.
	// TODO: increase coverage. The stored trace is missing some structs.

	// Unmarshal the js trace into our TraceData.
	jsBytes, err := os.ReadFile(filepath.Join("testdata", "trace.json"))
	if err != nil {
		t.Fatal(err)
	}
	var td Data
	if err := json.Unmarshal(jsBytes, &td); err != nil {
		t.Fatal(err)
	}

	// Marshal that TraceData.
	goBytes, err := json.Marshal(td)
	if err != nil {
		t.Fatal(err)
	}

	// Unmarshal both JSON objects into maps.
	var jsMap, goMap map[string]any
	if err := json.Unmarshal(jsBytes, &jsMap); err != nil {
		t.Fatal(err)
	}
	if err := json.Unmarshal(goBytes, &goMap); err != nil {
		t.Fatal(err)
	}

	// Compare the maps.
	if diff := cmp.Diff(jsMap, goMap); diff != "" {
		t.Errorf("mismatch (-want, +got):\n%s", diff)
	}
}
