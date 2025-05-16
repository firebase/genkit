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
//
// SPDX-License-Identifier: Apache-2.0

package ollama

import (
	"bufio"
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"slices"
	"strings"
	"sync"
	"time"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/internal/uri"
)

const provider = "ollama"

var (
	mediaSupportedModels = []string{"llava", "bakllava", "llava-llama3", "llava:13b", "llava:7b", "llava:latest"}
	toolSupportedModels  = []string{
		"qwq", "mistral-small3.1", "llama3.3", "llama3.2", "llama3.1", "mistral",
		"qwen2.5", "qwen2.5-coder", "qwen2", "mistral-nemo", "mixtral", "smollm2",
		"mistral-small", "command-r", "hermes3", "mistral-large", "command-r-plus",
		"phi4-mini", "granite3.1-dense", "granite3-dense", "granite3.2", "athene-v2",
		"nemotron-mini", "nemotron", "llama3-groq-tool-use", "aya-expanse", "granite3-moe",
		"granite3.2-vision", "granite3.1-moe", "cogito", "command-r7b", "firefunction-v2",
		"granite3.3", "command-a", "command-r7b-arabic",
	}
	roleMapping = map[ai.Role]string{
		ai.RoleUser:   "user",
		ai.RoleModel:  "assistant",
		ai.RoleSystem: "system",
		ai.RoleTool:   "tool",
	}
)

func (o *Ollama) DefineModel(g *genkit.Genkit, model ModelDefinition, info *ai.ModelInfo) ai.Model {
	o.mu.Lock()
	defer o.mu.Unlock()
	if !o.initted {
		panic("ollama.Init not called")
	}
	var mi ai.ModelInfo

	if info != nil {
		mi = *info
	} else {
		// Check if the model supports tools (must be a chat model and in the supported list)
		supportsTools := model.Type == "chat" && slices.Contains(toolSupportedModels, model.Name)
		mi = ai.ModelInfo{
			Label: model.Name,
			Supports: &ai.ModelSupports{
				Multiturn:  true,
				SystemRole: true,
				Media:      slices.Contains(mediaSupportedModels, model.Name),
				Tools:      supportsTools,
			},
			Versions: []string{},
		}
	}
	meta := &ai.ModelInfo{
		Label:    "Ollama - " + model.Name,
		Supports: mi.Supports,
		Versions: []string{},
	}
	gen := &generator{model: model, serverAddress: o.ServerAddress}
	return genkit.DefineModel(g, provider, model.Name, meta, gen.generate)
}

// IsDefinedModel reports whether a model is defined.
func IsDefinedModel(g *genkit.Genkit, name string) bool {
	return genkit.LookupModel(g, provider, name) != nil
}

// Model returns the [ai.Model] with the given name.
// It returns nil if the model was not configured.
func Model(g *genkit.Genkit, name string) ai.Model {
	return genkit.LookupModel(g, provider, name)
}

// ModelDefinition represents a model with its name and type.
type ModelDefinition struct {
	Name string
	Type string
}

type generator struct {
	model         ModelDefinition
	serverAddress string
}

type ollamaMessage struct {
	Role      string           `json:"role"`
	Content   string           `json:"content,omitempty"`
	Images    []string         `json:"images,omitempty"`
	ToolCalls []ollamaToolCall `json:"tool_calls,omitempty"`
}

// Ollama has two API endpoints, one with a chat interface and another with a generate response interface.
// That's why have multiple request interfaces for the Ollama API below.

/*
TODO: Support optional, advanced parameters:
format: the format to return a response in. Currently the only accepted value is json
options: additional model parameters listed in the documentation for the Modelfile such as temperature
system: system message to (overrides what is defined in the Modelfile)
template: the prompt template to use (overrides what is defined in the Modelfile)
context: the context parameter returned from a previous request to /generate, this can be used to keep a short conversational memory
stream: if false the response will be returned as a single response object, rather than a stream of objects
raw: if true no formatting will be applied to the prompt. You may choose to use the raw parameter if you are specifying a full templated prompt in your request to the API
keep_alive: controls how long the model will stay loaded into memory following the request (default: 5m)
*/
type ollamaChatRequest struct {
	Messages []*ollamaMessage `json:"messages"`
	Images   []string         `json:"images,omitempty"`
	Model    string           `json:"model"`
	Stream   bool             `json:"stream"`
	Format   string           `json:"format,omitempty"`
	Tools    []ollamaTool     `json:"tools,omitempty"`
}

