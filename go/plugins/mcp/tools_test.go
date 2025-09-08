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

    "github.com/mark3labs/mcp-go/mcp"
)

func asMap(t *testing.T, v any, label string) map[string]any {
    t.Helper()
    m, ok := v.(map[string]any)
    if !ok {
        t.Fatalf("%s: want map[string]any, got %T", label, v)
    }
    return m
}

func eqStr(t *testing.T, got any, want string, label string) {
    t.Helper()
    s, ok := got.(string)
    if !ok || s != want {
        t.Fatalf("%s: got %v", label, got)
    }
}

func eqNum(t *testing.T, got any, want int, label string) {
    t.Helper()
    f, ok := got.(float64)
    if !ok || int(f) != want {
        t.Fatalf("%s: got %v", label, got)
    }
}

func reqContains(t *testing.T, v any, want string) {
    t.Helper()
    switch arr := v.(type) {
    case []any:
        for _, x := range arr {
            if s, ok := x.(string); ok && s == want {
                return
            }
        }
    case []string:
        for _, s := range arr {
            if s == want {
                return
            }
        }
    default:
        t.Fatalf("required: unexpected type %T", v)
    }
    t.Fatalf("required does not contain %q: %v", want, v)
}

// TestCreateTool tests the createTool function.
func TestCreateTool(t *testing.T) {
    client := &GenkitMCPClient{options: MCPClientOptions{Name: "srv"}}

    m := mcp.Tool{
        Name:        "echo",
        Description: "Echo",
        InputSchema: mcp.JSONSchema{
            Type:        "object",
            Required:    []string{"q"},
            Description: "Echo input",
            Properties: map[string]mcp.JSONSchema{
                "q": {
                    Type:        "string",
                    Description: "query",
                },
                "n": {
                    Type:     "number",
                    Minimum:  1,
                    Maximum:  10,
                },
                "arr": {
                    Type:     "array",
                    MinItems: 2,
                    MaxItems: 4,
                },
            },
        },
    }

    tool, err := client.createTool(m)
    if err != nil {
        t.Fatalf("createTool error: %v", err)
    }

	// Validate that the tool is namespaced
    def := tool.Definition()
    if def.Name != "srv_echo" {
        t.Fatalf("namespacing failed: got %q", def.Name)
    }
    if def.Description != "Echo" {
        t.Fatalf("description mismatch: %q", def.Description)
    }
    if def.InputSchema == nil {
        t.Fatalf("input schema missing")
    }

	// Validate that the schema is propagated correctly.
    eqStr(t, def.InputSchema["type"], "object", "schema.type")
    eqStr(t, def.InputSchema["description"], "Echo input", "schema.description")
    props := asMap(t, def.InputSchema["properties"], "schema.properties")

    q := asMap(t, props["q"], "properties.q")
    eqStr(t, q["type"], "string", "q.type")
    eqStr(t, q["description"], "query", "q.description")

    n := asMap(t, props["n"], "properties.n")
    eqStr(t, n["type"], "number", "n.type")
    eqNum(t, n["minimum"], 1, "n.minimum")
    eqNum(t, n["maximum"], 10, "n.maximum")

    arr := asMap(t, props["arr"], "properties.arr")
    eqStr(t, arr["type"], "array", "arr.type")
    eqNum(t, arr["minItems"], 2, "arr.minItems")
    eqNum(t, arr["maxItems"], 4, "arr.maxItems")

    reqContains(t, def.InputSchema["required"], "q")
}


// TestPrepareToolArguments tests the prepareToolArguments function.
// Ensures that required fields are validated.
func TestPrepareToolArguments(t *testing.T) {
    tool := mcp.Tool{
        Name: "echo",
        InputSchema: mcp.JSONSchema{
            Type:     "object",
            Required: []string{"q"},
        },
    }

    okArgs := map[string]any{"q": "hi"}
    got, err := prepareToolArguments(tool, okArgs)
    if err != nil {
        t.Fatalf("unexpected error for valid args: %v", err)
    }
    if got["q"] != "hi" {
        t.Fatalf("args not preserved: %v", got)
    }

    _, err = prepareToolArguments(tool, map[string]any{})
    if err == nil {
        t.Fatalf("expected error for missing required field")
    }
    _, err = prepareToolArguments(tool, nil)
    if err == nil {
        t.Fatalf("expected error for nil args with required field")
    }
}


