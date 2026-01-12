// Copyright 2026 Google LLC
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

// Package openai contains the Genkit Plugin implementation for OpenAI provider
package openai

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"os"
	"reflect"
	"strings"
	"sync"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/core/api"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/internal/base"
	"github.com/firebase/genkit/go/plugins/internal"
	"github.com/invopop/jsonschema"
	"github.com/openai/openai-go/v3"
	"github.com/openai/openai-go/v3/option"
	"github.com/openai/openai-go/v3/packages/param"
	"github.com/openai/openai-go/v3/responses"
	"github.com/openai/openai-go/v3/shared"
)

const (
	openaiProvider    = "openai"
	openaiLabelPrefix = "OpenAI"
)

var defaultOpenAIOpts = ai.ModelOptions{
	Supports: &internal.Multimodal,
	Versions: []string{},
	Stage:    ai.ModelStageUnstable,
}

var defaultEmbedOpts = ai.EmbedderOptions{}

type OpenAI struct {
	mu      sync.Mutex             // protects concurrent access to the client and init state
	initted bool                   // tracks weter the plugin has been initialized
	client  *openai.Client         // openAI client used for making requests
	Opts    []option.RequestOption // request options for the OpenAI client
	APIKey  string                 // API key to use with the desired plugin
	BaseURL string                 // Base URL for custom endpoints
}

func (o *OpenAI) Name() string {
	return openaiProvider
}

func (o *OpenAI) Init(ctx context.Context) []api.Action {
	if o == nil {
		o = &OpenAI{}
	}
	o.mu.Lock()
	defer o.mu.Unlock()
	if o.initted {
		panic("plugin already initialized")
	}

	apiKey := os.Getenv("OPENAI_API_KEY")
	if apiKey != "" {
		o.Opts = append([]option.RequestOption{option.WithAPIKey(apiKey)}, o.Opts...)
	}

	baseURL := os.Getenv("OPENAI_BASE_URL")
	if baseURL != "" {
		o.Opts = append([]option.RequestOption{option.WithBaseURL(baseURL)}, o.Opts...)
	}

	client := openai.NewClient(o.Opts...)
	o.client = &client
	o.initted = true

	return []api.Action{}
}

// DefineModel defines an unknown model with the given name.
func (o *OpenAI) DefineModel(g *genkit.Genkit, name string, opts *ai.ModelOptions) (ai.Model, error) {
	o.mu.Lock()
	defer o.mu.Unlock()
	if !o.initted {
		panic("OpenAI.Init not called")
	}
	if name == "" {
		return nil, fmt.Errorf("OpenAI.DefineModel: called with empty model name")
	}

	if opts == nil {
		return nil, fmt.Errorf("OpenAI.DefineModel: called with unknown model options")
	}
	return newModel(o.client, name, opts), nil
}

// Model returns the [ai.Model] with the given name.
// It returns nil if the model was not previously defined.
func Model(g *genkit.Genkit, name string) ai.Model {
	return genkit.LookupModel(g, api.NewName(openaiProvider, name))
}

// IsDefinedModel reports whether the named [ai.Model] is defined by this plugin
func IsDefinedModel(g *genkit.Genkit, name string) bool {
	return genkit.LookupModel(g, name) != nil
}

// DefineEmbedder defines an embedder with a given name
func (o *OpenAI) DefineEmbedder(g *genkit.Genkit, name string, embedOpts *ai.EmbedderOptions) (ai.Embedder, error) {
	o.mu.Lock()
	defer o.mu.Unlock()
	if !o.initted {
		panic("OpenAI.Init not called")
	}
	return newEmbedder(o.client, name, embedOpts), nil
}

// Embedder returns the [ai.Embedder] with the given name.
// It returns nil if the embedder was not previously defined.
func Embedder(g *genkit.Genkit, name string) ai.Embedder {
	return genkit.LookupEmbedder(g, name)
}