type ollamaModelRequest struct {
	System string   `json:"system,omitempty"`
	Images []string `json:"images,omitempty"`
	Model  string   `json:"model"`
	Prompt string   `json:"prompt"`
	Stream bool     `json:"stream"`
	Format string   `json:"format,omitempty"`
}

// Tool definition from Ollama API
type ollamaTool struct {
	Type     string         `json:"type"`
	Function ollamaFunction `json:"function"`
}

// Function definition for Ollama API
type ollamaFunction struct {
	Name        string         `json:"name"`
	Description string         `json:"description"`
	Parameters  map[string]any `json:"parameters"`
}

// Tool Call from Ollama API
type ollamaToolCall struct {
	Function ollamaFunctionCall `json:"function"`
}

// Function Call for Ollama API
type ollamaFunctionCall struct {
	Name      string `json:"name"`
	Arguments any    `json:"arguments"`
}

// TODO: Add optional parameters (images, format, options, etc.) based on your use case
type ollamaChatResponse struct {
	Model     string `json:"model"`
	CreatedAt string `json:"created_at"`
	Message   struct {
		Role      string           `json:"role"`
		Content   string           `json:"content"`
		ToolCalls []ollamaToolCall `json:"tool_calls,omitempty"`
	} `json:"message"`
}

type ollamaModelResponse struct {
	Model     string `json:"model"`
	CreatedAt string `json:"created_at"`
	Response  string `json:"response"`
}

// Ollama provides configuration options for the Init function.
type Ollama struct {
	ServerAddress string // Server address of oLLama.

	mu      sync.Mutex // Mutex to control access.
	initted bool       // Whether the plugin has been initialized.
}

func (o *Ollama) Name() string {
	return provider
}

// Init initializes the plugin.
// Since Ollama models are locally hosted, the plugin doesn't initialize any default models.
// After downloading a model, call [DefineModel] to use it.
func (o *Ollama) Init(ctx context.Context, g *genkit.Genkit) (err error) {
	o.mu.Lock()
	defer o.mu.Unlock()
	if o.initted {
		panic("ollama.Init already called")
	}
	if o == nil || o.ServerAddress == "" {
		return errors.New("ollama: need ServerAddress")
	}
	o.initted = true
	return nil
}

// Generate makes a request to the Ollama API and processes the response.
func (g *generator) generate(ctx context.Context, input *ai.ModelRequest, cb func(context.Context, *ai.ModelResponseChunk) error) (*ai.ModelResponse, error) {
	stream := cb != nil
	var payload any
	isChatModel := g.model.Type == "chat"

	// Check if this is an image model
	hasMediaSupport := slices.Contains(mediaSupportedModels, g.model.Name)

	// Extract images if the model supports them
	var images []string
	var err error
	if hasMediaSupport {
		images, err = concatImages(input, []ai.Role{ai.RoleUser, ai.RoleModel})
		if err != nil {
			return nil, fmt.Errorf("failed to grab image parts: %v", err)
		}
	}

	if !isChatModel {
		payload = ollamaModelRequest{
			Model:  g.model.Name,
			Prompt: concatMessages(input, []ai.Role{ai.RoleUser, ai.RoleModel, ai.RoleTool}),
			System: concatMessages(input, []ai.Role{ai.RoleSystem}),
			Images: images,
			Stream: stream,
		}
	} else {
		var messages []*ollamaMessage
		// Translate all messages to ollama message format.
		for _, m := range input.Messages {
			message, err := convertParts(m.Role, m.Content)
			if err != nil {
				return nil, fmt.Errorf("failed to convert message parts: %v", err)
			}
			messages = append(messages, message)
		}
		chatReq := ollamaChatRequest{
			Messages: messages,
			Model:    g.model.Name,
			Stream:   stream,
			Images:   images,
		}
		if len(input.Tools) > 0 {
			tools, err := convertTools(input.Tools)
			if err != nil {
				return nil, fmt.Errorf("failed to convert tools: %v", err)
			}
			chatReq.Tools = tools
		}
		payload = chatReq
	}

	client := &http.Client{Timeout: 30 * time.Second}
	payloadBytes, err := json.Marshal(payload)
	if err != nil {
		return nil, err
	}

	// Determine the correct endpoint
	endpoint := g.serverAddress + "/api/chat"
	if !isChatModel {
		endpoint = g.serverAddress + "/api/generate"
	}

	req, err := http.NewRequest("POST", endpoint, bytes.NewReader(payloadBytes))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %v", err)
	}
	req.Header.Set("Content-Type", "application/json")
	req = req.WithContext(ctx)

	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to send request: %v", err)
	}
	defer resp.Body.Close()

	if cb == nil {
		// Existing behavior for non-streaming responses
		var err error
		body, err := io.ReadAll(resp.Body)
		if err != nil {
			return nil, fmt.Errorf("failed to read response body: %v", err)
		}
		if resp.StatusCode != http.StatusOK {
			return nil, fmt.Errorf("server returned non-200 status: %d, body: %s", resp.StatusCode, body)
		}

		var response *ai.ModelResponse
		if isChatModel {
			response, err = translateChatResponse(body)
		} else {
			response, err = translateModelResponse(body)
		}
		response.Request = input
		if err != nil {
			return nil, fmt.Errorf("failed to parse response: %v", err)
		}
		return response, nil
	} else {
		var chunks []*ai.ModelResponseChunk
		scanner := bufio.NewScanner(resp.Body)
		chunkCount := 0

		for scanner.Scan() {
			line := scanner.Text()
			chunkCount++

			var chunk *ai.ModelResponseChunk
			if isChatModel {
				chunk, err = translateChatChunk(line)
			} else {
				chunk, err = translateGenerateChunk(line)
			}
			if err != nil {
				return nil, fmt.Errorf("failed to translate chunk: %v", err)
			}
			chunks = append(chunks, chunk)
			cb(ctx, chunk)
		}

		if err := scanner.Err(); err != nil {
			return nil, fmt.Errorf("reading response stream: %v", err)
		}

		// Create a final response with the merged chunks
		finalResponse := &ai.ModelResponse{
			Request:      input,
			FinishReason: ai.FinishReason("stop"),
			Message: &ai.Message{
				Role: ai.RoleModel,
			},
		}
		// Add all the merged content to the final response's candidate
		for _, chunk := range chunks {
			finalResponse.Message.Content = append(finalResponse.Message.Content, chunk.Content...)
		}
		return finalResponse, nil // Return the final merged response

	}
}

