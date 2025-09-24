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

package ai

import (
	"context"
	"testing"

	"github.com/firebase/genkit/go/internal/base"
	"github.com/google/go-cmp/cmp"
)

func TestConstrainedGenerate(t *testing.T) {
	JSON := "\n{\"foo\": \"bar\"}\n"
	JSONmd := "```json" + JSON + "```"

	modelOpts := ModelOptions{
		Label: modelName,
		Supports: &ModelSupports{
			Multiturn:   true,
			Tools:       true,
			SystemRole:  true,
			Media:       false,
			Constrained: ConstrainedSupportAll,
		},
		Versions: []string{"echo-001", "echo-002"},
	}

	formatModel := DefineModel(r, "test/format", &modelOpts, func(ctx context.Context, gr *ModelRequest, msc ModelStreamCallback) (*ModelResponse, error) {
		if msc != nil {
			msc(ctx, &ModelResponseChunk{
				Content: []*Part{NewTextPart("stream!")},
			})
		}

		return &ModelResponse{
			Request: gr,
			Message: NewModelTextMessage(JSONmd),
		}, nil
	})

	t.Run("doesn't inject instructions when model supports native contrained generation", func(t *testing.T) {
		wantText := JSON
		wantStreamText := "stream!"
		wantRequest := &ModelRequest{
			Messages: []*Message{
				{
					Role: RoleUser,
					Content: []*Part{
						NewTextPart("generate json"),
					},
				},
			},
			Output: &ModelOutputConfig{
				Format: OutputFormatJSON,
				Schema: map[string]any{
					"additionalProperties": bool(false),
					"properties": map[string]any{
						"foo": map[string]any{"type": string("string")},
					},
					"required": []any{string("foo")},
					"type":     string("object"),
				},
				Constrained: true,
				ContentType: "application/json",
			},
			Config: &GenerationCommonConfig{Temperature: 1},
			Tools:  []*ToolDefinition{},
		}

		streamText := ""
		res, err := Generate(context.Background(), r,
			WithModel(formatModel),
			WithPrompt("generate json"),
			WithConfig(&GenerationCommonConfig{
				Temperature: 1,
			}),
			WithStreaming(func(ctx context.Context, grc *ModelResponseChunk) error {
				streamText += grc.Text()
				return nil
			}),
			WithOutputType(struct {
				Foo string `json:"foo"`
			}{}),
		)
		if err != nil {
			t.Fatal(err)
		}

		gotText := res.Text()
		if diff := cmp.Diff(gotText, wantText); diff != "" {
			t.Errorf("Text() diff (+got -want):\n%s", diff)
		}
		if diff := cmp.Diff(streamText, wantStreamText); diff != "" {
			t.Errorf("Text() diff (+got -want):\n%s", diff)
		}
		if diff := cmp.Diff(res.Request, wantRequest); diff != "" {
			t.Errorf("Request diff (+got -want):\n%s", diff)
		}
	})

	t.Run("doesn't use format instructions when explicitly instructed not to", func(t *testing.T) {
		wantText := JSON
		wantStreamText := "stream!"
		wantRequest := &ModelRequest{
			Messages: []*Message{
				{
					Role: RoleUser,
					Content: []*Part{
						NewTextPart("generate json"),
					},
				},
			},
			Output: &ModelOutputConfig{
				Format:      OutputFormatJSON,
				ContentType: "application/json",
			},
			Config: &GenerationCommonConfig{Temperature: 1},
			Tools:  []*ToolDefinition{},
		}

		streamText := ""
		res, err := Generate(context.Background(), r,
			WithModel(formatModel),
			WithPrompt("generate json"),
			WithConfig(&GenerationCommonConfig{
				Temperature: 1,
			}),
			WithStreaming(func(ctx context.Context, grc *ModelResponseChunk) error {
				streamText += grc.Text()
				return nil
			}),
			WithOutputType(struct {
				Foo string `json:"foo"`
			}{}),
			WithOutputInstructions(""),
		)
		if err != nil {
			t.Fatal(err)
		}

		gotText := res.Text()
		if diff := cmp.Diff(gotText, wantText); diff != "" {
			t.Errorf("Text() diff (+got -want):\n%s", diff)
		}
		if diff := cmp.Diff(streamText, wantStreamText); diff != "" {
			t.Errorf("Text() diff (+got -want):\n%s", diff)
		}
		if diff := cmp.Diff(res.Request, wantRequest); diff != "" {
			t.Errorf("Request diff (+got -want):\n%s", diff)
		}
	})

	t.Run("uses format instructions given by user", func(t *testing.T) {
		customInstructions := "The generated output should be in JSON format and conform to the following schema:\n\n```{\"additionalProperties\":false,\"properties\":{\"foo\":{\"type\":\"string\"}},\"required\":[\"foo\"],\"type\":\"object\"}```"
		wantText := JSON
		wantStreamText := "stream!"
		wantRequest := &ModelRequest{
			Messages: []*Message{
				{
					Role: RoleUser,
					Content: []*Part{
						NewTextPart("generate json"),
						{
							Kind:        PartText,
							ContentType: "plain/text",
							Text:        customInstructions,
							Metadata:    map[string]any{"purpose": "output"},
						},
					},
				},
			},
			Output: &ModelOutputConfig{
				Format:      OutputFormatJSON,
				ContentType: "application/json",
			},
			Config: &GenerationCommonConfig{Temperature: 1},
			Tools:  []*ToolDefinition{},
		}

		streamText := ""
		res, err := Generate(context.Background(), r,
			WithModel(formatModel),
			WithPrompt("generate json"),
			WithConfig(&GenerationCommonConfig{
				Temperature: 1,
			}),
			WithStreaming(func(ctx context.Context, grc *ModelResponseChunk) error {
				streamText += grc.Text()
				return nil
			}),
			WithOutputType(struct {
				Foo string `json:"foo"`
			}{}),
			WithOutputInstructions(customInstructions),
		)
		if err != nil {
			t.Fatal(err)
		}

		gotText := res.Text()
		if diff := cmp.Diff(gotText, wantText); diff != "" {
			t.Errorf("Text() diff (+got -want):\n%s", diff)
		}
		if diff := cmp.Diff(streamText, wantStreamText); diff != "" {
			t.Errorf("Text() diff (+got -want):\n%s", diff)
		}
		if diff := cmp.Diff(res.Request, wantRequest); diff != "" {
			t.Errorf("Request diff (+got -want):\n%s", diff)
		}
	})

	t.Run("uses simulated constrained generation when explicitly told to do so", func(t *testing.T) {
		wantText := JSON
		wantStreamText := "stream!"
		wantRequest := &ModelRequest{
			Messages: []*Message{
				{
					Role: RoleUser,
					Content: []*Part{
						NewTextPart("generate json"),
						{
							Kind:        PartText,
							ContentType: "plain/text",
							Text:        "Output should be in JSON format and conform to the following schema:\n\n```{\"additionalProperties\":false,\"properties\":{\"foo\":{\"type\":\"string\"}},\"required\":[\"foo\"],\"type\":\"object\"}```",
							Metadata:    map[string]any{"purpose": "output"},
						},
					},
				},
			},
			Output: &ModelOutputConfig{
				Format:      OutputFormatJSON,
				ContentType: "application/json",
			},
			Config: &GenerationCommonConfig{Temperature: 1},
			Tools:  []*ToolDefinition{},
		}

		streamText := ""
		res, err := Generate(context.Background(), r,
			WithModel(formatModel),
			WithPrompt("generate json"),
			WithConfig(&GenerationCommonConfig{
				Temperature: 1,
			}),
			WithStreaming(func(ctx context.Context, grc *ModelResponseChunk) error {
				streamText += grc.Text()
				return nil
			}),
			WithOutputType(struct {
				Foo string `json:"foo"`
			}{}),
			WithCustomConstrainedOutput(),
		)
		if err != nil {
			t.Fatal(err)
		}

		gotText := res.Text()
		if diff := cmp.Diff(gotText, wantText); diff != "" {
			t.Errorf("Text() diff (+got -want):\n%s", diff)
		}
		if diff := cmp.Diff(streamText, wantStreamText); diff != "" {
			t.Errorf("Text() diff (+got -want):\n%s", diff)
		}
		if diff := cmp.Diff(res.Request, wantRequest); diff != "" {
			t.Errorf("Request diff (+got -want):\n%s", diff)
		}
	})

	t.Run("works with prompts", func(t *testing.T) {
		wantText := JSON
		wantRequest := &ModelRequest{
			Messages: []*Message{
				{
					Role: RoleUser,
					Content: []*Part{
						NewTextPart("generate json"),
						{
							Kind:        PartText,
							ContentType: "plain/text",
							Text:        "Output should be in JSON format and conform to the following schema:\n\n```{\"additionalProperties\":false,\"properties\":{\"foo\":{\"type\":\"string\"}},\"required\":[\"foo\"],\"type\":\"object\"}```",
							Metadata:    map[string]any{"purpose": "output"},
						},
					},
				},
			},
			Output: &ModelOutputConfig{
				Format:      OutputFormatJSON,
				ContentType: "application/json",
			},
			Config: &GenerationCommonConfig{Temperature: 1},
			Tools:  []*ToolDefinition{},
		}

		p := DefinePrompt(r, "formatPrompt",
			WithPrompt("generate json"),
			WithModel(formatModel),
			WithOutputType(struct {
				Foo string `json:"foo"`
			}{}),
			WithCustomConstrainedOutput(),
		)

		res, err := p.Execute(
			context.Background(),
			WithConfig(&GenerationCommonConfig{Temperature: 1}),
		)
		if err != nil {
			t.Fatal(err)
		}

		gotText := res.Text()
		if diff := cmp.Diff(gotText, wantText); diff != "" {
			t.Errorf("Text() diff (+got -want):\n%s", diff)
		}
		if diff := cmp.Diff(res.Request, wantRequest); diff != "" {
			t.Errorf("Request diff (+got -want):\n%s", diff)
		}
	})
}

