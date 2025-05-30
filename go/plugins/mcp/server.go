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
	"encoding/json"
	"fmt"
	"log/slog"
	"strings"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/internal/atype"
	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
)

// MCPServerOptions holds configuration for creating an MCP server
type MCPServerOptions struct {
	// Name is the server name advertised to MCP clients
	Name string
	// Version is the server version (defaults to "1.0.0" if empty)
	Version string
	// Tools is an optional list of specific tools to expose.
	// If provided, only these tools will be exposed (no auto-discovery).
	// If nil or empty, all tools will be auto-discovered from the registry.
	Tools []ai.Tool
}

// GenkitMCPServer represents an MCP server that exposes Genkit tools
type GenkitMCPServer struct {
	genkit    *genkit.Genkit
	options   MCPServerOptions
	mcpServer *server.MCPServer

	// Tools discovered from Genkit registry or explicitly specified
	tools map[string]ai.Tool
}

// NewMCPServer creates a new MCP server instance that can expose Genkit tools
func NewMCPServer(g *genkit.Genkit, options MCPServerOptions) *GenkitMCPServer {
	if options.Version == "" {
		options.Version = "1.0.0"
	}

	s := &GenkitMCPServer{
		genkit:  g,
		options: options,
		tools:   make(map[string]ai.Tool),
	}

	// Discover or load tools based on options
	if len(options.Tools) > 0 {
		s.loadExplicitTools()
	} else {
		s.discoverTools()
	}

	return s
}

// loadExplicitTools loads only the specified tools
func (s *GenkitMCPServer) loadExplicitTools() {
	var loadedCount int
	for _, tool := range s.options.Tools {
		if tool != nil {
			s.tools[tool.Name()] = tool
			loadedCount++
			slog.Debug("MCP Server: Loaded explicit tool", "name", tool.Name())
		} else {
			slog.Warn("MCP Server: Nil tool in explicit tools list")
		}
	}
	slog.Info("MCP Server: Explicit tool loading complete", "loaded", loadedCount, "requested", len(s.options.Tools))
}

// discoverTools discovers all tools from the Genkit registry
func (s *GenkitMCPServer) discoverTools() {
	// Get all actions from the registry
	allActions := s.genkit.Registry().ListActions()

	var discoveredCount int
	for _, actionDesc := range allActions {
		// Filter for tool actions (key format: "/tool/{name}")
		if strings.HasPrefix(actionDesc.Key, "/"+string(atype.Tool)+"/") {
			// Extract tool name from key
			toolName := strings.TrimPrefix(actionDesc.Key, "/"+string(atype.Tool)+"/")

			// Lookup the actual tool
			tool := genkit.LookupTool(s.genkit, toolName)
			if tool != nil {
				s.tools[toolName] = tool
				discoveredCount++
				slog.Debug("MCP Server: Discovered tool", "name", toolName)
			}
		}
	}

	slog.Info("MCP Server: Tool discovery complete", "discovered", discoveredCount)
}

// setup initializes the MCP server
func (s *GenkitMCPServer) setup() error {
	// Create MCP server with tool capabilities
	s.mcpServer = server.NewMCPServer(
		s.options.Name,
		s.options.Version,
		server.WithToolCapabilities(true),
	)

	// Register all discovered tools with the MCP server
	for toolName, tool := range s.tools {
		if err := s.addToolToMCPServer(toolName, tool); err != nil {
			return fmt.Errorf("failed to add tool %q to MCP server: %w", toolName, err)
		}
	}

	slog.Info("MCP Server setup complete", "name", s.options.Name, "tools", len(s.tools))
	return nil
}

// addToolToMCPServer converts a Genkit tool to MCP format and registers it
func (s *GenkitMCPServer) addToolToMCPServer(toolName string, tool ai.Tool) error {
	// Convert Genkit tool to MCP tool format
	mcpTool, err := s.convertGenkitToolToMCP(tool)
	if err != nil {
		return fmt.Errorf("failed to convert Genkit tool to MCP format: %w", err)
	}

	// Create tool handler function
	toolHandler := s.createToolHandler(tool)

	// Add tool to MCP server
	s.mcpServer.AddTool(mcpTool, toolHandler)
	return nil
}

// convertGenkitToolToMCP converts a Genkit tool definition to MCP tool format
func (s *GenkitMCPServer) convertGenkitToolToMCP(tool ai.Tool) (mcp.Tool, error) {
	def := tool.Definition()

	// Create basic MCP tool
	mcpTool := mcp.NewTool(def.Name, mcp.WithDescription(def.Description))

	// Convert input schema if available
	if def.InputSchema != nil {
		schemaBytes, err := json.Marshal(def.InputSchema)
		if err != nil {
			return mcpTool, fmt.Errorf("failed to marshal input schema: %w", err)
		}
		mcpTool = mcp.NewToolWithRawSchema(def.Name, def.Description, schemaBytes)
	}

	return mcpTool, nil
}

// createToolHandler creates an MCP tool handler function for a Genkit tool
func (s *GenkitMCPServer) createToolHandler(tool ai.Tool) func(context.Context, mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	return func(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		// Log the tool call
		slog.Debug("MCP Server: Tool called", "name", request.Params.Name, "args", request.Params.Arguments)

		// Execute the Genkit tool
		result, err := tool.RunRaw(ctx, request.Params.Arguments)
		if err != nil {
			slog.Error("MCP Server: Tool execution failed", "name", request.Params.Name, "error", err)
			return mcp.NewToolResultError(err.Error()), nil
		}

		// Convert result to MCP format
		return s.convertResultToMCP(result), nil
	}
}

// convertResultToMCP converts a Genkit tool result to MCP format
func (s *GenkitMCPServer) convertResultToMCP(result any) *mcp.CallToolResult {
	switch v := result.(type) {
	case string:
		return mcp.NewToolResultText(v)
	case nil:
		return mcp.NewToolResultText("")
	default:
		// Convert complex types to JSON
		jsonBytes, err := json.Marshal(v)
		if err != nil {
			return mcp.NewToolResultError(fmt.Sprintf("Failed to marshal result: %v", err))
		}
		return mcp.NewToolResultText(string(jsonBytes))
	}
}

// ServeStdio starts the MCP server with stdio transport (primary MCP transport)
func (s *GenkitMCPServer) ServeStdio(ctx context.Context) error {
	if err := s.setup(); err != nil {
		return fmt.Errorf("failed to setup MCP server: %w", err)
	}

	slog.Info("MCP Server starting with stdio transport", "name", s.options.Name, "tools", len(s.tools))
	return server.ServeStdio(s.mcpServer)
}

// ServeSSE starts the MCP server with SSE transport (for web clients)
func (s *GenkitMCPServer) ServeSSE(ctx context.Context, addr string) error {
	if err := s.setup(); err != nil {
		return fmt.Errorf("failed to setup MCP server: %w", err)
	}

	slog.Info("MCP Server starting with SSE transport", "name", s.options.Name, "addr", addr, "tools", len(s.tools))
	sseServer := server.NewSSEServer(s.mcpServer)
	return sseServer.Start(addr)
}

// Stop gracefully stops the MCP server
func (s *GenkitMCPServer) Stop() error {
	// The mcp-go server handles cleanup internally
	return nil
}

// ListRegisteredTools returns the names of all discovered tools
func (s *GenkitMCPServer) ListRegisteredTools() []string {
	var toolNames []string
	for name := range s.tools {
		toolNames = append(toolNames, name)
	}
	return toolNames
}
