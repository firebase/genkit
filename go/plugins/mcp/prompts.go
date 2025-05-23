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
	"fmt"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/mark3labs/mcp-go/mcp"
)

// GetPrompt retrieves a prompt from the MCP server
func (c *GenkitMCPClient) GetPrompt(ctx context.Context, g *genkit.Genkit, promptName string, args map[string]string) (*ai.Prompt, error) {
	if !c.IsEnabled() || c.server == nil {
		return nil, fmt.Errorf("MCP client is disabled or not connected")
	}

	// Check if prompt already exists
	namespacedPromptName := c.GetPromptNameWithNamespace(promptName)
	if existingPrompt := genkit.LookupPrompt(g, namespacedPromptName); existingPrompt != nil {
		return existingPrompt, nil
	}

	// Fetch prompt from MCP server
	mcpPrompt, err := c.fetchMCPPrompt(ctx, promptName, args)
	if err != nil {
		return nil, err
	}

	// Convert and register the prompt
	return c.createGenkitPrompt(g, namespacedPromptName, mcpPrompt)
}

// fetchMCPPrompt retrieves a prompt from the MCP server
func (c *GenkitMCPClient) fetchMCPPrompt(ctx context.Context, promptName string, args map[string]string) (*mcp.GetPromptResult, error) {
	req := mcp.GetPromptRequest{
		Params: struct {
			Name      string            `json:"name"`
			Arguments map[string]string `json:"arguments,omitempty"`
		}{
			Name:      promptName,
			Arguments: args,
		},
	}

	result, err := c.server.Client.GetPrompt(ctx, req)
	if err != nil {
		return nil, fmt.Errorf("failed to get prompt %s: %w", promptName, err)
	}

	return result, nil
}

// createGenkitPrompt converts MCP prompt to Genkit prompt and registers it
func (c *GenkitMCPClient) createGenkitPrompt(g *genkit.Genkit, promptName string, mcpPrompt *mcp.GetPromptResult) (*ai.Prompt, error) {
	messages := c.convertMCPMessages(mcpPrompt.Messages)

	promptOpts := []ai.PromptOption{
		ai.WithDescription(mcpPrompt.Description),
	}

	if len(messages) > 0 {
		promptOpts = append(promptOpts, ai.WithMessages(messages...))
	}

	prompt, err := genkit.DefinePrompt(g, promptName, promptOpts...)
	if err != nil {
		return nil, fmt.Errorf("failed to define prompt %s: %w", promptName, err)
	}

	return prompt, nil
}

// convertMCPMessages converts MCP messages to Genkit messages
func (c *GenkitMCPClient) convertMCPMessages(mcpMessages []mcp.PromptMessage) []*ai.Message {
	var messages []*ai.Message

	for _, msg := range mcpMessages {
		text := ExtractTextFromContent(msg.Content)
		if text == "" {
			continue
		}

		switch msg.Role {
		case mcp.RoleUser:
			messages = append(messages, ai.NewUserTextMessage(text))
		case mcp.RoleAssistant:
			messages = append(messages, ai.NewModelTextMessage(text))
		}
	}

	return messages
}
