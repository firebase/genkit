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

package dotprompt

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/google/go-cmp/cmp"
	"github.com/invopop/jsonschema"
	"gopkg.in/yaml.v3"
)

// TestPicoschema tests the same cases as picoschema_test.ts.
func TestPicoschema(t *testing.T) {
	type test struct {
		Description string
		YAML        string
		Want        map[string]any
	}

	convertSchema(&jsonschema.Schema{})
	data, err := os.ReadFile(filepath.FromSlash("../../../js/plugins/dotprompt/tests/picoschema_tests.yaml"))
	if err != nil {
		t.Fatal(err)
	}

	var tests []test
	if err := yaml.Unmarshal(data, &tests); err != nil {
		t.Fatal(err)
	}

	skip := map[string]bool{
		"required field":                 true,
		"nested object in array and out": true,
	}

	for _, test := range tests {
		t.Run(test.Description, func(t *testing.T) {
			if skip[test.Description] {
				t.Skip("no support for type as an array")
			}
			var val any
			if err := yaml.Unmarshal([]byte(test.YAML), &val); err != nil {
				t.Fatalf("YAML unmarshal failure: %v", err)
			}

			// The tests, copied from TypeScript, use a schema field.
			val = val.(map[string]any)["schema"]

			schema, err := picoschemaToJSONSchema(val)
			if err != nil {
				t.Fatal(err)
			}
			got, err := convertSchema(schema)
			if err != nil {
				t.Fatal(err)
			}
			want := replaceEmptySchemas(test.Want)
			if diff := cmp.Diff(want, got); diff != "" {
				t.Errorf("mismatch (-want, +got):\n%s", diff)
			}
		})
	}
}

// replaceEmptySchemas replaces empty maps in m, which represent
// empty JSON schemas, with the value true.
// It transforms the expected values taken from the suite of JS test cases
// into a form that matches the JSON marshalling of jsonschema.Schema,
// which marshals empty schemas as "true".
func replaceEmptySchemas(m map[string]any) any {
	if m == nil {
		return nil
	}
	if len(m) == 0 {
		return true
	}
	if p, ok := m["properties"]; ok {
		pm := p.(map[string]any)
		for k, v := range pm {
			if vm, ok := v.(map[string]any); ok && len(vm) == 0 {
				pm[k] = true
			}
		}
	}
	return m
}
