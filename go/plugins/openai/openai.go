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

package openai

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"os"
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

var defaultImagenOpts = ai.ModelOptions{
	Supports: &internal.Media,
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
func (o *OpenAI) DefineModel(g *genkit.Genkit, name string, opts ai.ModelOptions) (ai.Model, error) {
	o.mu.Lock()
	defer o.mu.Unlock()
	if !o.initted {
		panic("OpenAI.Init not called")
	}

	// TODO: define a model, basically you need the generate() func
	return nil, nil
}

// OpenAIModel returns the [ai.Model] with the given name.
// It returns nil if the model was not previously defined.
func (o *OpenAI) OpenAIModel(g *genkit.Genkit, name string) ai.Model {
	return genkit.LookupModel(g, api.NewName(openaiProvider, name))
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
func (o *OpenAI) Embedder(g *genkit.Genkit, name string) ai.Embedder {
	return genkit.LookupEmbedder(g, name)
}

// IsDefinedEmbedder reports whether the named [ai.Embedder] is defined by this plugin
func (o *OpenAI) IsDefinedEmbedder(g *genkit.Genkit, name string) bool {
	return genkit.LookupEmbedder(g, name) != nil
}

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

func (o *OpenAI) ResolveAction(atype api.ActionType, name string) api.Action {
	return nil
}

type openaiModels struct {
	chat      []string // gpt, tts, o1, o2, o3...
	image     []string // gpt-image
	video     []string // sora
	embedders []string // text-embedding...
}

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

		// NOTE: model list is just a slice of names, no extra information about them
		// is available, we might select deprecated models here
		// see platform.openai.com/docs/models
		models.chat = append(models.chat, m.ID)
	}
	if err := iter.Err(); err != nil {
		return openaiModels{}, err
	}

	return models, nil
}

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

func newModel(client *openai.Client, name string, opts *ai.ModelOptions) ai.Model {
	// TODO: add support for imagen models
	var config any
	config = &openai.ChatCompletionNewParams{}
	meta := &ai.ModelOptions{
		Label:        opts.Label,
		Supports:     opts.Supports,
		Versions:     opts.Versions,
		ConfigSchema: configToMap(config),
		Stage:        opts.Stage,
	}

	fmt.Printf("meta for [%s]: %#v\n", name, meta)
	fn := func(
		ctx context.Context,
		input *ai.ModelRequest,
		cb func(context.Context, *ai.ModelResponseChunk) error,
	) (*ai.ModelResponse, error) {
		switch config.(type) {
		default:
			return nil, nil
		}
	}

	return ai.NewModel(api.NewName(openaiProvider, name), meta, fn)
}

// configToMap converts a config struct to a map[string]any
func configToMap(config any) map[string]any {
	r := jsonschema.Reflector{
		DoNotReference: true,
		ExpandedStruct: true,
	}
	schema := r.Reflect(config)
	result := base.SchemaAsMap(schema)
	return result
}

func generate(ctx context.Context, client *openai.Client, model string, input *ai.ModelRequest, cb func(context.Context, *ai.ModelResponseChunk) error,
) (*ai.ModelResponse, error) {
	req, err := toOpenAIRequest(model, input)
	if err != nil {
		return nil, err
	}
	if cb != nil {
		return generateStream(ctx, client, req, cb)
	}
	return generateComplete(ctx, client, req, input)
}

func toOpenAIRequest(model string, input *ai.ModelRequest) (*openai.ChatCompletionNewParams, error) {
	request, err := configFromRequest(input.Config)
	if err != nil {
		return nil, err
	}
	if request == nil {
		request = &openai.ChatCompletionNewParams{}
	}

	request.Model = model
	// generate only one candidate response
	if request.N == openai.Int(0) {
		request.N = openai.Int(1)
	}

	// Genkit primitive fields must be used instead of openai-go fields
	if request.N != openai.Int(1) {
		return nil, errors.New("generation of multiple candidates is not supported")
	}
	if !param.IsOmitted(request.ResponseFormat) {
		return nil, errors.New("response format must be set using Genkit feature: ai.WithOutputType() or ai.WithOutputSchema()")
	}
	if request.ParallelToolCalls == openai.Bool(true) {
		return nil, errors.New("only one tool call per turn is allowed")
	}

	if len(input.Tools) > 0 {
		tools, tc, err := toOpenAITools(input.Tools, input.ToolChoice)
		if err != nil {
			return nil, err
		}
		request.Tools = tools
		request.ToolChoice = *tc
	}

	oaiMessages := make([]openai.ChatCompletionMessageParamUnion, 0, len(input.Messages))
	for _, m := range input.Messages {
		switch m.Role {
		case ai.RoleSystem:
			oaiMessages = append(oaiMessages, toOpenAISystemMessage(m))

		case ai.RoleModel:
			msg, err := toOpenAIModelMessage(m)
			if err != nil {
				return nil, err
			}
			oaiMessages = append(oaiMessages, msg)

		case ai.RoleUser:
			msg, err := toOpenAIUserMessage(m)
			if err != nil {
				return nil, err
			}
			oaiMessages = append(oaiMessages, msg)

		case ai.RoleTool:
			msgs, err := toOpenAIToolMessages(m)
			if err != nil {
				return nil, err
			}
			oaiMessages = append(oaiMessages, msgs...)

		default:
			return nil, fmt.Errorf("unsupported role detected: %q", m.Role)
		}
	}

	request.Messages = oaiMessages

	return request, nil
}

