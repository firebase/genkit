// Copyright 2024 Google LLC
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
	"github.com/firebase/genkit/go/plugins/internal/uri"
)

const provider = "ollama"

var mediaSupportedModels = []string{"llava"}
var roleMapping = map[ai.Role]string{
	ai.RoleUser:   "user",
	ai.RoleModel:  "assistant",
	ai.RoleSystem: "system",
}
var state struct {
	mu            sync.Mutex
	initted       bool
	serverAddress string
}

func DefineModel(model ModelDefinition, caps *ai.ModelCapabilities) *ai.Model {
	state.mu.Lock()
	defer state.mu.Unlock()
	if !state.initted {
		panic("ollama.Init not called")
	}
	var mc ai.ModelCapabilities
	if caps != nil {
		mc = *caps
	} else {
		mc = ai.ModelCapabilities{
			Multiturn:  true,
			SystemRole: true,
			Media:      slices.Contains(mediaSupportedModels, model.Name),
		}
	}
	meta := &ai.ModelMetadata{
		Label:    "Ollama - " + model.Name,
		Supports: mc,
	}
	g := &generator{model: model, serverAddress: state.serverAddress}
	return ai.DefineModel(provider, model.Name, meta, g.generate)

}

// Model returns the [ai.Model] with the given name.
// It returns nil if the model was not configured.
func Model(name string) *ai.Model {
	return ai.LookupModel(provider, name)
}

// ModelDefinition represents a model with its name and type.
type ModelDefinition struct {
	Name string
	Type string
}

// Config provides configuration options for the Init function.
type Config struct {
	// Server Address of oLLama.
	ServerAddress string
	// Generative models to provide.
	Models []ModelDefinition
}

type generator struct {
	model         ModelDefinition
	serverAddress string
}

type ollamaMessage struct {
	Role    string   `json:"role"`
	Content string   `json:"content"`
	Images  []string `json:"images,omitempty"`
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
	Model    string           `json:"model"`
	Stream   bool             `json:"stream"`
}

type ollamaGenerateRequest struct {
	System string   `json:"system,omitempty"`
	Images []string `json:"images,omitempty"`
	Model  string   `json:"model"`
	Prompt string   `json:"prompt"`
	Stream bool     `json:"stream"`
}

// TODO: Add optional parameters (images, format, options, etc.) based on your use case
type ollamaChatResponse struct {
	Model     string `json:"model"`
	CreatedAt string `json:"created_at"`
	Message   struct {
		Role    string `json:"role"`
		Content string `json:"content"`
	} `json:"message"`
}

type ollamaGenerateResponse struct {
	Model     string `json:"model"`
	CreatedAt string `json:"created_at"`
	Response  string `json:"response"`
}

// Note: Since Ollama models are locally hosted, the plugin doesn't initialize any default models.
// The user has to explicitly decide which model to pull down.
func Init(ctx context.Context, serverAddress string) (err error) {
	state.mu.Lock()
	defer state.mu.Unlock()
	if state.initted {
		panic("ollama.Init already called")
	}
	defer func() {
		if err != nil {
			err = fmt.Errorf("ollama.Init: %w", err)
		}
	}()
	state.serverAddress = serverAddress
	state.initted = true
	return nil
}

// Generate makes a request to the Ollama API and processes the response.
func (g *generator) generate(ctx context.Context, input *ai.GenerateRequest, cb func(context.Context, *ai.GenerateResponseChunk) error) (*ai.GenerateResponse, error) {

	stream := cb != nil
	var payload any
	isChatModel := g.model.Type == "chat"
	if !isChatModel {
		images, err := concatImages(input, []ai.Role{ai.RoleUser, ai.RoleModel})
		if err != nil {
			return nil, fmt.Errorf("failed to grab image parts: %v", err)
		}
		payload = ollamaGenerateRequest{
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
		payload = ollamaChatRequest{
			Messages: messages,
			Model:    g.model.Name,
			Stream:   stream,
		}
	}
	client := &http.Client{
		Timeout: time.Second * 30,
	}
	payloadBytes, err := json.Marshal(payload)
	// Determine the correct endpoint
	endpoint := g.serverAddress + "/api/chat"
	if !isChatModel {
		endpoint = g.serverAddress + "/api/generate"
	}
	req, err := http.NewRequest("POST", endpoint, bytes.NewBuffer(payloadBytes))
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
		var response *ai.GenerateResponse
		if isChatModel {
			response, err = translateChatResponse(body)
		} else {
			response, err = translateGenerateResponse(body)
		}
		response.Request = input
		if err != nil {
			return nil, fmt.Errorf("failed to parse response: %v", err)
		}
		return response, nil
	} else {
		var chunks []*ai.GenerateResponseChunk
		scanner := bufio.NewScanner(resp.Body)
		for scanner.Scan() {
			line := scanner.Text()
			var chunk *ai.GenerateResponseChunk
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
			return nil, fmt.Errorf("failed to read stream: %v", err)
		}
		// Create a final response with the merged chunks
		finalResponse := &ai.GenerateResponse{
			Request: input,
			Candidates: []*ai.Candidate{
				{
					FinishReason: ai.FinishReason("stop"),
					Message: &ai.Message{
						Role: ai.RoleModel,
					},
				},
			},
		}
		// Add all the merged content to the final response's candidate
		for _, chunk := range chunks {
			finalResponse.Candidates[0].Message.Content = append(finalResponse.Candidates[0].Message.Content, chunk.Content...)
		}
		return finalResponse, nil // Return the final merged response

	}
}

