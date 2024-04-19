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
	"testing"

	"github.com/google/go-cmp/cmp"
	"github.com/invopop/jsonschema"
)

func TestPrompts(t *testing.T) {
	SetDirectory("testdata")

	var tests = []struct {
		name   string
		model  string
		input  string
		output string
	}{
		{
			name:  "recipe",
			model: "googleai/gemini-pro",
			input: `{
 "properties": {
  "food": {
   "type": "string"
  }
 },
 "type": "object",
 "required": [
  "food"
 ]
}`,
			output: `{
 "properties": {
  "steps": {
   "items": {
    "type": "string"
   },
   "type": "array",
   "description": "the steps required to complete the recipe"
  },
  "title": {
   "type": "string",
   "description": "recipe title"
  },
  "ingredients": {
   "items": {
    "properties": {
     "name": {
      "type": "string"
     },
     "quantity": {
      "type": "string"
     }
    },
    "type": "object",
    "required": [
     "name",
     "quantity"
    ]
   },
   "type": "array"
  }
 },
 "type": "object",
 "required": [
  "ingredients",
  "steps",
  "title"
 ]
}`,
		},
		{
			name:  "story",
			model: "googleai/gemini-pro",
			input: `{
 "properties": {
  "subject": {
   "type": "string"
  }
 },
 "required": [
  "subject"
 ],
 "type": "object"
}`,
			output: "",
		},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			prompt, err := Open(test.name)
			if err != nil {
				t.Fatal(err)
			}

			if prompt.Frontmatter.Model != test.model {
				t.Errorf("got model %q want %q", prompt.Frontmatter.Model, test.model)
			}
			if diff := cmpSchema(t, prompt.Frontmatter.Input.Schema, test.input); diff != "" {
				t.Errorf("input schema mismatch (-want, +got):\n%s", diff)
			}

			if test.output == "" {
				if prompt.Frontmatter.Output != nil && prompt.Frontmatter.Output.Schema != nil {
					t.Errorf("unexpected output schema: %v", prompt.Frontmatter.Output.Schema)
				}
			} else {
				var output map[string]any
				if err := json.Unmarshal([]byte(test.output), &output); err != nil {
					t.Fatalf("JSON unmarshal of %q failed: %v", test.output, err)
				}
				if diff := cmp.Diff(output, prompt.Frontmatter.Output.Schema); diff != "" {
					t.Errorf("output schema mismatch (-want, +got):\n%s", diff)
				}
			}
		})
	}
}

// cmpSchema compares schema values, returning the output of cmp.Diff.
// There doesn't seem to be a good way to compare jsonschema.Schema values.
// They have unexported fields and fields of type orderedmap.OrderedMap.
// They don't marshal to JSON consistently.
// So we marshal to JSON, unmarshal to any, and compare to our
// expected JSON also unmarshaled.
func cmpSchema(t *testing.T, got *jsonschema.Schema, want string) string {
	t.Helper()

	if want == "" {
		if got != nil {
			return "got unexpected schema"
		}
		return ""
	}

	// JSON sorts maps but not slices.
	// jsonschema slices are not sorted consistently.
	sortSchemaSlices(got)

	data, err := json.Marshal(got)
	if err != nil {
		t.Fatal(err)
	}
	var jsonGot, jsonWant any
	if err := json.Unmarshal(data, &jsonGot); err != nil {
		t.Fatal(err)
	}
	if err := json.Unmarshal([]byte(want), &jsonWant); err != nil {
		t.Fatalf("unmarshaling %q failed: %v", want, err)
	}
	return cmp.Diff(jsonWant, jsonGot)
}
