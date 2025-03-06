// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

// Parts of this file are copied into vertexai, because the code is identical
// except for the import path of the Gemini SDK.
//go:generate go run ../../internal/cmd/copy -dest ../vertexai googleai.go

package googleai

import (
	"context"
	"fmt"
	"os"
	"strings"
	"sync"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/internal"
	"github.com/firebase/genkit/go/plugins/internal/gemini"
	"github.com/firebase/genkit/go/plugins/internal/uri"

	googleai "github.com/google/generative-ai-go/genai"
	"google.golang.org/api/option"
	"google.golang.org/genai"
)

const (
	provider    = "googleai"
	labelPrefix = "Google AI"
)

var state struct {
	gclient *genai.Client
	// TODO: prediction client should use the genai module but embedding support
	// is not enabled yet
	pclient *googleai.Client
	mu      sync.Mutex
	initted bool
}

var (
	supportedModels = map[string]ai.ModelInfo{
		"gemini-1.5-flash": {
			Versions: []string{
				"gemini-1.5-flash-latest",
				"gemini-1.5-flash-001",
				"gemini-1.5-flash-002",
			},
			Supports: &gemini.Multimodal,
		},
		"gemini-1.5-pro": {
			Versions: []string{
				"gemini-1.5-pro-latest",
				"gemini-1.5-pro-001",
				"gemini-1.5-pro-002",
			},
			Supports: &gemini.Multimodal,
		},
		"gemini-1.5-flash-8b": {
			Versions: []string{
				"gemini-1.5-flash-8b-latest",
				"gemini-1.5-flash-8b-001",
			},
			Supports: &gemini.Multimodal,
		},
		"gemini-2.0-flash": {
			Versions: []string{
				"gemini-2.0-flash-001",
			},
			Supports: &gemini.Multimodal,
		},
		"gemini-2.0-flash-lite": {
			Versions: []string{
				"gemini-2.0-flash-lite-001",
			},
			Supports: &gemini.Multimodal,
		},
		"gemini-2.0-pro-exp-02-05": {
			Versions: []string{},
			Supports: &gemini.Multimodal,
		},
		"gemini-2.0-flash-thinking-exp-01-21": {
			Versions: []string{},
			Supports: &gemini.Multimodal,
		},
	}

	knownEmbedders = []string{
		"text-embedding-004",
		"embedding-001",
	}
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
func Init(ctx context.Context, g *genkit.Genkit, cfg *Config) (err error) {
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
		googleai.WithClientInfo("genkit-go", internal.Version),
	},
		cfg.ClientOptions...,
	)

	client, err := genai.NewClient(ctx, &genai.ClientConfig{
		APIKey:  apiKey,
		Backend: genai.BackendGeminiAPI,
	})
	if err != nil {
		return err
	}

	pclient, err := googleai.NewClient(ctx, opts...)
	if err != nil {
		return err
	}

	state.gclient = client
	state.pclient = pclient
	state.initted = true
	for model, details := range supportedModels {
		defineModel(g, model, details)
	}
	for _, e := range knownEmbedders {
		defineEmbedder(g, e)
	}
	return nil
}

//copy:start vertexai.go defineModel

// DefineModel defines an unknown model with the given name.
// The second argument describes the capability of the model.
// Use [IsDefinedModel] to determine if a model is already defined.
// After [Init] is called, only the known models are defined.
func DefineModel(g *genkit.Genkit, name string, info *ai.ModelInfo) (ai.Model, error) {
	state.mu.Lock()
	defer state.mu.Unlock()
	if !state.initted {
		panic(provider + ".Init not called")
	}
	var mi ai.ModelInfo
	if info == nil {
		var ok bool
		mi, ok = supportedModels[name]
		if !ok {
			return nil, fmt.Errorf("%s.DefineModel: called with unknown model %q and nil ModelInfo", provider, name)
		}
	} else {
		// TODO: unknown models could also specify versions?
		mi = *info
	}
	return defineModel(g, name, mi), nil
}