func TestHandlers(t *testing.T) {
	type TestEnum struct {
		FavColor string `json:"fav_color,omitempty" jsonschema:"enum=red,enum=green,enum=blue"`
	}

	enumSchema := base.SchemaAsMap(base.InferJSONSchema(TestEnum{}))

	tests := []struct {
		name         string
		format       string
		schema       map[string]any
		output       ModelOutputConfig
		instructions string
		wantErr      bool
	}{
		{
			name:   "not existing format",
			format: "foobar",
			schema: map[string]any{
				"type": "object",
				"properties": map[string]any{
					"name": map[string]any{"type": "string"},
					"age":  map[string]any{"type": "integer"},
				},
				"additionalProperties": false,
			},
			wantErr: true,
		},
		{
			name:   "text handler",
			format: "text",
			schema: nil,
			output: ModelOutputConfig{
				ContentType: "text/plain",
			},
			instructions: "",
			wantErr:      false,
		},
		{
			name:   "json handler",
			format: "json",
			schema: map[string]any{
				"type": "object",
				"properties": map[string]any{
					"name": map[string]any{"type": "string"},
					"age":  map[string]any{"type": "integer"},
				},
				"additionalProperties": false,
			},
			output: ModelOutputConfig{
				Format: "json",
				Schema: map[string]any{
					"type": "object",
					"properties": map[string]any{
						"name": map[string]any{"type": "string"},
						"age":  map[string]any{"type": "integer"},
					},
					"additionalProperties": false,
				},
				ContentType: "application/json",
			},
			instructions: "Output should be in JSON format and conform to the following schema:\n\n```{\"additionalProperties\":false,\"properties\":{\"age\":{\"type\":\"integer\"},\"name\":{\"type\":\"string\"}},\"type\":\"object\"}```",
			wantErr:      false,
		},
		{
			name:   "jsonl handler",
			format: OutputFormatJSONL,
			schema: map[string]any{
				"type": "array",
				"items": map[string]any{
					"type": "object",
					"properties": map[string]any{
						"name": map[string]any{"type": "string"},
						"age":  map[string]any{"type": "integer"},
					},
				},
				"additionalProperties": false,
			},
			output: ModelOutputConfig{
				Format: OutputFormatJSONL,
				Schema: map[string]any{
					"type": "array",
					"items": map[string]any{
						"type": "object",
						"properties": map[string]any{
							"name": map[string]any{"type": "string"},
							"age":  map[string]any{"type": "integer"},
						},
					},
					"additionalProperties": false,
				},
				ContentType: "application/jsonl",
			},
			instructions: "Output should be JSONL format, a sequence of JSON objects (one per line) separated by a newline '\\n' character. Each line should be a JSON object conforming to the following schema:\n\n```{\"properties\":{\"age\":{\"type\":\"integer\"},\"name\":{\"type\":\"string\"}},\"type\":\"object\"}```",
			wantErr:      false,
		},
		{
			name:   "array handler",
			format: "array",
			schema: map[string]any{
				"type": "array",
				"items": map[string]any{
					"type": "object",
					"properties": map[string]any{
						"id":   map[string]any{"type": "integer"},
						"name": map[string]any{"type": "string"},
					},
				},
				"additionalProperties": false,
			},
			output: ModelOutputConfig{
				Format: OutputFormatArray,
				Schema: map[string]any{
					"type": "array",
					"items": map[string]any{
						"type": "object",
						"properties": map[string]any{
							"id":   map[string]any{"type": "integer"},
							"name": map[string]any{"type": "string"},
						},
					},
					"additionalProperties": false,
				},
				Constrained: false,
				ContentType: "application/json",
			},
			instructions: "Output should be a JSON array conforming to the following schema:\n\n```{\"properties\":{\"id\":{\"type\":\"integer\"},\"name\":{\"type\":\"string\"}},\"type\":\"object\"}```",
			wantErr:      false,
		},
		{
			name:   "enum handler",
			format: "enum",
			schema: enumSchema,
			output: ModelOutputConfig{
				Format:      OutputFormatEnum,
				Schema:      enumSchema,
				Constrained: false,
				ContentType: "text/enum",
			},
			instructions: "Output should be ONLY one of the following enum values. Do not output any additional information or add quotes.\n\n```red\ngreen\nblue```",
			wantErr:      false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			format, err := resolveFormat(r, tt.schema, tt.format)
			if (err != nil) != tt.wantErr {
				t.Errorf("resolveFormat() error = %v, wantErr %v", err, tt.wantErr)
				if err != nil {
					t.Logf("Error message: %v", err)
				}
			}

			if !tt.wantErr {
				handler, err := format.Handler(tt.schema)
				if err != nil {
					t.Fatalf("Handler() error = %v", err)
				}
				instructions := handler.Instructions()
				config := handler.Config()

				if diff := cmp.Diff(tt.instructions, instructions); diff != "" {
					t.Errorf("Instructions diff (+got -want):\n%s", diff)
				}
				if diff := cmp.Diff(tt.output, config); diff != "" {
					t.Errorf("config diff (+got -want):\n%s", diff)
				}
			}
		})
	}
}

