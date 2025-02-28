// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package dotprompt

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/google/go-cmp/cmp"
	"gopkg.in/yaml.v3"
)

// TestPicoschema tests the same cases as picoschema_test.ts.
// Temporarily disabled, see https://github.com/firebase/genkit/pull/1741.
func disableTestPicoschema(t *testing.T) {
	type test struct {
		Description string
		YAML        string
		Want        map[string]any
	}

	// TODO(https://github.com/firebase/genkit/issues/1741): This file has been removed #1651
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
