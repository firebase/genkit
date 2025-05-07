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
	"encoding/json"
	"fmt"

	"github.com/firebase/genkit/go/ai"
	"github.com/openai/openai-go"
	"github.com/openai/openai-go/shared"
)

// mapToStruct unmarshals a map[string]any to the expected config type.
func mapToStruct(m map[string]any, v any) error {
	jsonData, err := json.Marshal(m)
	if err != nil {
		return err
	}
	return json.Unmarshal(jsonData, v)
}

// ModelGenerator handles OpenAI generation requests
type ModelGenerator struct {
	client    *openai.Client
	modelName string
	request   *openai.ChatCompletionNewParams
	// Store any errors that occur during building
	err error
}

func (g *ModelGenerator) GetRequest() *openai.ChatCompletionNewParams {
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
	// Return early if we already have an error
	if g.err != nil {
		return g
	}

	if messages == nil {
		return g
	}

	oaiMessages := make([]openai.ChatCompletionMessageParamUnion, 0, len(messages))
	for _, msg := range messages {
		content := g.concatenateContent(msg.Content)
		switch msg.Role {
		case ai.RoleSystem:
			oaiMessages = append(oaiMessages, openai.SystemMessage(content))
		case ai.RoleModel:
			oaiMessages = append(oaiMessages, openai.AssistantMessage(content))

			am := openai.ChatCompletionAssistantMessageParam{
				Role: openai.F(openai.ChatCompletionAssistantMessageParamRoleAssistant),
			}
			if msg.Content[0].Text != "" {
				am.Content = openai.F([]openai.ChatCompletionAssistantMessageParamContentUnion{
					openai.TextPart(msg.Content[0].Text),
				})
			}
			toolCalls := convertToolCalls(msg.Content)
			if len(toolCalls) > 0 {
				am.ToolCalls = openai.F(toolCalls)
			}
			oaiMessages = append(oaiMessages, am)
		case ai.RoleTool:
			for _, p := range msg.Content {
				if !p.IsToolResponse() {
					continue
				}
				tm := openai.ToolMessage(
					// NOTE: Temporarily set its name instead of its ref (i.e. call_xxxxx) since it's not defined in the ai.ToolResponse struct.
					p.ToolResponse.Name,
					anyToJSONString(p.ToolResponse.Output),
				)
				oaiMessages = append(oaiMessages, tm)
			}
		default:
			oaiMessages = append(oaiMessages, openai.UserMessage(content))
		}
	}
	g.request.Messages = openai.F(oaiMessages)
	return g
}

// OpenaiConfig mirrors the OpenAI API configuration fields
type OpenAIConfig struct {
	// Maximum number of tokens to generate
	MaxOutputTokens int `json:"max_output_tokens,omitempty"`
	// Temperature for sampling
	Temperature float64 `json:"temperature,omitempty"`
	// Top-p value for nucleus sampling
	TopP float64 `json:"top_p,omitempty"`
	// List of sequences where the model will stop generating
	StopSequences []string `json:"stop_sequences,omitempty"`
}

// WithConfig adds configuration parameters from the model request
// see https://platform.openai.com/docs/api-reference/responses/create
// for more details on openai's request fields
func (g *ModelGenerator) WithConfig(config any) *ModelGenerator {
	// Return early if we already have an error
	if g.err != nil {
		return g
	}

	if config == nil {
		return g
	}

	var openaiConfig OpenAIConfig
	switch cfg := config.(type) {
	case OpenAIConfig:
		openaiConfig = cfg
	case *OpenAIConfig:
		openaiConfig = *cfg
	case map[string]any:
		if err := mapToStruct(cfg, &openaiConfig); err != nil {
			g.err = fmt.Errorf("failed to convert config to OpenAIConfig: %w", err)
			return g
		}
	default:
		g.err = fmt.Errorf("unexpected config type: %T", config)
		return g
	}

	// Map fields from OpenaiConfig to OpenAI request
	if openaiConfig.MaxOutputTokens != 0 {
		g.request.MaxCompletionTokens = openai.F(int64(openaiConfig.MaxOutputTokens))
	}
	if len(openaiConfig.StopSequences) > 0 {
		g.request.Stop = openai.F[openai.ChatCompletionNewParamsStopUnion](
			openai.ChatCompletionNewParamsStopArray(openaiConfig.StopSequences))
	}
	if openaiConfig.Temperature != 0 {
		g.request.Temperature = openai.F(openaiConfig.Temperature)
	}
	if openaiConfig.TopP != 0 {
		g.request.TopP = openai.F(openaiConfig.TopP)
	}

	return g
}