// requires state.mu
func defineModel(g *genkit.Genkit, name string, info ai.ModelInfo) ai.Model {
	meta := &ai.ModelInfo{
		Label:    labelPrefix + " - " + name,
		Supports: info.Supports,
		Versions: info.Versions,
	}
	return genkit.DefineModel(g, provider, name, meta, func(
		ctx context.Context,
		input *ai.ModelRequest,
		cb func(context.Context, *ai.ModelResponseChunk) error,
	) (*ai.ModelResponse, error) {
		return generate(ctx, state.gclient, name, input, cb)
	})
}

// IsDefinedModel reports whether the named [Model] is defined by this plugin.
func IsDefinedModel(g *genkit.Genkit, name string) bool {
	return genkit.IsDefinedModel(g, provider, name)
}

//copy:stop

//copy:start vertexai.go defineEmbedder

// DefineEmbedder defines an embedder with a given name.
func DefineEmbedder(g *genkit.Genkit, name string) ai.Embedder {
	state.mu.Lock()
	defer state.mu.Unlock()
	if !state.initted {
		panic(provider + ".Init not called")
	}
	return defineEmbedder(g, name)
}

// IsDefinedEmbedder reports whether the named [Embedder] is defined by this plugin.
func IsDefinedEmbedder(g *genkit.Genkit, name string) bool {
	return genkit.IsDefinedEmbedder(g, provider, name)
}

//copy:stop

