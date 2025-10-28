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

package googlegenai

import (
	"errors"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"google.golang.org/genai"
)

func TestConvertRequest(t *testing.T) {
	text := "hello"
	tool := &ai.ToolDefinition{
		Description: "this is a dummy tool",
		Name:        "myTool",
		InputSchema: map[string]any{
			"additionalProperties": bool(false),
			"properties":           map[string]any{"Test": map[string]any{"type": string("string")}},
			"required":             []any{string("Test")},
			"type":                 string("object"),
		},
		OutputSchema: map[string]any{"type": string("string")},
	}

	req := &ai.ModelRequest{
		Config: genai.GenerateContentConfig{
			MaxOutputTokens: 10,
			StopSequences:   []string{"stop"},
			Temperature:     genai.Ptr[float32](0.4),
			TopK:            genai.Ptr[float32](0.1),
			TopP:            genai.Ptr[float32](1.0),
			Tools: []*genai.Tool{
				{GoogleSearch: &genai.GoogleSearch{}},
			},
			ThinkingConfig: &genai.ThinkingConfig{
				IncludeThoughts: false,
				ThinkingBudget:  genai.Ptr[int32](0),
			},
		},
		Tools:      []*ai.ToolDefinition{tool},
		ToolChoice: ai.ToolChoiceAuto,
		Output: &ai.ModelOutputConfig{
			Constrained: true,
			Schema: map[string]any{
				"type": string("object"),
				"properties": map[string]any{
					"string": map[string]any{
						"type": string("string"),
					},
					"boolean": map[string]any{
						"type": string("boolean"),
					},
					"float": map[string]any{
						"type": string("float64"),
					},
					"number": map[string]any{
						"type": string("number"),
					},
					"array": map[string]any{
						"type": string("array"),
					},
					"object": map[string]any{
						"type": string("object"),
					},
					"domain": map[string]any{
						"anyOf": []map[string]any{
							{
								"type": string("string"),
							},
							{
								"type": string("null"),
							},
						},
						"default": "null",
						"title":   string("Domain"),
					},
				},
			},
		},
		Messages: []*ai.Message{
			{
				Role: ai.RoleUser,
				Content: []*ai.Part{
					{Text: text},
				},
			},
			{
				Role: ai.RoleSystem,
				Content: []*ai.Part{
					{Text: text},
				},
			},
			{
				Role: ai.RoleUser,
				Content: []*ai.Part{
					{Text: text},
				},
			},
			{
				Role: ai.RoleSystem,
				Content: []*ai.Part{
					{Text: text},
				},
			},
		},
	}
	t.Run("convert request", func(t *testing.T) {
		gcc, err := toGeminiRequest(req, nil)
		if err != nil {
			t.Fatal(err)
		}
		if gcc.SystemInstruction == nil {
			t.Error("expecting system instructions to be populated")
		}
		if len(gcc.SystemInstruction.Parts) != 2 {
			t.Errorf("got: %d, want: 2", len(gcc.SystemInstruction.Parts))
		}
		if gcc.SystemInstruction.Role != string(ai.RoleSystem) {
			t.Errorf(" system instruction role: got: %q, want: %q", gcc.SystemInstruction.Role, string(ai.RoleSystem))
		}
		// this is explicitly set to 1 in source
		if gcc.CandidateCount == 0 {
			t.Error("candidate count: got: 0, want: 1")
		}
		ogCfg, ok := req.Config.(genai.GenerateContentConfig)
		if !ok {
			t.Fatalf("request config should have been of type: genai.GenerateContentConfig, got: %T", req.Config)
		}
		if gcc.MaxOutputTokens == 0 {
			t.Errorf("max output tokens: got: 0, want %d", ogCfg.MaxOutputTokens)
		}
		if len(gcc.StopSequences) == 0 {
			t.Errorf("stop sequences: got: 0, want: %d", len(ogCfg.StopSequences))
		}
		if gcc.Temperature == nil {
			t.Errorf("temperature: got: nil, want %f", *ogCfg.Temperature)
		}
		if gcc.TopP == nil {
			t.Errorf("topP: got: nil, want %f", *ogCfg.TopP)
		}
		if gcc.TopK == nil {
			t.Errorf("topK: got: nil, want %d", ogCfg.TopK)
		}
		if gcc.ResponseMIMEType != "" {
			t.Errorf("ResponseMIMEType should been empty if tools are present")
		}
		if gcc.ResponseSchema == nil {
			t.Errorf("ResponseSchema should not be empty")
		}
		if gcc.ThinkingConfig == nil {
			t.Errorf("ThinkingConfig should not be empty")
		}
		if len(gcc.Tools) != 1 {
			t.Errorf("tools should have been: 1, got: %d", len(gcc.Tools))
		}
	})
	t.Run("use valid tools outside genkit", func(t *testing.T) {
		badCfg := genai.GenerateContentConfig{
			Temperature: genai.Ptr[float32](1.0),
			Tools: []*genai.Tool{
				{
					CodeExecution: &genai.ToolCodeExecution{},
					GoogleSearch:  &genai.GoogleSearch{},
				},
			},
		}
		req := ai.ModelRequest{
			Config: badCfg,
		}
		_, err := toGeminiRequest(&req, nil)
		if err != nil {
			t.Fatalf("expected nil, got: %v", err)
		}
	})
	t.Run("forbidden primitives outside genkit", func(t *testing.T) {
		type testCase struct {
			name string
			cfg  genai.GenerateContentConfig
			err  error
		}
		tests := []testCase{
			{
				name: "use system instruction outside genkit",
				cfg: genai.GenerateContentConfig{
					Temperature:       genai.Ptr[float32](1.0),
					SystemInstruction: &genai.Content{Parts: []*genai.Part{{Text: "talk like a pirate"}}},
				},
				err: errors.New("system instruction should be set using Genkit features"),
			},
			{
				name: "use function declaration tools outside genkit",
				cfg: genai.GenerateContentConfig{
					Temperature: genai.Ptr[float32](1.0),
					Tools: []*genai.Tool{
						{
							FunctionDeclarations: []*genai.FunctionDeclaration{},
							GoogleSearch:         &genai.GoogleSearch{},
						},
					},
				},
				err: errors.New("function declaration tools should be set using Genkit features"),
			},
			{
				name: "use code execution tool",
				cfg: genai.GenerateContentConfig{
					Temperature: genai.Ptr[float32](1.0),
					Tools: []*genai.Tool{
						{
							FunctionDeclarations: []*genai.FunctionDeclaration{},
						},
						{
							CodeExecution: &genai.ToolCodeExecution{},
						},
					},
				},
				err: errors.New("function declaration tools should be set using Genkit features"),
			},
			{
				name: "use cache outside genkit",
				cfg: genai.GenerateContentConfig{
					CachedContent: "some cache uuid",
				},
				err: errors.New("cache contents should be set using Genkit features"),
			},
			{
				name: "use response schema outside genkit",
				cfg: genai.GenerateContentConfig{
					ResponseSchema: &genai.Schema{
						Description: "some schema",
					},
				},
				err: errors.New("response schema should be set using Genkit features"),
			},
			{
				name: "use response MIME type outside genkit",
				cfg: genai.GenerateContentConfig{
					ResponseMIMEType: "image/png",
				},
				err: errors.New("response schema should be set using Genkit features"),
			},
		}

		for _, tc := range tests {
			t.Run(tc.name, func(t *testing.T) {
				req := ai.ModelRequest{
					Config: tc.cfg,
				}
				_, err := toGeminiRequest(&req, nil)
				if err == nil {
					t.Fatalf("expected an error: '%v' but got nil", tc.err)
				}
			})
		}
	})
	t.Run("convert tools with valid tool", func(t *testing.T) {
		tools := []*ai.ToolDefinition{tool}
		gt, err := toGeminiTools(tools)
		if err != nil {
			t.Fatalf("expected tool convertion but got error: %v", err)
		}
		for _, tt := range gt {
			for _, fd := range tt.FunctionDeclarations {
				if fd.Description == "" {
					t.Error("expecting tool description, got empty")
				}
				if fd.Name == "" {
					t.Error("expecting tool name, got empty")
				}
				if fd.Parameters == nil {
					t.Error("expecting parameters, got empty")
				}
			}
		}
	})
	t.Run("convert tools with empty tools", func(t *testing.T) {
		tools := []*ai.ToolDefinition{}
		gt, err := toGeminiTools(tools)
		if err != nil {
			t.Fatal("should not expect errors")
		}
		if gt != nil {
			t.Fatalf("should expect an empty tool list, got %#v", gt)
		}
	})
	t.Run("convert tools with invalid name", func(t *testing.T) {
		tools := []*ai.ToolDefinition{{
			Description:  tool.Description,
			InputSchema:  tool.InputSchema,
			OutputSchema: tool.OutputSchema,
			Name:         "something/myTool", // '/' is not a valid character for a Gemini tool name
		}}
		_, err := toGeminiTools(tools)
		if err == nil {
			t.Fatalf("expected error, got nil")
		}
	})
}