func TestJsonParser(t *testing.T) {
	tests := []struct {
		name     string
		schema   map[string]any
		response *Message
		want     *Message
		wantErr  bool
	}{
		{
			name: "parses json schema",
			schema: map[string]any{
				"type": "object",
				"properties": map[string]any{
					"name": map[string]any{"type": "string"},
					"age":  map[string]any{"type": "integer"},
				},
				"additionalProperties": false,
			},
			response: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewTextPart(JSONMarkdown(`{"name": "John", "age": 19}`)),
				},
			},
			want: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewJSONPart("\n{\"name\": \"John\", \"age\": 19}\n"),
				},
			},
			wantErr: false,
		},
		{
			name: "contains unexpected field fails",
			schema: map[string]any{
				"type": "object",
				"properties": map[string]any{
					"name": map[string]any{"type": "string"},
					"age":  map[string]any{"type": "integer"},
				},
				"additionalProperties": false,
			},
			response: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewTextPart(JSONMarkdown(`{"name": "John", "height": 190}`)),
				},
			},
			wantErr: true,
		},
		{
			name: "parses JSON with preamble and code fence",
			schema: map[string]any{
				"type": "object",
				"properties": map[string]any{
					"id": map[string]any{"type": "integer"},
				},
				"additionalProperties": false,
			},
			response: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewTextPart("Here is the JSON:\n\n```json\n{\"id\": 1}\n```"),
				},
			},
			want: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewJSONPart("\n{\"id\": 1}\n"),
				},
			},
			wantErr: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			formatter := jsonFormatter{}
			handler, err := formatter.Handler(tt.schema)
			if err != nil {
				t.Fatalf("Handler() error = %v", err)
			}
			message, err := handler.ParseMessage(tt.response)

			if (err != nil) != tt.wantErr {
				t.Errorf("ParseMessage() error = %v, wantErr %v", err, tt.wantErr)
				if err != nil {
					t.Logf("Error message: %v", err)
				}
			}

			if !tt.wantErr {
				if diff := cmp.Diff(tt.want, message); diff != "" {
					t.Errorf("Request msgs diff (+got -want):\n%s", diff)
				}
			}
		})
	}
}

