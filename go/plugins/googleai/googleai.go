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

// Parts of this file are copied into vertexai, because the code is identical
// except for the import path of the Gemini SDK.
//go:generate go run ../../internal/cmd/copy -dest ../vertexai googleai.go

package googleai

import (
	"context"
	"fmt"
	"os"
	"sync"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/internal"
	"github.com/firebase/genkit/go/plugins/internal/gemini"
	"github.com/firebase/genkit/go/plugins/internal/uri"
	"github.com/google/generative-ai-go/genai"
	"google.golang.org/api/iterator"
	"google.golang.org/api/option"
)

const (
	provider    = "googleai"
	labelPrefix = "Google AI"
)

var state struct {
	mu      sync.Mutex
	initted bool
	// These happen to be the same.
	gclient, pclient *genai.Client
}

var (
	knownCaps = map[string]ai.ModelCapabilities{
		"gemini-1.0-pro":   gemini.BasicText,
		"gemini-1.5-pro":   gemini.Multimodal,
		"gemini-1.5-flash": gemini.Multimodal,
	}

	knownEmbedders = []string{"text-embedding-004", "embedding-001"}
)

// Config is the configuration for the plugin.
type Config struct {
	// The API key to access the service.
	// If empty, the values of the environment variables GOOGLE_GENAI_API_KEY
	// and GOOGLE_API_KEY will be consulted, in that order.
	APIKey string
	// Options to the Google AI client.
	ClientOptions []option.ClientOption
}

// Init initializes the plugin and all known models and embedders.
// After calling Init, you may call [DefineModel] and [DefineEmbedder] to create
// and register any additional generative models and embedders
func Init(ctx context.Context, cfg *Config) (err error) {
	if cfg == nil {
		cfg = &Config{}
	}
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

	apiKey := cfg.APIKey
	if apiKey == "" {
		apiKey = os.Getenv("GOOGLE_GENAI_API_KEY")
		if apiKey == "" {
			apiKey = os.Getenv("GOOGLE_API_KEY")
		}
		if apiKey == "" {
			return fmt.Errorf("Google AI requires setting GOOGLE_GENAI_API_KEY or GOOGLE_API_KEY in the environment. You can get an API key at https://ai.google.dev")
		}
	}

	opts := append([]option.ClientOption{
		option.WithAPIKey(apiKey),
		genai.WithClientInfo("genkit-go", internal.Version)},
		cfg.ClientOptions...,
	)
	client, err := genai.NewClient(ctx, opts...)
	if err != nil {
		return err
	}
	state.gclient = client
	state.pclient = client
	state.initted = true
	for model, caps := range knownCaps {
		defineModel(model, caps)
	}
	for _, e := range knownEmbedders {
		defineEmbedder(e)
	}
	return nil
}

//copy:start vertexai.go defineModel

// DefineModel defines an unknown model with the given name.
// The second argument describes the capability of the model.
// Use [IsDefinedModel] to determine if a model is already defined.
// After [Init] is called, only the known models are defined.
func DefineModel(name string, caps *ai.ModelCapabilities) (*ai.Model, error) {
	state.mu.Lock()
	defer state.mu.Unlock()
	if !state.initted {
		panic(provider + ".Init not called")
	}
	var mc ai.ModelCapabilities
	if caps == nil {
		var ok bool
		mc, ok = knownCaps[name]
		if !ok {
			return nil, fmt.Errorf("%s.DefineModel: called with unknown model %q and nil ModelCapabilities", provider, name)
		}
	} else {
		mc = *caps
	}
	return defineModel(name, mc), nil
}

// requires state.mu
func defineModel(name string, caps ai.ModelCapabilities) *ai.Model {
	meta := &ai.ModelMetadata{
		Label:    labelPrefix + " - " + name,
		Supports: caps,
	}
	return ai.DefineModel(provider, name, meta, func(
		ctx context.Context,
		input *ai.GenerateRequest,
		cb func(context.Context, *ai.GenerateResponseChunk) error,
	) (*ai.GenerateResponse, error) {
		return generate(ctx, state.gclient, name, input, cb)
	})
}