// convertTools converts Genkit tool definitions to Ollama tool format
func convertTools(tools []*ai.ToolDefinition) ([]ollamaTool, error) {
	ollamaTools := make([]ollamaTool, 0, len(tools))
	for _, tool := range tools {
		ollamaTools = append(ollamaTools, ollamaTool{
			Type: "function",
			Function: ollamaFunction{
				Name:        tool.Name,
				Description: tool.Description,
				Parameters:  tool.InputSchema,
			},
		})
	}
	return ollamaTools, nil
}

func convertParts(role ai.Role, parts []*ai.Part) (*ollamaMessage, error) {
	message := &ollamaMessage{
		Role: roleMapping[role],
	}
	var contentBuilder strings.Builder
	var toolCalls []ollamaToolCall
	var images []string
	for _, part := range parts {
		if part.IsText() {
			contentBuilder.WriteString(part.Text)
		} else if part.IsMedia() {
			_, data, err := uri.Data(part)
			if err != nil {
				return nil, fmt.Errorf("failed to extract media data: %v", err)
			}
			base64Encoded := base64.StdEncoding.EncodeToString(data)
			images = append(images, base64Encoded)
		} else if part.IsToolRequest() {
			toolReq := part.ToolRequest
			toolCalls = append(toolCalls, ollamaToolCall{
				Function: ollamaFunctionCall{
					Name:      toolReq.Name,
					Arguments: toolReq.Input,
				},
			})
		} else if part.IsToolResponse() {
			toolResp := part.ToolResponse
			outputJSON, err := json.Marshal(toolResp.Output)
			if err != nil {
				return nil, fmt.Errorf("failed to marshal tool response: %v", err)
			}
			contentBuilder.WriteString(string(outputJSON))
		} else {
			return nil, errors.New("unsupported content type")
		}
	}

	message.Content = contentBuilder.String()
	if len(toolCalls) > 0 {
		message.ToolCalls = toolCalls
	}
	if len(images) > 0 {
		message.Images = images
	}
	return message, nil
}

