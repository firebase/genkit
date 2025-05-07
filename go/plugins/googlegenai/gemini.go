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
	"fmt"
	"net/http"
	"net/url"
	"regexp"
	"slices"
	"strconv"
	"strings"

	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/internal/base"
	"github.com/invopop/jsonschema"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/internal"
	"github.com/firebase/genkit/go/plugins/internal/uri"
	"google.golang.org/genai"
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

	// Tool name regex
	toolNameRegex = "^[a-zA-Z_][a-zA-Z0-9_.-]{0,63}$"

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
	}
	schema := r.Reflect(config)
	result := base.SchemaAsMap(schema)
	return result
}

// mapToStruct unmarshals a map[string]any to the expected config type.
func mapToStruct(m map[string]any, v any) error {
	jsonData, err := json.Marshal(m)
	if err != nil {
		return err
	}
	return json.Unmarshal(jsonData, v)
}

// toGeminiSafetySettings converts a list of [SafetySetting] to a list of [genai.SafetySetting].
func toGeminiSafetySettings(settings []*SafetySetting) []*genai.SafetySetting {
	if len(settings) == 0 {
		return nil
	}

	result := make([]*genai.SafetySetting, len(settings))
	for i, s := range settings {
		result[i] = &genai.SafetySetting{
			Method:    genai.HarmBlockMethod(s.Method),
			Category:  genai.HarmCategory(s.Category),
			Threshold: genai.HarmBlockThreshold(s.Threshold),
		}
	}
	return result
}

type HarmCategory string

const (
	// The harm category is unspecified.
	HarmCategoryUnspecified HarmCategory = "HARM_CATEGORY_UNSPECIFIED"
	// The harm category is hate speech.
	HarmCategoryHateSpeech HarmCategory = "HARM_CATEGORY_HATE_SPEECH"
	// The harm category is dangerous content.
	HarmCategoryDangerousContent HarmCategory = "HARM_CATEGORY_DANGEROUS_CONTENT"
	// The harm category is harassment.
	HarmCategoryHarassment HarmCategory = "HARM_CATEGORY_HARASSMENT"
	// The harm category is sexually explicit content.
	HarmCategorySexuallyExplicit HarmCategory = "HARM_CATEGORY_SEXUALLY_EXPLICIT"
	// The harm category is civic integrity.
	HarmCategoryCivicIntegrity HarmCategory = "HARM_CATEGORY_CIVIC_INTEGRITY"
)

// Specify if the threshold is used for probability or severity score. If not specified,
// the threshold is used for probability score.
type HarmBlockMethod string

const (
	// The harm block method is unspecified.
	HarmBlockMethodUnspecified HarmBlockMethod = "HARM_BLOCK_METHOD_UNSPECIFIED"
	// The harm block method uses both probability and severity scores.
	HarmBlockMethodSeverity HarmBlockMethod = "SEVERITY"
	// The harm block method uses the probability score.
	HarmBlockMethodProbability HarmBlockMethod = "PROBABILITY"
)

// The harm block threshold.
type HarmBlockThreshold string

const (
	// Unspecified harm block threshold.
	HarmBlockThresholdUnspecified HarmBlockThreshold = "HARM_BLOCK_THRESHOLD_UNSPECIFIED"
	// Block low threshold and above (i.e. block more).
	HarmBlockThresholdBlockLowAndAbove HarmBlockThreshold = "BLOCK_LOW_AND_ABOVE"
	// Block medium threshold and above.
	HarmBlockThresholdBlockMediumAndAbove HarmBlockThreshold = "BLOCK_MEDIUM_AND_ABOVE"
	// Block only high threshold (i.e. block less).
	HarmBlockThresholdBlockOnlyHigh HarmBlockThreshold = "BLOCK_ONLY_HIGH"
	// Block none.
	HarmBlockThresholdBlockNone HarmBlockThreshold = "BLOCK_NONE"
	// Turn off the safety filter.
	HarmBlockThresholdOff HarmBlockThreshold = "OFF"
)

