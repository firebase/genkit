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
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/google/go-cmp/cmp"
	"gopkg.in/yaml.v3"
)

// TestPicoschema tests the same cases as picoschema_test.ts.
func TestPicoschema(t *testing.T) {
	type test struct {
		Description string
		YAML        string
		Want        map[string]any
	}

	data, err := os.ReadFile(filepath.FromSlash("../../../js/plugins/dotprompt/tests/picoschema_tests.yaml"))
	if err != nil {
		t.Fatal(err)
	}

	var tests []test
	if err := yaml.Unmarshal(data, &tests); err != nil {
		t.Fatal(err)
	}

	for _, test := range tests {
		t.Run(test.Description, func(t *testing.T) {
			var val any
			if err := yaml.Unmarshal([]byte(test.YAML), &val); err != nil {
				t.Fatalf("YAML unmarshal failure: %v", err)
			}

			// The tests use a schema field.
			val = val.(map[string]any)["schema"]

			schema, err := picoschemaToJSONSchema(val)
			if err != nil {
				t.Fatal(err)
			}
			got, err := convertSchema(schema)
			if err != nil {
				t.Fatal(err)
			}
			gotData, err := json.Marshal(got)
			if err != nil {
				t.Fatal(err)
			}
			var gotMap map[string]any
			if err := json.Unmarshal(gotData, &gotMap); err != nil {
				t.Fatal(err)
			}
			replaceAnyOfWithTypeArray(gotMap)
			want := replaceEmptySchemas(test.Want)
			if diff := cmp.Diff(want, gotMap); diff != "" {
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

func replaceAnyOfWithTypeArray(schema map[string]any) {
	// Check if 'anyOf' is present
	if anyOf, ok := schema["anyOf"].([]any); ok && len(anyOf) > 0 {
		types := []any{}
		descriptions := []string{}
		otherKeysExist := false

		for _, item := range anyOf {
			if subSchema, ok := item.(map[string]any); ok {
				// Collect 'type' and 'description' from sub-schemas
				if t, hasType := subSchema["type"]; hasType {
					types = append(types, t)
				} else {
					otherKeysExist = true
					break
				}
				if desc, hasDesc := subSchema["description"]; hasDesc {
					descriptions = append(descriptions, desc.(string))
				}
			} else {
				otherKeysExist = true
				break
			}
		}

		// Replace 'anyOf' with 'type' array if no other keys exist
		if !otherKeysExist && len(types) > 0 {
			schema["type"] = types
			delete(schema, "anyOf")
			// Combine descriptions if necessary
			if len(descriptions) > 0 && schema["description"] == nil {
				schema["description"] = strings.Join(descriptions, "; ")
			}
		}
	}

	// Recursively process nested schemas
	for _, value := range schema {
		switch v := value.(type) {
		case map[string]any:
			replaceAnyOfWithTypeArray(v)
		case []any:
			for _, item := range v {
				if m, ok := item.(map[string]any); ok {
					replaceAnyOfWithTypeArray(m)
				}
			}
		}
	}
}