func toOpenAISystemMessage(m *ai.Message) openai.ChatCompletionMessageParamUnion {
	return openai.SystemMessage(m.Text())
}

func toOpenAIModelMessage(m *ai.Message) (openai.ChatCompletionMessageParamUnion, error) {
	var (
		textParts []openai.ChatCompletionAssistantMessageParamContentArrayOfContentPartUnion
		toolCalls []openai.ChatCompletionMessageToolCallUnionParam
	)

	for _, p := range m.Content {
		if p.IsText() {
			textParts = append(textParts, openai.ChatCompletionAssistantMessageParamContentArrayOfContentPartUnion{
				OfText: openai.TextContentPart(p.Text).OfText,
			})
		} else if p.IsToolRequest() {
			toolCall, err := convertToolCall(p)
			if err != nil {
				return openai.ChatCompletionMessageParamUnion{}, err
			}
			toolCalls = append(toolCalls, *toolCall)
		} else {
			slog.Warn("unsupported part for assistant message", "kind", p.Kind)
		}
	}

	msg := openai.ChatCompletionAssistantMessageParam{}
	if len(textParts) > 0 {
		msg.Content = openai.ChatCompletionAssistantMessageParamContentUnion{
			OfArrayOfContentParts: textParts,
		}
	}
	if len(toolCalls) > 0 {
		msg.ToolCalls = toolCalls
	}
	return openai.ChatCompletionMessageParamUnion{
		OfAssistant: &msg,
	}, nil
}

func toOpenAIUserMessage(m *ai.Message) (openai.ChatCompletionMessageParamUnion, error) {
	msg, err := toOpenAIParts(m.Content)
	if err != nil {
		return openai.ChatCompletionMessageParamUnion{}, err
	}
	userParts := make([]openai.ChatCompletionContentPartUnionParam, len(msg))
	for i, p := range msg {
		userParts[i] = *p
	}
	return openai.ChatCompletionMessageParamUnion{
		OfUser: &openai.ChatCompletionUserMessageParam{
			Content: openai.ChatCompletionUserMessageParamContentUnion{
				OfArrayOfContentParts: userParts,
			},
		},
	}, nil
}

func toOpenAIToolMessages(m *ai.Message) ([]openai.ChatCompletionMessageParamUnion, error) {
	var msgs []openai.ChatCompletionMessageParamUnion
	for _, p := range m.Content {
		if p.IsToolResponse() {
			content, err := json.Marshal(p.ToolResponse.Output)
			if err != nil {
				return nil, fmt.Errorf("failed to marshal tool response output: %w", err)
			}
			msgs = append(msgs, openai.ChatCompletionMessageParamUnion{
				OfTool: &openai.ChatCompletionToolMessageParam{
					ToolCallID: p.ToolResponse.Ref,
					Content: openai.ChatCompletionToolMessageParamContentUnion{
						OfString: param.NewOpt(string(content)),
					},
				},
			})
		}
	}
	return msgs, nil
}

// toOpenAIParts converts a slice of [ai.Part] to a slice of [openai.ChatCompletionMessageParamUnion]
func toOpenAIParts(parts []*ai.Part) ([]*openai.ChatCompletionContentPartUnionParam, error) {
	resp := make([]*openai.ChatCompletionContentPartUnionParam, 0, len(parts))
	for _, p := range parts {
		part, err := toOpenAIPart(p)
		if err != nil {
			return nil, err
		}
		resp = append(resp, part)
	}
	return resp, nil
}

func toOpenAIPart(p *ai.Part) (*openai.ChatCompletionContentPartUnionParam, error) {
	var m openai.ChatCompletionContentPartUnionParam
	if p == nil {
		return nil, fmt.Errorf("empty part detected")
	}

	switch {
	case p.IsText():
		m = openai.TextContentPart(p.Text)
	case p.IsImage(), p.IsMedia():
		m = openai.ImageContentPart(openai.ChatCompletionContentPartImageImageURLParam{
			URL: p.Text,
		})
	case p.IsData():
		m = openai.FileContentPart(openai.ChatCompletionContentPartFileFileParam{
			FileData: openai.String(p.Text),
		})
	default:
		return nil, fmt.Errorf("unsupported part kind: %v", p.Kind)
	}

	return &m, nil
}

