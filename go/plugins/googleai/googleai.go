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

package googleai

import (
	"context"
	"errors"
	"fmt"
	"path"
	"slices"
	"sync"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/plugins/internal/uri"
	"github.com/google/generative-ai-go/genai"
	"golang.org/x/exp/maps"
	"google.golang.org/api/iterator"
	"google.golang.org/api/option"
)

var state struct {
	mu        sync.Mutex
	client    *genai.Client
	models    map[string]ai.Generator
	embedders map[string]ai.Embedder
}

// Config configures the plugin.
type Config struct {
	// API key. Required.
	APIKey string
	// Generative models to provide.
	// If empty, a complete list will be obtained from the service.
	Models []string
	// Embedding models to provide.
	// If empty, a complete list will be obtained from the service.
	Embedders []string
}

func Init(ctx context.Context, cfg Config) (err error) {
	defer func() {
		if err != nil {
			err = fmt.Errorf("googleai.Init: %w", err)
		}
	}()

	if err := initClient(ctx, cfg.APIKey); err != nil {
		return err
	}

	needModels := len(cfg.Models) == 0
	needEmbedders := len(cfg.Embedders) == 0
	if needModels || needEmbedders {
		iter := state.client.ListModels(ctx)
		for {
			mi, err := iter.Next()
			if err == iterator.Done {
				break
			}
			if err != nil {
				return err
			}
			// Model names are of the form "model/name".
			name := path.Base(mi.Name)
			if needModels && slices.Contains(mi.SupportedGenerationMethods, "generateContent") {
				cfg.Models = append(cfg.Models, name)
			}
			if needEmbedders && slices.Contains(mi.SupportedGenerationMethods, "embedContent") {
				cfg.Embedders = append(cfg.Embedders, name)
			}
		}
	}
	state.models = map[string]ai.Generator{}
	for _, name := range cfg.Models {
		state.models[name] = defineModel(name, state.client)
	}

	state.embedders = map[string]ai.Embedder{}
	for _, name := range cfg.Embedders {
		state.embedders[name] = defineEmbedder(name, state.client)
	}
	return nil
}

func initClient(ctx context.Context, apiKey string) error {
	if apiKey == "" {
		return errors.New("missing API key")
	}

	state.mu.Lock()
	defer state.mu.Unlock()
	if state.client != nil {
		return errors.New("already initialized")
	}
	c, err := genai.NewClient(ctx, option.WithAPIKey(apiKey))
	if err != nil {
		return err
	}
	state.client = c
	return nil
}

func defineModel(name string, client *genai.Client) ai.Generator {
	meta := &ai.GeneratorMetadata{
		Label: "Google AI - " + name,
		Supports: ai.GeneratorCapabilities{
			Multiturn: true,
		},
	}
	g := generator{model: name, client: client}
	return ai.DefineGenerator("google-genai", name, meta, g.Generate)
}

func defineEmbedder(name string, client *genai.Client) ai.Embedder {
	return ai.DefineEmbedder("google-genai", name, func(ctx context.Context, input *ai.EmbedRequest) ([]float32, error) {
		em := client.EmbeddingModel(name)
		parts, err := convertParts(input.Document.Content)
		if err != nil {
			return nil, err
		}
		res, err := em.EmbedContent(ctx, parts...)
		if err != nil {
			return nil, err
		}
		return res.Embedding.Values, nil
	})
}

// Generator returns the generator with the given name.
// It panics if the generator was not configured.
func Generator(name string) ai.Generator {
	if g, ok := state.models[name]; ok {
		return g
	}
	panic(fmt.Sprintf("googleai: generator %q not configured", name))
}

// Embedder returns the embedder with the given name.
// It panics if the embedder was not configured.
func Embedder(name string) ai.Embedder {
	if e, ok := state.embedders[name]; ok {
		return e
	}
	panic(fmt.Sprintf("googleai: embedder %q not configured", name))
}

// Generators returns the names of the configured generators.
func Generators() []string {
	return maps.Keys(state.models)
}

// Embedders returns the names of the configured embedders.
func Embedders() []string {
	return maps.Keys(state.embedders)
}

type generator struct {
	model  string
	client *genai.Client
	//session *genai.ChatSession // non-nil if we're in the middle of a chat
}

