// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package vertexai

import (
	"context"
	"fmt"
	"os"
	"runtime"
	"strings"
	"sync"

	aiplatform "cloud.google.com/go/aiplatform/apiv1"
	"cloud.google.com/go/vertexai/genai"
	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/internal"
	"github.com/firebase/genkit/go/plugins/internal/gemini"
	"github.com/firebase/genkit/go/plugins/internal/uri"
	"google.golang.org/api/iterator"
	"google.golang.org/api/option"
)

const (
	provider    = "vertexai"
	labelPrefix = "Vertex AI"
)

var (
	supportedModels = map[string]ai.ModelInfo{
		"gemini-1.5-flash": {
			Versions: []string{"gemini-1.5-flash-latest", "gemini-1.5-flash-001", "gemini-1.5-flash-002"},
			Supports: &gemini.Multimodal,
		},

		"gemini-1.5-pro": {
			Versions: []string{"gemini-1.5-pro-latest", "gemini-1.5-pro-001", "gemini-1.5-pro-002"},
			Supports: &gemini.Multimodal,
		},

		"gemini-2.0-flash-001": {
			Versions: []string{},
			Supports: &gemini.Multimodal,
		},

		"gemini-2.0-flash-lite-preview-02-05": {
			Versions: []string{},
			Supports: &gemini.Multimodal,
		},

		"gemini-2.0-pro-exp-02-05": {
			Versions: []string{},
			Supports: &gemini.Multimodal,
		},
	}

	knownEmbedders = []string{
		"textembedding-gecko@003",
		"textembedding-gecko@002",
		"textembedding-gecko@001",
		"text-embedding-004",
		"textembedding-gecko-multilingual@001",
		"text-multilingual-embedding-002",
		"multimodalembedding",
	}
)

var state struct {
	mu        sync.Mutex
	initted   bool
	projectID string
	location  string
	gclient   *genai.Client
	pclient   *aiplatform.PredictionClient
}

// Config is the configuration for the plugin.
type Config struct {
	// The cloud project to use for Vertex AI.
	// If empty, the values of the environment variables GCLOUD_PROJECT
	// and GOOGLE_CLOUD_PROJECT will be consulted, in that order.
	ProjectID string
	// The location of the Vertex AI service. The default is "us-central1".
	Location string
	// Options to the Vertex AI client.
	ClientOptions []option.ClientOption
}

// Init initializes the plugin and all known models and embedders.
// After calling Init, you may call [DefineModel] and [DefineEmbedder] to create
// and register any additional generative models and embedders
func Init(ctx context.Context, g *genkit.Genkit, cfg *Config) error {
	if cfg == nil {
		cfg = &Config{}
	}
	state.mu.Lock()
	defer state.mu.Unlock()
	if state.initted {
		panic("vertexai.Init already called")
	}

	state.projectID = cfg.ProjectID
	if state.projectID == "" {
		state.projectID = os.Getenv("GCLOUD_PROJECT")
	}
	if state.projectID == "" {
		state.projectID = os.Getenv("GOOGLE_CLOUD_PROJECT")
	}
	if state.projectID == "" {
		return fmt.Errorf("vertexai.Init: Vertex AI requires setting GCLOUD_PROJECT or GOOGLE_CLOUD_PROJECT in the environment")
	}

	state.location = cfg.Location
	if state.location == "" {
		state.location = "us-central1"
	}
	var err error
	// Client for Gemini SDK.
	opts := append([]option.ClientOption{genai.WithClientInfo("genkit-go", internal.Version)}, cfg.ClientOptions...)
	state.gclient, err = genai.NewClient(ctx, state.projectID, state.location, opts...)
	if err != nil {
		return err
	}
	endpoint := fmt.Sprintf("%s-aiplatform.googleapis.com:443", state.location)
	numConns := max(runtime.GOMAXPROCS(0), 4)
	o := []option.ClientOption{
		option.WithEndpoint(endpoint),
		option.WithGRPCConnectionPool(numConns),
	}

	state.pclient, err = aiplatform.NewPredictionClient(ctx, o...)
	if err != nil {
		return err
	}
	state.initted = true
	for model, info := range supportedModels {
		defineModel(g, model, info)
	}
	for _, e := range knownEmbedders {
		defineEmbedder(g, e)
	}
	return nil
}

//copy:sink defineModel from ../googleai/googleai.go
// DO NOT MODIFY below vvvv

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

// DO NOT MODIFY above ^^^^
//copy:endsink defineModel

//copy:sink defineEmbedder from ../googleai/googleai.go
// DO NOT MODIFY below vvvv

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

// DO NOT MODIFY above ^^^^
//copy:endsink defineEmbedder

