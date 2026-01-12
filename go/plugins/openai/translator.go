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
	"encoding/json"
	"fmt"
	"reflect"
	"strings"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/internal/base"
	"github.com/invopop/jsonschema"
	"github.com/openai/openai-go/v3/packages/param"
	"github.com/openai/openai-go/v3/responses"
	"github.com/openai/openai-go/v3/shared"
	"github.com/openai/openai-go/v3/shared/constant"
)

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
		// Append user tools to any existing tools (e.g. built-in tools provided in config)
		params.Tools = append(params.Tools, tools...)

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
							Type:        constant.OutputText("output_text"),
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
			fmt.Printf("tool request detected: %#v\n", p.ToolRequest)
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
