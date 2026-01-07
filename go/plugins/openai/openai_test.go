// Copyright 2026 Google LLC
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

package openai

import (
	"encoding/json"
	"reflect"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/openai/openai-go/v3"
)

func TestToOpenAISystemMessage(t *testing.T) {
	tests := []struct {
		name string
		msg  *ai.Message
		want string
	}{
		{
			name: "basic system message",
			msg: &ai.Message{
				Role:    ai.RoleSystem,
				Content: []*ai.Part{ai.NewTextPart("system instruction")},
			},
			want: "system instruction",
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			gotUnion := toOpenAISystemMessage(tc.msg)

			if gotUnion.OfSystem == nil {
				t.Fatalf("toOpenAISystemMessage() returned union with nil OfSystem")
			}
			val := gotUnion.OfSystem.Content.OfString.Value
			if val != tc.want {
				t.Errorf("toOpenAISystemMessage() content = %q, want %q", val, tc.want)
			}
		})
	}
}

func TestToOpenAIModelMessage(t *testing.T) {
	tests := []struct {
		name      string
		msg       *ai.Message
		checkFunc func(*testing.T, openai.ChatCompletionMessageParamUnion)
	}{
		{
			name: "text message",
			msg: &ai.Message{
				Role:    ai.RoleModel,
				Content: []*ai.Part{ai.NewTextPart("model response")},
			},
			checkFunc: func(t *testing.T, gotUnion openai.ChatCompletionMessageParamUnion) {
				if gotUnion.OfAssistant == nil {
					t.Fatalf("expected OfAssistant to be non-nil")
				}
				parts := gotUnion.OfAssistant.Content.OfArrayOfContentParts
				if len(parts) != 1 {
					t.Fatalf("got %d content parts, want 1", len(parts))
				}
				textPart := parts[0].OfText
				if got, want := textPart.Text, "model response"; got != want {
					t.Errorf("content = %q, want %q", got, want)
				}
			},
		},
		{
			name: "tool call message",
			msg: &ai.Message{
				Role: ai.RoleModel,
				Content: []*ai.Part{
					ai.NewToolRequestPart(&ai.ToolRequest{
						Name:  "myTool",
						Ref:   "call_123",
						Input: map[string]any{"arg": "value"},
					}),
				},
			},
			checkFunc: func(t *testing.T, gotUnion openai.ChatCompletionMessageParamUnion) {
				if gotUnion.OfAssistant == nil {
					t.Fatalf("expected OfAssistant to be non-nil")
				}
				toolCalls := gotUnion.OfAssistant.ToolCalls
				if len(toolCalls) != 1 {
					t.Fatalf("got %d tool calls, want 1", len(toolCalls))
				}

				if toolCalls[0].OfFunction == nil {
					t.Fatalf("expected Function tool call")
				}
				fnCall := toolCalls[0].OfFunction

				if got, want := fnCall.ID, "call_123"; got != want {
					t.Errorf("tool call ID = %q, want %q", got, want)
				}
				if got, want := fnCall.Function.Name, "myTool"; got != want {
					t.Errorf("function name = %q, want %q", got, want)
				}

				var gotArgs map[string]any
				if err := json.Unmarshal([]byte(fnCall.Function.Arguments), &gotArgs); err != nil {
					t.Fatalf("failed to unmarshal arguments: %v", err)
				}
				wantArgs := map[string]any{"arg": "value"}
				if !reflect.DeepEqual(gotArgs, wantArgs) {
					t.Errorf("arguments = %v, want %v", gotArgs, wantArgs)
				}
			},
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			got, err := toOpenAIModelMessage(tc.msg)
			if err != nil {
				t.Fatalf("toOpenAIModelMessage() unexpected error: %v", err)
			}
			tc.checkFunc(t, got)
		})
	}
}

