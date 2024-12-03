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
	"context"
	"encoding/json"
	"testing"

	"github.com/firebase/genkit/go/ai"
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
 ],
 "additionalProperties": false
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
    ],
    "additionalProperties": false
   },
   "type": "array"
  }
 },
 "additionalProperties": false,
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

			if prompt.ModelName != test.model {
				t.Errorf("got model %q want %q", prompt.ModelName, test.model)
			}
			if diff := cmpSchema(t, prompt.InputSchema, test.input); diff != "" {
				t.Errorf("input schema mismatch (-want, +got):\n%s", diff)
			}

			if test.output == "" {
				if prompt.OutputSchema != nil {
					t.Errorf("unexpected output schema: %v", prompt.OutputSchema)
				}
			} else {
				if diff := cmpSchema(t, prompt.OutputSchema, test.output); diff != "" {
					t.Errorf("input schema mismatch (-want, +got):\n%s", diff)
				}
			}
		})
	}
}

func TestOptionsPatternDefine(t *testing.T) {
	testTool := ai.DefineTool("optionstest", "use when need to execute a test",
		func(ctx context.Context, input struct {
			Test string
		}) (string, error) {
			return input.Test, nil
		},
	)

	type InputOutput struct {
		Test string `json:"test"`
	}

	dotPrompt, err := Define(
		"TestExecute",
		"TestExecute",
		WithVariant("variant"),
		WithTools(testTool),
		WithGenerationConfig(&ai.GenerationCommonConfig{}),
		WithInputType(InputOutput{}),
		WithOutputType(InputOutput{}),
		WithOutputFormat(ai.OutputFormatText),
		WithDefaults(map[string]any{"test": "test"}),
		WithMetaData(map[string]any{"test": "test"}),
	)
	if err != nil {
		t.Fatal(err)
	}

	if dotPrompt.Config.Variant == "" {
		t.Error("variant not set")
	}
	if dotPrompt.Tools == nil {
		t.Error("tools not set")
	}
	if dotPrompt.Config.GenerationConfig == nil {
		t.Error("generationConfig not set")
	}
	if dotPrompt.Config.InputSchema == nil {
		t.Error("inputschema not set")
	}
	if dotPrompt.Config.OutputSchema == nil {
		t.Error("outputschema not set")
	}
	if dotPrompt.Config.OutputFormat == "" {
		t.Error("outputschema not set")
	}
	if dotPrompt.Config.VariableDefaults == nil {
		t.Error("defaults not set")
	}
	if dotPrompt.Config.Metadata == nil {
		t.Error("metadata not set")
	}
	// TODO Inherit from model in genkit
	// if dotPrompt.Config.Model == nil {
	// 	t.Error("model not inherited")
	// }
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

	jsonGot, err := convertSchema(got)
	if err != nil {
		t.Fatal(err)
	}
	var jsonWant any
	if err := json.Unmarshal([]byte(want), &jsonWant); err != nil {
		t.Fatalf("unmarshaling %q failed: %v", want, err)
	}
	return cmp.Diff(jsonWant, jsonGot)
}

// convertSchema marshals s to JSON, then unmarshals the result.
func convertSchema(s *jsonschema.Schema) (any, error) {
	// JSON sorts maps but not slices.
	// jsonschema slices are not sorted consistently.
	sortSchemaSlices(s)
	data, err := json.Marshal(s)
	if err != nil {
		return nil, err
	}
	var a any
	if err := json.Unmarshal(data, &a); err != nil {
		return nil, err
	}
	return a, nil
}
