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

	"github.com/google/go-cmp/cmp"
)

func TestSimulateConstrainedGeneration(t *testing.T) {
	tests := []struct {
		name       string
		info       *ModelInfo
		input      *ModelRequest
		wantMsgs   []*Message
		wantConfig *ModelOutputConfig
	}{
		{
			name: "simulates constraint if no model support",
			info: &ModelInfo{
				Supports: &ModelSupports{
					Constrained: ConstrainedSupportNone,
				},
			},
			input: &ModelRequest{
				Messages: []*Message{
					NewSystemTextMessage("You are a helpful assistant."),
					NewUserTextMessage("hello!"),
				},
				Output: &ModelOutputConfig{
					Format:      string(OutputFormatJSON),
					Constrained: true,
					Schema: map[string]any{
						"type":     "object",
						"required": []string{"name"},
						"properties": map[string]any{
							"name": map[string]any{"type": "string"},
						},
					},
				},
			},
			wantMsgs: []*Message{
				{
					Role: RoleSystem,
					Content: []*Part{
						NewTextPart("You are a helpful assistant."),
						{
							Kind:        PartText,
							ContentType: "plain/text",
							Text:        "Output should be in JSON format and conform to the following schema:\n\n```\"{\\\"properties\\\":{\\\"name\\\":{\\\"type\\\":\\\"string\\\"}},\\\"required\\\":[\\\"name\\\"],\\\"type\\\":\\\"object\\\"}\"```",
							Metadata:    map[string]any{"purpose": "output"},
						},
					},
				},
				NewUserTextMessage("hello!"),
			},
			wantConfig: &ModelOutputConfig{
				Format:      string(OutputFormatJSON),
				Constrained: false,
				Schema: map[string]any{
					"type":     "object",
					"required": []string{"name"},
					"properties": map[string]any{
						"name": map[string]any{"type": "string"},
					},
				},
			},
		},
		{
			name: "simulates constraint if no tool support and tools are in request",
			info: &ModelInfo{
				Supports: &ModelSupports{
					Constrained: ConstrainedSupportNoTools,
				},
			},
			input: &ModelRequest{
				Messages: []*Message{
					NewSystemTextMessage("You are a helpful assistant."),
					NewUserTextMessage("hello!"),
				},
				Output: &ModelOutputConfig{
					Format:      string(OutputFormatJSON),
					Constrained: true,
					Schema: map[string]any{
						"type":     "object",
						"required": []string{"name"},
						"properties": map[string]any{
							"name": map[string]any{"type": "string"},
						},
					},
				},
				Tools: []*ToolDefinition{
					{
						Name:        "test-tool",
						Description: "A test tool",
					},
				},
			},
			wantMsgs: []*Message{
				{
					Role: RoleSystem,
					Content: []*Part{
						NewTextPart("You are a helpful assistant."),
						{
							Kind:        PartText,
							ContentType: "plain/text",
							Text:        "Output should be in JSON format and conform to the following schema:\n\n```\"{\\\"properties\\\":{\\\"name\\\":{\\\"type\\\":\\\"string\\\"}},\\\"required\\\":[\\\"name\\\"],\\\"type\\\":\\\"object\\\"}\"```",
							Metadata:    map[string]any{"purpose": "output"},
						},
					},
				},
				NewUserTextMessage("hello!"),
			},
			wantConfig: &ModelOutputConfig{
				Format:      string(OutputFormatJSON),
				Constrained: false,
				Schema: map[string]any{
					"type":     "object",
					"required": []string{"name"},
					"properties": map[string]any{
						"name": map[string]any{"type": "string"},
					},
				},
			},
		},
		{
			name: "doesn't simulate constraint if no tools are in request",
			info: &ModelInfo{
				Supports: &ModelSupports{
					Constrained: ConstrainedSupportNoTools,
				},
			},
			input: &ModelRequest{
				Messages: []*Message{
					NewSystemTextMessage("You are a helpful assistant."),
					NewUserTextMessage("hello!"),
				},
				Output: &ModelOutputConfig{
					Format:      string(OutputFormatJSON),
					Constrained: true,
					Schema: map[string]any{
						"type":     "object",
						"required": []string{"name"},
						"properties": map[string]any{
							"name": map[string]any{"type": "string"},
						},
					},
				},
			},
			wantMsgs: []*Message{
				{
					Role: RoleSystem,
					Content: []*Part{
						NewTextPart("You are a helpful assistant."),
					},
				},
				NewUserTextMessage("hello!"),
			},
			wantConfig: &ModelOutputConfig{
				Format:      string(OutputFormatJSON),
				Constrained: true,
				Schema: map[string]any{
					"type":     "object",
					"required": []string{"name"},
					"properties": map[string]any{
						"name": map[string]any{"type": "string"},
					},
				},
			},
		},
		{
			name: "relies on native support -- no instructions",
			info: &ModelInfo{
				Supports: &ModelSupports{
					Constrained: ConstrainedSupportAll,
				},
			},
			input: &ModelRequest{
				Messages: []*Message{
					NewUserTextMessage("generate json"),
				},
				Output: &ModelOutputConfig{
					Format: string(OutputFormatJSON),
					Schema: map[string]any{
						"type":     "object",
						"required": []string{"name"},
						"properties": map[string]any{
							"name": map[string]any{"type": "string"},
						},
					},
				},
			},
			wantMsgs: []*Message{
				NewUserTextMessage("generate json"),
			},
			wantConfig: &ModelOutputConfig{
				Format: string(OutputFormatJSON),
				Schema: map[string]any{
					"type":     "object",
					"required": []string{"name"},
					"properties": map[string]any{
						"name": map[string]any{"type": "string"},
					},
				},
			},
		},
	}

	mockModelFunc := func(ctx context.Context, req *ModelRequest, cb ModelStreamCallback) (*ModelResponse, error) {
		return &ModelResponse{Request: req}, nil
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			handler := simulateConstrainedGeneration("test-model", tt.info)(mockModelFunc)
			resp, err := handler(context.Background(), tt.input, nil)
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}

			if diff := cmp.Diff(resp.Request.Messages, tt.wantMsgs); diff != "" {
				t.Errorf("Request msgs diff (+got -want):\n%s", diff)
			}

			if diff := cmp.Diff(resp.Request.Output, tt.wantConfig); diff != "" {
				t.Errorf("Request config diff (+got -want):\n%s", diff)
			}
		})
	}
}