func TestTextParser(t *testing.T) {
	tests := []struct {
		name     string
		response *Message
		want     *Message
		wantErr  bool
	}{
		{
			name: "parses complete text response",
			response: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewTextPart("Hello World"),
				},
			},
			want: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewTextPart("Hello World"),
				},
			},
			wantErr: false,
		},
		{
			name: "handles empty response",
			response: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewTextPart(""),
				},
			},
			want: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewTextPart(""),
				},
			},
			wantErr: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			formatter := textFormatter{}
			handler, err := formatter.Handler(nil)
			if err != nil {
				t.Fatalf("Handler() error = %v", err)
			}
			message, err := handler.ParseMessage(tt.response)

			if (err != nil) != tt.wantErr {
				t.Errorf("ParseMessage() error = %v, wantErr %v", err, tt.wantErr)
				if err != nil {
					t.Logf("Error message: %v", err)
				}
			}

			if !tt.wantErr {
				if diff := cmp.Diff(tt.want, message); diff != "" {
					t.Errorf("Request msgs diff (+got -want):\n%s", diff)
				}
			}
		})
	}
}

func TestJsonlParser(t *testing.T) {
	tests := []struct {
		name     string
		schema   map[string]any
		response *Message
		want     *Message
		wantErr  bool
	}{
		{
			name: "parses jsonl schema",
			schema: map[string]any{
				"type": "array",
				"items": map[string]any{
					"type": "object",
					"properties": map[string]any{
						"id":   map[string]any{"type": "integer"},
						"name": map[string]any{"type": "string"},
					},
				},
				"additionalProperties": false,
			},
			response: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewTextPart(JSONMarkdown(`{"id": 1, "name": "test"}\n{"id": 2}\n`)),
				},
			},
			want: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewJSONPart("{\"id\": 1, \"name\": \"test\"}"),
					NewJSONPart("{\"id\": 2}"),
				},
			},
			wantErr: false,
		},
		{
			name: "contains unexpected field fails",
			schema: map[string]any{
				"type": "array",
				"items": map[string]any{
					"type": "object",
					"properties": map[string]any{
						"name": map[string]any{"type": "string"},
						"age":  map[string]any{"type": "integer"},
					},
				},
				"additionalProperties": false,
			},
			response: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewTextPart(JSONMarkdown(`{"id": 1, "foo": "bar"}\n{"id": 2}\n`)),
				},
			},
			wantErr: true,
		},
		{
			name: "parses JSONl with preamble and code fence",
			schema: map[string]any{
				"type": "array",
				"items": map[string]any{
					"type": "object",
					"properties": map[string]any{
						"id": map[string]any{"type": "integer"},
					},
				},
				"additionalProperties": false,
			},
			response: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewTextPart("Here are the objects:\n\n```\n{\"id\": 1}\n{\"id\": 2}\n```"),
				},
			},
			want: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewJSONPart("{\"id\": 1}"),
					NewJSONPart("{\"id\": 2}"),
				},
			},
			wantErr: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			formatter := jsonlFormatter{}
			defer func() {
				if r := recover(); r != nil && tt.wantErr {
					t.Log("Test passed, panic was caught!")
				}
			}()
			handler, err := formatter.Handler(tt.schema)
			if err != nil {
				t.Fatalf("Handler() error = %v", err)
			}

			message, err := handler.ParseMessage(tt.response)
			if err != nil {
				t.Errorf("Parse failed")
			}

			if !tt.wantErr {
				if diff := cmp.Diff(tt.want, message); diff != "" {
					t.Errorf("Request msgs diff (+got -want):\n%s", diff)
				}
			}
		})
	}
}

