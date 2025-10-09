// Copyright 2025 Google LLC
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
//
// SPDX-License-Identifier: Apache-2.0

package base

import (
	"reflect"
	"testing"
)

func TestNormalizeInput(t *testing.T) {
	tests := []struct {
		name     string
		data     any
		schema   map[string]any
		expected any
	}{
		{
			name: "removes null fields from object",
			data: map[string]any{
				"name":        "test",
				"nullField":   nil,
				"emptyString": "",
				"number":      42.0,
			},
			schema: map[string]any{
				"type": "object",
				"properties": map[string]any{
					"name":        map[string]any{"type": "string"},
					"nullField":   map[string]any{"type": "string"},
					"emptyString": map[string]any{"type": "string"},
					"number":      map[string]any{"type": "integer"},
				},
			},
			expected: map[string]any{
				"name":        "test",
				"emptyString": "",
				"number":      int64(42),
			},
		},
		{
			name: "removes null fields without schema",
			data: map[string]any{
				"name":      "test",
				"nullField": nil,
				"value":     123,
			},
			schema: nil,
			expected: map[string]any{
				"name":  "test",
				"value": 123,
			},
		},
		{
			name: "handles nested objects with null fields",
			data: map[string]any{
				"outer": map[string]any{
					"inner":     "value",
					"nullInner": nil,
				},
				"nullOuter": nil,
			},
			schema: map[string]any{
				"type": "object",
				"properties": map[string]any{
					"outer": map[string]any{
						"type": "object",
						"properties": map[string]any{
							"inner":     map[string]any{"type": "string"},
							"nullInner": map[string]any{"type": "string"},
						},
					},
					"nullOuter": map[string]any{"type": "string"},
				},
			},
			expected: map[string]any{
				"outer": map[string]any{
					"inner": "value",
				},
			},
		},
		{
			name: "converts numbers correctly",
			data: map[string]any{
				"intField":   42.0,
				"floatField": 3.14,
			},
			schema: map[string]any{
				"type": "object",
				"properties": map[string]any{
					"intField":   map[string]any{"type": "integer"},
					"floatField": map[string]any{"type": "number"},
				},
			},
			expected: map[string]any{
				"intField":   int64(42),
				"floatField": 3.14,
			},
		},
		{
			name: "handles arrays with null elements",
			data: []any{"item1", nil, "item2"},
			schema: map[string]any{
				"type": "array",
				"items": map[string]any{
					"type": "string",
				},
			},
			expected: []any{"item1", nil, "item2"}, // Arrays preserve null elements
		},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			result, err := NormalizeInput(test.data, test.schema)
			if err != nil {
				t.Fatalf("NormalizeInput returned error: %v", err)
			}

			if !reflect.DeepEqual(result, test.expected) {
				t.Errorf("NormalizeInput result mismatch:\nExpected: %+v\nGot: %+v", test.expected, result)
			}
		})
	}
}