// IsDefinedEmbedder reports whether the named [ai.Embedder] is defined by this plugin
func IsDefinedEmbedder(g *genkit.Genkit, name string) bool {
	return genkit.LookupEmbedder(g, name) != nil
}

// ListActions lists all the actions supported by the OpenAI plugin.
func (o *OpenAI) ListActions(ctx context.Context) []api.ActionDesc {
	actions := []api.ActionDesc{}
	models, err := listOpenAIModels(ctx, o.client)
	if err != nil {
		slog.Error("unable to fetch models from OpenAI API")
		return nil
	}

	for _, name := range models.chat {
		model := newModel(o.client, name, &defaultOpenAIOpts)
		if actionDef, ok := model.(api.Action); ok {
			actions = append(actions, actionDef.Desc())
		}
	}
	for _, e := range models.embedders {
		embedder := newEmbedder(o.client, e, &defaultEmbedOpts)
		if actionDef, ok := embedder.(api.Action); ok {
			actions = append(actions, actionDef.Desc())
		}
	}
	return actions
}

// ResolveAction resolves an action with the given name.
func (o *OpenAI) ResolveAction(atype api.ActionType, name string) api.Action {
	switch atype {
	case api.ActionTypeEmbedder:
		return newEmbedder(o.client, name, &ai.EmbedderOptions{}).(api.Action)
	case api.ActionTypeModel:
		var supports *ai.ModelSupports
		var config any

		switch {
		// TODO: add image and video models
		default:
			supports = &internal.Multimodal
			config = &openai.ChatCompletionNewParams{}
		}
		return newModel(o.client, name, &ai.ModelOptions{
			Label:        fmt.Sprintf("%s - %s", openaiLabelPrefix, name),
			Stage:        ai.ModelStageStable,
			Versions:     []string{},
			Supports:     supports,
			ConfigSchema: configToMap(config),
		}).(api.Action)
	}
	return nil
}

// openaiModels contains the collection of supported OpenAI models
type openaiModels struct {
	chat      []string // gpt, tts, o1, o2, o3...
	image     []string // gpt-image
	video     []string // sora
	embedders []string // text-embedding...
}

// listOpenAIModels returns a list of models available in the OpenAI API
// The returned struct is a filtered list of models based on plain string comparisons:
// chat: gpt, tts, o1, o2, o3...
// image: gpt-image
// video: sora
// embedders: text-embedding
// NOTE: the returned list from the SDK is just a plain slice of model names.
// No extra information about the model stage or type is provided.
// See: platform.openai.com/docs/models
func listOpenAIModels(ctx context.Context, client *openai.Client) (openaiModels, error) {
	models := openaiModels{}
	iter := client.Models.ListAutoPaging(ctx)
	for iter.Next() {
		m := iter.Current()
		if strings.Contains(m.ID, "sora") {
			models.video = append(models.video, m.ID)
			continue
		}
		if strings.Contains(m.ID, "image") {
			models.image = append(models.image, m.ID)
			continue
		}
		if strings.Contains(m.ID, "embedding") {
			models.embedders = append(models.embedders, m.ID)
			continue
		}
		models.chat = append(models.chat, m.ID)
	}
	if err := iter.Err(); err != nil {
		return openaiModels{}, err
	}

	return models, nil
}