func (g *generator) Generate(ctx context.Context, input *ai.GenerateRequest, cb func(context.Context, *ai.Candidate) error) (*ai.GenerateResponse, error) {
	gm := g.client.GenerativeModel(g.model)

	// Translate from a ai.GenerateRequest to a genai request.
	gm.SetCandidateCount(int32(input.Candidates))
	if c, ok := input.Config.(*ai.GenerationCommonConfig); ok && c != nil {
		gm.SetMaxOutputTokens(int32(c.MaxOutputTokens))
		gm.StopSequences = c.StopSequences
		gm.SetTemperature(float32(c.Temperature))
		gm.SetTopK(int32(c.TopK))
		gm.SetTopP(float32(c.TopP))
	}

	// Start a "chat".
	cs := gm.StartChat()

	// All but the last message goes in the history field.
	messages := input.Messages
	for len(messages) > 1 {
		m := messages[0]
		messages = messages[1:]
		parts, err := convertParts(m.Content)
		if err != nil {
			return nil, err
		}
		cs.History = append(cs.History, &genai.Content{
			Parts: parts,
			Role:  string(m.Role),
		})
	}
	// The last message gets added to the parts slice.
	var parts []genai.Part
	if len(messages) > 0 {
		var err error
		parts, err = convertParts(messages[0].Content)
		if err != nil {
			return nil, err
		}
	}

	// Convert input.Tools and append to gm.Tools
	for _, t := range input.Tools {
		schema := &genai.Schema{}
		schema.Type = genai.TypeObject
		schema.Properties = map[string]*genai.Schema{}
		for k, v := range t.InputSchema {
			typ := genai.TypeUnspecified
			switch v {
			case "string":
				typ = genai.TypeString
			case "float64":
				typ = genai.TypeNumber
			case "int":
				typ = genai.TypeInteger
			case "bool":
				typ = genai.TypeBoolean
			default:
				return nil, fmt.Errorf("schema value \"%s\" not allowed", v)
			}
			schema.Properties[k] = &genai.Schema{Type: typ}
		}
		fd := &genai.FunctionDeclaration{
			Name:        t.Name,
			Parameters:  schema,
			Description: t.Description,
		}
		gm.Tools = append(gm.Tools, &genai.Tool{FunctionDeclarations: []*genai.FunctionDeclaration{fd}})
	}
	// TODO: gm.ToolConfig?

	// Send out the actual request.
	if cb == nil {
		resp, err := cs.SendMessage(ctx, parts...)
		if err != nil {
			return nil, err
		}
		r := translateResponse(resp)
		r.Request = input
		return r, nil
	}

	// Streaming version.
	iter := cs.SendMessageStream(ctx, parts...)
	var r *ai.GenerateResponse
	for {
		chunk, err := iter.Next()
		if err == iterator.Done {
			r = translateResponse(iter.MergedResponse())
			break
		}
		if err != nil {
			return nil, err
		}
		// Send candidates to the callback.
		for _, c := range chunk.Candidates {
			err := cb(ctx, translateCandidate(c))
			if err != nil {
				return nil, err
			}
		}
	}
	if r == nil {
		// No candidates were returned. Probably rare, but it might avoid a NPE
		// to return an empty instead of nil result.
		r = &ai.GenerateResponse{}
	}
	r.Request = input
	return r, nil
}

// translateCandidate translates from a genai.GenerateContentResponse to an ai.GenerateResponse.
func translateCandidate(cand *genai.Candidate) *ai.Candidate {
	c := &ai.Candidate{}
	c.Index = int(cand.Index)
	switch cand.FinishReason {
	case genai.FinishReasonStop:
		c.FinishReason = ai.FinishReasonStop
	case genai.FinishReasonMaxTokens:
		c.FinishReason = ai.FinishReasonLength
	case genai.FinishReasonSafety:
		c.FinishReason = ai.FinishReasonBlocked
	case genai.FinishReasonRecitation:
		c.FinishReason = ai.FinishReasonBlocked
	case genai.FinishReasonOther:
		c.FinishReason = ai.FinishReasonOther
	default: // Unspecified
		c.FinishReason = ai.FinishReasonUnknown
	}
	m := &ai.Message{}
	m.Role = ai.Role(cand.Content.Role)
	for _, part := range cand.Content.Parts {
		var p *ai.Part
		switch part := part.(type) {
		case genai.Text:
			p = ai.NewTextPart(string(part))
		case genai.Blob:
			p = ai.NewMediaPart(part.MIMEType, string(part.Data))
		case genai.FunctionCall:
			p = ai.NewToolRequestPart(&ai.ToolRequest{
				Name:  part.Name,
				Input: part.Args,
			})
		default:
			panic(fmt.Sprintf("unknown part %#v", part))
		}
		m.Content = append(m.Content, p)
	}
	c.Message = m
	return c
}

// Translate from a genai.GenerateContentResponse to a ai.GenerateResponse.
func translateResponse(resp *genai.GenerateContentResponse) *ai.GenerateResponse {
	r := &ai.GenerateResponse{}
	for _, c := range resp.Candidates {
		r.Candidates = append(r.Candidates, translateCandidate(c))
	}
	return r
}

// convertParts converts a slice of *ai.Part to a slice of genai.Part.
func convertParts(parts []*ai.Part) ([]genai.Part, error) {
	res := make([]genai.Part, 0, len(parts))
	for _, p := range parts {
		part, err := convertPart(p)
		if err != nil {
			return nil, err
		}
		res = append(res, part)
	}
	return res, nil
}

// convertPart converts a *ai.Part to a genai.Part.
func convertPart(p *ai.Part) (genai.Part, error) {
	switch {
	case p.IsText():
		return genai.Text(p.Text), nil
	case p.IsMedia():
		contentType, data, err := uri.Data(p)
		if err != nil {
			return nil, err
		}
		return genai.Blob{MIMEType: contentType, Data: data}, nil
	case p.IsData():
		panic("googleai does not support Data parts")
	case p.IsToolResponse():
		toolResp := p.ToolResponse
		fr := genai.FunctionResponse{
			Name:     toolResp.Name,
			Response: toolResp.Output,
		}
		return fr, nil
	case p.IsToolRequest():
		toolReq := p.ToolRequest
		fc := genai.FunctionCall{
			Name: toolReq.Name,
			Args: toolReq.Input,
		}
		return fc, nil
	default:
		panic("unknown part type in a request")
	}
}
