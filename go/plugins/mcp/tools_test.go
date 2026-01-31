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
//
// SPDX-License-Identifier: Apache-2.0

package mcp

import (
	"reflect"
	"testing"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

func TestParseInputSchema(t *testing.T) {
	client := &GenkitMCPClient{}

	t.Run("valid schema", func(t *testing.T) {
		input := map[string]any{
			"type": "object",
			"properties": map[string]any{
				"location": map[string]any{"type": "string"},
			},
		}

		got, err := client.parseInputSchema(input)
		if err != nil {
			t.Fatalf("parseInputSchema() error = %v, want nil", err)
		}

		if !reflect.DeepEqual(got, input) {
			t.Errorf("parseInputSchema() got = %v, want %v", got, input)
		}
	})

	t.Run("nil schema returns empty object", func(t *testing.T) {
		got, err := client.parseInputSchema(nil)
		if err != nil {
			t.Fatalf("parseInputSchema() error = %v, want nil", err)
		}

		want := map[string]any{"type": "object"}
		if !reflect.DeepEqual(got, want) {
			t.Errorf("parseInputSchema() got = %v, want %v", got, want)
		}
	})
}

func TestCreateTool(t *testing.T) {
	client := &GenkitMCPClient{
		options: MCPClientOptions{Name: "test-srv"},
	}

	mcpTool := &mcp.Tool{
		Name:        "get_weather",
		Description: "Fetches weather data",
		InputSchema: map[string]any{
			"type": "object",
			"properties": map[string]any{
				"city": map[string]any{"type": "string"},
			},
		},
	}

	tool, err := client.createTool(mcpTool)
	if err != nil {
		t.Fatalf("createTool() error = %v, want nil", err)
	}

	// Test Namespacing
	wantName := "test-srv_get_weather"
	if got := tool.Name(); got != wantName {
		t.Errorf("tool.Name() got = %q, want %q", got, wantName)
	}

	// Test Description
	def := tool.Definition()
	if got := def.Description; got != mcpTool.Description {
		t.Errorf("tool.Description got = %q, want %q", got, mcpTool.Description)
	}

	// Test Schema presence
	if def.InputSchema == nil {
		t.Error("tool.InputSchema is nil, want valid schema")
	}

	// Test Schema content
	gotCityType := def.InputSchema["properties"].(map[string]any)["city"].(map[string]any)["type"]
	if gotCityType != "string" {
		t.Errorf("schema city type got = %v, want %q", gotCityType, "string")
	}
}
