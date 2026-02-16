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
	"context"
	"encoding/json"
	"fmt"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// GetActiveTools retrieves all available tools from the MCP server
func (c *GenkitMCPClient) GetActiveTools(ctx context.Context, g *genkit.Genkit) ([]ai.Tool, error) {
	if !c.IsEnabled() || c.server == nil || c.server.Session == nil {
		return nil, nil
	}
	if c.server.Error != nil {
		return nil, c.server.Error
	}

	var tools []ai.Tool
	for mt, err := range c.server.Session.Tools(ctx, nil) {
		if err != nil {
			return nil, fmt.Errorf("failed to list tools: %w", err)
		}
		tool, err := c.createTool(mt)
		if err != nil {
			return nil, err
		}
		tools = append(tools, tool)
	}
	return tools, nil
}

// parseInputSchema converts a given schema into a map[string]any
func (c *GenkitMCPClient) parseInputSchema(schema any) (map[string]any, error) {
	if schema == nil {
		return map[string]any{"type": "object"}, nil
	}

	bytes, err := json.Marshal(schema)
	if err != nil {
		return nil, err
	}

	var res map[string]any
	if err := json.Unmarshal(bytes, &res); err != nil {
		return nil, err
	}

	return res, nil
}

func (c *GenkitMCPClient) createTool(mt *mcp.Tool) (ai.Tool, error) {
	namespaceName := fmt.Sprintf("%s_%s", c.options.Name, mt.Name)

	toolFunc := c.createToolFunction(mt.Name)

	inputSchema, err := c.parseInputSchema(mt.InputSchema)
	if err != nil {
		return nil, fmt.Errorf("failed to parse schema for tool %s: %w", mt.Name, err)
	}

	return ai.NewTool(namespaceName, mt.Description, toolFunc, ai.WithInputSchema(inputSchema)), nil
}

func (c *GenkitMCPClient) createToolFunction(toolName string) func(*ai.ToolContext, any) (any, error) {
	return func(toolCtx *ai.ToolContext, args any) (any, error) {
		if c.server == nil || c.server.Session == nil {
			return nil, fmt.Errorf("MCP session is closed")
		}
		if c.server.Error != nil {
			return nil, c.server.Error
		}

		params := &mcp.CallToolParams{
			Name:      toolName,
			Arguments: args,
		}
		result, err := c.server.Session.CallTool(toolCtx.Context, params)
		if err != nil {
			return nil, fmt.Errorf("MCP tool call failed: %w", err)
		}

		if result.IsError {
			// in mcp, errors are often returned as text
			return nil, fmt.Errorf("tool execution error: %v", result.Content)
		}
		return result, nil
	}
}
