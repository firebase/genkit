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

package compat_oai

import (
	"context"
	"fmt"
	"reflect"

	"github.com/firebase/genkit/go/ai"
	"github.com/openai/openai-go"
)

// ModelGenerator handles OpenAI generation requests
type ModelGenerator struct {
	client    *openai.Client
	modelName string
	request   *openai.ChatCompletionNewParams
}

// NewModelGenerator creates a new ModelGenerator instance
func NewModelGenerator(client *openai.Client, modelName string) *ModelGenerator {
	return &ModelGenerator{
		client:    client,
		modelName: modelName,
		request: &openai.ChatCompletionNewParams{
			Model: openai.F(modelName),
		},
	}
}

// WithMessages adds messages to the request
func (g *ModelGenerator) WithMessages(messages []*ai.Message) *ModelGenerator {
	oaiMessages := make([]openai.ChatCompletionMessageParamUnion, 0, len(messages))
	for _, msg := range messages {
		content := g.concatenateContent(msg.Content)
		switch msg.Role {
		case ai.RoleSystem:
			oaiMessages = append(oaiMessages, openai.SystemMessage(content))
		case ai.RoleModel:
			oaiMessages = append(oaiMessages, openai.AssistantMessage(content))
		case ai.RoleTool:
			oaiMessages = append(oaiMessages, openai.ToolMessage("", content)) // TODO: Add tool ID if needed
		default:
			oaiMessages = append(oaiMessages, openai.UserMessage(content))
		}
	}
	g.request.Messages = openai.F(oaiMessages)
	return g
}

// WithConfig adds configuration parameters from the model request
func (g *ModelGenerator) WithConfig(config any) *ModelGenerator {
	if config == nil {
		return g
	}

	// Copy all fields from config to g.request
	cfgVal := reflect.ValueOf(config).Elem()
	reqVal := reflect.ValueOf(g.request).Elem()

	for i := 0; i < cfgVal.NumField(); i++ {
		field := cfgVal.Field(i)

		// Handle different field types appropriately
		if field.Kind() == reflect.Ptr {
			if !field.IsNil() {
				reqVal.Field(i).Set(field)
			}
		} else {
			// Special handling for non-pointer types

			// For booleans, we always copy the value whether true or false
			if field.Kind() == reflect.Bool {
				reqVal.Field(i).Set(field)
			} else if !field.IsZero() {
				// For other non-pointer types, only copy non-zero values
				reqVal.Field(i).Set(field)
			}
		}
	}

	return g
}

// WithTools adds tools to the request
func (g *ModelGenerator) WithTools(tools []ai.Tool, choice ai.ToolChoice) *ModelGenerator {
	// TODO: Implement tools from model request
	// see vertex ai recent pr here for reference: https://github.com/firebase/genkit/pull/2259
	return g
}

// Generate executes the generation request
func (g *ModelGenerator) Generate(ctx context.Context, handleChunk func(context.Context, *ai.ModelResponseChunk) error) (*ai.ModelResponse, error) {
	if handleChunk != nil {
		return g.generateStream(ctx, handleChunk)
	}
	return g.generateComplete(ctx)
}

// concatenateContent concatenates text content into a single string
func (g *ModelGenerator) concatenateContent(parts []*ai.Part) string {
	content := ""
	for _, part := range parts {
		content += part.Text
	}
	return content
}

// generateStream generates a streaming model response
func (g *ModelGenerator) generateStream(ctx context.Context, handleChunk func(context.Context, *ai.ModelResponseChunk) error) (*ai.ModelResponse, error) {
	stream := g.client.Chat.Completions.NewStreaming(ctx, *g.request)
	defer stream.Close()

	var fullResponse ai.ModelResponse
	fullResponse.Message = &ai.Message{
		Role:    ai.RoleModel,
		Content: make([]*ai.Part, 0),
	}

	// Initialize request and usage
	fullResponse.Request = &ai.ModelRequest{}
	fullResponse.Usage = &ai.GenerationUsage{
		InputTokens:  0,
		OutputTokens: 0,
		TotalTokens:  0,
	}

	for stream.Next() {
		chunk := stream.Current()
		if len(chunk.Choices) > 0 {
			content := chunk.Choices[0].Delta.Content
			modelChunk := &ai.ModelResponseChunk{
				Content: []*ai.Part{ai.NewTextPart(content)},
			}

			if err := handleChunk(ctx, modelChunk); err != nil {
				return nil, fmt.Errorf("callback error: %w", err)
			}

			fullResponse.Message.Content = append(fullResponse.Message.Content, modelChunk.Content...)

			// Update Usage
			fullResponse.Usage.InputTokens += int(chunk.Usage.PromptTokens)
			fullResponse.Usage.OutputTokens += int(chunk.Usage.CompletionTokens)
			fullResponse.Usage.TotalTokens += int(chunk.Usage.TotalTokens)
		}
	}

	if err := stream.Err(); err != nil {
		return nil, fmt.Errorf("stream error: %w", err)
	}

	return &fullResponse, nil
}

// generateComplete generates a complete model response
func (g *ModelGenerator) generateComplete(ctx context.Context) (*ai.ModelResponse, error) {
	completion, err := g.client.Chat.Completions.New(ctx, *g.request)
	if err != nil {
		return nil, fmt.Errorf("failed to create completion: %w", err)
	}

	return &ai.ModelResponse{
		Message: &ai.Message{
			Role: ai.RoleModel,
			Content: []*ai.Part{
				ai.NewTextPart(completion.Choices[0].Message.Content),
			},
		},
		FinishReason: ai.FinishReason("stop"),
		Request:      &ai.ModelRequest{},
		Usage: &ai.GenerationUsage{
			InputTokens:  int(completion.Usage.PromptTokens),
			OutputTokens: int(completion.Usage.CompletionTokens),
			TotalTokens:  int(completion.Usage.TotalTokens),
		},
	}, nil
}
