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
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"slices"
	"strings"
	"sync"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/plugins/internal/uri"
	"github.com/ollama/ollama/api"
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
	client        *api.Client
}

func DefineModel(model ModelDefinition, caps *ai.ModelCapabilities) ai.Model {
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
	g := &generator{model: model, client: state.client}
	return ai.DefineModel(provider, model.Name, meta, g.generate)
}

// IsDefinedModel reports whether a model is defined.
func IsDefinedModel(name string) bool {
	return ai.IsDefinedModel(provider, name)
}

// Model returns the [ai.Model] with the given name.
// It returns nil if the model was not configured.
func Model(name string) ai.Model {
	return ai.LookupModel(provider, name)
}

// ModelDefinition represents a model with its name and type.
type ModelDefinition struct {
	Name string
	Type string
}

type generator struct {
	model  ModelDefinition
	client *api.Client
}

// Config provides configuration options for the Init function.
type Config struct {
	// Server Address of oLLama.
	ServerAddress string
}

// Init initializes the plugin.
func Init(ctx context.Context, cfg *Config) (err error) {
	state.mu.Lock()
	defer state.mu.Unlock()
	if state.initted {
		panic("ollama.Init already called")
	}
	if cfg == nil || cfg.ServerAddress == "" {
		return errors.New("ollama: need ServerAddress")
	}
	state.serverAddress = cfg.ServerAddress
	client, err := api.ClientFromEnvironment()
	if err != nil {
		return err
	}
	state.client = client
	state.initted = true
	return nil
}