// newEmbedder creates a new embedder without registering it
func newEmbedder(client *openai.Client, name string, embedOpts *ai.EmbedderOptions) ai.Embedder {
	return ai.NewEmbedder(api.NewName(openaiProvider, name), embedOpts, func(ctx context.Context, req *ai.EmbedRequest) (*ai.EmbedResponse, error) {
		var data openai.EmbeddingNewParamsInputUnion
		for _, doc := range req.Input {
			for _, p := range doc.Content {
				data.OfArrayOfStrings = append(data.OfArrayOfStrings, p.Text)
			}
		}

		params := openai.EmbeddingNewParams{
			Input:          openai.EmbeddingNewParamsInputUnion(data),
			Model:          name,
			EncodingFormat: openai.EmbeddingNewParamsEncodingFormatFloat,
		}

		embeddingResp, err := client.Embeddings.New(ctx, params)
		if err != nil {
			return nil, err
		}

		resp := &ai.EmbedResponse{}
		for _, e := range embeddingResp.Data {
			embedding := make([]float32, len(e.Embedding))
			for i, v := range e.Embedding {
				embedding[i] = float32(v)
			}
			resp.Embeddings = append(resp.Embeddings, &ai.Embedding{Embedding: embedding})
		}
		return resp, nil
	})
}

// newModel creates a new model without registering it in the registry
func newModel(client *openai.Client, name string, opts *ai.ModelOptions) ai.Model {
	var config any
	config = &responses.ResponseNewParams{}
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
		// TODO: add support for imagen and video
		case *responses.ResponseNewParams:
			return generate(ctx, client, name, input, cb)
		default:
			return generate(ctx, client, name, input, cb)
		}
	}

	return ai.NewModel(api.NewName(openaiProvider, name), meta, fn)
}

// configToMap converts a config struct to a map[string]any
func configToMap(config any) map[string]any {
	r := jsonschema.Reflector{
		DoNotReference:             true,
		AllowAdditionalProperties:  false,
		ExpandedStruct:             true,
		RequiredFromJSONSchemaTags: true,
	}

	r.Mapper = func(r reflect.Type) *jsonschema.Schema {
		if r.Name() == "Opt[float64]" {
			return &jsonschema.Schema{
				Type: "number",
			}
		}
		if r.Name() == "Opt[int64]" {
			return &jsonschema.Schema{
				Type: "integer",
			}
		}
		if r.Name() == "Opt[string]" {
			return &jsonschema.Schema{
				Type: "string",
			}
		}
		if r.Name() == "Opt[bool]" {
			return &jsonschema.Schema{
				Type: "boolean",
			}
		}
		return nil
	}
	schema := r.Reflect(config)
	result := base.SchemaAsMap(schema)

	return result
}

// generate is the entry point function to request content generation to the OpenAI client
func generate(ctx context.Context, client *openai.Client, model string, input *ai.ModelRequest, cb func(context.Context, *ai.ModelResponseChunk) error,
) (*ai.ModelResponse, error) {
	req, err := toOpenAIResponseParams(model, input)
	if err != nil {
		return nil, err
	}

	// stream mode
	if cb != nil {
		resp, err := generateStream(ctx, client, req, input, cb)
		if err != nil {
			return nil, err
		}
		return resp, nil

	}

	resp, err := generateComplete(ctx, client, req, input)
	if err != nil {
		return nil, err
	}
	return resp, nil
}

