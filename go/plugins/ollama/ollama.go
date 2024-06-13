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
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"
	"time"

	"github.com/firebase/genkit/go/ai"
)

const provider = "ollama"

func defineModel(name string, serverAddress string) {
	meta := &ai.ModelMetadata{
		Label: "Ollama - " + name,
		Supports: ai.ModelCapabilities{
			Multiturn: true,
		},
	}
	g := generator{model: name, serverAddress: serverAddress}
	ai.DefineModel(provider, name, meta, g.generate)
}

// Model returns the [ai.ModelAction] with the given name.
// It returns nil if the model was not configured.
func Model(name string) *ai.ModelAction {
	return ai.LookupModel(provider, name)
}

// Config provides configuration options for the Init function.
type Config struct {
	// API key. Required.
	ServerAddress string
	// Generative models to provide.
	Model string
}

// Init registers all the actions in this package with ai.
func Init(ctx context.Context, cfg Config) error {
	defineModel(cfg.Model, cfg.ServerAddress)
	return nil
}

type generator struct {
	model         string
	serverAddress string
}

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
type OllamaRequest struct {
	Messages []map[string]string `json:"messages"`
	Model    string              `json:"model"`
	Stream   bool                `json:"stream"`
}

// Generate makes a request to the Ollama API and processes the response.
func (g *generator) generate(ctx context.Context, input *ai.GenerateRequest, cb func(context.Context, *ai.GenerateResponseChunk) error) (*ai.GenerateResponse, error) {
	// Step 1: Combine parts from all messages into a single payload slice
	var messages []map[string]string

	// Add all messages to history field.
	for _, m := range input.Messages {
		message, err := convertParts(m.Role, m.Content)
		if err != nil {
			return nil, fmt.Errorf("error converting message parts: %v", err)
		}
		messages = append(messages, message)
	}
	fmt.Println("should stream", cb != nil)
	stream := cb != nil
	payload := OllamaRequest{
		Messages: messages,
		Model:    g.model,
		Stream:   stream,
	}
	client := &http.Client{
		Timeout: time.Second * 30,
	}
	payloadBytes, err := json.Marshal(payload)
	req, err := http.NewRequest("POST", g.serverAddress+"/api/chat", bytes.NewBuffer(payloadBytes))
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
		body, err := io.ReadAll(resp.Body)
		if err != nil {
			return nil, fmt.Errorf("failed to read response body: %v", err)
		}
		if resp.StatusCode != http.StatusOK {
			return nil, fmt.Errorf("server returned non-200 status: %d, body: %s", resp.StatusCode, body)
		}
		response, err := translateResponse(body)
		if err != nil {
			return nil, fmt.Errorf("failed to parse response: %v", err)
		}
		return response, nil
	} else {
		// Handle streaming response here
		scanner := bufio.NewScanner(resp.Body) // Create a scanner to read lines
		for scanner.Scan() {
			line := scanner.Text()

			chunk, err := translateChunk(line)
			if err != nil {
				// Handle parsing error (log, maybe send an error candidate?)
				return nil, fmt.Errorf("error translating chunk: %v", err)
			}
			cb(ctx, chunk)
		}

		if err := scanner.Err(); err != nil {
			return nil, fmt.Errorf("error reading stream: %v", err)
		}
		// Handle end of stream (optional: send a final candidate to signal completion)
	}
	//Return an empty generate response, since we use callback for streaming
	return &ai.GenerateResponse{}, nil
}

// convertParts serializes a slice of *ai.Part into a a map (represent Ollama message type)
func convertParts(role ai.Role, parts []*ai.Part) (map[string]string, error) {
	roleMapping := map[ai.Role]string{
		ai.RoleUser:   "user",
		ai.RoleModel:  "assistant",
		ai.RoleSystem: "system",
		// Add more mappings as needed
	}

	partMap := map[string]string{}
	for _, part := range parts {
		partMap["role"] = roleMapping[role]
		switch {
		case part.IsText():
			partMap["content"] = part.Text
		default:
			return nil, errors.New("unknown content type")
		}
	}
	return partMap, nil
}

func translateChunk(input string) (*ai.GenerateResponseChunk, error) {
	log.Printf("translating chunk")
	var response GenerateResponse

	if err := json.Unmarshal([]byte(input), &response); err != nil {
		return nil, fmt.Errorf("error parsing response JSON: %v", err)
	}
	chunk := &ai.GenerateResponseChunk{
		Index:   0,
		Content: make([]*ai.Part, 0, 1),
	}
	return chunk, nil
}

type GenerateResponse struct {
	Model     string `json:"model"`
	CreatedAt string `json:"created_at"`
	Message   struct {
		Role    string `json:"role"`
		Content string `json:"content"`
	} `json:"message"`
}

// translateResponse deserializes a JSON response from the Ollama API into a GenerateResponse.
func translateResponse(responseData []byte) (*ai.GenerateResponse, error) {
	var response GenerateResponse

	if err := json.Unmarshal(responseData, &response); err != nil {
		return nil, fmt.Errorf("error parsing response JSON: %v", err)
	}
	generateResponse := &ai.GenerateResponse{
		Candidates: make([]*ai.Candidate, 0, 1),
	}
	aiCandidate := &ai.Candidate{
		Index:        0,
		FinishReason: ai.FinishReason("stop"),
		Message: &ai.Message{
			Role:    ai.Role(response.Message.Role),
			Content: make([]*ai.Part, 0, 1),
		},
	}
	aiPart := ai.NewTextPart(response.Message.Content)
	aiCandidate.Message.Content = append(aiCandidate.Message.Content, aiPart)
	generateResponse.Candidates = append(generateResponse.Candidates, aiCandidate)
	return generateResponse, nil
}
