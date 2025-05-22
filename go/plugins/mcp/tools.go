// Package mcp provides a client for integration with the Model Context Protocol.
package mcp

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"strings"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/invopop/jsonschema"
	"github.com/mark3labs/mcp-go/mcp"
)

// GetActiveTools retrieves all tools available from the MCP server
// and returns them as Genkit ToolAction objects
func (c *GenkitMCPClient) GetActiveTools(ctx context.Context, gk *genkit.Genkit) ([]ai.Tool, error) {
	if !c.IsEnabled() || c.server == nil {
		return nil, nil
	}

	var tools []ai.Tool
	var cursor mcp.Cursor

	for {
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
			return nil, fmt.Errorf("failed to list tools: %w", err)
		}

		for _, mcpTool := range result.Tools {
			// Use namespaced tool name
			namespacedToolName := c.GetToolNameWithNamespace(mcpTool.Name)
			log.Printf("Processing MCP Tool: %s (namespaced as %s)", mcpTool.Name, namespacedToolName)

			// Check if the tool already exists in the registry
			existingTool := ai.LookupTool(gk.Registry(), namespacedToolName)
			if existingTool != nil {
				log.Printf("Found existing tool %s in registry, reusing it", namespacedToolName)
				tools = append(tools, existingTool)
				continue
			}

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

			// Capture mcpTool by value for the closure
			currentMCPTool := mcpTool
			client := c.server.Client
			rawToolResponses := c.options.RawToolResponses

			toolFunc := func(toolCtx *ai.ToolContext, args interface{}) (interface{}, error) {
				log.Printf("Executing MCP tool %q", currentMCPTool.Name)

				// Log detailed information about the arguments received
				argsJSON, _ := json.MarshalIndent(args, "", "  ")
				log.Printf("Tool %q received arguments: %s", currentMCPTool.Name, argsJSON)

				var callToolArgs map[string]interface{}
				if args != nil {
					jsonBytes, jsonErr := json.Marshal(args)
					if jsonErr != nil {
						log.Printf("ERROR: Failed to marshal args for tool %q: %v", currentMCPTool.Name, jsonErr)
						return nil, fmt.Errorf("tool arguments must be marshallable to map[string]interface{}, got %T (marshal error: %v)", args, jsonErr)
					}

					log.Printf("Tool %q arguments JSON: %s", currentMCPTool.Name, string(jsonBytes))

					if err := json.Unmarshal(jsonBytes, &callToolArgs); err != nil {
						log.Printf("ERROR: Failed to unmarshal args to map for tool %q: %v", currentMCPTool.Name, err)
						return nil, fmt.Errorf("tool arguments could not be converted to map[string]interface{} for tool %s (re-marshal/unmarshal error: %v)", currentMCPTool.Name, err)
					}
				} else {
					log.Printf("WARNING: No arguments provided for tool %q", currentMCPTool.Name)
				}

				// Check for required fields based on schema
				if currentMCPTool.InputSchema.Required != nil {
					log.Printf("Tool %q required fields: %v", currentMCPTool.Name, currentMCPTool.InputSchema.Required)
					for _, required := range currentMCPTool.InputSchema.Required {
						if _, exists := callToolArgs[required]; !exists {
							log.Printf("ERROR: Required field %q missing for tool %q", required, currentMCPTool.Name)
						}
					}
				}

				callReq := mcp.CallToolRequest{
					Params: struct {
						Name      string    `json:"name"`
						Arguments any       `json:"arguments,omitempty"`
						Meta      *mcp.Meta `json:"_meta,omitempty"`
					}{
						Name:      currentMCPTool.Name,
						Arguments: callToolArgs,
						Meta:      nil,
					},
				}

				// Log the actual request being sent
				callReqJSON, _ := json.MarshalIndent(callReq, "", "  ")
				log.Printf("Sending tool request to MCP server: %s", callReqJSON)

				mcpResult, err := client.CallTool(toolCtx, callReq)
				if err != nil {
					log.Printf("Tool %q execution failed: %v", currentMCPTool.Name, err)
					return nil, fmt.Errorf("failed to call tool %s: %w", currentMCPTool.Name, err)
				}

				// Log successful response
				resultJSON, _ := json.MarshalIndent(mcpResult, "", "  ")
				log.Printf("Tool %q execution succeeded with result: %s", currentMCPTool.Name, resultJSON)

				if rawToolResponses {
					log.Printf("Returning raw tool response for %s", currentMCPTool.Name)
					return mcpResult, nil
				}

				return ProcessToolResult(mcpResult)
			}

			// Use DefineToolWithInputSchema instead of DefineTool to properly pass the schema to the model
			tool := ai.DefineToolWithInputSchema(
				gk.Registry(),
				namespacedToolName,
				mcpTool.Description,
				inputSchemaForAI,
				toolFunc,
			)
			tools = append(tools, tool)
		}

		cursor = result.NextCursor
		if cursor == "" {
			break
		}
	}

	return tools, nil
}

// ProcessToolResult processes the result from an MCP tool call
func ProcessToolResult(result *mcp.CallToolResult) (interface{}, error) {
	if result.IsError {
		errorMsg := "tool error"
		if len(result.Content) > 0 {
			// Convert result.Content from []interface{} to []mcp.Content
			var mcpContents []mcp.Content
			for _, item := range result.Content {
				if mcpContent, ok := item.(mcp.Content); ok {
					mcpContents = append(mcpContents, mcpContent)
				}
			}
			tempMsg := ContentToText(mcpContents)
			if tempMsg != "" {
				errorMsg = tempMsg
			}
		}
		return nil, fmt.Errorf("tool error: %s", errorMsg)
	}

	isAllText := true
	if len(result.Content) == 0 {
		isAllText = false
	}
	for _, contentItem := range result.Content {
		textContent, ok := contentItem.(mcp.TextContent)
		if !ok || textContent.Type != "text" {
			isAllText = false
			break
		}
	}

	if isAllText {
		// Convert result.Content from []interface{} to []mcp.Content
		var mcpContents []mcp.Content
		for _, item := range result.Content {
			if mcpContent, ok := item.(mcp.Content); ok {
				mcpContents = append(mcpContents, mcpContent)
			}
		}
		text := ContentToText(mcpContents)
		trimmedText := strings.TrimSpace(text)
		if strings.HasPrefix(trimmedText, "{") || strings.HasPrefix(trimmedText, "[") {
			var jsonData interface{}
			if err := json.Unmarshal([]byte(trimmedText), &jsonData); err == nil {
				return jsonData, nil
			}
		}
		return text, nil
	}

	if len(result.Content) == 1 {
		contentItem := result.Content[0]
		if tc, ok := contentItem.(mcp.TextContent); ok && tc.Type == "text" {
			trimmedText := strings.TrimSpace(tc.Text)
			if strings.HasPrefix(trimmedText, "{") || strings.HasPrefix(trimmedText, "[") {
				var jsonData interface{}
				if err := json.Unmarshal([]byte(trimmedText), &jsonData); err == nil {
					return jsonData, nil
				}
			}
			return tc.Text, nil
		}
		if ec, ok := contentItem.(mcp.EmbeddedResource); ok && ec.Type == "resource" {
			if trc, ok := ec.Resource.(mcp.TextResourceContents); ok && trc.MIMEType == "application/json" {
				var jsonData interface{}
				if err := json.Unmarshal([]byte(trc.Text), &jsonData); err == nil {
					return jsonData, nil
				}
			}
		}
		return contentItem, nil
	}

	return result.Content, nil
}
