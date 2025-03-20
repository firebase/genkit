// Copyright 2025 Google LLC
// SPDX-License-Identifier: Apache-2.0

// Package gemini contains code that is common to both the googleai and vertexai plugins.
// Most most cannot be shared in this way because the import paths are different.
package gemini

import (
	"context"
	"fmt"
	"net/http"
	"strings"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/internal"
	"github.com/firebase/genkit/go/plugins/internal/uri"
	"google.golang.org/genai"
)

const (
	GoogleAIProvider = "googleai"
	VertexAIProvider = "vertexai"
)

var (
	// BasicText describes model capabilities for text-only Gemini models.
	BasicText = ai.ModelSupports{
		Multiturn:  true,
		Tools:      true,
		ToolChoice: true,
		SystemRole: true,
		Media:      false,
	}

	//  Multimodal describes model capabilities for multimodal Gemini models.
	Multimodal = ai.ModelSupports{
		Multiturn:  true,
		Tools:      true,
		ToolChoice: true,
		SystemRole: true,
		Media:      true,
	}

	// Attribution header
	xGoogApiClientHeader = http.CanonicalHeaderKey("x-goog-api-client")
	GenkitClientHeader   = http.Header{
		xGoogApiClientHeader: {fmt.Sprintf("genkit-go/%s", internal.Version)},
	}
)

// EmbedOptions are options for the Vertex AI embedder.
// Set [ai.EmbedRequest.Options] to a value of type *[EmbedOptions].
type EmbedOptions struct {
	// Document title.
	Title string `json:"title,omitempty"`
	// Task type: RETRIEVAL_QUERY, RETRIEVAL_DOCUMENT, and so forth.
	// See the Vertex AI text embedding docs.
	TaskType string `json:"task_type,omitempty"`
}

// DefineModel defines a model in the registry
func DefineModel(g *genkit.Genkit, client *genai.Client, name string, info ai.ModelInfo) ai.Model {
	provider := GoogleAIProvider
	if client.ClientConfig().Backend == genai.BackendVertexAI {
		provider = VertexAIProvider
	}

	meta := &ai.ModelInfo{
		Label:    info.Label,
		Supports: info.Supports,
		Versions: info.Versions,
	}
	return genkit.DefineModel(g, provider, name, meta, func(
		ctx context.Context,
		input *ai.ModelRequest,
		cb func(context.Context, *ai.ModelResponseChunk) error,
	) (*ai.ModelResponse, error) {
		return Generate(ctx, client, name, input, cb)
	})
}

// DefineEmbedder defines embeddings for the provided contents and embedder
// model
func DefineEmbedder(g *genkit.Genkit, client *genai.Client, name string) ai.Embedder {
	provider := GoogleAIProvider
	if client.ClientConfig().Backend == genai.BackendVertexAI {
		provider = VertexAIProvider
	}

	return genkit.DefineEmbedder(g, provider, name, func(ctx context.Context, input *ai.EmbedRequest) (*ai.EmbedResponse, error) {
		var content []*genai.Content
		var embedConfig *genai.EmbedContentConfig

		// check if request options matches VertexAI configuration
		if opts, _ := input.Options.(*EmbedOptions); opts != nil {
			if provider == GoogleAIProvider {
				return nil, fmt.Errorf("wrong options provided for %s provider, got %T", provider, opts)
			}
			embedConfig = &genai.EmbedContentConfig{
				Title:    opts.Title,
				TaskType: opts.TaskType,
			}
		}

		for _, doc := range input.Documents {
			parts, err := convertParts(doc.Content)
			if err != nil {
				return nil, err
			}
			content = append(content, &genai.Content{
				Parts: parts,
			})
		}

		r, err := genai.Models.EmbedContent(*client.Models, ctx, name, content, embedConfig)
		if err != nil {
			return nil, err
		}
		var res ai.EmbedResponse
		for _, emb := range r.Embeddings {
			res.Embeddings = append(res.Embeddings, &ai.DocumentEmbedding{Embedding: emb.Values})
		}
		return &res, nil
	})
}

// Generate requests a generate call to the specified model with the provided
// configuration
func Generate(
	ctx context.Context,
	client *genai.Client,
	model string,
	input *ai.ModelRequest,
	cb func(context.Context, *ai.ModelResponseChunk) error,
) (*ai.ModelResponse, error) {
	// since context caching is only available for specific model versions, we
	// must make sure the configuration has the right version
	if c, ok := input.Config.(*ai.GenerationCommonConfig); ok {
		if c != nil {
			model = c.Version
		}
	}

	cache, err := handleCache(ctx, client, input, model)
	if err != nil {
		return nil, err
	}

	gc, err := convertRequest(client, model, input, cache)
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
		if cache != nil {
			r.Message.Metadata = setCacheMetadata(r.Message.Metadata, cache)
		}
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
			tc := translateCandidate(c)
			err := cb(ctx, &ai.ModelResponseChunk{
				Content: tc.Message.Content,
			})
			if err != nil {
				return nil, err
			}
			// stream only supports text
			chunks = append(chunks, c.Content.Parts[i].Text)
		}
		// keep the last chunk for usage metadata
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
	if cache != nil {
		r.Message.Metadata = setCacheMetadata(r.Message.Metadata, cache)
	}

	return r, nil
}

// convertRequest translates from [*ai.ModelRequest] to
// *genai.GenerateContentParameters
func convertRequest(client *genai.Client, model string, input *ai.ModelRequest, cache *genai.CachedContent) (*genai.GenerateContentConfig, error) {
	gc := genai.GenerateContentConfig{}
	gc.CandidateCount = genai.Ptr[int32](1)
	if c, ok := input.Config.(*ai.GenerationCommonConfig); ok && c != nil {
		if c.MaxOutputTokens != 0 {
			gc.MaxOutputTokens = genai.Ptr[int32](int32(c.MaxOutputTokens))
		}
		if len(c.StopSequences) > 0 {
			gc.StopSequences = c.StopSequences
		}
		if c.Temperature != 0 {
			gc.Temperature = genai.Ptr[float32](float32(c.Temperature))
		}
		if c.TopK != 0 {
			gc.TopK = genai.Ptr[float32](float32(c.TopK))
		}
		if c.TopP != 0 {
			gc.TopP = genai.Ptr[float32](float32(c.TopP))
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

	if len(systemParts) > 0 {
		gc.SystemInstruction = &genai.Content{
			Parts: systemParts,
			Role:  string(ai.RoleSystem),
		}
	}

	tools, err := convertTools(input.Tools)
	if err != nil {
		return nil, err
	}
	gc.Tools = tools

	choice := convertToolChoice(input.ToolChoice, input.Tools)
	gc.ToolConfig = choice

	if cache != nil {
		gc.CachedContent = cache.Name
	}

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
		panic(fmt.Sprintf("tool choice mode %q not supported", toolChoice))
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

// Translate from a genai.GenerateContentResponse to a ai.ModelResponse.
func translateResponse(resp *genai.GenerateContentResponse) *ai.ModelResponse {
	r := translateCandidate(resp.Candidates[0])

	r.Usage = &ai.GenerationUsage{}
	if u := resp.UsageMetadata; u != nil {
		r.Usage.InputTokens = int(*u.PromptTokenCount)
		r.Usage.OutputTokens = int(*u.CandidatesTokenCount)
		r.Usage.TotalTokens = int(u.TotalTokenCount)
	}
	return r
}

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
		panic("data parts not supported")
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