// requires state.mu
func defineEmbedder(g *genkit.Genkit, name string) ai.Embedder {
	return genkit.DefineEmbedder(g, provider, name, func(ctx context.Context, input *ai.EmbedRequest) (*ai.EmbedResponse, error) {
		em := state.pclient.EmbeddingModel(name)
		// TODO: set em.TaskType from EmbedRequest.Options?
		batch := em.NewBatch()
		for _, doc := range input.Documents {
			parts, err := convertGoogleaiParts(doc.Content)
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

// convertParts converts a slice of *ai.Part to a slice of genai.Part.
func convertGoogleaiParts(parts []*ai.Part) ([]googleai.Part, error) {
	res := make([]googleai.Part, 0, len(parts))
	for _, p := range parts {
		part, err := convertGoogleaiPart(p)
		if err != nil {
			return nil, err
		}
		res = append(res, part)
	}
	return res, nil
}

// convertPart converts a *ai.Part to a genai.Part.
func convertGoogleaiPart(p *ai.Part) (googleai.Part, error) {
	switch {
	case p.IsText():
		return googleai.Text(p.Text), nil
	case p.IsMedia():
		contentType, data, err := uri.Data(p)
		if err != nil {
			return nil, err
		}
		return googleai.Blob{MIMEType: contentType, Data: data}, nil
	case p.IsData():
		panic(fmt.Sprintf("%s does not support Data parts", provider))
	case p.IsToolResponse():
		toolResp := p.ToolResponse
		var output map[string]any
		if m, ok := toolResp.Output.(map[string]any); ok {
			output = m
		} else {
			output = map[string]any{
				"name":    toolResp.Name,
				"content": toolResp.Output,
			}
		}
		fr := googleai.FunctionResponse{
			Name:     toolResp.Name,
			Response: output,
		}
		return fr, nil
	case p.IsToolRequest():
		toolReq := p.ToolRequest
		var input map[string]any
		if m, ok := toolReq.Input.(map[string]any); ok {
			input = m
		} else {
			input = map[string]any{
				"input": toolReq.Input,
			}
		}
		fc := googleai.FunctionCall{
			Name: toolReq.Name,
			Args: input,
		}
		return fc, nil
	default:
		panic("unknown part type in a request")
	}
}

//copy:start vertexai.go lookups

// Model returns the [ai.Model] with the given name.
// It returns nil if the model was not defined.
func Model(g *genkit.Genkit, name string) ai.Model {
	return genkit.LookupModel(g, provider, name)
}

// Embedder returns the [ai.Embedder] with the given name.
// It returns nil if the embedder was not defined.
func Embedder(g *genkit.Genkit, name string) ai.Embedder {
	return genkit.LookupEmbedder(g, provider, name)
}

//copy:stop

//copy:start vertexai.go generate

func generate(
	ctx context.Context,
	client *genai.Client,
	model string,
	input *ai.ModelRequest,
	cb func(context.Context, *ai.ModelResponseChunk) error,
) (*ai.ModelResponse, error) {
	gc, err := convertRequest(client, model, input)
	if err != nil {
		return nil, err
	}

	var contents []*genai.Content
	for _, m := range input.Messages {
		if m.Role == ai.RoleSystem {
			continue
		}
		parts, err := convertParts(m.Content)
		if err != nil {
			return nil, err
		}
		contents = append(contents, &genai.Content{
			Parts: parts,
			Role:  string(m.Role),
		})
	}

	// Send out the actual request.
	if cb == nil {
		resp, err := client.Models.GenerateContent(ctx, model, contents, gc)
		if err != nil {
			return nil, err
		}
		r := translateResponse(resp)
		r.Request = input
		return r, nil
	}

	// Streaming version.
	iter := client.Models.GenerateContentStream(ctx, model, contents, gc)
	var r *ai.ModelResponse

	// merge all streamed responses
	var resp *genai.GenerateContentResponse
	var chunks []string
	for chunk, err := range iter {
		// abort stream if error found in the iterator items
		if err != nil {
			return nil, err
		}
		for i, c := range chunk.Candidates {
			tc := translateCandidate((c))
			err := cb(ctx, &ai.ModelResponseChunk{
				Content: tc.Message.Content,
			})
			if err != nil {
				return nil, err
			}
			// stream only supports text
			chunks = append(chunks, c.Content.Parts[i].Text)
		}
		// keep the last chunk
		resp = chunk
	}

	// manually merge all candidate responses, iterator does not provide a
	// merged response utility
	merged := []*genai.Candidate{
		{
			Content: &genai.Content{
				Parts: []*genai.Part{genai.NewPartFromText(strings.Join(chunks, ""))},
			},
		},
	}
	resp.Candidates = merged
	r = translateResponse(resp)

	if r == nil {
		// No candidates were returned. Probably rare, but it might avoid a NPE
		// to return an empty instead of nil result.
		r = &ai.ModelResponse{}
	}
	r.Request = input
	return r, nil
}

func int64Ptr(n int) *int64 {
	val := int64(n)
	return &val
}

// float64Ptr converts an int to a *float64
func float64Ptr(n int) *float64 {
	val := float64(n)
	return &val
}

// convertRequest translates from [*ai.ModelRequest] to
// *genai.GenerateContentParameters
func convertRequest(client *genai.Client, model string, input *ai.ModelRequest) (*genai.GenerateContentConfig, error) {
	gc := genai.GenerateContentConfig{}
	gc.CandidateCount = int64Ptr(1)
	if c, ok := input.Config.(*ai.GenerationCommonConfig); ok && c != nil {
		if c.MaxOutputTokens != 0 {
			gc.MaxOutputTokens = int64Ptr(c.MaxOutputTokens)
		}
		if len(c.StopSequences) > 0 {
			gc.StopSequences = c.StopSequences
		}
		if c.Temperature != 0 {
			gc.Temperature = &c.Temperature
		}
		if c.TopK != 0 {
			gc.TopK = float64Ptr(c.TopK)
		}
		if c.TopP != 0 {
			gc.TopP = &c.TopP
		}
	}

	var systemParts []*genai.Part
	for _, m := range input.Messages {
		if m.Role == ai.RoleSystem {
			parts, err := convertParts(m.Content)
			if err != nil {
				return nil, err
			}
			systemParts = append(systemParts, parts...)
		}
	}

	// configure system instruction
	if len(systemParts) > 0 {
		gc.SystemInstruction = &genai.Content{
			Parts: systemParts,
			Role:  string(ai.RoleSystem),
		}
	}

	// configure tools
	tools, err := convertTools(input.Tools)
	if err != nil {
		return nil, err
	}
	gc.Tools = tools

	// configure tool choice
	choice := convertToolChoice(input.ToolChoice, input.Tools)
	gc.ToolConfig = choice

	// TODO: configure cache

	return &gc, nil
}

// convertTools translates an [*ai.ToolDefinition] to a *genai.Tool
func convertTools(inTools []*ai.ToolDefinition) ([]*genai.Tool, error) {
	var outTools []*genai.Tool
	for _, t := range inTools {
		inputSchema, err := convertSchema(t.InputSchema, t.InputSchema)
		if err != nil {
			return nil, err
		}
		fd := &genai.FunctionDeclaration{
			Name:        t.Name,
			Parameters:  inputSchema,
			Description: t.Description,
		}
		outTools = append(outTools, &genai.Tool{FunctionDeclarations: []*genai.FunctionDeclaration{fd}})
	}
	return outTools, nil
}

func convertSchema(originalSchema map[string]any, genkitSchema map[string]any) (*genai.Schema, error) {
	// this covers genkitSchema == nil and {}
	// genkitSchema will be {} if it's any
	if len(genkitSchema) == 0 {
		return nil, nil
	}
	if v, ok := genkitSchema["$ref"]; ok {
		ref := v.(string)
		return convertSchema(originalSchema, resolveRef(originalSchema, ref))
	}
	schema := &genai.Schema{}

	switch genkitSchema["type"].(string) {
	case "string":
		schema.Type = genai.TypeString
	case "float64":
		schema.Type = genai.TypeNumber
	case "number":
		schema.Type = genai.TypeNumber
	case "integer":
		schema.Type = genai.TypeInteger
	case "bool":
		schema.Type = genai.TypeBoolean
	case "object":
		schema.Type = genai.TypeObject
	case "array":
		schema.Type = genai.TypeArray
	default:
		return nil, fmt.Errorf("schema type %q not allowed", genkitSchema["type"])
	}
	if v, ok := genkitSchema["required"]; ok {
		schema.Required = castToStringArray(v.([]any))
	}
	if v, ok := genkitSchema["description"]; ok {
		schema.Description = v.(string)
	}
	if v, ok := genkitSchema["format"]; ok {
		schema.Format = v.(string)
	}
	if v, ok := genkitSchema["enum"]; ok {
		schema.Enum = castToStringArray(v.([]any))
	}
	if v, ok := genkitSchema["items"]; ok {
		items, err := convertSchema(originalSchema, v.(map[string]any))
		if err != nil {
			return nil, err
		}
		schema.Items = items
	}
	if val, ok := genkitSchema["properties"]; ok {
		props := map[string]*genai.Schema{}
		for k, v := range val.(map[string]any) {
			p, err := convertSchema(originalSchema, v.(map[string]any))
			if err != nil {
				return nil, err
			}
			props[k] = p
		}
		schema.Properties = props
	}
	// Nullable -- not supported in jsonschema.Schema

	return schema, nil
}

func resolveRef(originalSchema map[string]any, ref string) map[string]any {
	tkns := strings.Split(ref, "/")
	// refs look like: $/ref/foo -- we need the foo part
	name := tkns[len(tkns)-1]
	defs := originalSchema["$defs"].(map[string]any)
	return defs[name].(map[string]any)
}

func castToStringArray(i []any) []string {
	// Is there a better way to do this??
	var r []string
	for _, v := range i {
		r = append(r, v.(string))
	}
	return r
}

func convertToolChoice(toolChoice ai.ToolChoice, tools []*ai.ToolDefinition) *genai.ToolConfig {
	var mode genai.FunctionCallingConfigMode
	switch toolChoice {
	case "":
		return nil
	case ai.ToolChoiceAuto:
		mode = genai.FunctionCallingConfigModeAuto
	case ai.ToolChoiceRequired:
		mode = genai.FunctionCallingConfigModeAny
	case ai.ToolChoiceNone:
		mode = genai.FunctionCallingConfigModeNone
	default:
		panic(fmt.Sprintf("%s does not support tool choice mode %q", provider, toolChoice))
	}

	var toolNames []string
	// Per docs, only set AllowedToolNames with mode set to ANY.
	if mode == genai.FunctionCallingConfigModeAny {
		for _, t := range tools {
			toolNames = append(toolNames, t.Name)
		}
	}
	return &genai.ToolConfig{
		FunctionCallingConfig: &genai.FunctionCallingConfig{
			Mode:                 mode,
			AllowedFunctionNames: toolNames,
		},
	}
}

//copy:stop

//copy:start vertexai.go translateCandidate

// translateCandidate translates from a genai.GenerateContentResponse to an ai.ModelResponse.
func translateCandidate(cand *genai.Candidate) *ai.ModelResponse {
	m := &ai.ModelResponse{}
	switch cand.FinishReason {
	case genai.FinishReasonStop:
		m.FinishReason = ai.FinishReasonStop
	case genai.FinishReasonMaxTokens:
		m.FinishReason = ai.FinishReasonLength
	case genai.FinishReasonSafety:
		m.FinishReason = ai.FinishReasonBlocked
	case genai.FinishReasonRecitation:
		m.FinishReason = ai.FinishReasonBlocked
	case genai.FinishReasonOther:
		m.FinishReason = ai.FinishReasonOther
	default: // Unspecified
		m.FinishReason = ai.FinishReasonUnknown
	}
	msg := &ai.Message{}
	msg.Role = ai.Role(cand.Content.Role)

	// iterate over the candidate parts, only one struct member
	// must be populated, more than one is considered an error
	for _, part := range cand.Content.Parts {
		var p *ai.Part
		partFound := 0

		if part.Text != "" {
			partFound++
			p = ai.NewTextPart(part.Text)
		}
		if part.InlineData != nil {
			partFound++
			p = ai.NewMediaPart(part.InlineData.MIMEType, string(part.InlineData.Data))
		}
		if part.FunctionCall != nil {
			partFound++
			p = ai.NewToolRequestPart(&ai.ToolRequest{
				Name:  part.FunctionCall.Name,
				Input: part.FunctionCall.Args,
			})
		}
		if partFound > 1 {
			panic(fmt.Sprintf("expected only 1 content part in response, got %d, part: %#v", partFound, part))
		}

		msg.Content = append(msg.Content, p)
	}
	m.Message = msg
	return m
}

//copy:stop

//copy:start vertexai.go translateResponse

// Translate from a genai.GenerateContentResponse to a ai.ModelResponse.
func translateResponse(resp *genai.GenerateContentResponse) *ai.ModelResponse {
	r := translateCandidate(resp.Candidates[0])

	fmt.Printf("token usage: %#v\n\n", resp.UsageMetadata)
	r.Usage = &ai.GenerationUsage{}
	if u := resp.UsageMetadata; u != nil {
		r.Usage.InputTokens = int(*u.PromptTokenCount)
		r.Usage.OutputTokens = int(*u.CandidatesTokenCount)
		r.Usage.TotalTokens = int(u.TotalTokenCount)
	}
	return r
}

//copy:stop

//copy:start vertexai.go convertParts

// convertParts converts a slice of *ai.Part to a slice of genai.Part.
func convertParts(parts []*ai.Part) ([]*genai.Part, error) {
	res := make([]*genai.Part, 0, len(parts))
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
func convertPart(p *ai.Part) (*genai.Part, error) {
	switch {
	case p.IsText():
		return genai.NewPartFromText(p.Text), nil
	case p.IsMedia():
		contentType, data, err := uri.Data(p)
		if err != nil {
			return nil, err
		}
		return genai.NewPartFromBytes(data, contentType), nil
	case p.IsData():
		panic(fmt.Sprintf("%s does not support Data parts", provider))
	case p.IsToolResponse():
		toolResp := p.ToolResponse
		var output map[string]any
		if m, ok := toolResp.Output.(map[string]any); ok {
			output = m
		} else {
			output = map[string]any{
				"name":    toolResp.Name,
				"content": toolResp.Output,
			}
		}
		fr := genai.NewPartFromFunctionResponse(toolResp.Name, output)
		return fr, nil
	case p.IsToolRequest():
		toolReq := p.ToolRequest
		var input map[string]any
		if m, ok := toolReq.Input.(map[string]any); ok {
			input = m
		} else {
			input = map[string]any{
				"input": toolReq.Input,
			}
		}
		fc := genai.NewPartFromFunctionCall(toolReq.Name, input)
		return fc, nil
	default:
		panic("unknown part type in a request")
	}
}

//copy:stop