func convertParts(role ai.Role, parts []*ai.Part) (*ollamaMessage, error) {
	message := &ollamaMessage{
		Role: roleMapping[role],
	}
	var contentBuilder strings.Builder
	for _, part := range parts {
		if part.IsText() {
			contentBuilder.WriteString(part.Text)
		} else if part.IsMedia() {
			_, data, err := uri.Data(part)
			if err != nil {
				return nil, err
			}
			base64Encoded := base64.StdEncoding.EncodeToString(data)
			message.Images = append(message.Images, base64Encoded)
		} else {
			return nil, errors.New("unknown content type")
		}
	}
	message.Content = contentBuilder.String()
	return message, nil
}

// translateChatResponse translates Ollama chat response into a genkit response.
func translateChatResponse(responseData []byte) (*ai.GenerateResponse, error) {
	var response ollamaChatResponse

	if err := json.Unmarshal(responseData, &response); err != nil {
		return nil, fmt.Errorf("failed to parse response JSON: %v", err)
	}
	generateResponse := &ai.GenerateResponse{}
	aiCandidate := &ai.Candidate{
		FinishReason: ai.FinishReason("stop"),
		Message: &ai.Message{
			Role: ai.Role(response.Message.Role),
		},
	}
	aiPart := ai.NewTextPart(response.Message.Content)
	aiCandidate.Message.Content = append(aiCandidate.Message.Content, aiPart)
	generateResponse.Candidates = append(generateResponse.Candidates, aiCandidate)
	return generateResponse, nil
}

// translateResponse translates Ollama generate response into a genkit response.
func translateGenerateResponse(responseData []byte) (*ai.GenerateResponse, error) {
	var response ollamaGenerateResponse

	if err := json.Unmarshal(responseData, &response); err != nil {
		return nil, fmt.Errorf("failed to parse response JSON: %v", err)
	}
	generateResponse := &ai.GenerateResponse{}
	aiCandidate := &ai.Candidate{
		FinishReason: ai.FinishReason("stop"),
		Message: &ai.Message{
			Role: ai.RoleModel,
		},
	}
	aiPart := ai.NewTextPart(response.Response)
	aiCandidate.Message.Content = append(aiCandidate.Message.Content, aiPart)
	generateResponse.Candidates = append(generateResponse.Candidates, aiCandidate)
	generateResponse.Usage = &ai.GenerationUsage{} // TODO: can we get any of this info?
	return generateResponse, nil
}

func translateChatChunk(input string) (*ai.GenerateResponseChunk, error) {
	var response ollamaChatResponse

	if err := json.Unmarshal([]byte(input), &response); err != nil {
		return nil, fmt.Errorf("failed to parse response JSON: %v", err)
	}
	chunk := &ai.GenerateResponseChunk{}
	aiPart := ai.NewTextPart(response.Message.Content)
	chunk.Content = append(chunk.Content, aiPart)
	return chunk, nil
}

func translateGenerateChunk(input string) (*ai.GenerateResponseChunk, error) {
	var response ollamaGenerateResponse

	if err := json.Unmarshal([]byte(input), &response); err != nil {
		return nil, fmt.Errorf("failed to parse response JSON: %v", err)
	}
	chunk := &ai.GenerateResponseChunk{}
	aiPart := ai.NewTextPart(response.Response)
	chunk.Content = append(chunk.Content, aiPart)
	return chunk, nil
}

// concatMessages translates a list of messages into a prompt-style format
func concatMessages(input *ai.GenerateRequest, roles []ai.Role) string {
	roleSet := make(map[ai.Role]bool)
	for _, role := range roles {
		roleSet[role] = true // Create a set for faster lookup
	}

	var sb strings.Builder

	for _, message := range input.Messages {
		// Check if the message role is in the allowed set
		if roleSet[message.Role] {
			for _, part := range message.Content {
				sb.WriteString(part.Text)
			}
		}
	}
	return sb.String()
}

// concatMessages translates a list of messages into a prompt-style format
func concatImages(input *ai.GenerateRequest, roles []ai.Role) ([]string, error) {
	roleSet := make(map[ai.Role]bool)
	for _, role := range roles {
		roleSet[role] = true // Create a set for faster lookup
	}

	var images []string

	for _, message := range input.Messages {
		// Check if the message role is in the allowed set
		if roleSet[message.Role] {
			for _, part := range message.Content {
				if !part.IsMedia() {
					return nil, errors.New("unknown content type")
				}
				_, data, err := uri.Data(part)
				if err != nil {
					return nil, err
				}
				base64Encoded := base64.StdEncoding.EncodeToString(data)
				images = append(images, base64Encoded)
			}
		}
	}
	return images, nil
}