// IsDefinedModel reports whether the named [Model] is defined by this plugin.
func IsDefinedModel(name string) bool {
	return ai.IsDefinedModel(provider, name)
}

//copy:stop

//copy:start vertexai.go defineEmbedder

// DefineEmbedder defines an embedder with a given name.
func DefineEmbedder(name string) *ai.Embedder {
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

//copy:stop

// requires state.mu
func defineEmbedder(name string) *ai.Embedder {
	return ai.DefineEmbedder(provider, name, func(ctx context.Context, input *ai.EmbedRequest) (*ai.EmbedResponse, error) {
		em := state.pclient.EmbeddingModel(name)
		// TODO: set em.TaskType from EmbedRequest.Options?
		batch := em.NewBatch()
		for _, doc := range input.Documents {
			parts, err := convertParts(doc.Content)
			if err != nil {
				return nil, err
			}
			batch.AddContent(parts...)
		}
		bres, err := em.BatchEmbedContents(ctx, batch)
		if err != nil {
			return nil, err
		}
		var res ai.EmbedResponse
		for _, emb := range bres.Embeddings {
			res.Embeddings = append(res.Embeddings, &ai.DocumentEmbedding{Embedding: emb.Values})
		}
		return &res, nil
	})
}

//copy:start vertexai.go lookups

// Model returns the [ai.Model] with the given name.
// It returns nil if the model was not defined.
func Model(name string) *ai.Model {
	return ai.LookupModel(provider, name)
}

// Embedder returns the [ai.Embedder] with the given name.
// It returns nil if the embedder was not defined.
func Embedder(name string) *ai.Embedder {
	return ai.LookupEmbedder(provider, name)
}

//copy:stop

//copy:start vertexai.go generate

func generate(
	ctx context.Context,
	client *genai.Client,
	model string,
	input *ai.GenerateRequest,
	cb func(context.Context, *ai.GenerateResponseChunk) error,
) (*ai.GenerateResponse, error) {
	gm := newModel(client, model, input)
	cs, err := startChat(gm, input)
	if err != nil {
		return nil, err
	}
	// The last message gets added to the parts slice.
	var parts []genai.Part
	if len(input.Messages) > 0 {
		last := input.Messages[len(input.Messages)-1]
		var err error
		parts, err = convertParts(last.Content)
		if err != nil {
			return nil, err
		}
	}

	gm.Tools, err = convertTools(input.Tools)
	if err != nil {
		return nil, err
	}
	// Convert input.Tools and append to gm.Tools

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

func newModel(client *genai.Client, model string, input *ai.GenerateRequest) *genai.GenerativeModel {
	gm := client.GenerativeModel(model)
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
	return gm
}

// startChat starts a chat session and configures it with the input messages.
func startChat(gm *genai.GenerativeModel, input *ai.GenerateRequest) (*genai.ChatSession, error) {
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
	return cs, nil
}
func convertTools(inTools []*ai.ToolDefinition) ([]*genai.Tool, error) {
	var outTools []*genai.Tool
	for _, t := range inTools {
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
				return nil, fmt.Errorf("schema value %q not allowed", v)
			}
			schema.Properties[k] = &genai.Schema{Type: typ}
		}
		fd := &genai.FunctionDeclaration{
			Name:        t.Name,
			Parameters:  schema,
			Description: t.Description,
		}
		outTools = append(outTools, &genai.Tool{FunctionDeclarations: []*genai.FunctionDeclaration{fd}})
	}
	return outTools, nil
}

//copy:stop

//copy:start vertexai.go translateCandidate

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

//copy:stop

//copy:start vertexai.go translateResponse

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

//copy:stop

//copy:start vertexai.go convertParts

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
		panic(fmt.Sprintf("%s does not support Data parts", provider))
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

//copy:stop
