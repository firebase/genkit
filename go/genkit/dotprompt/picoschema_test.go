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
	"testing"

	"gopkg.in/yaml.v3"
)

// TestPicoschema tests the same cases as picoschema_test.ts.
func TestPicoschema(t *testing.T) {
	tests := []struct {
		description string
		yaml        string
		want        string
	}{
		{
			description: "simple scalar, no description",
			yaml:        `schema: string`,
			want:        `{ "type": "string" }`,
		},
		{
			description: "simple scalar, with description",
			yaml:        `schema: number, the description`,
			want:        `{ "type": "number", "description": "the description" }`,
		},
		{
			description: "simple scalar, with description (no whitespace)",
			yaml:        `schema: number,the description`,
			want:        `{ "type": "number", "description": "the description" }`,
		},
		{
			description: "simple scalar, with description (comma in description)",
			yaml:        `schema: number,the description, which has, multiple commas`,
			want: `{
			        "type": "number",
			        "description": "the description, which has, multiple commas"
			}`,
		},
		{
			description: "simple scalar, with description (extra whitespace)",
			yaml:        `schema: number,    the description`,
			want:        `{ "type": "number", "description": "the description" }`,
		},
		{
			description: "simple object",
			yaml: `schema:
  field1: boolean
  field2: string`,
			want: `{
			        "type": "object",
			        "properties": {
			          "field1": { "type": "boolean" },
			          "field2": { "type": "string" }
			        },
			        "required": ["field1", "field2"]
			}`,
		},
		{
			description: "required field",
			yaml: `schema:
  req: string, required field
  nonreq?: boolean, optional field`,
			want: `{
			        "type": "object",
			        "properties": {
			          "req": { "type": "string", "description": "required field" },
			          "nonreq": { "type": "boolean", "description": "optional field" }
			        },
			        "required": ["req"]
			}`,
		},
		{
			description: "array of scalars, with and without description",
			yaml: `schema:
  tags(array, list of tags): string, the tag
  vector(array): number`,
			want: `{
			        "type": "object",
			        "properties": {
			          "tags": {
			            "type": "array",
			            "description": "list of tags",
			            "items": { "type": "string", "description": "the tag" }
			          },
			          "vector": { "type": "array", "items": { "type": "number" } }
			        },
			        "required": ["tags", "vector"]
			}`,
		},
		{
			description: "nested object in array and out",
			yaml: `schema:
  obj?(object, a nested object):
    nest1?: string
  arr(array, array of objects):
    nest2?: boolean`,
			want: `{
			        "type": "object",
			        "properties": {
			          "obj": {
			            "type": "object",
			            "description": "a nested object",
			            "properties": { "nest1": { "type": "string" } }
			          },
			          "arr": {
			            "type": "array",
			            "description": "array of objects",
			            "items": {
			              "type": "object",
			              "properties": { "nest2": { "type": "boolean" } }
			            }
			          }
			        },
			        "required": ["arr"]
			}`,
		},
		{
			description: "simple json schema type",
			yaml: `schema:
  type: string`,
			want: `{ "type": "string" }`,
		},
		{
			description: "simple json schema type",
			yaml: `schema:
  type: string`,
			want: `{ "type": "string" }`,
		},
		{
			description: "inferred json schema from properties",
			yaml: `schema:
  properties:
    foo: {type: string}`,
			want: `{ "type": "object", "properties": { "foo": { "type": "string" } } }`,
		},
	}

	for _, test := range tests {
		var val any
		if err := yaml.Unmarshal([]byte(test.yaml), &val); err != nil {
			t.Errorf("%s YAML unmarshal failure: %v", test.description, err)
			continue
		}

		// The tests, copied from TypeScript, use a schema field.
		val = val.(map[string]any)["schema"]

		schema, err := picoschemaToJSONSchema(val)
		if err != nil {
			t.Errorf("%s: %v", test.description, err)
			continue
		}

		if diff := cmpSchema(t, schema, test.want); diff != "" {
			t.Errorf("%s: mismatch (-want, +got):\n%s", test.description, diff)
		}
	}
}
