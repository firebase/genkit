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
	"github.com/firebase/genkit/go/genkit"
)

func TestToMCPTool(t *testing.T) {
	ctx := context.Background()
	g := genkit.Init(ctx)
	server := &GenkitMCPServer{genkit: g}

	// Use genkit.DefineTool to create a real tool
	genkitTool := genkit.DefineTool(g, "gablorken", "calculates a gablorken",
		func(ctx *ai.ToolContext, input struct {
			Value int
			Over  float64
		},
		) (float64, error) {
			return 0, nil
		},
	)

	got := server.toMCPTool(genkitTool)

	if got.Name != "gablorken" {
		t.Errorf("mcpTool.Name got = %q, want %q", got.Name, "gablorken")
	}
	if got.Description != "calculates a gablorken" {
		t.Errorf("mcpTool.Description got = %q, want %q", got.Description, "calculates a gablorken")
	}
	if got.InputSchema == nil {
		t.Fatal("mcpTool.InputSchema is nil")
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