// toOpenAIResponseParams translates an [ai.ModelRequest] into [responses.ResponseNewParams]
func toOpenAIResponseParams(model string, input *ai.ModelRequest) (*responses.ResponseNewParams, error) {
	params, err := configFromRequest(input.Config)
	if err != nil {
		return nil, err
	}
	if params == nil {
		params = &responses.ResponseNewParams{}
	}

	params.Model = shared.ResponsesModel(model)

	// Handle tools
	if len(input.Tools) > 0 {
		tools, err := toOpenAITools(input.Tools)
		if err != nil {
			return nil, err
		}
		params.Tools = tools
		switch input.ToolChoice {
		case ai.ToolChoiceAuto, "":
			params.ToolChoice = responses.ResponseNewParamsToolChoiceUnion{
				OfToolChoiceMode: param.NewOpt(responses.ToolChoiceOptions("auto")),
			}
		case ai.ToolChoiceRequired:
			params.ToolChoice = responses.ResponseNewParamsToolChoiceUnion{
				OfToolChoiceMode: param.NewOpt(responses.ToolChoiceOptions("required")),
			}
		case ai.ToolChoiceNone:
			params.ToolChoice = responses.ResponseNewParamsToolChoiceUnion{
				OfToolChoiceMode: param.NewOpt(responses.ToolChoiceOptions("none")),
			}
		default:
			params.ToolChoice = responses.ResponseNewParamsToolChoiceUnion{
				OfFunctionTool: &responses.ToolChoiceFunctionParam{
					Name: string(input.ToolChoice),
				},
			}
		}
	}

	// messages to input items
	var inputItems []responses.ResponseInputItemUnionParam
	var instructions []string

	for _, m := range input.Messages {
		if m.Role == ai.RoleSystem {
			instructions = append(instructions, m.Text())
			continue
		}

		items, err := toOpenAIInputItems(m)
		if err != nil {
			return nil, err
		}
		inputItems = append(inputItems, items...)
	}

	if len(instructions) > 0 {
		params.Instructions = param.NewOpt(strings.Join(instructions, "\n"))
	}
	if len(inputItems) > 0 {
		params.Input = responses.ResponseNewParamsInputUnion{
			OfInputItemList: inputItems,
		}
	}

	return params, nil
}

// toOpenAIInputItems converts a Genkit message to OpenAI Input Items
func toOpenAIInputItems(m *ai.Message) ([]responses.ResponseInputItemUnionParam, error) {
	var items []responses.ResponseInputItemUnionParam
	var partsBuffer []*ai.Part

	// flush() converts a sequence of text and media parts into a single OpenAI Input Item.
	// Message roles taken in consideration:
	// Model (or Assistant): converted to [responses.ResponseOutputMessageContentUnionParam]
	// User/System: converted to [responses.ResponseInputContentUnionParam]
	//
	// This is needed for the Responses API since it forbids to use Input Items for assistant role messages
	flush := func() error {
		if len(partsBuffer) == 0 {
			return nil
		}

		if m.Role == ai.RoleModel {
			// conversation-history text messages that the model previously generated
			var content []responses.ResponseOutputMessageContentUnionParam
			for _, p := range partsBuffer {
				if p.IsText() {
					content = append(content, responses.ResponseOutputMessageContentUnionParam{
						OfOutputText: &responses.ResponseOutputTextParam{
							Text:        p.Text,
							Annotations: []responses.ResponseOutputTextAnnotationUnionParam{},
						},
					})
				}
			}
			if len(content) > 0 {
				// we need a unique ID for the output message
				id := fmt.Sprintf("msg_%p", m)
				items = append(items, responses.ResponseInputItemParamOfOutputMessage(
					content,
					id,
					responses.ResponseOutputMessageStatusCompleted,
				))
			}
		} else {
			var content []responses.ResponseInputContentUnionParam
			for _, p := range partsBuffer {
				if p.IsText() {
					content = append(content, responses.ResponseInputContentParamOfInputText(p.Text))
				} else if p.IsImage() || p.IsMedia() {
					content = append(content, responses.ResponseInputContentUnionParam{
						OfInputImage: &responses.ResponseInputImageParam{
							ImageURL: param.NewOpt(p.Text),
						},
					})
				}
			}
			if len(content) > 0 {
				role := responses.EasyInputMessageRoleUser
				// prevent unexpected system messages being sent as User, use Developer role to
				// provide new "system" instructions during the conversation
				if m.Role == ai.RoleSystem {
					role = responses.EasyInputMessageRole("developer")
				}
				items = append(items, responses.ResponseInputItemParamOfMessage(
					responses.ResponseInputMessageContentListParam(content), role),
				)
			}
		}

		partsBuffer = nil
		return nil
	}

	for _, p := range m.Content {
		if p.IsText() || p.IsImage() || p.IsMedia() {
			partsBuffer = append(partsBuffer, p)
		} else if p.IsToolRequest() {
			if err := flush(); err != nil {
				return nil, err
			}
			args, err := anyToJSONString(p.ToolRequest.Input)
			if err != nil {
				return nil, err
			}
			ref := p.ToolRequest.Ref
			if ref == "" {
				ref = p.ToolRequest.Name
			}
			items = append(items, responses.ResponseInputItemParamOfFunctionCall(args, ref, p.ToolRequest.Name))
		} else if p.IsToolResponse() {
			if err := flush(); err != nil {
				return nil, err
			}
			output, err := anyToJSONString(p.ToolResponse.Output)
			if err != nil {
				return nil, err
			}
			ref := p.ToolResponse.Ref
			items = append(items, responses.ResponseInputItemParamOfFunctionCallOutput(ref, output))
		}
	}
	if err := flush(); err != nil {
		return nil, err
	}

	return items, nil
}