// Safety settings.
type SafetySetting struct {
	// Determines if the harm block method uses probability or probability
	// and severity scores.
	Method HarmBlockMethod `json:"method,omitempty"`
	// Required. Harm category.
	Category HarmCategory `json:"category,omitempty"`
	// Required. The harm block threshold.
	Threshold HarmBlockThreshold `json:"threshold,omitempty"`
}

type Modality string

const (
	// Indicates the model should return images
	ImageMode Modality = "IMAGE"
	// Indicates the model should return text
	TextMode Modality = "TEXT"
)

// GeminiConfig mirrors GenerateContentConfig without direct genai dependency
type GeminiConfig struct {
	// MaxOutputTokens is the maximum number of tokens to generate.
	MaxOutputTokens int `json:"maxOutputTokens,omitempty"`
	// StopSequences is the list of sequences where the model will stop generating further tokens.
	StopSequences []string `json:"stopSequences,omitempty"`
	// Temperature is the temperature to use for the model.
	Temperature float64 `json:"temperature,omitempty"`
	// TopK is the number of top tokens to consider for the model.
	TopK int `json:"topK,omitempty"`
	// TopP is the top-p value to use for the model.
	TopP float64 `json:"topP,omitempty"`
	// Version is the version of the model to use.
	Version string `json:"version,omitempty"`
	// SafetySettings is the list of safety settings to use for the model.
	SafetySettings []*SafetySetting `json:"safetySettings,omitempty"`
	// CodeExecution is whether to allow executing of code generated by the model.
	CodeExecution bool `json:"codeExecution,omitempty"`
	// Response modalities for returned model messages
	ResponseModalities []Modality `json:"responseModalities,omitempty"`
}

