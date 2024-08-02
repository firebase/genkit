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

package vertexai

import (
	"context"
	"fmt"
	"os"
	"runtime"
	"strconv"
	"strings"
	"sync"

	aiplatform "cloud.google.com/go/aiplatform/apiv1"
	"cloud.google.com/go/vertexai/genai"
	"github.com/firebase/genkit/go/ai"
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
	knownCaps = map[string]ai.ModelCapabilities{
		"gemini-1.0-pro":   gemini.BasicText,
		"gemini-1.5-pro":   gemini.Multimodal,
		"gemini-1.5-flash": gemini.Multimodal,
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
func Init(ctx context.Context, cfg *Config) error {
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
	for model, caps := range knownCaps {
		defineModel(model, caps)
	}
	for _, e := range knownEmbedders {
		defineEmbedder(e)
	}
	return nil
}

//copy:sink defineModel from ../googleai/googleai.go
// DO NOT MODIFY below vvvv

// DefineModel defines an unknown model with the given name.
// The second argument describes the capability of the model.
// Use [IsDefinedModel] to determine if a model is already defined.
// After [Init] is called, only the known models are defined.
func DefineModel(name string, caps *ai.ModelCapabilities) (ai.Model, error) {
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
func defineModel(name string, caps ai.ModelCapabilities) ai.Model {
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

// DO NOT MODIFY above ^^^^
//copy:endsink defineModel

//copy:sink defineEmbedder from ../googleai/googleai.go
// DO NOT MODIFY below vvvv

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

// DO NOT MODIFY above ^^^^
//copy:endsink defineEmbedder

// requires state.mu
func defineEmbedder(name string) ai.Embedder {
	fullName := fmt.Sprintf("projects/%s/locations/%s/publishers/google/models/%s", state.projectID, state.location, name)
	return ai.DefineEmbedder(provider, name, func(ctx context.Context, req *ai.EmbedRequest) (*ai.EmbedResponse, error) {
		return embed(ctx, fullName, state.pclient, req)
	})
}

//copy:sink lookups from ../googleai/googleai.go
// DO NOT MODIFY below vvvv

// Model returns the [ai.Model] with the given name.
// It returns nil if the model was not defined.
func Model(name string) ai.Model {
	return ai.LookupModel(provider, name)
}

// Embedder returns the [ai.Embedder] with the given name.
// It returns nil if the embedder was not defined.
func Embedder(name string) ai.Embedder {
	return ai.LookupEmbedder(provider, name)
}

// DO NOT MODIFY above ^^^^
//copy:endsink lookups

//copy:sink generate from ../googleai/googleai.go
// DO NOT MODIFY below vvvv

func generate(
	ctx context.Context,
	client *genai.Client,
	model string,
	input *ai.GenerateRequest,
	cb func(context.Context, *ai.GenerateResponseChunk) error,
) (*ai.GenerateResponse, error) {
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

func newModel(client *genai.Client, model string, input *ai.GenerateRequest) (*genai.GenerativeModel, error) {
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
func startChat(gm *genai.GenerativeModel, input *ai.GenerateRequest) (*genai.ChatSession, error) {
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
		if err != err {
			return nil, err
		}
		outputSchema, err := convertSchema(t.OutputSchema, t.OutputSchema)
		if err != err {
			return nil, err
		}
		fd := &genai.FunctionDeclaration{
			Name:        t.Name,
			Parameters:  inputSchema,
			Response:    outputSchema,
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
	case "int":
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
	if v, ok := genkitSchema["pattern"]; ok {
		schema.Pattern = v.(string)
	}
	if v, ok := genkitSchema["title"]; ok {
		schema.Title = v.(string)
	}
	if v, ok := genkitSchema["minItems"]; ok {
		schema.MinItems = v.(int64)
	}
	if v, ok := genkitSchema["maxItems"]; ok {
		schema.MaxItems = v.(int64)
	}
	if v, ok := genkitSchema["minItems"]; ok {
		schema.MinItems = v.(int64)
	}
	if v, ok := genkitSchema["maxProperties"]; ok {
		schema.MaxProperties = v.(int64)
	}
	if v, ok := genkitSchema["minProperties"]; ok {
		schema.MinProperties = v.(int64)
	}
	if v, ok := genkitSchema["maxLength"]; ok {
		schema.MaxLength = v.(int64)
	}
	if v, ok := genkitSchema["minLength"]; ok {
		schema.MinLength = v.(int64)
	}
	if v, ok := genkitSchema["enum"]; ok {
		schema.Enum = castToStringArray(v.([]any))
	}
	if v, ok := genkitSchema["maximum"]; ok {
		m, err := strconv.ParseFloat(v.(string), 64)
		if err != nil {
			return nil, err
		}
		schema.Maximum = m
	}
	if v, ok := genkitSchema["minimum"]; ok {
		m, err := strconv.ParseFloat(v.(string), 64)
		if err != nil {
			return nil, err
		}
		schema.Minimum = m
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

// DO NOT MODIFY above ^^^^
//copy:endsink generate

//copy:sink translateCandidate from ../googleai/googleai.go
// DO NOT MODIFY below vvvv

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

// DO NOT MODIFY above ^^^^
//copy:endsink translateCandidate

//copy:sink translateResponse from ../googleai/googleai.go
// DO NOT MODIFY below vvvv

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

// DO NOT MODIFY above ^^^^
//copy:endsink convertParts