// toOpenAITools converts a slice of [ai.ToolDefinition] to [responses.ToolUnionParam]
func toOpenAITools(tools []*ai.ToolDefinition) ([]responses.ToolUnionParam, error) {
	var result []responses.ToolUnionParam
	for _, t := range tools {
		if t == nil || t.Name == "" {
			continue
		}
		result = append(result, responses.ToolParamOfFunction(t.Name, t.InputSchema, false))
	}
	return result, nil
}

// generateStream starts a new streaming response
func generateStream(ctx context.Context, client *openai.Client, req *responses.ResponseNewParams, input *ai.ModelRequest, cb func(context.Context, *ai.ModelResponseChunk) error) (*ai.ModelResponse, error) {
	stream := client.Responses.NewStreaming(ctx, *req)
	defer stream.Close()

	var (
		toolRefMap = make(map[string]string)
		finalResp  *responses.Response
	)

	for stream.Next() {
		evt := stream.Current()
		chunk := &ai.ModelResponseChunk{}

		switch v := evt.AsAny().(type) {
		case responses.ResponseTextDeltaEvent:
			chunk.Content = append(chunk.Content, ai.NewTextPart(v.Delta))

		case responses.ResponseFunctionCallArgumentsDeltaEvent:
			name := toolRefMap[v.ItemID]
			chunk.Content = append(chunk.Content, ai.NewToolRequestPart(&ai.ToolRequest{
				Ref:   v.ItemID,
				Name:  name,
				Input: v.Delta,
			}))

		case responses.ResponseOutputItemAddedEvent:
			switch item := v.Item.AsAny().(type) {
			case responses.ResponseFunctionToolCall:
				toolRefMap[item.CallID] = item.Name
				chunk.Content = append(chunk.Content, ai.NewToolRequestPart(&ai.ToolRequest{
					Ref:  item.CallID,
					Name: item.Name,
				}))
			}

		case responses.ResponseCompletedEvent:
			finalResp = &v.Response
		}

		if len(chunk.Content) > 0 {
			if err := cb(ctx, chunk); err != nil {
				return nil, fmt.Errorf("callback error: %w", err)
			}
		}
	}

	if err := stream.Err(); err != nil {
		return nil, fmt.Errorf("stream error: %w", err)
	}

	if finalResp != nil {
		mResp, err := translateResponse(finalResp)
		if err != nil {
			return nil, err
		}
		mResp.Request = input
		return mResp, nil
	}

	// prevent returning an error if stream does not provide [responses.ResponseCompletedEvent]
	// user might already have received the chunks throughout the loop
	return &ai.ModelResponse{
		Request: input,
		Message: &ai.Message{Role: ai.RoleModel},
	}, nil
}

// generateComplete starts a new completion
func generateComplete(ctx context.Context, client *openai.Client, req *responses.ResponseNewParams, input *ai.ModelRequest) (*ai.ModelResponse, error) {
	resp, err := client.Responses.New(ctx, *req)
	if err != nil {
		return nil, err
	}

	modelResp, err := translateResponse(resp)
	if err != nil {
		return nil, err
	}
	modelResp.Request = input
	return modelResp, nil
}