func TestArrayParser(t *testing.T) {
	tests := []struct {
		name     string
		schema   map[string]any
		response *Message
		want     *Message
		wantErr  bool
	}{
		{
			name: "parses array schema",
			schema: map[string]any{
				"type": "array",
				"items": map[string]any{
					"type": "object",
					"properties": map[string]any{
						"id":   map[string]any{"type": "integer"},
						"name": map[string]any{"type": "string"},
					},
					"required": []string{"id"},
				},
				"additionalProperties": false,
			},
			response: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewTextPart(JSONMarkdown(`{"id": 1, "name": "test"}\n{"id": 2}\n`)),
				},
			},
			want: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewJSONPart("{\"id\": 1, \"name\": \"test\"}"),
					NewJSONPart("{\"id\": 2}"),
				},
			},
			wantErr: false,
		},
		{
			name: "contains unexpected field fails",
			schema: map[string]any{
				"type": "array",
				"items": map[string]any{
					"type": "object",
					"properties": map[string]any{
						"name": map[string]any{"type": "string"},
						"age":  map[string]any{"type": "integer"},
					},
					"required": []string{"name", "age"},
				},
				"additionalProperties": false,
			},
			response: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewTextPart(JSONMarkdown(`{"id": 1, "foo": "bar"}`)),
				},
			},
			wantErr: true,
		},
		{
			name: "parses empty array",
			schema: map[string]any{
				"type": "array",
				"items": map[string]any{
					"type": "object",
					"properties": map[string]any{
						"id": map[string]any{"type": "integer"},
					},
				},
				"additionalProperties": false,
			},
			response: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewTextPart("[]"),
				},
			},
			want: &Message{
				Role:    RoleModel,
				Content: nil,
			},
			wantErr: false,
		},
		{
			name: "parses array with preamble and code fence",
			schema: map[string]any{
				"type": "array",
				"items": map[string]any{
					"type": "object",
					"properties": map[string]any{
						"id": map[string]any{"type": "integer"},
					},
				},
				"additionalProperties": false,
			},
			response: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewTextPart("Here are the objects:\n\n```\n{\"id\": 1}\n{\"id\": 2}\n```"),
				},
			},
			want: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewJSONPart("{\"id\": 1}"),
					NewJSONPart("{\"id\": 2}"),
				},
			},
			wantErr: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			formatter := arrayFormatter{}
			handler, err := formatter.Handler(tt.schema)
			if err != nil {
				t.Fatalf("Handler() error = %v", err)
			}
			message, err := handler.ParseMessage(tt.response)

			if (err != nil) != tt.wantErr {
				t.Errorf("ParseMessage() error = %v, wantErr %v", err, tt.wantErr)
				if err != nil {
					t.Logf("Error message: %v", err)
				}
			}

			if !tt.wantErr {
				if diff := cmp.Diff(tt.want, message); diff != "" {
					t.Errorf("Request msgs diff (+got -want):\n%s", diff)
				}
			}
		})
	}
}