// translateChatResponse translates Ollama chat response into a genkit response.
func translateChatResponse(responseData []byte) (*ai.ModelResponse, error) {
	var response ollamaChatResponse

	if err := json.Unmarshal(responseData, &response); err != nil {
		return nil, fmt.Errorf("failed to parse response JSON: %v", err)
	}
	modelResponse := &ai.ModelResponse{
		FinishReason: ai.FinishReason("stop"),
		Message: &ai.Message{
			Role: ai.RoleModel,
		},
	}
	if len(response.Message.ToolCalls) > 0 {
		for _, toolCall := range response.Message.ToolCalls {
			toolRequest := &ai.ToolRequest{
				Name:  toolCall.Function.Name,
				Input: toolCall.Function.Arguments,
			}
			toolPart := ai.NewToolRequestPart(toolRequest)
			modelResponse.Message.Content = append(modelResponse.Message.Content, toolPart)
		}
	} else if response.Message.Content != "" {
		aiPart := ai.NewTextPart(response.Message.Content)
		modelResponse.Message.Content = append(modelResponse.Message.Content, aiPart)
	}

	return modelResponse, nil
}

// translateModelResponse translates Ollama generate response into a genkit response.
func translateModelResponse(responseData []byte) (*ai.ModelResponse, error) {
	var response ollamaModelResponse

	if err := json.Unmarshal(responseData, &response); err != nil {
		return nil, fmt.Errorf("failed to parse response JSON: %v", err)
	}

	modelResponse := &ai.ModelResponse{
		FinishReason: ai.FinishReason("stop"),
		Message: &ai.Message{
			Role: ai.RoleModel,
		},
	}

	aiPart := ai.NewTextPart(response.Response)
	modelResponse.Message.Content = append(modelResponse.Message.Content, aiPart)
	modelResponse.Usage = &ai.GenerationUsage{} // TODO: can we get any of this info?
	return modelResponse, nil
}

func translateChatChunk(input string) (*ai.ModelResponseChunk, error) {
	var response ollamaChatResponse

	if err := json.Unmarshal([]byte(input), &response); err != nil {
		return nil, fmt.Errorf("failed to parse response JSON: %v", err)
	}
	chunk := &ai.ModelResponseChunk{}
	if len(response.Message.ToolCalls) > 0 {
		for _, toolCall := range response.Message.ToolCalls {
			toolRequest := &ai.ToolRequest{
				Name:  toolCall.Function.Name,
				Input: toolCall.Function.Arguments,
			}
			toolPart := ai.NewToolRequestPart(toolRequest)
			chunk.Content = append(chunk.Content, toolPart)
		}
	} else if response.Message.Content != "" {
		aiPart := ai.NewTextPart(response.Message.Content)
		chunk.Content = append(chunk.Content, aiPart)
	}

	return chunk, nil
}

func translateGenerateChunk(input string) (*ai.ModelResponseChunk, error) {
	var response ollamaModelResponse

	if err := json.Unmarshal([]byte(input), &response); err != nil {
		return nil, fmt.Errorf("failed to parse response JSON: %v", err)
	}
	chunk := &ai.ModelResponseChunk{}
	aiPart := ai.NewTextPart(response.Response)
	chunk.Content = append(chunk.Content, aiPart)
	return chunk, nil
}

// concatMessages translates a list of messages into a prompt-style format
func concatMessages(input *ai.ModelRequest, roles []ai.Role) string {
	roleSet := make(map[ai.Role]bool)
	for _, role := range roles {
		roleSet[role] = true // Create a set for faster lookup
	}
	var sb strings.Builder
	for _, message := range input.Messages {
		// Check if the message role is in the allowed set
		if !roleSet[message.Role] {
			continue
		}
		for _, part := range message.Content {
			if !part.IsText() {
				continue
			}
			sb.WriteString(part.Text)
		}
	}
	return sb.String()
}

// concatImages grabs the images from genkit message parts
func concatImages(input *ai.ModelRequest, roleFilter []ai.Role) ([]string, error) {
	roleSet := make(map[ai.Role]bool)
	for _, role := range roleFilter {
		roleSet[role] = true
	}

	var images []string

	for _, message := range input.Messages {
		// Check if the message role is in the allowed set
		if roleSet[message.Role] {
			for _, part := range message.Content {
				if !part.IsMedia() {
					continue
				}

				// Get the media type and data
				mediaType, data, err := uri.Data(part)
				if err != nil {
					return nil, fmt.Errorf("failed to extract image data: %v", err)
				}

				// Only include image media types
				if !strings.HasPrefix(mediaType, "image/") {
					continue
				}

				base64Encoded := base64.StdEncoding.EncodeToString(data)
				images = append(images, base64Encoded)
			}
		}
	}
	return images, nil
}