// WithTools adds tools to the request
func (g *ModelGenerator) WithTools(tools []*ai.ToolDefinition, choice ai.ToolChoice) *ModelGenerator {
	if g.err != nil {
		return g
	}

	if tools == nil {
		return g
	}

	toolParams := make([]openai.ChatCompletionToolParam, 0, len(tools))
	for _, tool := range tools {
		if tool == nil || tool.Name == "" {
			continue
		}

		toolParams = append(toolParams, openai.ChatCompletionToolParam{
			Type: openai.F(openai.ChatCompletionToolTypeFunction),
			Function: openai.F(shared.FunctionDefinitionParam{
				Name:        openai.F(tool.Name),
				Description: openai.F(tool.Description),
				Parameters:  openai.F(openai.FunctionParameters(tool.InputSchema)),
				Strict:      openai.F(false), // TODO: implement strict mode
			}),
		})
	}

	// Set the tools in the request
	// If no tools are provided, set it to nil
	// This is important to avoid sending an empty array in the request
	// which is not supported by some vendor APIs
	if len(toolParams) > 0 {
		g.request.Tools = openai.F(toolParams)
	}

	switch choice {
	case ai.ToolChoiceAuto:
		g.request.ToolChoice = openai.F[openai.ChatCompletionToolChoiceOptionUnionParam](openai.ChatCompletionToolChoiceOptionAutoAuto)
	case ai.ToolChoiceRequired:
		g.request.ToolChoice = openai.F[openai.ChatCompletionToolChoiceOptionUnionParam](openai.ChatCompletionToolChoiceOptionAutoRequired)
	case ai.ToolChoiceNone:
		g.request.ToolChoice = openai.F[openai.ChatCompletionToolChoiceOptionUnionParam](openai.ChatCompletionToolChoiceOptionAutoNone)
	}

	return g
}