// requires state.mu
func defineEmbedder(g *genkit.Genkit, name string) ai.Embedder {
	fullName := fmt.Sprintf("projects/%s/locations/%s/publishers/google/models/%s", state.projectID, state.location, name)
	return genkit.DefineEmbedder(g, provider, name, func(ctx context.Context, req *ai.EmbedRequest) (*ai.EmbedResponse, error) {
		return embed(ctx, fullName, state.pclient, req)
	})
}

//copy:sink lookups from ../googleai/googleai.go
// DO NOT MODIFY below vvvv

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

// DO NOT MODIFY above ^^^^
//copy:endsink lookups

//copy:sink generate from ../googleai/googleai.go
// DO NOT MODIFY below vvvv

func generate(
	ctx context.Context,
	client *genai.Client,
	model string,
	input *ai.ModelRequest,
	cb func(context.Context, *ai.ModelResponseChunk) error,
) (*ai.ModelResponse, error) {
	gm, err := newModel(client, model, input)
	if err != nil {
		return nil, err
	}
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

	// Convert input.Tools and append to gm.Tools
	gm.Tools, err = convertTools(input.Tools)
	if err != nil {
		return nil, err
	}

	gm.ToolConfig = convertToolChoice(input.ToolChoice, input.Tools)

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
	var r *ai.ModelResponse
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
			err := cb(ctx, &ai.ModelResponseChunk{
				Content: tc.Message.Content,
			})
			if err != nil {
				return nil, err
			}
		}
	}
	if r == nil {
		// No candidates were returned. Probably rare, but it might avoid a NPE
		// to return an empty instead of nil result.
		r = &ai.ModelResponse{}
	}
	r.Request = input
	return r, nil
}

func newModel(client *genai.Client, model string, input *ai.ModelRequest) (*genai.GenerativeModel, error) {
	gm := client.GenerativeModel(model)
	gm.SetCandidateCount(1)
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
	for _, m := range input.Messages {
		systemParts, err := convertParts(m.Content)
		if err != nil {
			return nil, err
		}
		// system prompts go into GenerativeModel.SystemInstruction field.
		if m.Role == ai.RoleSystem {
			gm.SystemInstruction = &genai.Content{
				Parts: systemParts,
				Role:  string(m.Role),
			}
		}
	}
	return gm, nil
}

// startChat starts a chat session and configures it with the input messages.
func startChat(gm *genai.GenerativeModel, input *ai.ModelRequest) (*genai.ChatSession, error) {
	cs := gm.StartChat()

	// All but the last message goes in the history field.
	messages := input.Messages
	for len(messages) > 1 {
		m := messages[0]
		messages = messages[1:]

		// skip system prompt message, it's handled separately.
		if m.Role == ai.RoleSystem {
			continue
		}

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
	var mode genai.FunctionCallingMode
	switch toolChoice {
	case "":
		return nil
	case ai.ToolChoiceAuto:
		mode = genai.FunctionCallingAuto
	case ai.ToolChoiceRequired:
		mode = genai.FunctionCallingAny
	case ai.ToolChoiceNone:
		mode = genai.FunctionCallingNone
	default:
		panic(fmt.Sprintf("%s does not support tool choice mode %q", provider, toolChoice))
	}

	var toolNames []string
	// Per docs, only set AllowedToolNames with mode set to ANY.
	if mode == genai.FunctionCallingAny {
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

// DO NOT MODIFY above ^^^^
//copy:endsink generate

//copy:sink translateCandidate from ../googleai/googleai.go
// DO NOT MODIFY below vvvv

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
		msg.Content = append(msg.Content, p)
	}
	m.Message = msg
	return m
}

// DO NOT MODIFY above ^^^^
//copy:endsink translateCandidate

//copy:sink translateResponse from ../googleai/googleai.go
// DO NOT MODIFY below vvvv

// Translate from a genai.GenerateContentResponse to a ai.ModelResponse.
func translateResponse(resp *genai.GenerateContentResponse) *ai.ModelResponse {
	r := translateCandidate(resp.Candidates[0])

	r.Usage = &ai.GenerationUsage{}
	if u := resp.UsageMetadata; u != nil {
		r.Usage.InputTokens = int(u.PromptTokenCount)
		r.Usage.OutputTokens = int(u.CandidatesTokenCount)
		r.Usage.TotalTokens = int(u.TotalTokenCount)
	}
	return r
}

// DO NOT MODIFY above ^^^^
//copy:endsink translateResponse

//copy:sink convertParts from ../googleai/googleai.go
// DO NOT MODIFY below vvvv

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
		var output map[string]any
		if m, ok := toolResp.Output.(map[string]any); ok {
			output = m
		} else {
			output = map[string]any{
				"name":    toolResp.Name,
				"content": toolResp.Output,
			}
		}
		fr := genai.FunctionResponse{
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
		fc := genai.FunctionCall{
			Name: toolReq.Name,
			Args: input,
		}
		return fc, nil
	default:
		panic("unknown part type in a request")
	}
}

// DO NOT MODIFY above ^^^^
//copy:endsink convertParts
