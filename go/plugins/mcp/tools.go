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

// Package mcp provides a client for integration with the Model Context Protocol.
package mcp

import (
	"context"
	"encoding/json"
	"fmt"
	"log"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/invopop/jsonschema"
	"github.com/mark3labs/mcp-go/client"
	"github.com/mark3labs/mcp-go/mcp"
)

// GetActiveTools retrieves all tools available from the MCP server
// and returns them as Genkit ToolAction objects
func (c *GenkitMCPClient) GetActiveTools(ctx context.Context, gk *genkit.Genkit) ([]ai.Tool, error) {
	if !c.IsEnabled() || c.server == nil {
		return nil, nil
	}

	// Get all MCP tools
	mcpTools, err := c.getTools(ctx)
	if err != nil {
		return nil, err
	}

	// Register all tools
	return c.registerTools(ctx, gk, mcpTools)
}

// registerTools registers all MCP tools with Genkit
// It returns tools that were successfully registered
func (c *GenkitMCPClient) registerTools(ctx context.Context, gk *genkit.Genkit, mcpTools []mcp.Tool) ([]ai.Tool, error) {
	var tools []ai.Tool
	for _, mcpTool := range mcpTools {
		tool, err := c.registerTool(ctx, gk, mcpTool)
		if err != nil {
			return nil, err
		}
		if tool != nil {
			tools = append(tools, tool)
		}
	}

	return tools, nil
}

// getTools retrieves all tools from the MCP server by paginating through results
func (c *GenkitMCPClient) getTools(ctx context.Context) ([]mcp.Tool, error) {
	var allMcpTools []mcp.Tool
	var cursor mcp.Cursor

	// Paginate through all available tools from the MCP server
	for {
		// Fetch a page of tools
		mcpTools, nextCursor, err := c.fetchToolsPage(ctx, cursor)
		if err != nil {
			return nil, err
		}

		allMcpTools = append(allMcpTools, mcpTools...)

		// Check if we've reached the last page
		cursor = nextCursor
		if cursor == "" {
			break
		}
	}

	return allMcpTools, nil
}

// fetchToolsPage retrieves a single page of tools from the MCP server
func (c *GenkitMCPClient) fetchToolsPage(ctx context.Context, cursor mcp.Cursor) ([]mcp.Tool, mcp.Cursor, error) {
	listReq := mcp.ListToolsRequest{
		PaginatedRequest: mcp.PaginatedRequest{
			Params: struct {
				Cursor mcp.Cursor `json:"cursor,omitempty"`
			}{
				Cursor: cursor,
			},
		},
	}

	result, err := c.server.Client.ListTools(ctx, listReq)
	if err != nil {
		return nil, "", fmt.Errorf("failed to list tools: %w", err)
	}

	return result.Tools, result.NextCursor, nil
}

// registerTool converts a single MCP tool to a Genkit tool
// Returns nil for the tool if it already exists in the registry
func (c *GenkitMCPClient) registerTool(ctx context.Context, g *genkit.Genkit, mcpTool mcp.Tool) (ai.Tool, error) {
	// Use namespaced tool name
	namespacedToolName := c.GetToolNameWithNamespace(mcpTool.Name)
	log.Printf("Processing MCP Tool: %s (namespaced as %s)", mcpTool.Name, namespacedToolName)

	// Check if the tool already exists in the registry
	existingTool := genkit.LookupTool(g, namespacedToolName)
	if existingTool != nil {
		log.Printf("Found existing tool %s in registry, reusing it", namespacedToolName)
		return existingTool, nil
	}

	// Process the tool's input schema
	inputSchemaForAI, err := c.getInputSchema(mcpTool)
	if err != nil {
		return nil, err
	}

	// Create the tool function that will handle execution
	toolFunc := c.createToolFunction(mcpTool)

	// Register the tool with Genkit
	tool := ai.DefineToolWithInputSchema(
		g.Registry(),
		namespacedToolName,
		mcpTool.Description,
		inputSchemaForAI,
		toolFunc,
	)

	return tool, nil
}

// getInputSchema exposes the MCP input schema as a jsonschema.Schema for Genkit
func (c *GenkitMCPClient) getInputSchema(mcpTool mcp.Tool) (*jsonschema.Schema, error) {
	// Log the tool's input schema
	schemaJSON, _ := json.MarshalIndent(mcpTool.InputSchema, "", "  ")
	log.Printf("Tool %s input schema: %s", mcpTool.Name, schemaJSON)

	var inputSchemaForAI *jsonschema.Schema
	if mcpTool.InputSchema.Type != "" {
		schemaBytes, err := json.Marshal(mcpTool.InputSchema)
		if err != nil {
			return nil, fmt.Errorf("failed to marshal MCP input schema for tool %s: %w", mcpTool.Name, err)
		}
		inputSchemaForAI = new(jsonschema.Schema)
		if err := json.Unmarshal(schemaBytes, inputSchemaForAI); err != nil {
			log.Printf("Warning: Failed to unmarshal MCP input schema directly for tool %s: %v. Using empty schema.", mcpTool.Name, err)
			inputSchemaForAI = &jsonschema.Schema{}
		}
	} else {
		inputSchemaForAI = &jsonschema.Schema{}
	}

	return inputSchemaForAI, nil
}

