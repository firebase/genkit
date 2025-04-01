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
)

func TestConvertRequest(t *testing.T) {
	text := "hello"
	req := &ai.ModelRequest{
		Config: &ai.GenerationCommonConfig{
			MaxOutputTokens: 10,
			StopSequences:   []string{"stop"},
			Temperature:     0.4,
			TopK:            1.0,
			TopP:            1.0,
			Version:         text,
		},
		Tools: []*ai.ToolDefinition{
			{
				Description: "this is a dummy tool",
				Name:        "myTool",
			},
		},
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
}
