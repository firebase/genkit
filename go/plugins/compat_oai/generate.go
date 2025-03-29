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

func (g *ModelGenerator) GetRequestConfig() any {
	return g.request
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
func (g *ModelGenerator) WithConfig(config any) (*ModelGenerator, error) {
	if config == nil {
		return g, nil
	}

	// Handle only the supported config types with a type switch
	switch cfg := config.(type) {
	case *openai.ChatCompletionNewParams:
		// Handle OpenAI-specific config
		if cfg != nil {
			// Copy all non-nil fields directly from the OpenAI config
			srcVal := reflect.ValueOf(cfg).Elem()
			dstVal := reflect.ValueOf(g.request).Elem()

			for i := 0; i < srcVal.NumField(); i++ {
				field := srcVal.Field(i)
				if field.Kind() == reflect.Pointer && !field.IsNil() {
					dstVal.Field(i).Set(field)
				} else if field.Kind() != reflect.Pointer && !field.IsZero() {
					// For scalar fields, only copy non-zero values
					dstVal.Field(i).Set(field)
				}
			}
		}
	case *ai.GenerationCommonConfig:
		// Handle common config by mapping specific fields
		if cfg != nil {
			// Map fields explicitly from common config to OpenAI config
			if cfg.MaxOutputTokens != 0 {
				g.request.MaxTokens = openai.F(int64(cfg.MaxOutputTokens))
			}
			if len(cfg.StopSequences) > 0 {
				g.request.Stop = openai.F[openai.ChatCompletionNewParamsStopUnion](
					openai.ChatCompletionNewParamsStopArray(cfg.StopSequences))
			}
			if cfg.Temperature != 0 {
				g.request.Temperature = openai.F(cfg.Temperature)
			}
			if cfg.TopP != 0 {
				g.request.TopP = openai.F(cfg.TopP)
			}
		}
	default:
		// Provide detailed error message for unsupported types
		configType := reflect.TypeOf(config)
		if configType == nil {
			return g, fmt.Errorf("invalid nil config of unknown type")
		}

		// Check if it's a pointer to a struct
		if configType.Kind() != reflect.Pointer {
			return g, fmt.Errorf("config must be a pointer, got %s", configType.Kind())
		}

		// If it's a nil pointer, give specific error
		if reflect.ValueOf(config).IsNil() {
			return g, fmt.Errorf("config is a nil %s pointer", configType.Elem().Name())
		}

		// Give helpful message about what types are supported
		return g, fmt.Errorf("unsupported config type: %T\n\nSupported types:\n- *openai.ChatCompletionNewParams\n- *ai.GenerationCommonConfig", config)
	}

	return g, nil
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
