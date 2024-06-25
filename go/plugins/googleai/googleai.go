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
	"fmt"
	"os"
	"sync"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/plugins/internal/uri"
	"github.com/google/generative-ai-go/genai"
	"google.golang.org/api/iterator"
	"google.golang.org/api/option"
)

const provider = "googleai"

var state struct {
	mu      sync.Mutex
	initted bool
	client  *genai.Client
}

var (
	basicText = ai.ModelCapabilities{
		Multiturn:  true,
		Tools:      true,
		SystemRole: true,
		Media:      false,
	}

	multimodal = ai.ModelCapabilities{
		Multiturn:  true,
		Tools:      true,
		SystemRole: true,
		Media:      true,
	}

	knownCaps = map[string]ai.ModelCapabilities{
		"gemini-1.0-pro":   basicText,
		"gemini-1.5-flash": multimodal,
	}
)

// Init initializes the plugin.
// After calling Init, call [DefineModel] and [DefineEmbedder] to create and register
// generative models and embedders.
func Init(ctx context.Context, apiKey string) (err error) {
	state.mu.Lock()
	defer state.mu.Unlock()
	if state.initted {
		panic("googleai.Init already called")
	}
	defer func() {
		if err != nil {
			err = fmt.Errorf("googleai.Init: %w", err)
		}
	}()

	if apiKey == "" {
		apiKey := os.Getenv("GOOGLE_GENAI_API_KEY")
		if apiKey == "" {
			return fmt.Errorf("googleai.Init: Google AI requires setting GOOGLE_GENAI_API_KEY in the environment. You can get an API key at https://ai.google.dev")
		}
	}

	client, err := genai.NewClient(ctx, option.WithAPIKey(apiKey))
	if err != nil {
		return err
	}
	state.client = client
	state.initted = true
	return nil
}

// IsKnownModel reports whether a model is known to this plugin.
func IsKnownModel(name string) bool {
	_, ok := knownCaps[name]
	return ok
}

// DefineModel defines a model with the given name.
// The second argument describes the capability of the model.
// For known models, it can be nil, or if non-nil it will override the known value.
// It must be supplied for unknown models.
// Use [IsKnownModel] to determine if a model is known.
func DefineModel(name string, caps *ai.ModelCapabilities) (*ai.Model, error) {
	state.mu.Lock()
	defer state.mu.Unlock()
	if !state.initted {
		panic("googleai.Init not called")
	}
	var mc ai.ModelCapabilities
	if caps == nil {
		var ok bool
		mc, ok = knownCaps[name]
		if !ok {
			return nil, fmt.Errorf("googleai.DefineModel: called with unknown model %q and nil ModelCapabilities", name)
		}
	} else {
		mc = *caps
	}
	return defineModel(name, mc), nil
}

// requires state.mu
func defineModel(name string, caps ai.ModelCapabilities) *ai.Model {
	meta := &ai.ModelMetadata{
		Label:    "Google AI - " + name,
		Supports: caps,
	}
	g := generator{model: name, client: state.client}
	return ai.DefineModel(provider, name, meta, g.generate)
}

// DefineEmbedder defines an embedder with a given name.
func DefineEmbedder(name string) *ai.Embedder {
	state.mu.Lock()
	defer state.mu.Unlock()
	if !state.initted {
		panic("googleai.Init not called")
	}
	return defineEmbedder(name)
}

// requires state.mu
func defineEmbedder(name string) *ai.Embedder {
	return ai.DefineEmbedder(provider, name, func(ctx context.Context, input *ai.EmbedRequest) ([]float32, error) {
		em := state.client.EmbeddingModel(name)
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
func Model(name string) *ai.Model {
	return ai.LookupModel(provider, name)
}

// Embedder returns the [ai.Embedder] with the given name.
// It returns nil if the embedder was not configured.
func Embedder(name string) *ai.Embedder {
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
	r.Usage = &ai.GenerationUsage{}
	if u := resp.UsageMetadata; u != nil {
		r.Usage.InputTokens = int(u.PromptTokenCount)
		r.Usage.OutputTokens = int(u.CandidatesTokenCount)
		r.Usage.TotalTokens = int(u.TotalTokenCount)
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