// translateResponse translates an [responses.Response] into an [ai.ModelResponse]
func translateResponse(r *responses.Response) (*ai.ModelResponse, error) {
	resp := &ai.ModelResponse{
		Message: &ai.Message{
			Role:    ai.RoleModel,
			Content: make([]*ai.Part, 0),
		},
	}

	resp.Usage = &ai.GenerationUsage{
		InputTokens:         int(r.Usage.InputTokens),
		OutputTokens:        int(r.Usage.OutputTokens),
		CachedContentTokens: int(r.Usage.InputTokensDetails.CachedTokens),
		ThoughtsTokens:      int(r.Usage.OutputTokensDetails.ReasoningTokens),
		TotalTokens:         int(r.Usage.TotalTokens),
	}

	switch r.Status {
	case responses.ResponseStatusCompleted:
		resp.FinishReason = ai.FinishReasonStop
	case responses.ResponseStatusIncomplete:
		resp.FinishReason = ai.FinishReasonLength
	case responses.ResponseStatusFailed, responses.ResponseStatusCancelled:
		resp.FinishReason = ai.FinishReasonOther
	default:
		resp.FinishReason = ai.FinishReasonUnknown
	}

	for _, item := range r.Output {
		switch v := item.AsAny().(type) {
		case responses.ResponseOutputMessage:
			for _, content := range v.Content {
				switch c := content.AsAny().(type) {
				case responses.ResponseOutputText:
					resp.Message.Content = append(resp.Message.Content, ai.NewTextPart(c.Text))
				case responses.ResponseOutputRefusal:
					resp.FinishMessage = c.Refusal
					resp.FinishReason = ai.FinishReasonBlocked
				}
			}
		case responses.ResponseFunctionToolCall:
			args, err := jsonStringToMap(v.Arguments)
			if err != nil {
				return nil, fmt.Errorf("could not parse tool args: %w", err)
			}
			resp.Message.Content = append(resp.Message.Content, ai.NewToolRequestPart(&ai.ToolRequest{
				Ref:   v.CallID,
				Name:  v.Name,
				Input: args,
			}))
		}
	}

	return resp, nil
}

// configFromRequest casts the given configuration into [responses.ResponseNewParams]
func configFromRequest(config any) (*responses.ResponseNewParams, error) {
	if config == nil {
		return nil, nil
	}

	var openaiConfig responses.ResponseNewParams
	switch cfg := config.(type) {
	case responses.ResponseNewParams:
		openaiConfig = cfg
	case *responses.ResponseNewParams:
		openaiConfig = *cfg
	case map[string]any:
		if err := mapToStruct(cfg, &openaiConfig); err != nil {
			return nil, fmt.Errorf("failed to convert config to responses.ResponseNewParams: %w", err)
		}
	default:
		return nil, fmt.Errorf("unexpected config type: %T", config)
	}
	return &openaiConfig, nil
}

// anyToJSONString converts a stream of bytes to a JSON string
func anyToJSONString(data any) (string, error) {
	jsonBytes, err := json.Marshal(data)
	if err != nil {
		return "", fmt.Errorf("failed to marshal any to JSON string: %w", err)
	}
	return string(jsonBytes), nil
}

// mapToStruct converts the provided map into a given struct
func mapToStruct(m map[string]any, v any) error {
	jsonData, err := json.Marshal(m)
	if err != nil {
		return err
	}
	return json.Unmarshal(jsonData, v)
}

// jsonStringToMap translates a JSON string into a map
func jsonStringToMap(jsonString string) (map[string]any, error) {
	var result map[string]any
	if err := json.Unmarshal([]byte(jsonString), &result); err != nil {
		return nil, fmt.Errorf("unmarshal failed to parse json string %s: %w", jsonString, err)
	}
	return result, nil
}
