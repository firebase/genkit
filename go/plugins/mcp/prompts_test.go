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

package mcp

import (
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

func TestToGenkitMessages(t *testing.T) {
	client := &GenkitMCPClient{}

	mcpMessages := []*mcp.PromptMessage{
		{
			Role:    "user",
			Content: &mcp.TextContent{Text: "how are you?"},
		},
		{
			Role:    "assistant",
			Content: &mcp.TextContent{Text: "I am fine"},
		},
	}

	got := client.toGenkitMessages(mcpMessages)

	if len(got) != 2 {
		t.Fatalf("len(messages) got = %d, want 2", len(got))
	}

	// Test User Message
	if got[0].Role != ai.RoleUser {
		t.Errorf("msg[0].Role got = %v, want %v", got[0].Role, ai.RoleUser)
	}
	if got[0].Content[0].Text != "how are you?" {
		t.Errorf("msg[0].Text got = %q, want %q", got[0].Content[0].Text, "how are you?")
	}

	// Test Assistant -> Model Role Mapping
	if got[1].Role != ai.RoleModel {
		t.Errorf("msg[1].Role got = %v, want %v (RoleModel)", got[1].Role, ai.RoleModel)
	}
	if got[1].Content[0].Text != "I am fine" {
		t.Errorf("msg[1].Text got = %q, want %q", got[1].Content[0].Text, "I am fine")
	}
}