func TestEnumParser(t *testing.T) {
	type TestEnum struct {
		FavColor string `json:"fav_color,omitempty" jsonschema:"enum=red,enum=green,enum=blue"`
	}

	enumSchema := base.SchemaAsMap(base.InferJSONSchema(TestEnum{}))

	tests := []struct {
		name     string
		schema   map[string]any
		response *Message
		want     *Message
		wantErr  bool
	}{
		{
			name:   "parses simple enum value",
			schema: enumSchema,
			response: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewTextPart("red"),
				},
			},
			want: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewTextPart("red"),
				},
			},
			wantErr: false,
		},
		{
			name:   "trims whitespace",
			schema: enumSchema,
			response: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewTextPart("  green\n"),
				},
			},
			want: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewTextPart("green"),
				},
			},
			wantErr: false,
		},
		{
			name:   "fails on invalid enum",
			schema: enumSchema,
			response: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewTextPart("VALUE1"),
				},
			},
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			formatter := enumFormatter{}
			handler, err := formatter.Handler(tt.schema)
			if err != nil {
				t.Fatalf("Handler() error = %v", err)
			}
			message, err := handler.ParseMessage(tt.response)

			if (err != nil) != tt.wantErr {
				t.Errorf("ParseMessage() error = %v, wantErr %v", err, tt.wantErr)
				if err != nil {
					t.Logf("Error message: %v", err)
				}
			}

			if !tt.wantErr {
				if diff := cmp.Diff(tt.want, message); diff != "" {
					t.Errorf("Request msgs diff (+got -want):\n%s", diff)
				}
			}
		})
	}
}