// createToolFunction creates a Genkit tool function that will execute the MCP tool
func (c *GenkitMCPClient) createToolFunction(mcpTool mcp.Tool) func(*ai.ToolContext, interface{}) (interface{}, error) {
	// Capture mcpTool by value for the closure
	currentMCPTool := mcpTool
	client := c.server.Client

	return func(toolCtx *ai.ToolContext, args interface{}) (interface{}, error) {
		log.Printf("Executing MCP tool %q", currentMCPTool.Name)

		// Convert the arguments to the format expected by MCP
		callToolArgs, err := prepareToolArguments(currentMCPTool, args)
		if err != nil {
			return nil, err
		}

		// Create and execute the MCP tool call request
		mcpResult, err := executeToolCall(toolCtx, client, currentMCPTool.Name, callToolArgs)
		if err != nil {
			log.Printf("Tool %q execution failed: %v", currentMCPTool.Name, err)
			return nil, fmt.Errorf("failed to call tool %s: %w", currentMCPTool.Name, err)
		}

		// Log successful response
		resultJSON, _ := json.MarshalIndent(mcpResult, "", "  ")
		log.Printf("Tool %q execution succeeded with result: %s", currentMCPTool.Name, resultJSON)

		log.Printf("Returning raw tool response for %s", currentMCPTool.Name)
		return mcpResult, nil
	}
}

// prepareToolArguments converts Genkit tool arguments to MCP format
// and validates required fields based on the tool's schema
func prepareToolArguments(mcpTool mcp.Tool, args interface{}) (map[string]interface{}, error) {
	// Log detailed information about the arguments received
	argsJSON, _ := json.MarshalIndent(args, "", "  ")
	log.Printf("Tool %q received arguments: %s", mcpTool.Name, argsJSON)

	var callToolArgs map[string]interface{}
	if args != nil {
		jsonBytes, jsonErr := json.Marshal(args)
		if jsonErr != nil {
			log.Printf("ERROR: Failed to marshal args for tool %q: %v", mcpTool.Name, jsonErr)
			return nil, fmt.Errorf("tool arguments must be marshallable to map[string]interface{}, got %T (marshal error: %v)", args, jsonErr)
		}

		log.Printf("Tool %q arguments JSON: %s", mcpTool.Name, string(jsonBytes))

		if err := json.Unmarshal(jsonBytes, &callToolArgs); err != nil {
			log.Printf("ERROR: Failed to unmarshal args to map for tool %q: %v", mcpTool.Name, err)
			return nil, fmt.Errorf("tool arguments could not be converted to map[string]interface{} for tool %s (re-marshal/unmarshal error: %v)", mcpTool.Name, err)
		}
	} else {
		log.Printf("WARNING: No arguments provided for tool %q", mcpTool.Name)
		callToolArgs = make(map[string]interface{})
	}

	// Check for required fields based on schema
	validateRequiredArguments(mcpTool, callToolArgs)

	return callToolArgs, nil
}

// validateRequiredArguments checks if all required arguments are present
// Logs warnings if required fields are missing
func validateRequiredArguments(mcpTool mcp.Tool, args map[string]interface{}) {
	if mcpTool.InputSchema.Required != nil {
		log.Printf("Tool %q required fields: %v", mcpTool.Name, mcpTool.InputSchema.Required)
		for _, required := range mcpTool.InputSchema.Required {
			if _, exists := args[required]; !exists {
				log.Printf("ERROR: Required field %q missing for tool %q", required, mcpTool.Name)
			}
		}
	}
}

// executeToolCall makes the actual MCP tool call
func executeToolCall(ctx context.Context, client *client.Client, toolName string, args map[string]interface{}) (*mcp.CallToolResult, error) {
	callReq := mcp.CallToolRequest{
		Params: struct {
			Name      string    `json:"name"`
			Arguments any       `json:"arguments,omitempty"`
			Meta      *mcp.Meta `json:"_meta,omitempty"`
		}{
			Name:      toolName,
			Arguments: args,
			Meta:      nil,
		},
	}

	// Log the actual request being sent
	callReqJSON, _ := json.MarshalIndent(callReq, "", "  ")
	log.Printf("Sending tool request to MCP server: %s", callReqJSON)

	return client.CallTool(ctx, callReq)
}
