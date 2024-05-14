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

// TODO: REMEMBER to customize the template

package ollama

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"time"

	"github.com/google/genkit/go/ai" // Assuming this namespace for custom AI-related types
	"github.com/google/genkit/go/genkit"
)

// Init registers all the actions in this package with ai.
func Init(ctx context.Context, serverAddress string) error {
	g := NewGenerator(ctx, serverAddress)
	ai.RegisterGenerator("ollama", g)

	return nil
}

type generator struct {
	Model         string
	ServerAddress string
}

// NewGenerator creates a new generator with the necessary configuration.
func NewGenerator(ctx context.Context, serverAddress string) ai.Generator {

	return &generator{
		Model:         "llama2",
		ServerAddress: serverAddress,
	}
}

/*
Advanced parameters (optional):

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
	Stream   *bool               `json:"stream,omitempty"` // Optional stream field
}

// Generate makes a request to the Ollama API and processes the response.
func (g *generator) Generate(ctx context.Context, input *ai.GenerateRequest, cb genkit.StreamingCallback[*ai.Candidate]) (*ai.GenerateResponse, error) {
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
	stream := false
	// Step 2: Create the full payload structure
	payload := OllamaRequest{
		Messages: messages,
		Model:    "llama2",
		Stream:   &stream,
	}

	// Create an HTTP client with a timeout
	client := &http.Client{
		Timeout: time.Second * 30,
	}
	payloadBytes, err := json.Marshal(payload)
	// Create the HTTP request
	// TODO IMPORTANT: This should be chat completion body; not sure it's being sent correctly.
	req, err := http.NewRequest("POST", g.ServerAddress+"/api/chat", bytes.NewBuffer(payloadBytes))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %v", err)
	}
	req.Header.Set("Content-Type", "application/json")
	req = req.WithContext(ctx)

	// Send the request
	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to send request: %v", err)
	}
	defer resp.Body.Close()

	// Read and parse the response
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
}

// Helper functions would be implemented here, such as convertParts and translateResponse,
// adapted to align with the specifics of the Ollama API and response structures.

// convertParts serializes a slice of *ai.Part into a JSON byte array suitable for the Ollama API.

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
		partMap["content"] = part.Text()

		switch part.ContentType() {
		case "image":
			// Handle image parts (add to an image array, etc.)
			log.Println("Image part:", part.Text()) // Example: logging the image URL or description
		case "text":
			// You might have specific handling for text parts here if needed
		default:
			log.Println("Unknown content type:", part.ContentType())
		}
	}
	return partMap, nil
}

type GenerateResponse struct {
	Model     string `json:"model"`
	CreatedAt string `json:"created_at"`
	Message   struct {
		Role    string `json:"role"`
		Content string `json:"content"`
	} `json:"message"`
	Done bool `json:"done"`
	// ... other fields you might need ...
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
