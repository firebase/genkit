// Package mcp provides a client for integration with the Model Context Protocol.
package mcp

import (
	"context"
	"fmt"
	"log"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/mark3labs/mcp-go/mcp"
)

// GetPrompt retrieves a prompt from the MCP server
func (c *GenkitMCPClient) GetPrompt(ctx context.Context, gk *genkit.Genkit, promptName string, args map[string]string) (*ai.Prompt, error) {
	if !c.IsEnabled() || c.server == nil {
		return nil, fmt.Errorf("MCP client is disabled or not connected")
	}

	log.Printf("Getting MCP prompt %s with args: %+v", promptName, args)

	// Create a request to get the prompt with arguments
	req := mcp.GetPromptRequest{
		Params: struct {
			Name      string            `json:"name"`
			Arguments map[string]string `json:"arguments,omitempty"`
		}{
			Name:      promptName,
			Arguments: args,
		},
	}

	// Get the prompt from the MCP server
	result, err := c.server.Client.GetPrompt(ctx, req)
	if err != nil {
		return nil, fmt.Errorf("failed to get prompt %s: %w", promptName, err)
	}

	// Use the namespaced name for the prompt in Genkit
	namespacedPromptName := c.GetPromptNameWithNamespace(promptName)

	// Check if the prompt already exists in the registry
	existingPrompt := ai.LookupPrompt(gk.Registry(), namespacedPromptName)
	if existingPrompt != nil {
		log.Printf("Found existing prompt %s in registry, returning it", namespacedPromptName)
		return existingPrompt, nil
	}

	// Convert MCP prompt messages to Genkit prompt messages
	var systemMessage string
	var userMessages []*ai.Message

	for _, msg := range result.Messages {
		switch msg.Role {
		case mcp.RoleUser:
			// Extract text content from the message
			text := ExtractTextFromContent(msg.Content)
			if text != "" {
				userMessages = append(userMessages, ai.NewUserTextMessage(text))
			}
		case mcp.RoleAssistant:
			// Model responses typically don't go into the prompt definition
			// but could be included in message history if needed
			text := ExtractTextFromContent(msg.Content)
			if text != "" {
				userMessages = append(userMessages, ai.NewModelTextMessage(text))
			}
		}
	}

	// Create a new prompt with the extracted content
	promptOpts := []ai.PromptOption{
		ai.WithDescription(result.Description),
	}

	// Add system message if found
	if systemMessage != "" {
		promptOpts = append(promptOpts, ai.WithSystem(systemMessage))
	}

	// Add messages if found
	if len(userMessages) > 0 {
		promptOpts = append(promptOpts, ai.WithMessages(userMessages...))
	}

	// Define the prompt
	prompt, err := ai.DefinePrompt(gk.Registry(), namespacedPromptName, promptOpts...)
	if err != nil {
		return nil, fmt.Errorf("failed to define prompt %s: %w", namespacedPromptName, err)
	}

	log.Printf("Successfully created Genkit prompt %s from MCP prompt", namespacedPromptName)
	return prompt, nil
}
