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
	"fmt"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

func (c *GenkitMCPClient) GetActivePrompts(ctx context.Context) ([]mcp.Prompt, error) {
	if !c.IsEnabled() || c.server == nil || c.server.Session == nil {
		return nil, nil
	}
	if c.server.Error != nil {
		return nil, c.server.Error
	}

	var prompts []mcp.Prompt
	for p, err := range c.server.Session.Prompts(ctx, nil) {
		if err != nil {
			return nil, fmt.Errorf("failed to list prompts: %w", err)
		}
		prompts = append(prompts, *p)
	}

	return prompts, nil
}

func (c *GenkitMCPClient) GetPrompt(ctx context.Context, g *genkit.Genkit, name string, args map[string]string) (ai.Prompt, error) {
	if !c.IsEnabled() || c.server == nil || c.server.Session == nil {
		return nil, fmt.Errorf("MCP client is disabled or not connected")
	}

	promptName := fmt.Sprintf("%s_%s", c.options.Name, name)
	if prompt := genkit.LookupPrompt(g, promptName); prompt != nil {
		return prompt, nil
	}

	res, err := c.server.Session.GetPrompt(ctx, &mcp.GetPromptParams{
		Name:      name,
		Arguments: args,
	})
	if err != nil {
		return nil, fmt.Errorf("failed to get prompt %s: %w", name, err)
	}

	msgs := c.toGenkitMessages(res.Messages)
	prompt := genkit.DefinePrompt(g, promptName,
		ai.WithDescription(res.Description),
		ai.WithMessages(msgs...),
	)

	return prompt, nil
}

func (c *GenkitMCPClient) toGenkitMessages(mcpMessages []*mcp.PromptMessage) []*ai.Message {
	var messages []*ai.Message

	for _, msg := range mcpMessages {
		role := ai.RoleUser
		// "assistant" as per the MCP spec
		if msg.Role == "assistant" {
			role = ai.RoleModel
		}

		text := ExtractTextFromContent(msg.Content)
		if text == "" {
			continue
		}
		messages = append(messages, &ai.Message{
			Role:    role,
			Content: []*ai.Part{ai.NewTextPart(text)},
		})
	}

	return messages
}