func TestJsonParserStreaming(t *testing.T) {
	tests := []struct {
		name     string
		schema   map[string]any
		response *Message
		want     *Message
		wantErr  bool
	}{
		{
			name: "parses streaming JSON from multiple parts",
			schema: map[string]any{
				"type": "object",
				"properties": map[string]any{
					"name": map[string]any{"type": "string"},
					"age":  map[string]any{"type": "integer"},
				},
				"additionalProperties": false,
			},
			response: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewTextPart(`{"name`),
					NewTextPart(`": "John", `),
					NewTextPart(`"age": 19}`),
				},
			},
			want: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewJSONPart(`{"name": "John", "age": 19}`),
				},
			},
			wantErr: false,
		},
		{
			name: "parses streaming JSON with markdown from multiple parts",
			schema: map[string]any{
				"type": "object",
				"properties": map[string]any{
					"id": map[string]any{"type": "integer"},
				},
				"additionalProperties": false,
			},
			response: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewTextPart("```json\n"),
					NewTextPart(`{"id"`),
					NewTextPart(`: 1}`),
					NewTextPart("\n```"),
				},
			},
			want: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewJSONPart("\n{\"id\": 1}\n"),
				},
			},
			wantErr: false,
		},
		{
			name: "preserves non-text parts with streaming JSON",
			schema: map[string]any{
				"type": "object",
				"properties": map[string]any{
					"name": map[string]any{"type": "string"},
				},
				"additionalProperties": false,
			},
			response: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewTextPart(`{"name"`),
					NewTextPart(`: "test"}`),
					NewToolRequestPart(&ToolRequest{Name: "testTool"}),
				},
			},
			want: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewJSONPart(`{"name": "test"}`),
					NewToolRequestPart(&ToolRequest{Name: "testTool"}),
				},
			},
			wantErr: false,
		},
		{
			name: "no text part present streaming JSON",
			schema: map[string]any{
				"type": "object",
				"properties": map[string]any{
					"name": map[string]any{"type": "string"},
				},
				"additionalProperties": false,
			},
			response: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewToolRequestPart(&ToolRequest{Name: "testTool"}),
				},
			},
			want: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewToolRequestPart(&ToolRequest{Name: "testTool"}),
				},
			},
			wantErr: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			formatter := jsonFormatter{}
			handler, err := formatter.Handler(tt.schema)
			if err != nil {
				t.Fatalf("Handler() error = %v", err)
			}
			message, err := handler.ParseMessage(tt.response)

			if (err != nil) != tt.wantErr {
				t.Errorf("ParseMessage() error = %v, wantErr %v", err, tt.wantErr)
				if err != nil {
					t.Logf("Error message: %v", err)
				}
			}

			if !tt.wantErr {
				if diff := cmp.Diff(tt.want, message); diff != "" {
					t.Errorf("Request msgs diff (+got -want):\n%s", diff)
				}
			}
		})
	}
}

func TestJsonlParserStreaming(t *testing.T) {
	tests := []struct {
		name     string
		schema   map[string]any
		response *Message
		want     *Message
		wantErr  bool
	}{
		{
			name: "parses streaming JSONL from multiple parts",
			schema: map[string]any{
				"type": "array",
				"items": map[string]any{
					"type": "object",
					"properties": map[string]any{
						"id":   map[string]any{"type": "integer"},
						"name": map[string]any{"type": "string"},
					},
				},
				"additionalProperties": false,
			},
			response: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewTextPart(`{"id": 1, "na`),
					NewTextPart(`me": "Alice"}\n`),
					NewTextPart(`{"id": 2, "`),
					NewTextPart(`name": "Bob"}`),
				},
			},
			want: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewJSONPart(`{"id": 1, "name": "Alice"}`),
					NewJSONPart(`{"id": 2, "name": "Bob"}`),
				},
			},
			wantErr: false,
		},
		{
			name: "parses streaming JSONL with mixed content",
			schema: map[string]any{
				"type": "array",
				"items": map[string]any{
					"type": "object",
					"properties": map[string]any{
						"id": map[string]any{"type": "integer"},
					},
				},
				"additionalProperties": false,
			},
			response: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewTextPart(`{"id"`),
					NewTextPart(`: 1}\n{"id": 2}`),
					NewToolRequestPart(&ToolRequest{Name: "testTool"}),
				},
			},
			want: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewJSONPart(`{"id": 1}`),
					NewJSONPart(`{"id": 2}`),
					NewToolRequestPart(&ToolRequest{Name: "testTool"}),
				},
			},
			wantErr: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			formatter := jsonlFormatter{}
			handler, err := formatter.Handler(tt.schema)
			if err != nil {
				t.Fatalf("Handler() error = %v", err)
			}
			message, err := handler.ParseMessage(tt.response)

			if (err != nil) != tt.wantErr {
				t.Errorf("ParseMessage() error = %v, wantErr %v", err, tt.wantErr)
				if err != nil {
					t.Logf("Error message: %v", err)
				}
			}

			if !tt.wantErr {
				if diff := cmp.Diff(tt.want, message); diff != "" {
					t.Errorf("Request msgs diff (+got -want):\n%s", diff)
				}
			}
		})
	}
}