// configFromRequest converts any supported config type to [GeminiConfig].
func configFromRequest(input *ai.ModelRequest) (*GeminiConfig, error) {
	var result GeminiConfig

	switch config := input.Config.(type) {
	case GeminiConfig:
		result = config
	case *GeminiConfig:
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

// DefineModel defines a model in the registry
func defineModel(g *genkit.Genkit, client *genai.Client, name string, info ai.ModelInfo) ai.Model {
	provider := googleAIProvider
	if client.ClientConfig().Backend == genai.BackendVertexAI {
		provider = vertexAIProvider
	}

	meta := &ai.ModelInfo{
		Label:        info.Label,
		Supports:     info.Supports,
		Versions:     info.Versions,
		ConfigSchema: configToMap(&GeminiConfig{}),
	}

	fn := func(
		ctx context.Context,
		input *ai.ModelRequest,
		cb func(context.Context, *ai.ModelResponseChunk) error,
	) (*ai.ModelResponse, error) {
		return generate(ctx, client, name, input, cb)
	}
	// the gemini api doesn't support downloading media from http(s)
	if info.Supports.Media {
		fn = core.ChainMiddleware(ai.DownloadRequestMedia(&ai.DownloadMediaOptions{
			MaxBytes: 1024 * 1024 * 20, // 20MB
			Filter: func(part *ai.Part) bool {
				u, err := url.Parse(part.Text)
				if err != nil {
					return true
				}
				// Gemini can handle these URLs
				return !slices.Contains(
					[]string{"www.youtube.com", "youtube.com", "youtu.be"},
					u.Hostname(),
				)
			},
		}))(fn)
	}
	return genkit.DefineModel(g, provider, name, meta, fn)
}

// DefineEmbedder defines embeddings for the provided contents and embedder
// model
func defineEmbedder(g *genkit.Genkit, client *genai.Client, name string) ai.Embedder {
	provider := googleAIProvider
	if client.ClientConfig().Backend == genai.BackendVertexAI {
		provider = vertexAIProvider
	}

	return genkit.DefineEmbedder(g, provider, name, func(ctx context.Context, req *ai.EmbedRequest) (*ai.EmbedResponse, error) {
		var content []*genai.Content
		var embedConfig *genai.EmbedContentConfig

		// check if request options matches VertexAI configuration
		if opts, _ := req.Options.(*EmbedOptions); opts != nil {
			if provider == googleAIProvider {
				return nil, fmt.Errorf("wrong options provided for %s provider, got %T", provider, opts)
			}
			embedConfig = &genai.EmbedContentConfig{
				Title:    opts.Title,
				TaskType: opts.TaskType,
			}
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

// Generate requests a generate call to the specified model with the provided
// configuration
func generate(
	ctx context.Context,
	client *genai.Client,
	model string,
	input *ai.ModelRequest,
	cb func(context.Context, *ai.ModelResponseChunk) error,
) (*ai.ModelResponse, error) {
	// Extract configuration to get the model version
	config, err := configFromRequest(input)
	if err != nil {
		return nil, err
	}

	// Update model with version if specified
	if config.Version != "" {
		model = config.Version
	}

	cache, err := handleCache(ctx, client, input, model)
	if err != nil {
		return nil, err
	}

	gcc, err := toGeminiRequest(input, cache)
	if err != nil {
		return nil, err
	}

	if len(config.ResponseModalities) > 0 {
		err := validateResponseModalities(model, config.ResponseModalities)
		if err != nil {
			return nil, err
		}
		for _, m := range config.ResponseModalities {
			gcc.ResponseModalities = append(gcc.ResponseModalities, string(m))
		}

		// prevent an error in the client where:
		// if TEXT modality is not present and the model supports it, the client
		// will return an error
		if !slices.Contains(gcc.ResponseModalities, string(genai.ModalityText)) {
			gcc.ResponseModalities = append(gcc.ResponseModalities, string(genai.ModalityText))
		}
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
		r := translateResponse(resp)
		r.Request = input
		if cache != nil {
			r.Message.Metadata = setCacheMetadata(r.Message.Metadata, cache)
		}
		return r, nil
	}

	// Streaming version.
	iter := client.Models.GenerateContentStream(ctx, model, contents, gcc)
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

// toGeminiRequest translates from [*ai.ModelRequest] to
// *genai.GenerateContentParameters
func toGeminiRequest(input *ai.ModelRequest, cache *genai.CachedContent) (*genai.GenerateContentConfig, error) {
	gcc := genai.GenerateContentConfig{
		CandidateCount: 1,
	}

	c, err := configFromRequest(input)
	if err != nil {
		return nil, err
	}

	// Convert standard fields
	if c.MaxOutputTokens != 0 {
		gcc.MaxOutputTokens = int32(c.MaxOutputTokens)
	}
	if len(c.StopSequences) > 0 {
		gcc.StopSequences = c.StopSequences
	}
	if c.Temperature != 0 {
		gcc.Temperature = genai.Ptr(float32(c.Temperature))
	}
	if c.TopK != 0 {
		gcc.TopK = genai.Ptr(float32(c.TopK))
	}
	if c.TopP != 0 {
		gcc.TopP = genai.Ptr(float32(c.TopP))
	}
	// Convert non-primitive fields
	gcc.SafetySettings = toGeminiSafetySettings(c.SafetySettings)

	// Set response MIME type based on output format if specified
	hasOutput := input.Output != nil
	isJsonFormat := hasOutput && input.Output.Format == "json"
	isJsonContentType := hasOutput && input.Output.ContentType == "application/json"
	jsonMode := isJsonFormat || isJsonContentType
	// this setting is not compatible with tools forcing controlled output generation
	if jsonMode && len(input.Tools) == 0 {
		gcc.ResponseMIMEType = "application/json"
	}

	if input.Output != nil && input.Output.Constrained {
		schema, err := toGeminiSchema(input.Output.Schema, input.Output.Schema)
		if err != nil {
			return nil, err
		}
		gcc.ResponseSchema = schema
	}

	// Add tool configuration from input.Tools and input.ToolChoice directly
	// This overrides any functionCallingConfig in the passed config
	if len(input.Tools) > 0 {
		// First convert the tools
		tools, err := toGeminiTools(input.Tools)
		if err != nil {
			return nil, err
		}
		gcc.Tools = tools

		// Then set up the tool configuration based on ToolChoice
		tc, err := toGeminiToolChoice(input.ToolChoice, input.Tools)
		if err != nil {
			return nil, err
		}

		gcc.ToolConfig = tc
	}

	// Add CodeExecution tool if enabled in config
	if c.CodeExecution {
		// Initialize tools array if it doesn't exist yet
		if gcc.Tools == nil {
			gcc.Tools = []*genai.Tool{}
		}
		// Add the CodeExecution tool
		gcc.Tools = append(gcc.Tools, &genai.Tool{
			CodeExecution: &genai.ToolCodeExecution{},
		})
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

	return &gcc, nil
}

// validateResponseModalities checks if response modality is valid for the requested model
func validateResponseModalities(model string, modalities []Modality) error {
	for _, m := range modalities {
		switch m {
		case ImageMode:
			if !slices.Contains(imageGenModels, model) {
				return fmt.Errorf("IMAGE response modality is not supported for model %q", model)
			}
		case TextMode:
			continue
		default:
			return fmt.Errorf("unknown response modality provided: %q", m)
		}
	}
	return nil
}

// toGeminiTools translates a slice of [ai.ToolDefinition] to a slice of [genai.Tool].
func toGeminiTools(inTools []*ai.ToolDefinition) ([]*genai.Tool, error) {
	var outTools []*genai.Tool
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
		outTools = append(outTools, &genai.Tool{FunctionDeclarations: []*genai.FunctionDeclaration{fd}})
	}
	return outTools, nil
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
		ref := v.(string)
		return toGeminiSchema(originalSchema, resolveRef(originalSchema, ref))
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
		schema.Required = castToStringArray(v.([]any))
	}
	if v, ok := genkitSchema["propertyOrdering"]; ok {
		schema.PropertyOrdering = castToStringArray(v.([]any))
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
		i, err := strconv.ParseInt(v.(string), 10, 64)
		if err != nil {
			return nil, err
		}
		schema.MinItems = genai.Ptr[int64](i)
	}
	if v, ok := genkitSchema["maxItems"]; ok {
		i, err := strconv.ParseInt(v.(string), 10, 64)
		if err != nil {
			return nil, err
		}
		schema.MaxItems = genai.Ptr[int64](i)
	}
	if v, ok := genkitSchema["maximum"]; ok {
		i, err := strconv.ParseFloat(v.(string), 64)
		if err != nil {
			return nil, err
		}
		schema.Maximum = genai.Ptr[float64](i)
	}
	if v, ok := genkitSchema["minimum"]; ok {
		i, err := strconv.ParseFloat(v.(string), 64)
		if err != nil {
			return nil, err
		}
		schema.Minimum = genai.Ptr[float64](i)
	}
	if v, ok := genkitSchema["enum"]; ok {
		schema.Enum = castToStringArray(v.([]any))
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
			p = ai.NewMediaPart(part.InlineData.MIMEType, base64.StdEncoding.EncodeToString(part.InlineData.Data))
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
		r.Usage.InputTokens = int(u.PromptTokenCount)
		r.Usage.OutputTokens = int(u.CandidatesTokenCount)
		r.Usage.TotalTokens = int(u.TotalTokenCount)
		r.Usage.CachedContentTokens = int(u.CachedContentTokenCount)
		r.Usage.ThoughtsTokens = int(u.ThoughtsTokenCount)
	}
	return r
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
	switch {
	case p.IsText():
		return genai.NewPartFromText(p.Text), nil
	case p.IsMedia():
		if strings.HasPrefix(p.Text, "data:") {
			contentType, data, err := uri.Data(p)
			if err != nil {
				return nil, err
			}
			return genai.NewPartFromBytes(data, contentType), nil
		}
		return genai.NewPartFromURI(p.Text, p.ContentType), nil
	case p.IsData():
		contentType, data, err := uri.Data(p)
		if err != nil {
			return nil, err
		}
		return genai.NewPartFromBytes(data, contentType), nil
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
