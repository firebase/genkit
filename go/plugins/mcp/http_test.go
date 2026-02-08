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

package mcp

import (
	"context"
	"encoding/json"
	"math"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

func TestHTTPServerIntegration(t *testing.T) {
	ctx := context.Background()
	g := genkit.Init(ctx)

	genkit.DefineTool(g, "gablorken", "calculates a gablorken",
		func(ctx *ai.ToolContext, input struct {
			Value int
			Over  float64
		},
		) (float64, error) {
			return math.Pow(float64(input.Value), input.Over), nil
		},
	)

	server := NewMCPServer(g, MCPServerOptions{Name: "http-server"})
	handler, err := server.HTTPHandler()
	if err != nil {
		t.Fatalf("HTTPHandler failed: %v", err)
	}

	mux := http.NewServeMux()
	mux.Handle("/mcp", handler)
	ts := httptest.NewServer(mux)
	defer ts.Close()

	client, err := NewClient(ctx, MCPClientOptions{
		Name: "remote-mcp",
		SSE: &SSEConfig{
			BaseURL: ts.URL + "/mcp",
		},
	})
	if err != nil {
		t.Fatalf("NewGenkitMCPClient failed: %v", err)
	}
	defer client.Disconnect()

	tools, err := client.GetActiveTools(ctx, g)
	if err != nil {
		t.Fatalf("GetActiveTools failed: %v", err)
	}

	var gablorken ai.Tool
	for _, tool := range tools {
		if tool.Name() == "remote-mcp_gablorken" {
			gablorken = tool
			break
		}
	}

	if gablorken == nil {
		t.Fatal("gablorken tool not found via SSE")
	}

	args := map[string]any{"Value": 2, "Over": 3.0}
	rawRes, err := gablorken.RunRaw(ctx, args)
	if err != nil {
		t.Fatalf("gablorken.RunRaw failed: %v", err)
	}
	bytes, err := json.Marshal(rawRes)
	if err != nil {
		t.Fatalf("failed to marshal result: %v", err)
	}

	var res mcp.CallToolResult
	if err := json.Unmarshal(bytes, &res); err != nil {
		t.Fatalf("failed to unmarshal into CallToolResult: %v", err)
	}
	if len(res.Content) == 0 {
		t.Fatal("expected result content, got none")
	}

	gotText := ExtractTextFromContent(res.Content[0])
	wantText := "8"
	if gotText != wantText {
		t.Errorf("result text got = %q, want %q", gotText, wantText)
	}
}
