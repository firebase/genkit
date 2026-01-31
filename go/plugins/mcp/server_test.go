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
	"context"
	"testing"

	"github.com/firebase/genkit/go/ai"
)

// mockTool implements ai.Tool for testing
type mockTool struct {
	ai.Tool
	name string
	desc string
}

func (m *mockTool) Name() string { return m.name }
func (m *mockTool) Definition() *ai.ToolDefinition {
	return &ai.ToolDefinition{
		Name:        m.name,
		Description: m.desc,
		InputSchema: map[string]any{"type": "object"},
	}
}

func TestToMCPTool(t *testing.T) {
	server := &GenkitMCPServer{}
	
	mt := &mockTool{name: "test_tool", desc: "test desc"}
	got := server.toMCPTool(mt)

	if got.Name != "test_tool" {
		t.Errorf("mcpTool.Name got = %q, want %q", got.Name, "test_tool")
	}
	if got.Description != "test desc" {
		t.Errorf("mcpTool.Description got = %q, want %q", got.Description, "test desc")
	}
}

func TestNewMCPServer(t *testing.T) {
	ctx := context.Background()
	// Basic check that constructor sets up version
	s := NewMCPServer(nil, MCPServerOptions{Name: "test-server"})
	
	if got := s.options.Version; got != "1.0.0" {
		t.Errorf("default version got = %q, want %q", got, "1.0.0")
	}
    _ = ctx
}
