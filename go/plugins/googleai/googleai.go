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

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/plugins/internal/uri"
	"github.com/google/generative-ai-go/genai"
	"google.golang.org/api/iterator"
	"google.golang.org/api/option"
)

const provider = "google-genai"

// Config provides configuration options for the Init function.
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

// Init initializes the plugin.
// It defines all the configured models and embedders, and returns their actions.
// If [Config.Models] or [Config.Embedders] is non-empty, the actions are returned in the same
// order; otherwise the order is undefined. Call the [Model] or [Embedder] functions to get an action
// from the registry by name, or call the Name method of the action to get its name.
func Init(ctx context.Context, cfg Config) (models []*ai.ModelAction, embedders []*ai.EmbedderAction, err error) {
	defer func() {
		if err != nil {
			err = fmt.Errorf("googleai.Init: %w", err)
		}
	}()

	if cfg.APIKey == "" {
		return nil, nil, errors.New("missing API key")
	}

	client, err := genai.NewClient(ctx, option.WithAPIKey(cfg.APIKey))
	if err != nil {
		return nil, nil, err
	}

	needModels := len(cfg.Models) == 0
	needEmbedders := len(cfg.Embedders) == 0
	if needModels || needEmbedders {
		iter := client.ListModels(ctx)
		for {
			mi, err := iter.Next()
			if err == iterator.Done {
				break
			}
			if err != nil {
				return nil, nil, err
			}
			// Model names are of the form "models/name".
			name := path.Base(mi.Name)
			if needModels && slices.Contains(mi.SupportedGenerationMethods, "generateContent") {
				cfg.Models = append(cfg.Models, name)
			}
			if needEmbedders && slices.Contains(mi.SupportedGenerationMethods, "embedContent") {
				cfg.Embedders = append(cfg.Embedders, name)
			}
		}
	}
	for _, name := range cfg.Models {
		models = append(models, defineModel(name, client))
	}
	for _, name := range cfg.Embedders {
		embedders = append(embedders, defineEmbedder(name, client))
	}
	return models, embedders, nil
}

func defineModel(name string, client *genai.Client) *ai.ModelAction {
	meta := &ai.ModelMetadata{
		Label: "Google AI - " + name,
		Supports: ai.ModelCapabilities{
			Multiturn: true,
		},
	}
	g := generator{model: name, client: client}
	return ai.DefineModel(provider, name, meta, g.generate)
}

func defineEmbedder(name string, client *genai.Client) *ai.EmbedderAction {
	return ai.DefineEmbedder(provider, name, func(ctx context.Context, input *ai.EmbedRequest) ([]float32, error) {
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

// Model returns the [ai.ModelAction] with the given name.
// It returns nil if the model was not configured.
func Model(name string) *ai.ModelAction {
	return ai.LookupModel(provider, name)
}

// Embedder returns the [ai.EmbedderAction] with the given name.
// It returns nil if the embedder was not configured.
func Embedder(name string) *ai.EmbedderAction {
	return ai.LookupEmbedder(provider, name)
}

type generator struct {
	model  string
	client *genai.Client
	//session *genai.ChatSession // non-nil if we're in the middle of a chat
}

func (g *generator) generate(ctx context.Context, input *ai.GenerateRequest, cb func(context.Context, *ai.GenerateResponseChunk) error) (*ai.GenerateResponse, error) {
	gm := g.client.GenerativeModel(g.model)

	// Translate from a ai.GenerateRequest to a genai request.
	gm.SetCandidateCount(int32(input.Candidates))
	if c, ok := input.Config.(*ai.GenerationCommonConfig); ok && c != nil {
		if c.MaxOutputTokens != 0 {
			gm.SetMaxOutputTokens(int32(c.MaxOutputTokens))
		}
		if len(c.StopSequences) > 0 {
			gm.StopSequences = c.StopSequences
		}
		if c.Temperature != 0 {
			gm.SetTemperature(float32(c.Temperature))
		}
		if c.TopK != 0 {
			gm.SetTopK(int32(c.TopK))
		}
		if c.TopP != 0 {
			gm.SetTopP(float32(c.TopP))
		}
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
			tc := translateCandidate(c)
			err := cb(ctx, &ai.GenerateResponseChunk{
				Content: tc.Message.Content,
				Index:   tc.Index,
			})
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
