// Copyright 2025 Google LLC
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
//
// SPDX-License-Identifier: Apache-2.0

package googlegenai

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"net/url"
	"reflect"
	"regexp"
	"slices"
	"strconv"
	"strings"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/core/api"
	"github.com/firebase/genkit/go/internal"
	"github.com/firebase/genkit/go/internal/base"
	"github.com/firebase/genkit/go/plugins/internal/uri"
	"github.com/invopop/jsonschema"
	"google.golang.org/genai"
)

const (
	// Tool name regex
	toolNameRegex = "^[a-zA-Z_][a-zA-Z0-9_.-]{0,63}$"
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
		Multiturn:   true,
		Tools:       true,
		ToolChoice:  true,
		SystemRole:  true,
		Media:       true,
		Constrained: ai.ConstrainedSupportNoTools,
	}

	// Attribution header
	xGoogApiClientHeader = http.CanonicalHeaderKey("x-goog-api-client")
	genkitClientHeader   = http.Header{
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

// configToMap converts a config struct to a map[string]any.
func configToMap(config any) map[string]any {
	r := jsonschema.Reflector{
		DoNotReference: true, // Prevent $ref usage
		ExpandedStruct: true, // Include all fields directly
		// NOTE: keep track of updated fields in [genai.GenerateContentConfig] since
		// they could create runtime panics when parsing fields with type recursion
		IgnoredTypes: []any{
			genai.Schema{},
		},
	}

	schema := r.Reflect(config)
	result := base.SchemaAsMap(schema)
	return result
}

// mapToStruct unmarshals a map[string]any to the expected config api.
func mapToStruct(m map[string]any, v any) error {
	jsonData, err := json.Marshal(m)
	if err != nil {
		return err
	}
	return json.Unmarshal(jsonData, v)
}

// configFromRequest converts any supported config type to [genai.GenerateContentConfig].
func configFromRequest(input *ai.ModelRequest) (*genai.GenerateContentConfig, error) {
	var result genai.GenerateContentConfig

	switch config := input.Config.(type) {
	case genai.GenerateContentConfig:
		result = config
	case *genai.GenerateContentConfig:
		result = *config
	case map[string]any:
		// TODO: Log warnings if unknown parameters are found.
		if err := mapToStruct(config, &result); err != nil {
			return nil, err
		}
	case nil:
		// Empty but valid config
	default:
		return nil, fmt.Errorf("unexpected config type: %T", input.Config)
	}

	return &result, nil
}

// newModel creates a model without registering it
func newModel(client *genai.Client, name string, opts ai.ModelOptions) ai.Model {
	provider := googleAIProvider
	if client.ClientConfig().Backend == genai.BackendVertexAI {
		provider = vertexAIProvider
	}

	var config any
	config = &genai.GenerateContentConfig{}
	if strings.Contains(name, "imagen") {
		config = &genai.GenerateImagesConfig{}
	} else if vi, fnd := supportedVideoModels[name]; fnd {
		config = &genai.GenerateVideosConfig{}
		opts = vi
	}
	meta := &ai.ModelOptions{
		Label:        opts.Label,
		Supports:     opts.Supports,
		Versions:     opts.Versions,
		ConfigSchema: configToMap(config),
		Stage:        opts.Stage,
	}

	fn := func(
		ctx context.Context,
		input *ai.ModelRequest,
		cb func(context.Context, *ai.ModelResponseChunk) error,
	) (*ai.ModelResponse, error) {
		switch config.(type) {
		case *genai.GenerateImagesConfig:
			return generateImage(ctx, client, name, input, cb)
		default:
			return generate(ctx, client, name, input, cb)
		}
	}
	// the gemini api doesn't support downloading media from http(s)
	if opts.Supports.Media {
		fn = core.ChainMiddleware(ai.DownloadRequestMedia(&ai.DownloadMediaOptions{
			MaxBytes: 1024 * 1024 * 20, // 20MB
			Filter: func(part *ai.Part) bool {
				u, err := url.Parse(part.Text)
				if err != nil {
					return true
				}
				// Gemini can handle these URLs
				return !slices.Contains(
					[]string{
						"generativelanguage.googleapis.com",
						"www.youtube.com", "youtube.com", "youtu.be",
					},
					u.Hostname(),
				)
			},
		}))(fn)
	}
	return ai.NewModel(api.NewName(provider, name), meta, fn)
}

// newEmbedder creates an embedder without registering it
func newEmbedder(client *genai.Client, name string, embedOpts *ai.EmbedderOptions) ai.Embedder {
	provider := googleAIProvider
	if client.ClientConfig().Backend == genai.BackendVertexAI {
		provider = vertexAIProvider
	}

	if embedOpts.ConfigSchema == nil {
		embedOpts.ConfigSchema = core.InferSchemaMap(genai.EmbedContentConfig{})
	}

	return ai.NewEmbedder(api.NewName(provider, name), embedOpts, func(ctx context.Context, req *ai.EmbedRequest) (*ai.EmbedResponse, error) {
		var content []*genai.Content
		var embedConfig *genai.EmbedContentConfig

		if config, ok := req.Options.(*genai.EmbedContentConfig); ok {
			embedConfig = config
		}

		for _, doc := range req.Input {
			parts, err := toGeminiParts(doc.Content)
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
			res.Embeddings = append(res.Embeddings, &ai.Embedding{Embedding: emb.Values})
		}
		return &res, nil
	})
}

// Generate requests generate call to the specified model with the provided
// configuration
func generate(
	ctx context.Context,
	client *genai.Client,
	model string,
	input *ai.ModelRequest,
	cb func(context.Context, *ai.ModelResponseChunk) error,
) (*ai.ModelResponse, error) {
	if model == "" {
		return nil, errors.New("model not provided")
	}

	cache, err := handleCache(ctx, client, input, model)
	if err != nil {
		return nil, err
	}

	gcc, err := toGeminiRequest(input, cache)
	if err != nil {
		return nil, err
	}

	var contents []*genai.Content
	for _, m := range input.Messages {
		// system parts are handled separately
		if m.Role == ai.RoleSystem {
			continue
		}

		parts, err := toGeminiParts(m.Content)
		if err != nil {
			return nil, err
		}

		contents = append(contents, &genai.Content{
			Parts: parts,
			Role:  string(m.Role),
		})
	}
	if len(contents) == 0 {
		return nil, fmt.Errorf("at least one message is required in generate request")
	}

	// Send out the actual request.
	if cb == nil {
		resp, err := client.Models.GenerateContent(ctx, model, contents, gcc)
		if err != nil {
			return nil, err
		}
		r, err := translateResponse(resp)
		if err != nil {
			return nil, err
		}

		r.Request = input
		if cache != nil {
			r.Message.Metadata = cacheMetadata(r.Message.Metadata, cache)
		}
		return r, nil
	}

	// Streaming version.
	iter := client.Models.GenerateContentStream(ctx, model, contents, gcc)

	var r *ai.ModelResponse
	var genaiResp *genai.GenerateContentResponse

	genaiParts := []*genai.Part{}
	chunks := []*ai.Part{}
	for chunk, err := range iter {
		// abort stream if error found in the iterator items
		if err != nil {
			return nil, err
		}
		for _, c := range chunk.Candidates {
			tc, err := translateCandidate(c)
			if err != nil {
				return nil, err
			}
			err = cb(ctx, &ai.ModelResponseChunk{
				Content: tc.Message.Content,
				Role:    ai.RoleModel,
			})
			if err != nil {
				return nil, err
			}
			genaiParts = append(genaiParts, c.Content.Parts...)
			chunks = append(chunks, tc.Message.Content...)
		}
		genaiResp = chunk

	}

	if len(genaiResp.Candidates) == 0 {
		return nil, fmt.Errorf("no valid candidates found")
	}

	// preserve original parts since they will be included in the
	// "custom" response field
	merged := []*genai.Candidate{
		{
			FinishReason: genaiResp.Candidates[0].FinishReason,
			Content: &genai.Content{
				Role:  string(ai.RoleModel),
				Parts: genaiParts,
			},
		},
	}

	genaiResp.Candidates = merged
	r, err = translateResponse(genaiResp)
	r.Message.Content = chunks

	if err != nil {
		return nil, fmt.Errorf("failed to generate contents: %w", err)
	}
	r.Request = input
	if cache != nil {
		r.Message.Metadata = cacheMetadata(r.Message.Metadata, cache)
	}

	return r, nil
}

// toGeminiRequest translates an [*ai.ModelRequest] to
// *genai.GenerateContentConfig
func toGeminiRequest(input *ai.ModelRequest, cache *genai.CachedContent) (*genai.GenerateContentConfig, error) {
	gcc, err := configFromRequest(input)
	if err != nil {
		return nil, err
	}

	// candidate count might not be set to 1 and will keep its zero value if not set
	// e.g. default value from reflection server is 0
	if gcc.CandidateCount == 0 {
		gcc.CandidateCount = 1
	}

	// Genkit primitive fields must be used instead of go-genai fields
	// i.e.: system prompt, tools, cached content, response schema, etc
	if gcc.CandidateCount != 1 {
		return nil, errors.New("multiple candidates is not supported")
	}
	if gcc.SystemInstruction != nil {
		return nil, errors.New("system instruction must be set using Genkit feature: ai.WithSystemPrompt()")
	}
	if gcc.CachedContent != "" {
		return nil, errors.New("cached content must be set using Genkit feature: ai.WithCacheTTL()")
	}
	if gcc.ResponseSchema != nil {
		return nil, errors.New("response schema must be set using Genkit feature: ai.WithTools() or ai.WithOuputType()")
	}
	if gcc.ResponseMIMEType != "" {
		return nil, errors.New("response MIME type must be set using Genkit feature: ai.WithOuputType(), ai.WithOutputSchema(), ai.WithOutputSchemaByName()")
	}
	if gcc.ResponseJsonSchema != nil {
		return nil, errors.New("response JSON schema must be set using Genkit feature: ai.WithOutputSchema()")
	}

	// Set response MIME type and schema based on output format.
	// Gemini supports constrained output with application/json and text/x.enum.
	hasOutput := input.Output != nil
	// JSON mode is not compatible with tools
	if hasOutput && len(input.Tools) == 0 {
		switch {
		case input.Output.ContentType == "application/json" || input.Output.Format == "json":
			gcc.ResponseMIMEType = "application/json"
		case input.Output.ContentType == "text/enum" || input.Output.Format == "enum":
			gcc.ResponseMIMEType = "text/x.enum"
		}
	}

	if input.Output != nil && input.Output.Constrained && gcc.ResponseMIMEType != "" {
		schema, err := toGeminiSchema(input.Output.Schema, input.Output.Schema)
		if err != nil {
			return nil, err
		}
		gcc.ResponseSchema = schema
	}

	// Add tool configuration from input.Tools and input.ToolChoice directly
	// Merge with existing tools to preserve Gemini-specific tools (Retrieval, GoogleSearch, CodeExecution)
	if len(input.Tools) > 0 {
		// First convert the tools
		tools, err := toGeminiTools(input.Tools)
		if err != nil {
			return nil, err
		}
		gcc.Tools = mergeTools(append(gcc.Tools, tools...))

		// Then set up the tool configuration based on ToolChoice
		tc, err := toGeminiToolChoice(input.ToolChoice, input.Tools)
		if err != nil {
			return nil, err
		}
		gcc.ToolConfig = tc
	}

	var systemParts []*genai.Part
	for _, m := range input.Messages {
		if m.Role == ai.RoleSystem {
			parts, err := toGeminiParts(m.Content)
			if err != nil {
				return nil, err
			}
			systemParts = append(systemParts, parts...)
		}
	}

	if len(systemParts) > 0 {
		gcc.SystemInstruction = &genai.Content{
			Parts: systemParts,
			Role:  string(ai.RoleSystem),
		}
	}

	if cache != nil {
		gcc.CachedContent = cache.Name
	}

	return gcc, nil
}

// toGeminiTools translates a slice of [ai.ToolDefinition] to a slice of [genai.Tool].
func toGeminiTools(inTools []*ai.ToolDefinition) ([]*genai.Tool, error) {
	var outTools []*genai.Tool
	functions := []*genai.FunctionDeclaration{}

	for _, t := range inTools {
		if !validToolName(t.Name) {
			return nil, fmt.Errorf(`invalid tool name: %q, must start with a letter or an underscore, must be alphanumeric, underscores, dots or dashes with a max length of 64 chars`, t.Name)
		}
		inputSchema, err := toGeminiSchema(t.InputSchema, t.InputSchema)
		if err != nil {
			return nil, err
		}
		fd := &genai.FunctionDeclaration{
			Name:        t.Name,
			Parameters:  inputSchema,
			Description: t.Description,
		}
		functions = append(functions, fd)
	}

	if len(functions) > 0 {
		outTools = append(outTools, &genai.Tool{
			FunctionDeclarations: functions,
		})
	}

	return outTools, nil
}

// toGeminiFunctionResponsePart translates a slice of [ai.Part] to a slice of [genai.FunctionResponsePart]
func toGeminiFunctionResponsePart(parts []*ai.Part) ([]*genai.FunctionResponsePart, error) {
	frp := []*genai.FunctionResponsePart{}
	for _, p := range parts {
		switch {
		case p.IsData():
			contentType, data, err := uri.Data(p)
			if err != nil {
				return nil, err
			}
			frp = append(frp, genai.NewFunctionResponsePartFromBytes(data, contentType))
		case p.IsMedia():
			if strings.HasPrefix(p.Text, "data:") {
				contentType, data, err := uri.Data(p)
				if err != nil {
					return nil, err
				}
				frp = append(frp, genai.NewFunctionResponsePartFromBytes(data, contentType))
				continue
			}
			frp = append(frp, genai.NewFunctionResponsePartFromURI(p.Text, p.ContentType))
		default:
			return nil, fmt.Errorf("unsupported function response part type: %d", p.Kind)
		}
	}
	return frp, nil
}

// mergeTools consolidates all FunctionDeclarations into a single Tool
// while preserving non-function tools (Retrieval, GoogleSearch, CodeExecution, etc.)
func mergeTools(ts []*genai.Tool) []*genai.Tool {
	var decls []*genai.FunctionDeclaration
	var out []*genai.Tool

	for _, t := range ts {
		if t == nil {
			continue
		}
		if len(t.FunctionDeclarations) == 0 {
			out = append(out, t)
			continue
		}
		decls = append(decls, t.FunctionDeclarations...)
		if cpy := cloneToolWithoutFunctions(t); cpy != nil && !reflect.ValueOf(*cpy).IsZero() {
			out = append(out, cpy)
		}
	}

	if len(decls) > 0 {
		out = append([]*genai.Tool{{FunctionDeclarations: decls}}, out...)
	}
	return out
}

func cloneToolWithoutFunctions(t *genai.Tool) *genai.Tool {
	if t == nil {
		return nil
	}
	clone := *t
	clone.FunctionDeclarations = nil
	return &clone
}

// toGeminiSchema translates a map representing a standard JSON schema to a more
// limited [genai.Schema].
func toGeminiSchema(originalSchema map[string]any, genkitSchema map[string]any) (*genai.Schema, error) {
	// this covers genkitSchema == nil and {}
	// genkitSchema will be {} if it's any
	if len(genkitSchema) == 0 {
		return nil, nil
	}
	if v, ok := genkitSchema["$ref"]; ok {
		ref, ok := v.(string)
		if !ok {
			return nil, fmt.Errorf("invalid $ref value: not a string")
		}
		s, err := resolveRef(originalSchema, ref)
		if err != nil {
			return nil, err
		}
		return toGeminiSchema(originalSchema, s)
	}

	// Handle "anyOf" subschemas by finding the first valid schema definition
	if v, ok := genkitSchema["anyOf"]; ok {
		if anyOfList, isList := v.([]map[string]any); isList {
			for _, subSchema := range anyOfList {
				if subSchemaType, hasType := subSchema["type"]; hasType {
					if typeStr, isString := subSchemaType.(string); isString && typeStr != "null" {
						if title, ok := genkitSchema["title"]; ok {
							subSchema["title"] = title
						}
						if description, ok := genkitSchema["description"]; ok {
							subSchema["description"] = description
						}
						// Found a schema like: {"type": "string"}
						return toGeminiSchema(originalSchema, subSchema)
					}
				}
			}
		}
	}

	schema := &genai.Schema{}
	typeVal, ok := genkitSchema["type"]
	if !ok {
		return nil, fmt.Errorf("schema is missing the 'type' field: %#v", genkitSchema)
	}

	typeStr, ok := typeVal.(string)
	if !ok {
		return nil, fmt.Errorf("schema 'type' field is not a string, but %T", typeVal)
	}

	switch typeStr {
	case "string":
		schema.Type = genai.TypeString
	case "float64", "number":
		schema.Type = genai.TypeNumber
	case "integer":
		schema.Type = genai.TypeInteger
	case "boolean":
		schema.Type = genai.TypeBoolean
	case "object":
		schema.Type = genai.TypeObject
	case "array":
		schema.Type = genai.TypeArray
	default:
		return nil, fmt.Errorf("schema type %q not allowed", genkitSchema["type"])
	}
	if v, ok := genkitSchema["required"]; ok {
		schema.Required = castToStringArray(v)
	}
	if v, ok := genkitSchema["propertyOrdering"]; ok {
		schema.PropertyOrdering = castToStringArray(v)
	}
	if v, ok := genkitSchema["description"]; ok {
		schema.Description = v.(string)
	}
	if v, ok := genkitSchema["format"]; ok {
		schema.Format = v.(string)
	}
	if v, ok := genkitSchema["title"]; ok {
		schema.Title = v.(string)
	}
	if v, ok := genkitSchema["minItems"]; ok {
		if i64, ok := castToInt64(v); ok {
			schema.MinItems = genai.Ptr(i64)
		}
	}
	if v, ok := genkitSchema["maxItems"]; ok {
		if i64, ok := castToInt64(v); ok {
			schema.MaxItems = genai.Ptr(i64)
		}
	}
	if v, ok := genkitSchema["maximum"]; ok {
		if f64, ok := castToFloat64(v); ok {
			schema.Maximum = genai.Ptr(f64)
		}
	}
	if v, ok := genkitSchema["minimum"]; ok {
		if f64, ok := castToFloat64(v); ok {
			schema.Minimum = genai.Ptr(f64)
		}
	}
	if v, ok := genkitSchema["enum"]; ok {
		schema.Enum = castToStringArray(v)
	}
	if v, ok := genkitSchema["items"]; ok {
		items, err := toGeminiSchema(originalSchema, v.(map[string]any))
		if err != nil {
			return nil, err
		}
		schema.Items = items
	}
	if val, ok := genkitSchema["properties"]; ok {
		props := map[string]*genai.Schema{}
		for k, v := range val.(map[string]any) {
			p, err := toGeminiSchema(originalSchema, v.(map[string]any))
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

func resolveRef(originalSchema map[string]any, ref string) (map[string]any, error) {
	tkns := strings.Split(ref, "/")
	// refs look like: $/ref/foo -- we need the foo part
	name := tkns[len(tkns)-1]
	if defs, ok := originalSchema["$defs"].(map[string]any); ok {
		if def, ok := defs[name].(map[string]any); ok {
			return def, nil
		}
	}
	// definitions (legacy)
	if defs, ok := originalSchema["definitions"].(map[string]any); ok {
		if def, ok := defs[name].(map[string]any); ok {
			return def, nil
		}
	}
	return nil, fmt.Errorf("unable to resolve schema reference")
}

// castToStringArray converts either []any or []string to []string, filtering non-strings.
// This handles enum values from JSON Schema which may come as either type depending on unmarshaling.
// Filter out non-string types from if v is []any type.
func castToStringArray(v any) []string {
	switch a := v.(type) {
	case []string:
		// Return a shallow copy to avoid aliasing
		out := make([]string, 0, len(a))
		for _, s := range a {
			if s != "" {
				out = append(out, s)
			}
		}
		return out
	case []any:
		var out []string
		for _, it := range a {
			if s, ok := it.(string); ok && s != "" {
				out = append(out, s)
			}
		}
		return out
	default:
		return nil
	}
}

// castToInt64 converts v to int64 when possible.
func castToInt64(v any) (int64, bool) {
	switch t := v.(type) {
	case int:
		return int64(t), true
	case int64:
		return t, true
	case float64:
		return int64(t), true
	case string:
		if i, err := strconv.ParseInt(t, 10, 64); err == nil {
			return i, true
		}
	case json.Number:
		if i, err := t.Int64(); err == nil {
			return i, true
		}
	}
	return 0, false
}

// castToFloat64 converts v to float64 when possible.
func castToFloat64(v any) (float64, bool) {
	switch t := v.(type) {
	case float64:
		return t, true
	case int:
		return float64(t), true
	case int64:
		return float64(t), true
	case string:
		if f, err := strconv.ParseFloat(t, 64); err == nil {
			return f, true
		}
	case json.Number:
		if f, err := t.Float64(); err == nil {
			return f, true
		}
	}
	return 0, false
}

func toGeminiToolChoice(toolChoice ai.ToolChoice, tools []*ai.ToolDefinition) (*genai.ToolConfig, error) {
	var mode genai.FunctionCallingConfigMode
	switch toolChoice {
	case "":
		return nil, nil
	case ai.ToolChoiceAuto:
		mode = genai.FunctionCallingConfigModeAuto
	case ai.ToolChoiceRequired:
		mode = genai.FunctionCallingConfigModeAny
	case ai.ToolChoiceNone:
		mode = genai.FunctionCallingConfigModeNone
	default:
		return nil, fmt.Errorf("tool choice mode %q not supported", toolChoice)
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
	}, nil
}

// translateCandidate translates from a genai.GenerateContentResponse to an ai.ModelResponse.
func translateCandidate(cand *genai.Candidate) (*ai.ModelResponse, error) {
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
	}

	m.FinishMessage = cand.FinishMessage
	if cand.Content == nil {
		return nil, fmt.Errorf("no valid candidates were found in the generate response")
	}
	msg := &ai.Message{}
	msg.Role = ai.Role(cand.Content.Role)
	// iterate over the candidate parts, only one struct member
	// must be populated, more than one is considered an error
	for _, part := range cand.Content.Parts {
		var p *ai.Part
		partFound := 0

		if part.Thought {
			p = ai.NewReasoningPart(part.Text, part.ThoughtSignature)
			partFound++
		}
		if part.Text != "" && !part.Thought {
			p = ai.NewTextPart(part.Text)
			partFound++
		}
		if part.InlineData != nil {
			partFound++
			p = ai.NewMediaPart(part.InlineData.MIMEType, "data:"+part.InlineData.MIMEType+";base64,"+base64.StdEncoding.EncodeToString((part.InlineData.Data)))
		}
		if part.FileData != nil {
			partFound++
			p = ai.NewMediaPart(part.FileData.MIMEType, part.FileData.FileURI)

		}
		if part.FunctionCall != nil {
			partFound++
			p = ai.NewToolRequestPart(&ai.ToolRequest{
				Name:  part.FunctionCall.Name,
				Input: part.FunctionCall.Args,
			})
			// FunctionCall parts may contain a ThoughtSignature that must be preserved
			// and returned in subsequent requests for the tool call to be valid.
			if len(part.ThoughtSignature) > 0 {
				if p.Metadata == nil {
					p.Metadata = make(map[string]any)
				}
				p.Metadata["signature"] = part.ThoughtSignature
			}
		}
		if part.CodeExecutionResult != nil {
			partFound++
			p = NewCodeExecutionResultPart(
				string(part.CodeExecutionResult.Outcome),
				part.CodeExecutionResult.Output,
			)
		}
		if part.ExecutableCode != nil {
			partFound++
			p = NewExecutableCodePart(
				string(part.ExecutableCode.Language),
				part.ExecutableCode.Code,
			)
		}
		if partFound > 1 {
			panic(fmt.Sprintf("expected only 1 content part in response, got %d, part: %#v", partFound, part))
		}
		if p == nil {
			continue
		}

		if len(part.ThoughtSignature) > 0 {
			if p.Metadata == nil {
				p.Metadata = make(map[string]any)
			}
			p.Metadata["signature"] = part.ThoughtSignature
		}

		msg.Content = append(msg.Content, p)
	}
	m.Message = msg
	return m, nil
}

// Translate from a genai.GenerateContentResponse to a ai.ModelResponse.
func translateResponse(resp *genai.GenerateContentResponse) (*ai.ModelResponse, error) {
	var r *ai.ModelResponse
	var err error

	if len(resp.Candidates) > 0 {
		r, err = translateCandidate(resp.Candidates[0])
		if err != nil {
			return nil, err
		}
	} else {
		r = &ai.ModelResponse{}
	}

	if r.Usage == nil {
		r.Usage = &ai.GenerationUsage{}
	}

	// populate "custom" with plugin custom information
	custom := make(map[string]any)
	custom["candidates"] = resp.Candidates

	if u := resp.UsageMetadata; u != nil {
		r.Usage.InputTokens = int(u.PromptTokenCount)
		r.Usage.OutputTokens = int(u.CandidatesTokenCount)
		r.Usage.TotalTokens = int(u.TotalTokenCount)
		r.Usage.CachedContentTokens = int(u.CachedContentTokenCount)
		r.Usage.ThoughtsTokens = int(u.ThoughtsTokenCount)
		custom["usageMetadata"] = resp.UsageMetadata
	}

	r.Custom = custom
	return r, nil
}

// toGeminiParts converts a slice of [ai.Part] to a slice of [genai.Part].
func toGeminiParts(parts []*ai.Part) ([]*genai.Part, error) {
	res := make([]*genai.Part, 0, len(parts))
	for _, p := range parts {
		part, err := toGeminiPart(p)
		if err != nil {
			return nil, err
		}
		res = append(res, part)
	}
	return res, nil
}

// toGeminiPart converts a [ai.Part] to a [genai.Part].
func toGeminiPart(p *ai.Part) (*genai.Part, error) {
	var gp *genai.Part
	switch {
	case p.IsReasoning():
		gp = genai.NewPartFromText(p.Text)
		gp.Thought = true
	case p.IsText():
		gp = genai.NewPartFromText(p.Text)
	case p.IsMedia():
		if strings.HasPrefix(p.Text, "data:") {
			contentType, data, err := uri.Data(p)
			if err != nil {
				return nil, err
			}
			gp = genai.NewPartFromBytes(data, contentType)
		} else {
			gp = genai.NewPartFromURI(p.Text, p.ContentType)
		}
	case p.IsData():
		contentType, data, err := uri.Data(p)
		if err != nil {
			return nil, err
		}
		gp = genai.NewPartFromBytes(data, contentType)
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
		var isMultipart bool
		if multiPart, ok := p.Metadata["multipart"].(bool); ok {
			isMultipart = multiPart
		}
		if len(toolResp.Content) > 0 {
			isMultipart = true
		}
		if isMultipart {
			toolRespParts, err := toGeminiFunctionResponsePart(toolResp.Content)
			if err != nil {
				return nil, err
			}
			return genai.NewPartFromFunctionResponseWithParts(toolResp.Name, output, toolRespParts), nil
		}
		return genai.NewPartFromFunctionResponse(toolResp.Name, output), nil
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
		// Restore ThoughtSignature if present in metadata
		if p.Metadata != nil {
			if sig, ok := p.Metadata["signature"].([]byte); ok {
				fc.ThoughtSignature = sig
			}
		}
		return fc, nil
	default:
		return nil, fmt.Errorf("unknown part in the request: %q", p.Kind)
	}

	if p.Metadata != nil {
		if sig, ok := p.Metadata["signature"].([]byte); ok {
			gp.ThoughtSignature = sig
		}
	}

	return gp, nil
}

// validToolName checks whether the provided tool name matches the
// following criteria:
// - Start with a letter or an underscore
// - Must be alphanumeric and can include underscores, dots or dashes
// - Maximum length of 64 chars
func validToolName(n string) bool {
	re := regexp.MustCompile(toolNameRegex)

	return re.MatchString(n)
}

// CodeExecutionResult represents the result of a code execution.
type CodeExecutionResult struct {
	Outcome string `json:"outcome"`
	Output  string `json:"output"`
}

// ExecutableCode represents executable code.
type ExecutableCode struct {
	Language string `json:"language"`
	Code     string `json:"code"`
}

// NewCodeExecutionResultPart returns a Part containing the result of code execution.
func NewCodeExecutionResultPart(outcome string, output string) *ai.Part {
	return ai.NewCustomPart(map[string]any{
		"codeExecutionResult": map[string]any{
			"outcome": outcome,
			"output":  output,
		},
	})
}

// NewExecutableCodePart returns a Part containing executable code.
func NewExecutableCodePart(language string, code string) *ai.Part {
	return ai.NewCustomPart(map[string]any{
		"executableCode": map[string]any{
			"language": language,
			"code":     code,
		},
	})
}

// ToCodeExecutionResult tries to convert an ai.Part to a CodeExecutionResult.
// Returns nil if the part doesn't contain code execution results.
func ToCodeExecutionResult(part *ai.Part) *CodeExecutionResult {
	if !part.IsCustom() {
		return nil
	}

	codeExec, ok := part.Custom["codeExecutionResult"]
	if !ok {
		return nil
	}

	result, ok := codeExec.(map[string]any)
	if !ok {
		return nil
	}

	outcome, _ := result["outcome"].(string)
	output, _ := result["output"].(string)

	return &CodeExecutionResult{
		Outcome: outcome,
		Output:  output,
	}
}

// ToExecutableCode tries to convert an ai.Part to an ExecutableCode.
// Returns nil if the part doesn't contain executable code.
func ToExecutableCode(part *ai.Part) *ExecutableCode {
	if !part.IsCustom() {
		return nil
	}

	execCode, ok := part.Custom["executableCode"]
	if !ok {
		return nil
	}

	code, ok := execCode.(map[string]any)
	if !ok {
		return nil
	}

	language, _ := code["language"].(string)
	codeStr, _ := code["code"].(string)

	return &ExecutableCode{
		Language: language,
		Code:     codeStr,
	}
}

// HasCodeExecution checks if a message contains code execution results or executable code.
func HasCodeExecution(msg *ai.Message) bool {
	return GetCodeExecutionResult(msg) != nil || GetExecutableCode(msg) != nil
}

// GetExecutableCode returns the first executable code from a message.
// Returns nil if the message doesn't contain executable code.
func GetExecutableCode(msg *ai.Message) *ExecutableCode {
	for _, part := range msg.Content {
		if code := ToExecutableCode(part); code != nil {
			return code
		}
	}
	return nil
}

// GetCodeExecutionResult returns the first code execution result from a message.
// Returns nil if the message doesn't contain a code execution result.
func GetCodeExecutionResult(msg *ai.Message) *CodeExecutionResult {
	for _, part := range msg.Content {
		if result := ToCodeExecutionResult(part); result != nil {
			return result
		}
	}
	return nil
}