func TestToOpenAIUserMessage(t *testing.T) {
	tests := []struct {
		name      string
		msg       *ai.Message
		checkFunc func(*testing.T, openai.ChatCompletionMessageParamUnion)
	}{
		{
			name: "text message",
			msg: &ai.Message{
				Role:    ai.RoleUser,
				Content: []*ai.Part{ai.NewTextPart("user query")},
			},
			checkFunc: func(t *testing.T, gotUnion openai.ChatCompletionMessageParamUnion) {
				if gotUnion.OfUser == nil {
					t.Fatalf("expected OfUser to be non-nil")
				}
				parts := gotUnion.OfUser.Content.OfArrayOfContentParts
				if len(parts) != 1 {
					t.Fatalf("got %d content parts, want 1", len(parts))
				}
				textPart := parts[0].OfText
				if textPart == nil {
					t.Fatalf("expected Text content part")
				}
				if got, want := textPart.Text, "user query"; got != want {
					t.Errorf("content = %q, want %q", got, want)
				}
			},
		},
		{
			name: "image message",
			msg: &ai.Message{
				Role: ai.RoleUser,
				Content: []*ai.Part{
					ai.NewMediaPart("image/png", "http://example.com/image.png"),
				},
			},
			checkFunc: func(t *testing.T, gotUnion openai.ChatCompletionMessageParamUnion) {
				if gotUnion.OfUser == nil {
					t.Fatalf("expected OfUser to be non-nil")
				}
				parts := gotUnion.OfUser.Content.OfArrayOfContentParts
				if len(parts) != 1 {
					t.Fatalf("got %d content parts, want 1", len(parts))
				}
				imagePart := parts[0].OfImageURL
				if imagePart == nil {
					t.Fatalf("expected Image content part")
				}
				if got, want := imagePart.ImageURL.URL, "http://example.com/image.png"; got != want {
					t.Errorf("image URL = %q, want %q", got, want)
				}
			},
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			got, err := toOpenAIUserMessage(tc.msg)
			if err != nil {
				t.Fatalf("toOpenAIUserMessage() unexpected error: %v", err)
			}
			tc.checkFunc(t, got)
		})
	}
}

func TestToOpenAIToolMessages(t *testing.T) {
	tests := []struct {
		name      string
		msg       *ai.Message
		checkFunc func(*testing.T, []openai.ChatCompletionMessageParamUnion)
	}{
		{
			name: "tool response",
			msg: &ai.Message{
				Role: ai.RoleTool,
				Content: []*ai.Part{
					ai.NewToolResponsePart(&ai.ToolResponse{
						Name:   "myTool",
						Ref:    "call_123",
						Output: map[string]any{"result": "success"},
					}),
				},
			},
			checkFunc: func(t *testing.T, gotMsgs []openai.ChatCompletionMessageParamUnion) {
				if len(gotMsgs) != 1 {
					t.Fatalf("got %d messages, want 1", len(gotMsgs))
				}
				if gotMsgs[0].OfTool == nil {
					t.Fatalf("expected OfTool to be non-nil")
				}
				toolMsg := gotMsgs[0].OfTool
				if got, want := toolMsg.ToolCallID, "call_123"; got != want {
					t.Errorf("tool call ID = %q, want %q", got, want)
				}

				// Content is Union. Expecting OfString.
				content := toolMsg.Content.OfString.Value

				var gotOutput map[string]any
				if err := json.Unmarshal([]byte(content), &gotOutput); err != nil {
					t.Fatalf("failed to unmarshal output: %v", err)
				}
				wantOutput := map[string]any{"result": "success"}
				if !reflect.DeepEqual(gotOutput, wantOutput) {
					t.Errorf("output = %v, want %v", gotOutput, wantOutput)
				}
			},
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			got, err := toOpenAIToolMessages(tc.msg)
			if err != nil {
				t.Fatalf("toOpenAIToolMessages() unexpected error: %v", err)
			}
			tc.checkFunc(t, got)
		})
	}
}