func TestValidToolName(t *testing.T) {
	testCases := []struct {
		name     string
		input    string
		expected bool
	}{
		{
			name:     "Valid single letter",
			input:    "a",
			expected: true,
		},
		{
			name:     "Valid single underscore",
			input:    "_",
			expected: true,
		},
		{
			name:     "Valid alphanumeric with underscore",
			input:    "my_tool",
			expected: true,
		},
		{
			name:     "Valid alphanumeric with dot and hyphen",
			input:    "user.name-id",
			expected: true,
		},
		{
			name:     "Valid max length",
			input:    "a" + genToolName(63, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-"),
			expected: true,
		},
		{
			name:     "Invalid starts with digit",
			input:    "1tool",
			expected: false,
		},
		{
			name:     "Invalid starts with hyphen",
			input:    "-tool",
			expected: false,
		},
		{
			name:     "Invalid starts with dot",
			input:    ".tool",
			expected: false,
		},
		{
			name:     "Invalid contains space",
			input:    "my tool",
			expected: false,
		},
		{
			name:     "Invalid contains special character",
			input:    "my$tool",
			expected: false,
		},
		{
			name:     "Invalid empty string",
			input:    "",
			expected: false,
		},
		{
			name:     "Invalid too long",
			input:    "a" + genToolName(64, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-"),
			expected: false,
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			got := validToolName(tc.input)
			if got != tc.expected {
				t.Errorf("Test %q failed: expected: %v, got: %v", tc.name, tc.expected, got)
			}
		})
	}
}

// genToolName generates a string of a specified length using only
// the valid characters for a Gemini Tool name
func genToolName(length int, chars string) string {
	r := make([]byte, length)

	for i := range length {
		r[i] = chars[i%len(chars)]
	}
	return string(r)
}
