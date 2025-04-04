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
		Config: &ai.GenerationCommonConfig{
			MaxOutputTokens: 10,
			StopSequences:   []string{"stop"},
			Temperature:     0.4,
			TopK:            1.0,
			TopP:            1.0,
			Version:         text,
		},
		Tools:      []*ai.ToolDefinition{tool},
		ToolChoice: ai.ToolChoiceAuto,
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
		gcc, err := convertRequest("gemini-2.0-flash-001", req, nil)
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
		if gcc.CandidateCount == nil {
			t.Error("candidate count: got: nil, want: 1")
		}
		ogCfg, ok := req.Config.(*ai.GenerationCommonConfig)
		if !ok {
			t.Fatalf("request config should have been of type: ai.GenerationCommonConfig, got: %T", req.Config)
		}
		if gcc.MaxOutputTokens == nil {
			t.Errorf("max output tokens: got: nil, want %d", ogCfg.MaxOutputTokens)
		}
		if len(gcc.StopSequences) == 0 {
			t.Errorf("stop sequences: got: 0, want: %d", len(ogCfg.StopSequences))
		}
		if gcc.Temperature == nil {
			t.Errorf("temperature: got: nil, want %f", ogCfg.Temperature)
		}
		if gcc.TopP == nil {
			t.Errorf("topP: got: nil, want %f", ogCfg.TopP)
		}
		if gcc.TopK == nil {
			t.Errorf("topK: got: nil, want %d", ogCfg.TopK)
		}
	})
	t.Run("convert tools with valid tool", func(t *testing.T) {
		tools := []*ai.ToolDefinition{tool}
		gt, err := convertTools(tools)
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
		gt, err := convertTools(tools)
		if err != nil {
			t.Fatal("should not expect errors")
		}
		if gt != nil {
			t.Fatalf("should expect an empty tool list, got %#v", gt)
		}
	})
	t.Run("convert schema with valid schema", func(t *testing.T) {
		schema := tool.InputSchema
		gs, err := convertSchema(schema, schema)
		if err != nil {
			t.Fatalf("expected schema convertion but got error: %v", err)
		}
		if gs == nil {
			t.Fatal("expected non nil schema")
		}
		if gs.Type != genai.TypeObject {
			t.Errorf("invalid schema type, want: genai.TypeObject, got: %T", gs.Type)
		}
		if gs.Properties == nil {
			t.Error("expecting non nil schema properties")
		}
		if len(gs.Required) == 0 {
			t.Error("expecting required elements, got 0")
		}
	})
	t.Run("convert schema with nil schema", func(t *testing.T) {
		gs, err := convertSchema(nil, nil)
		if err != nil {
			t.Errorf("not expecting an error, got: %v", err)
		}
		if gs != nil {
			t.Errorf("expecting a nil schema, got: %#v", gs)
		}
	})
	t.Run("convert tool choice with choice required", func(t *testing.T) {
		tools := []*ai.ToolDefinition{tool}
		tc, err := convertToolChoice(ai.ToolChoiceRequired, tools)
		if err != nil {
			t.Fatal(err)
		}
		if tc.FunctionCallingConfig == nil {
			t.Fatal("config should not be empty")
		}
		if tc.FunctionCallingConfig.Mode == "" {
			t.Errorf("mode should not be empty")
		}
		if len(tc.FunctionCallingConfig.AllowedFunctionNames) == 0 {
			t.Error("function names should not be empty")
		}
	})
	t.Run("convert tool choice with choice auto", func(t *testing.T) {
		tools := []*ai.ToolDefinition{tool}
		tc, err := convertToolChoice(ai.ToolChoiceAuto, tools)
		if err != nil {
			t.Fatal(err)
		}
		if tc.FunctionCallingConfig == nil {
			t.Fatal("config should not be empty")
		}
		if tc.FunctionCallingConfig.Mode == "" {
			t.Errorf("mode should not be empty")
		}
		if len(tc.FunctionCallingConfig.AllowedFunctionNames) > 0 {
			t.Error("function names should be empty")
		}
	})
	t.Run("convert tool choice, nil choice", func(t *testing.T) {
		tools := []*ai.ToolDefinition{tool}
		tc, err := convertToolChoice("", tools)
		if err != nil {
			t.Fatal(err)
		}
		if tc != nil {
			t.Fatalf("want: nil, got: %#v", tc)
		}
	})
	t.Run("convert tool choice, nil tools", func(t *testing.T) {
		_, err := convertToolChoice(ai.ToolChoiceRequired, nil)
		if err != nil {
			t.Fatal(err)
		}
	})
	t.Run("convert tool choice, unknown tool choice", func(t *testing.T) {
		tools := []*ai.ToolDefinition{tool}
		tc, err := convertToolChoice("customChoice", tools)
		if err == nil {
			t.Fatal("expecting an error, got nil")
		}
		if tc != nil {
			t.Fatalf("expecting empty tool config, got: %#v", tc)
		}
	})
}
