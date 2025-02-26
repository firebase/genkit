// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package dotprompt

import (
	"context"
	"encoding/json"
	"log"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/google/go-cmp/cmp"
	"github.com/invopop/jsonschema"
)

type InputOutput struct {
	Text string `json:"text"`
}

func testTool(g *genkit.Genkit, name string) *ai.ToolDef[struct{ Test string }, string] {
	return genkit.DefineTool(g, name, "use when need to execute a test",
		func(ctx *ai.ToolContext, input struct {
			Test string
		}) (string, error) {
			return input.Test, nil
		},
	)
}

var g, _ = genkit.Init(context.Background(), genkit.WithPromptDir("testdata"))

var testModel = genkit.DefineModel(g, "defineoptions", "test", nil, testGenerate)

func TestPrompts(t *testing.T) {
	g, err := genkit.Init(context.Background(), genkit.WithPromptDir("testdata"))
	if err != nil {
		log.Fatal(err)
	}

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
			prompt, err := Open(g, test.name)
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
	t.Run("WithTypesAndModel", func(t *testing.T) {
		dotPrompt, err := Define(
			g,
			"TestTypes",
			"TestTypes",
			WithTools(testTool(g, "testOptionsPatternDefine")),
			WithDefaultConfig(&ai.GenerationCommonConfig{}),
			WithInputType(InputOutput{}),
			WithOutputType(InputOutput{}),
			WithMetadata(map[string]any{"test": "test"}),
			WithDefaultModel(testModel),
		)
		if err != nil {
			t.Fatal(err)
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
		if dotPrompt.Config.DefaultInput == nil {
			t.Error("default input not set")
		}
		if dotPrompt.Config.Metadata == nil {
			t.Error("metadata not set")
		}
		if dotPrompt.Config.Model == nil {
			t.Error("model not set")
		}
		// TODO Inherit from model in genkit
		// if dotPrompt.Config.Model == nil {
		// 	t.Error("model not inherited")
		// }
	})

	t.Run("WithDefaultMap", func(t *testing.T) {
		dotPrompt, err := Define(
			g,
			"TestDefaultMap",
			"TestDefaultMap",
			WithInputType(map[string]any{"test": "test"}),
		)
		if err != nil {
			t.Fatal(err)
		}
		if dotPrompt.Config.InputSchema == nil {
			t.Error("inputschema not set")
		}
		if dotPrompt.Config.DefaultInput == nil {
			t.Error("Input default not set")
		}
		if dotPrompt.Config.DefaultInput["test"] != "test" {
			t.Error("Input default incorrect")
		}
	})

	t.Run("WithDefaultStruct", func(t *testing.T) {
		dotPrompt, err := Define(
			g,
			"TestDefaultStruct",
			"TestDefaultStruct",
			WithInputType(InputOutput{Text: "test"}),
		)
		if err != nil {
			t.Fatal(err)
		}
		if dotPrompt.Config.InputSchema == nil {
			t.Error("inputschema not set")
		}
		if dotPrompt.Config.DefaultInput == nil {
			t.Error("Input default not set")
		}
		if dotPrompt.Config.DefaultInput["text"] != "test" {
			t.Error("Input default incorrect")
		}
	})
}

func TestOutputFormat(t *testing.T) {
	var tests = []struct {
		name   string
		output any
		format ai.OutputFormat
		err    bool
	}{
		{
			name:   "mismatch",
			output: InputOutput{},
			format: ai.OutputFormatText,
			err:    true,
		},
		{
			name:   "json",
			output: InputOutput{},
			format: ai.OutputFormatJSON,
			err:    false,
		},
		{
			name:   "text",
			format: ai.OutputFormatText,
			err:    false,
		},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			var err error

			if test.output == nil {
				_, err = Define(
					g,
					"aModel",
					"aModel",
					WithInputType(InputOutput{Text: "test"}),
					WithOutputFormat(test.format),
				)
			} else {
				_, err = Define(
					g,
					"bModel",
					"bModel",
					WithInputType(InputOutput{Text: "test"}),
					WithOutputType(test.output),
					WithOutputFormat(test.format),
				)
			}
			if err != nil {
				if test.err {
					t.Logf("got expected error %v", err)
					return
				}
				t.Fatal(err)
			}
		})
	}
}

func TestInputFormat(t *testing.T) {
	type hello struct {
		Name string `json:"name"`
	}

	var tests = []struct {
		name         string
		templateText string
		inputType    any
		input        map[string]any
		render       string
	}{
		{
			name:         "noInput",
			templateText: "hello world",
			input:        nil,
			render:       "hello world",
		},
		{
			name:         "structInput",
			templateText: "hello {{name}}",
			inputType:    hello{},
			input:        map[string]any{"name": "world"},
			render:       "hello world",
		},
		{
			name:         "stringInput",
			templateText: "hello {{input}}",
			inputType:    "world",
			input:        map[string]any{"input": "world"},
			render:       "hello world",
		},
		{
			name:         "intInput",
			templateText: "hello {{input}}",
			inputType:    1,
			input:        map[string]any{"input": 1},
			render:       "hello 1",
		},
		{
			name:         "floatInput",
			templateText: "the value of pi is {{input}}",
			inputType:    3.14159,
			input:        map[string]any{"input": 3.14159},
			render:       "the value of pi is 3.14159",
		},
		{
			name:         "mapInput",
			templateText: "hello {{name}}",
			inputType:    map[string]any{"name": "world"},
			input:        map[string]any{"name": "world"},
			render:       "hello world",
		},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			var err error
			var p *Prompt

			if test.inputType != nil {
				p, err = Define(
					g,
					test.name,
					test.templateText,
					WithInputType(test.inputType),
				)
			} else {
				p, err = Define(
					g,
					"inputFormat",
					test.templateText,
				)
			}

			if err != nil {
				t.Fatal(err)
			}

			txt, err := p.RenderText(test.input)
			if err != nil {
				t.Fatal(err)
			}

			if txt != test.render {
				t.Errorf("got %q want %q", txt, test.render)
			}
		})
	}
}

func TestPromptOptions(t *testing.T) {
	var tests = []struct {
		name string
		with PromptOption
	}{
		{
			name: "WithTools",
			with: WithTools(testTool(g, "testPromptOptions")),
		},
		{
			name: "WithDefaultConfig",
			with: WithDefaultConfig(&ai.GenerationCommonConfig{}),
		},
		{
			name: "WithInputType",
			with: WithInputType(InputOutput{}),
		},
		{
			name: "WithOutputType",
			with: WithOutputType(InputOutput{}),
		},
		{
			name: "WithOutputFormat",
			with: WithOutputFormat(ai.OutputFormatJSON),
		},
		{
			name: "WithMetadata",
			with: WithMetadata(map[string]any{"test": "test"}),
		},
		{
			name: "WithDefaultModelName",
			with: WithDefaultModelName("defineoptions/test"),
		},
		{
			name: "WithDefaultModel",
			with: WithDefaultModel(testModel),
		},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			_, err := Define(
				g,
				"TestWith",
				"TestWith",
				test.with,
				test.with,
			)

			if err == nil {
				t.Errorf("%s could be set twice", test.name)
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