func TestConstrainedGenerate(t *testing.T) {
	JSON := "\n{\"foo\": \"bar\"}\n"
	JSONmd := "```json" + JSON + "```"

	modelInfo := ModelInfo{
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

	formatModel := DefineModel(r, "test", "format", &modelInfo, func(ctx context.Context, gr *ModelRequest, msc ModelStreamCallback) (*ModelResponse, error) {
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
				Format: string(OutputFormatJSON),
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
			WithPromptText("generate json"),
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
				Format: string(OutputFormatJSON),
				Schema: map[string]any{
					"additionalProperties": bool(false),
					"properties": map[string]any{
						"foo": map[string]any{"type": string("string")},
					},
					"required": []any{string("foo")},
					"type":     string("object"),
				},
				Constrained: false,
				ContentType: "application/json",
			},
			Config: &GenerationCommonConfig{Temperature: 1},
			Tools:  []*ToolDefinition{},
		}

		streamText := ""
		res, err := Generate(context.Background(), r,
			WithModel(formatModel),
			WithPromptText("generate json"),
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
			WithOutputNativeConstrained(false), // Need to set to false to satisfy testcase
			WithOutputInstructions(new(string)),
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
		customInstructions := "The generated output should be in JSON format and conform to the following schema:\n\n```\"{\\\"additionalProperties\\\":false,\\\"properties\\\":{\\\"foo\\\":{\\\"type\\\":\\\"string\\\"}},\\\"required\\\":[\\\"foo\\\"],\\\"type\\\":\\\"object\\\"}\"```"
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
				Format: string(OutputFormatJSON),
				Schema: map[string]any{
					"additionalProperties": bool(false),
					"properties": map[string]any{
						"foo": map[string]any{"type": string("string")},
					},
					"required": []any{string("foo")},
					"type":     string("object"),
				},
				Constrained: false, // Need to set to false to satisfy testcase
				ContentType: "application/json",
			},
			Config: &GenerationCommonConfig{Temperature: 1},
			Tools:  []*ToolDefinition{},
		}

		streamText := ""
		res, err := Generate(context.Background(), r,
			WithModel(formatModel),
			WithPromptText("generate json"),
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
			WithOutputNativeConstrained(false),
			WithOutputInstructions(&customInstructions),
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
							Text:        "Output should be in JSON format and conform to the following schema:\n\n```\"{\\\"additionalProperties\\\":false,\\\"properties\\\":{\\\"foo\\\":{\\\"type\\\":\\\"string\\\"}},\\\"required\\\":[\\\"foo\\\"],\\\"type\\\":\\\"object\\\"}\"```",
							Metadata:    map[string]any{"purpose": "output"},
						},
					},
				},
			},
			Output: &ModelOutputConfig{
				Format: string(OutputFormatJSON),
				Schema: map[string]any{
					"additionalProperties": bool(false),
					"properties": map[string]any{
						"foo": map[string]any{"type": string("string")},
					},
					"required": []any{string("foo")},
					"type":     string("object"),
				},
				Constrained: false,
				ContentType: "application/json",
			},
			Config: &GenerationCommonConfig{Temperature: 1},
			Tools:  []*ToolDefinition{},
		}

		streamText := ""
		res, err := Generate(context.Background(), r,
			WithModel(formatModel),
			WithPromptText("generate json"),
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
			WithOutputNativeConstrained(false),
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
							Text:        "Output should be in JSON format and conform to the following schema:\n\n```\"{\\\"additionalProperties\\\":false,\\\"properties\\\":{\\\"foo\\\":{\\\"type\\\":\\\"string\\\"}},\\\"required\\\":[\\\"foo\\\"],\\\"type\\\":\\\"object\\\"}\"```",
							Metadata:    map[string]any{"purpose": "output"},
						},
					},
				},
			},
			Output: &ModelOutputConfig{
				Format: string(OutputFormatJSON),
				Schema: map[string]any{
					"additionalProperties": bool(false),
					"properties": map[string]any{
						"foo": map[string]any{"type": string("string")},
					},
					"required": []any{string("foo")},
					"type":     string("object"),
				},
				Constrained: false,
				ContentType: "application/json",
			},
			Config: &GenerationCommonConfig{Temperature: 1},
			Tools:  []*ToolDefinition{},
		}

		p, err := DefinePrompt(r, "formatPrompt",
			WithPromptText("generate json"),
			WithModel(formatModel),
			WithOutputType(struct {
				Foo string `json:"foo"`
			}{}),
			WithOutputNativeConstrained(false),
		)
		if err != nil {
			t.Fatal(err)
		}

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
	tests := []struct {
		name         string
		format       string
		schema       map[string]any
		output       *ModelOutputConfig
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
			output: &ModelOutputConfig{
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
			output: &ModelOutputConfig{
				Format: "json",
				Schema: map[string]any{
					"type": "object",
					"properties": map[string]any{
						"name": map[string]any{"type": "string"},
						"age":  map[string]any{"type": "integer"},
					},
					"additionalProperties": false,
				},
				Constrained: true,
				ContentType: "application/json",
			},
			instructions: "Output should be in JSON format and conform to the following schema:\n\n```\"{\\\"additionalProperties\\\":false,\\\"properties\\\":{\\\"age\\\":{\\\"type\\\":\\\"integer\\\"},\\\"name\\\":{\\\"type\\\":\\\"string\\\"}},\\\"type\\\":\\\"object\\\"}\"```",
			wantErr:      false,
		},
		{
			name:   "jsonl handler",
			format: "jsonl",
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
			output: &ModelOutputConfig{
				Format: "jsonl",
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
				Constrained: true,
				ContentType: "application/jsonl",
			},
			instructions: "Output should be JSONL format, a sequence of JSON objects (one per line) separated by a newline '\\n' character. Each line should be a JSON object conforming to the following schema:\n\n```\"{\\\"properties\\\":{\\\"age\\\":{\\\"type\\\":\\\"integer\\\"},\\\"name\\\":{\\\"type\\\":\\\"string\\\"}},\\\"type\\\":\\\"object\\\"}\"```",
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
				instructions := resolveInstructions(format, tt.schema, nil)
				config := format.Handler(tt.schema).Config()

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
			formatter := JSONFormatter{"json"}
			message, err := formatter.Handler(tt.schema).ParseMessage(tt.response)

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
			formatter := TextFormatter{"text"}
			message, err := formatter.Handler(nil).ParseMessage(tt.response)

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
				"type":     "object",
				"required": []string{"id"},
				"properties": map[string]any{
					"id":   map[string]any{"type": "integer"},
					"name": map[string]any{"type": "string"},
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
					NewTextPart(JSONMarkdown(`{"id": 1, "foo": "bar"}\n{"id": 2}\n`)),
				},
			},
			wantErr: true,
		},
		{
			name: "parses JSONl with preamble and code fence",
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
			formatter := JSONLFormatter{"jsonl"}
			defer func() {
				if r := recover(); r != nil && tt.wantErr {
					t.Log("Test passed, panic was caught!")
				}
			}()
			message, err := formatter.Handler(tt.schema).ParseMessage(tt.response)
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