// Generate executes the generation request
func (g *ModelGenerator) Generate(ctx context.Context, handleChunk func(context.Context, *ai.ModelResponseChunk) error) (*ai.ModelResponse, error) {
	// Check for any errors that occurred during building
	if g.err != nil {
		return nil, g.err
	}

	// Ensure messages are set
	if len(g.request.Messages.Value) == 0 {
		return nil, fmt.Errorf("no messages provided")
	}

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

	var currentToolCall *ai.ToolRequest
	var currentArguments string

	for stream.Next() {
		chunk := stream.Current()
		if len(chunk.Choices) > 0 {
			choice := chunk.Choices[0]

			switch choice.FinishReason {
			case openai.ChatCompletionChunkChoicesFinishReasonStop, openai.ChatCompletionChunkChoicesFinishReasonToolCalls:
				fullResponse.FinishReason = ai.FinishReasonStop
			case openai.ChatCompletionChunkChoicesFinishReasonLength:
				fullResponse.FinishReason = ai.FinishReasonLength
			case openai.ChatCompletionChunkChoicesFinishReasonContentFilter:
				fullResponse.FinishReason = ai.FinishReasonBlocked
			case openai.ChatCompletionChunkChoicesFinishReasonFunctionCall:
				fullResponse.FinishReason = ai.FinishReasonOther
			default:
				fullResponse.FinishReason = ai.FinishReasonUnknown
			}

			// handle tool calls
			for _, toolCall := range choice.Delta.ToolCalls {
				// first tool call (= current tool call is nil) contains the tool call name
				if currentToolCall == nil {
					currentToolCall = &ai.ToolRequest{
						Name: toolCall.Function.Name,
					}
				}

				if toolCall.Function.Arguments != "" {
					currentArguments += toolCall.Function.Arguments
				}
			}

			// when tool call is complete
			if choice.FinishReason == openai.ChatCompletionChunkChoicesFinishReasonToolCalls && currentToolCall != nil {
				// parse accumulated arguments string
				if currentArguments != "" {
					currentToolCall.Input = jsonStringToMap(currentArguments)
				}

				fullResponse.Message.Content = []*ai.Part{ai.NewToolRequestPart(currentToolCall)}
				return &fullResponse, nil
			}

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

	resp := &ai.ModelResponse{
		Request: &ai.ModelRequest{},
		Usage: &ai.GenerationUsage{
			InputTokens:  int(completion.Usage.PromptTokens),
			OutputTokens: int(completion.Usage.CompletionTokens),
			TotalTokens:  int(completion.Usage.TotalTokens),
		},
		Message: &ai.Message{
			Role: ai.RoleModel,
		},
	}

	choice := completion.Choices[0]

	switch choice.FinishReason {
	case openai.ChatCompletionChoicesFinishReasonStop, openai.ChatCompletionChoicesFinishReasonToolCalls:
		resp.FinishReason = ai.FinishReasonStop
	case openai.ChatCompletionChoicesFinishReasonLength:
		resp.FinishReason = ai.FinishReasonLength
	case openai.ChatCompletionChoicesFinishReasonContentFilter:
		resp.FinishReason = ai.FinishReasonBlocked
	case openai.ChatCompletionChoicesFinishReasonFunctionCall:
		resp.FinishReason = ai.FinishReasonOther
	default:
		resp.FinishReason = ai.FinishReasonUnknown
	}

	// handle tool calls
	var toolRequestParts []*ai.Part
	for _, toolCall := range choice.Message.ToolCalls {
		toolRequestParts = append(toolRequestParts, ai.NewToolRequestPart(&ai.ToolRequest{
			Name:  toolCall.Function.Name,
			Input: jsonStringToMap(toolCall.Function.Arguments),
		}))
	}
	if len(toolRequestParts) > 0 {
		resp.Message.Content = toolRequestParts
		return resp, nil
	}

	resp.Message.Content = []*ai.Part{
		ai.NewTextPart(completion.Choices[0].Message.Content),
	}
	return resp, nil
}

func convertToolCalls(content []*ai.Part) []openai.ChatCompletionMessageToolCallParam {
	var toolCalls []openai.ChatCompletionMessageToolCallParam
	for _, p := range content {
		if !p.IsToolRequest() {
			continue
		}
		toolCall := convertToolCall(p)
		toolCalls = append(toolCalls, toolCall)
	}
	return toolCalls
}

func convertToolCall(part *ai.Part) openai.ChatCompletionMessageToolCallParam {
	param := openai.ChatCompletionMessageToolCallParam{
		// NOTE: Temporarily set its name instead of its ref (i.e. call_xxxxx) since it's not defined in the ai.ToolRequest struct.
		ID:   openai.F(part.ToolRequest.Name),
		Type: openai.F(openai.ChatCompletionMessageToolCallTypeFunction),
		Function: openai.F(openai.ChatCompletionMessageToolCallFunctionParam{
			Name: openai.F(part.ToolRequest.Name),
		}),
	}

	if part.ToolRequest.Input != nil {
		param.Function.Value.Arguments = openai.F(anyToJSONString(part.ToolRequest.Input))
	}

	return param
}

func jsonStringToMap(jsonString string) map[string]any {
	var result map[string]any
	if err := json.Unmarshal([]byte(jsonString), &result); err != nil {
		panic(fmt.Errorf("unmarshal failed to parse json string %s: %w", jsonString, err))
	}
	return result
}

func anyToJSONString(data any) string {
	jsonBytes, err := json.Marshal(data)
	if err != nil {
		panic(fmt.Errorf("failed to marshal any to JSON string: data, %#v %w", data, err))
	}
	return string(jsonBytes)
}