// Generate makes a request to the Ollama API and processes the response.
func (g *generator) generate(ctx context.Context, input *ai.GenerateRequest, cb func(context.Context, *ai.GenerateResponseChunk) error) (*ai.GenerateResponse, error) {
	stream := cb != nil
	isChatModel := g.model.Type == "chat"
	if !isChatModel {
		images, err := concatImages(input, []ai.Role{ai.RoleUser, ai.RoleModel})
		if err != nil {
			return nil, fmt.Errorf("failed to grab image parts: %v", err)
		}
		payload := api.GenerateRequest{
			Model:  g.model.Name,
			Prompt: concatMessages(input, []ai.Role{ai.RoleUser, ai.RoleModel, ai.RoleTool}),
			System: concatMessages(input, []ai.Role{ai.RoleSystem}),
			Images: images,
			Stream: &stream,
		}

		if stream {
			var chunks []*ai.GenerateResponseChunk
			err := g.client.Generate(ctx, &payload, func(r api.GenerateResponse) error {

				line, err := json.Marshal(r)
				if err != nil {
					return err
				}
				chunk, err := translateGenerateChunk(string(line))
				if err != nil {
					return err
				}
				chunks = append(chunks, chunk)
				cb(ctx, chunk)
				return nil
			})
			if err != nil {
				return nil, err
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
			return finalResponse, nil
		}
		var resp api.GenerateResponse

		g.client.Generate(ctx, &payload, func(r api.GenerateResponse) error {
			resp = r
			return nil
		})
		body, err := json.Marshal(resp)
		if err != nil {
			return nil, err
		}
		return translateGenerateResponse(input, body)
	} else {
		var messages []api.Message
		// Translate all messages to ollama message format.
		for _, m := range input.Messages {
			message, err := convertParts(m.Role, m.Content)
			if err != nil {
				return nil, fmt.Errorf("failed to convert message parts: %v", err)
			}
			messages = append(messages, *message)
		}
		payload := &api.ChatRequest{
			Messages: messages,
			Model:    g.model.Name,
			Stream:   &stream,
		}

		if stream {
			return g.handleStreamResponse(ctx, payload, isChatModel, input, cb)
		}
		return g.handleSingleResponse(ctx, payload, isChatModel, input)
	}
}

func (g *generator) handleSingleResponse(ctx context.Context, payload any, isChatModel bool, input *ai.GenerateRequest) (*ai.GenerateResponse, error) {
	var body []byte
	var err error

	if isChatModel {
		var request *api.ChatRequest = payload.(*api.ChatRequest)
		var resp api.ChatResponse
		err = g.client.Chat(ctx, request, func(r api.ChatResponse) error {
			resp = r
			return nil
		})
		body, err = json.Marshal(resp)
	} else {
		var request *api.GenerateRequest = payload.(*api.GenerateRequest)
		var resp api.GenerateResponse
		err = g.client.Generate(ctx, request, func(r api.GenerateResponse) error {
			resp = r
			return nil
		})
		body, err = json.Marshal(resp)
	}
	if err != nil {
		return nil, err
	}
	if isChatModel {
		return translateChatResponse(input, body)
	}
	return translateGenerateResponse(input, body)
}

func (g *generator) handleStreamResponse(ctx context.Context, payload any, isChatModel bool, input *ai.GenerateRequest, cb func(context.Context, *ai.GenerateResponseChunk) error) (*ai.GenerateResponse, error) {
	var chunks []*ai.GenerateResponseChunk
	if isChatModel {
		err := g.client.Chat(ctx, payload.(*api.ChatRequest), func(r api.ChatResponse) error {
			line, err := json.Marshal(r)
			if err != nil {
				return err
			}
			chunk, err := translateChatChunk(string(line))
			if err != nil {
				return err
			}
			chunks = append(chunks, chunk)
			cb(ctx, chunk)
			return nil
		})
		if err != nil {
			return nil, err
		}
	} else {
		err := g.client.Generate(ctx, payload.(*api.GenerateRequest), func(r api.GenerateResponse) error {
			line, err := json.Marshal(r)
			if err != nil {
				return err
			}
			chunk, err := translateGenerateChunk(string(line))
			if err != nil {
				return err
			}
			chunks = append(chunks, chunk)
			cb(ctx, chunk)
			return nil
		})
		if err != nil {
			return nil, err
		}
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
	return finalResponse, nil
}

func convertParts(role ai.Role, parts []*ai.Part) (*api.Message, error) {
	message := &api.Message{
		Role: roleMapping[role],
	}
	var contentBuilder strings.Builder
	var images []api.ImageData
	for _, part := range parts {
		if part.IsText() {
			contentBuilder.WriteString(part.Text)
		} else if part.IsMedia() {
			_, data, err := uri.Data(part)
			if err != nil {
				return nil, err
			}
			// Append the raw data to images slice
			images = append(images, data)
		} else {
			return nil, errors.New("unknown content type")
		}
	}
	message.Content = contentBuilder.String()
	message.Images = images
	return message, nil
}

// translateChatResponse translates Ollama chat response into a genkit response.
func translateChatResponse(request *ai.GenerateRequest, responseData []byte) (*ai.GenerateResponse, error) {
	var response api.ChatResponse

	if err := json.Unmarshal(responseData, &response); err != nil {
		return nil, fmt.Errorf("failed to parse response JSON: %v", err)
	}
	generateResponse := &ai.GenerateResponse{
		Request: request,
	}
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

// translateGenerateResponse translates Ollama generate response into a genkit response.
func translateGenerateResponse(request *ai.GenerateRequest, responseData []byte) (*ai.GenerateResponse, error) {
	var response api.GenerateResponse

	if err := json.Unmarshal(responseData, &response); err != nil {
		return nil, fmt.Errorf("failed to parse response JSON: %v", err)
	}
	generateResponse := &ai.GenerateResponse{
		Request: request,
		Candidates: []*ai.Candidate{
			{
				FinishReason: ai.FinishReason("stop"),
				Message: &ai.Message{
					Role: ai.RoleModel,
					Content: []*ai.Part{
						ai.NewTextPart(response.Response),
					},
				},
			},
		},
	}
	return generateResponse, nil
}

func translateChatChunk(input string) (*ai.GenerateResponseChunk, error) {
	var response api.ChatResponse

	if err := json.Unmarshal([]byte(input), &response); err != nil {
		return nil, fmt.Errorf("failed to parse response JSON: %v", err)
	}
	chunk := &ai.GenerateResponseChunk{}
	aiPart := ai.NewTextPart(response.Message.Content)
	chunk.Content = append(chunk.Content, aiPart)
	return chunk, nil
}

func translateGenerateChunk(input string) (*ai.GenerateResponseChunk, error) {
	var response api.GenerateResponse

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

func concatImages(input *ai.GenerateRequest, roleFilter []ai.Role) ([]api.ImageData, error) {
	roleSet := make(map[ai.Role]bool)
	for _, role := range roleFilter {
		roleSet[role] = true
	}

	var images []api.ImageData

	for _, message := range input.Messages {
		// Check if the message role is in the allowed set
		if roleSet[message.Role] {
			for _, part := range message.Content {
				if !part.IsMedia() {
					continue
				}
				_, data, err := uri.Data(part)
				if err != nil {
					return nil, err
				}
				// Append the raw data to images slice
				images = append(images, data)
			}
		}
	}
	return images, nil
}

// DefineEmbedder defines an embedder with a given name.
func DefineEmbedder(name string) ai.Embedder {
	state.mu.Lock()
	defer state.mu.Unlock()
	if !state.initted {
		panic(provider + ".Init not called")
	}
	return defineEmbedder(name)
}

// IsDefinedEmbedder reports whether the named [Embedder] is defined by this plugin.
func IsDefinedEmbedder(name string) bool {
	return ai.IsDefinedEmbedder(provider, name)
}

// requires state.mu
func defineEmbedder(name string) ai.Embedder {
	return ai.DefineEmbedder(provider, name, func(ctx context.Context, input *ai.EmbedRequest) (*ai.EmbedResponse, error) {
		em := &embedder{model: ModelDefinition{Name: name, Type: "embedding"}, client: state.client}
		return em.embed(ctx, input)
	})
}

// Embedder returns the [ai.Embedder] with the given name.
// It returns nil if the embedder was not defined.
func Embedder(name string) ai.Embedder {
	return ai.LookupEmbedder(provider, name)
}

type embedder struct {
	model  ModelDefinition
	client *api.Client
}

func (e *embedder) embed(ctx context.Context, input *ai.EmbedRequest) (*ai.EmbedResponse, error) {
	var inputs []string

	// Concatenate the content from input documents
	for _, doc := range input.Documents {
		var contentBuilder strings.Builder
		for _, part := range doc.Content {
			if part.IsText() {
				contentBuilder.WriteString(part.Text)
			} else {
				return nil, errors.New("only text parts are supported for embedding")
			}
		}
		inputs = append(inputs, contentBuilder.String())
	}

	payload := api.EmbedRequest{
		Model: e.model.Name,
		Input: inputs, // List of concatenated document contents
	}

	embedResponse, err := e.client.Embed(ctx, &payload)

	if err != nil {
		return nil, fmt.Errorf("failed to send embed request: %v", err)
	}

	// Prepare the response by creating DocumentEmbedding for each embedding returned
	var documentEmbeddings []*ai.DocumentEmbedding
	for _, embedding := range embedResponse.Embeddings {
		documentEmbeddings = append(documentEmbeddings, &ai.DocumentEmbedding{
			Embedding: embedding,
		})
	}

	response := &ai.EmbedResponse{
		Embeddings: documentEmbeddings,
	}

	return response, nil
}