func TestArrayParserStreaming(t *testing.T) {
	tests := []struct {
		name     string
		schema   map[string]any
		response *Message
		want     *Message
		wantErr  bool
	}{
		{
			name: "parses streaming array from multiple parts",
			schema: map[string]any{
				"type": "array",
				"items": map[string]any{
					"type": "object",
					"properties": map[string]any{
						"id":   map[string]any{"type": "integer"},
						"name": map[string]any{"type": "string"},
					},
					"required": []string{"id"},
				},
				"additionalProperties": false,
			},
			response: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewTextPart(`{"id": 1, "na`),
					NewTextPart(`me": "test"}\n`),
					NewTextPart(`{"id"`),
					NewTextPart(`: 2}`),
				},
			},
			want: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewJSONPart(`{"id": 1, "name": "test"}`),
					NewJSONPart(`{"id": 2}`),
				},
			},
			wantErr: false,
		},
		{
			name: "parses array with preamble and code fence",
			schema: map[string]any{
				"type": "array",
				"items": map[string]any{
					"type": "object",
					"properties": map[string]any{
						"id": map[string]any{"type": "integer"},
					},
				},
				"additionalProperties": false,
			},
			response: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewTextPart("Here are the"),
					NewTextPart("objects:\n\n```\n"),
					NewTextPart(" {\"id\": 1}\n"),
					NewTextPart("{\"id\": 2}\n```"),
				},
			},
			want: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewJSONPart("{\"id\": 1}"),
					NewJSONPart("{\"id\": 2}"),
				},
			},
			wantErr: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			formatter := arrayFormatter{}
			handler, err := formatter.Handler(tt.schema)
			if err != nil {
				t.Fatalf("Handler() error = %v", err)
			}
			message, err := handler.ParseMessage(tt.response)

			if (err != nil) != tt.wantErr {
				t.Errorf("ParseMessage() error = %v, wantErr %v", err, tt.wantErr)
				if err != nil {
					t.Logf("Error message: %v", err)
				}
			}

			if !tt.wantErr {
				if diff := cmp.Diff(tt.want, message); diff != "" {
					t.Errorf("Request msgs diff (+got -want):\n%s", diff)
				}
			}
		})
	}
}

func TestEnumParserStreaming(t *testing.T) {
	type TestEnum struct {
		FavColor string `json:"fav_color,omitempty" jsonschema:"enum=red,enum=green,enum=blue"`
	}

	enumSchema := base.SchemaAsMap(base.InferJSONSchema(TestEnum{}))

	tests := []struct {
		name     string
		schema   map[string]any
		response *Message
		want     *Message
		wantErr  bool
	}{
		{
			name:   "parses streaming enum from multiple parts",
			schema: enumSchema,
			response: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewTextPart(`"gr`),
					NewTextPart(`een"`),
				},
			},
			want: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewTextPart("green"),
				},
			},
			wantErr: false,
		},
		{
			name:   "parses streaming enum with whitespace",
			schema: enumSchema,
			response: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewTextPart(`  "re`),
					NewTextPart(`d"`),
				},
			},
			want: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewTextPart("red"),
				},
			},
			wantErr: false,
		},
		{
			name:   "fails on invalid streaming enum",
			schema: enumSchema,
			response: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewTextPart(`yel`),
					NewTextPart(`low`),
				},
			},
			wantErr: true,
		},
		{
			name:   "preserves non-text parts with streaming enum",
			schema: enumSchema,
			response: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewToolRequestPart(&ToolRequest{Name: "testTool"}),
					NewTextPart(`bl`),
					NewTextPart(`ue`),
				},
			},
			want: &Message{
				Role: RoleModel,
				Content: []*Part{
					NewTextPart("blue"),
					NewToolRequestPart(&ToolRequest{Name: "testTool"}),
				},
			},
			wantErr: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			formatter := enumFormatter{}
			handler, err := formatter.Handler(tt.schema)
			if err != nil {
				t.Fatalf("Handler() error = %v", err)
			}
			message, err := handler.ParseMessage(tt.response)

			if (err != nil) != tt.wantErr {
				t.Errorf("ParseMessage() error = %v, wantErr %v", err, tt.wantErr)
				if err != nil {
					t.Logf("Error message: %v", err)
				}
			}

			if !tt.wantErr {
				if diff := cmp.Diff(tt.want, message); diff != "" {
					t.Errorf("Request msgs diff (+got -want):\n%s", diff)
				}
			}
		})
	}
}