// toOpenAITools converts a slice of [ai.ToolDefinition] and [ai.ToolChoice] to their appropriate openAI types
func toOpenAITools(tools []*ai.ToolDefinition, toolChoice ai.ToolChoice) ([]openai.ChatCompletionToolUnionParam, *openai.ChatCompletionToolChoiceOptionUnionParam, error) {
	if tools == nil {
		return nil, nil, nil
	}

	toolParams := make([]openai.ChatCompletionToolUnionParam, 0, len(tools))
	for _, t := range tools {
		if t == nil || t.Name == "" {
			continue
		}
		toolParams = append(toolParams, openai.ChatCompletionFunctionTool(shared.FunctionDefinitionParam{
			Name:        t.Name,
			Description: openai.String(t.Description),
			Parameters:  shared.FunctionParameters(t.InputSchema),
			Strict:      openai.Bool(false), // TODO: implement constrained gen
		}))
	}

	var choice openai.ChatCompletionToolChoiceOptionUnionParam
	switch toolChoice {
	case ai.ToolChoiceAuto, "":
		choice = openai.ChatCompletionToolChoiceOptionUnionParam{
			OfAuto: param.NewOpt(string(openai.ChatCompletionToolChoiceOptionAutoAuto)),
		}
	case ai.ToolChoiceRequired:
		choice = openai.ChatCompletionToolChoiceOptionUnionParam{
			OfAuto: param.NewOpt(string(openai.ChatCompletionToolChoiceOptionAutoRequired)),
		}
	case ai.ToolChoiceNone:
		choice = openai.ChatCompletionToolChoiceOptionUnionParam{
			OfAuto: param.NewOpt(string(openai.ChatCompletionToolChoiceOptionAutoNone)),
		}
	default:
		choice = openai.ToolChoiceOptionFunctionToolChoice(openai.ChatCompletionNamedToolChoiceFunctionParam{
			Name: string(toolChoice),
		})
	}

	return toolParams, &choice, nil
}

func generateStream(ctx context.Context, client *openai.Client, req *openai.ChatCompletionNewParams, cb func(context.Context, *ai.ModelResponseChunk) error) (*ai.ModelResponse, error) {
	return nil, errors.New("not implemented: generateStream")
}

func generateComplete(ctx context.Context, client *openai.Client, req *openai.ChatCompletionNewParams, input *ai.ModelRequest) (*ai.ModelResponse, error) {
	return nil, errors.New("not implemented: generateComplete")
}

func configFromRequest(config any) (*openai.ChatCompletionNewParams, error) {
	if config == nil {
		return nil, nil
	}

	var openaiConfig openai.ChatCompletionNewParams
	switch cfg := config.(type) {
	case openai.ChatCompletionNewParams:
		openaiConfig = cfg
	case *openai.ChatCompletionNewParams:
		openaiConfig = *cfg
	case map[string]any:
		if err := mapToStruct(cfg, &openaiConfig); err != nil {
			return nil, fmt.Errorf("failed to convert config to openai.ChatCompletionNewParams: %w", err)
		}
	default:
		return nil, fmt.Errorf("unexpected config type: %T", config)
	}
	return &openaiConfig, nil
}

func convertToolCalls(content []*ai.Part) ([]openai.ChatCompletionMessageToolCallUnionParam, error) {
	var toolCalls []openai.ChatCompletionMessageToolCallUnionParam
	for _, p := range content {
		if !p.IsToolRequest() {
			continue
		}
		toolCall, err := convertToolCall(p)
		if err != nil {
			return nil, err
		}
		toolCalls = append(toolCalls, *toolCall)
	}
	return toolCalls, nil
}

func convertToolCall(part *ai.Part) (*openai.ChatCompletionMessageToolCallUnionParam, error) {
	toolCallID := part.ToolRequest.Ref
	if toolCallID == "" {
		toolCallID = part.ToolRequest.Name
	}

	param := &openai.ChatCompletionMessageToolCallUnionParam{
		OfFunction: &openai.ChatCompletionMessageFunctionToolCallParam{
			ID: (toolCallID),
			Function: (openai.ChatCompletionMessageFunctionToolCallFunctionParam{
				Name: (part.ToolRequest.Name),
			}),
		},
	}

	args, err := anyToJSONString(part.ToolRequest.Input)
	if err != nil {
		return nil, err
	}
	if part.ToolRequest.Input != nil {
		param.OfFunction.Function.Arguments = args
	}

	return param, nil
}

func anyToJSONString(data any) (string, error) {
	jsonBytes, err := json.Marshal(data)
	if err != nil {
		return "", fmt.Errorf("failed to marshal any to JSON string: data, %#v %w", data, err)
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
