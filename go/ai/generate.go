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

package ai

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"strconv"
	"strings"

	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/core/logger"
	"github.com/firebase/genkit/go/core/tracing"
	"github.com/firebase/genkit/go/internal/atype"
	"github.com/firebase/genkit/go/internal/base"
	"github.com/firebase/genkit/go/internal/registry"
)

type (
	// Model represents a model that can generate content based on a request.
	Model interface {
		// Name returns the registry name of the model.
		Name() string
		// Generate applies the [Model] to provided request, handling tool requests and handles streaming.
		Generate(ctx context.Context, req *ModelRequest, cb ModelStreamCallback) (*ModelResponse, error)
	}

	// ToolConfig handles configuration around tool calls during generation.
	ToolConfig struct {
		MaxTurns           int  // Maximum number of tool call iterations before erroring.
		ReturnToolRequests bool // Whether to return tool requests instead of making the tool calls and continuing the generation.
	}

	// ModelFunc is a streaming function that takes in a ModelRequest and generates a ModelResponse, optionally streaming ModelResponseChunks.
	ModelFunc = core.StreamingFunc[*ModelRequest, *ModelResponse, *ModelResponseChunk]

	// ModelStreamCallback is a stream callback of a ModelAction.
	ModelStreamCallback = func(context.Context, *ModelResponseChunk) error

	// ModelMiddleware is middleware for model generate requests that takes in a ModelFunc, does something, then returns another ModelFunc.
	ModelMiddleware = core.Middleware[*ModelRequest, *ModelResponse, *ModelResponseChunk]

	// ModelAction is the type for model generation actions.
	ModelAction = core.ActionDef[*ModelRequest, *ModelResponse, *ModelResponseChunk]

	// modelActionDef is an action with functions specific to model generation such as Generate().
	modelActionDef core.ActionDef[*ModelRequest, *ModelResponse, *ModelResponseChunk]

	// generateAction is the type for a utility model generation action that takes in a GenerateActionOptions instead of a ModelRequest.
	generateAction = core.ActionDef[*GenerateActionOptions, *ModelResponse, *ModelResponseChunk]
)

// DefineGenerateAction defines a utility generate action.
func DefineGenerateAction(ctx context.Context, r *registry.Registry) *generateAction {
	return (*generateAction)(core.DefineStreamingAction(r, "", "generate", atype.Util, nil,
		func(ctx context.Context, actionOpts *GenerateActionOptions, cb ModelStreamCallback) (resp *ModelResponse, err error) {
			logger.FromContext(ctx).Debug("GenerateAction",
				"input", fmt.Sprintf("%#v", actionOpts))
			defer func() {
				logger.FromContext(ctx).Debug("GenerateAction",
					"output", fmt.Sprintf("%#v", resp),
					"err", err)
			}()

			return tracing.RunInNewSpan(ctx, r.TracingState(), "generate", "util", false, actionOpts,
				func(ctx context.Context, actionOpts *GenerateActionOptions) (*ModelResponse, error) {
					return GenerateWithRequest(ctx, r, actionOpts, nil, cb)
				})
		}))
}

// DefineModel registers the given generate function as an action, and returns a [Model] that runs it.
func DefineModel(r *registry.Registry, provider, name string, info *ModelInfo, fn ModelFunc) Model {
	if info == nil {
		// Always make sure there's at least minimal metadata.
		info = &ModelInfo{
			Label:    name,
			Supports: &ModelSupports{},
			Versions: []string{},
		}
	}

	metadata := map[string]any{
		"model": map[string]any{
			"supports": map[string]bool{
				"media":      info.Supports.Media,
				"multiturn":  info.Supports.Multiturn,
				"systemRole": info.Supports.SystemRole,
				"tools":      info.Supports.Tools,
				"toolChoice": info.Supports.ToolChoice,
			},
			"versions": info.Versions,
		},
	}
	if info.Label != "" {
		metadata["label"] = info.Label
	}

	// Create the middleware list
	middlewares := []ModelMiddleware{
		simulateSystemPrompt(info, nil),
		augmentWithContext(info, nil),
		validateSupport(name, info),
	}

	fn = core.ChainMiddleware(middlewares...)(fn)

	return (*modelActionDef)(core.DefineStreamingAction(r, provider, name, atype.Model, metadata, fn))
}

// LookupModel looks up a [Model] registered by [DefineModel].
// It returns nil if the model was not defined.
func LookupModel(r *registry.Registry, provider, name string) Model {
	action := core.LookupActionFor[*ModelRequest, *ModelResponse, *ModelResponseChunk](r, atype.Model, provider, name)
	if action == nil {
		return nil
	}
	return (*modelActionDef)(action)
}

// LookupModelByName looks up a [Model] registered by [DefineModel].
// It returns an error if the model was not defined.
func LookupModelByName(r *registry.Registry, modelName string) (Model, error) {
	if modelName == "" {
		return nil, errors.New("ai.LookupModelByName: model not specified")
	}

	provider, name, found := strings.Cut(modelName, "/")
	if !found {
		name = provider
		provider = ""
	}

	model := LookupModel(r, provider, name)
	if model == nil {
		if provider == "" {
			return nil, fmt.Errorf("ai.LookupModelByName: no model named %q", name)
		}
		return nil, fmt.Errorf("ai.LookupModelByName: no model named %q for provider %q", name, provider)
	}

	return model, nil
}

// GenerateWithRequest is the central generation implementation for ai.Generate(), prompt.Execute(), and the GenerateAction direct call.
func GenerateWithRequest(ctx context.Context, r *registry.Registry, opts *GenerateActionOptions, mw []ModelMiddleware, cb ModelStreamCallback) (*ModelResponse, error) {
	if opts.Model == "" {
		opts.Model = r.LookupValue(registry.DefaultModelKey).(string)
		if opts.Model == "" {
			return nil, errors.New("ai.GenerateWithRequest: model is required")
		}
	}

	model, err := LookupModelByName(r, opts.Model)
	if err != nil {
		return nil, err
	}

	toolDefMap := make(map[string]*ToolDefinition)
	for _, t := range opts.Tools {
		if _, ok := toolDefMap[t]; ok {
			return nil, fmt.Errorf("ai.GenerateWithRequest: duplicate tool found: %q", t)
		}

		tool := LookupTool(r, t)
		if tool == nil {
			return nil, fmt.Errorf("ai.GenerateWithRequest: tool not found: %q", t)
		}

		toolDefMap[t] = tool.Definition()
	}
	toolDefs := make([]*ToolDefinition, 0, len(toolDefMap))
	for _, t := range toolDefMap {
		toolDefs = append(toolDefs, t)
	}

	maxTurns := opts.MaxTurns
	if maxTurns < 0 {
		return nil, fmt.Errorf("ai.GenerateWithRequest: max turns must be greater than 0, got %d", maxTurns)
	}
	if maxTurns == 0 {
		maxTurns = 5 // Default max turns.
	}

	var output *ModelOutputConfig
	if opts.Output != nil {
		output = &ModelOutputConfig{
			Format: opts.Output.Format,
			Schema: opts.Output.JsonSchema,
		}
		if output.Schema != nil && output.Format == "" {
			output.Format = string(OutputFormatJSON)
		}
	}

	req := &ModelRequest{
		Messages:   opts.Messages,
		Config:     opts.Config,
		Docs:       opts.Docs,
		ToolChoice: opts.ToolChoice,
		Tools:      toolDefs,
		Output:     output,
	}

	if err := conformOutput(req); err != nil {
		return nil, err
	}

	fn := core.ChainMiddleware(mw...)(model.Generate)

	currentTurn := 0
	for {
		resp, err := fn(ctx, req, cb)
		if err != nil {
			return nil, err
		}

		resp.Message, err = validResponse(ctx, resp)
		if err != nil {
			return nil, err
		}

		toolCount := 0
		for _, part := range resp.Message.Content {
			if part.IsToolRequest() {
				toolCount++
			}
		}
		if toolCount == 0 || opts.ReturnToolRequests {
			return resp, nil
		}

		if currentTurn+1 > maxTurns {
			return nil, fmt.Errorf("exceeded maximum tool call iterations (%d)", maxTurns)
		}

		newReq, interruptMsg, err := handleToolRequests(ctx, r, req, resp, cb)
		if err != nil {
			return nil, err
		}
		if interruptMsg != nil {
			resp.FinishReason = "interrupted"
			resp.FinishMessage = "One or more tool calls resulted in interrupts."
			resp.Message = interruptMsg
			return resp, nil
		}
		if newReq == nil {
			return resp, nil
		}

		req = newReq
		currentTurn++
	}
}

// Generate generates a model response based on the provided options.
func Generate(ctx context.Context, r *registry.Registry, opts ...GenerateOption) (*ModelResponse, error) {
	genOpts := &generateOptions{}
	for _, opt := range opts {
		err := opt.applyGenerate(genOpts)
		if err != nil {
			return nil, fmt.Errorf("ai.Generate: error applying options: %w", err)
		}
	}

	modelName := genOpts.ModelName
	if modelName == "" && genOpts.Model != nil {
		modelName = genOpts.Model.Name()
	}

	tools := make([]string, len(genOpts.Tools))
	for i, tool := range genOpts.Tools {
		tools[i] = tool.Name()
	}

	messages := []*Message{}
	if genOpts.SystemFn != nil {
		system, err := genOpts.SystemFn(ctx, genOpts)
		if err != nil {
			return nil, err
		}

		messages = append(messages, NewSystemTextMessage(system))
	}
	if genOpts.MessagesFn != nil {
		msgs, err := genOpts.MessagesFn(ctx, genOpts)
		if err != nil {
			return nil, err
		}

		messages = append(messages, msgs...)
	}
	if genOpts.PromptFn != nil {
		prompt, err := genOpts.PromptFn(ctx, genOpts)
		if err != nil {
			return nil, err
		}

		messages = append(messages, NewUserTextMessage(prompt))
	}

	actionOpts := &GenerateActionOptions{
		Model:              modelName,
		Messages:           messages,
		Tools:              tools,
		MaxTurns:           genOpts.MaxTurns,
		Config:             genOpts.Config,
		ToolChoice:         genOpts.ToolChoice,
		Docs:               genOpts.Documents,
		ReturnToolRequests: genOpts.ReturnToolRequests,
		Output: &GenerateActionOutputConfig{
			JsonSchema: genOpts.OutputSchema,
			Format:     string(genOpts.OutputFormat),
		},
	}

	return GenerateWithRequest(ctx, r, actionOpts, genOpts.Middleware, genOpts.Stream)
}

// GenerateText run generate request for this model. Returns generated text only.
func GenerateText(ctx context.Context, r *registry.Registry, opts ...GenerateOption) (string, error) {
	res, err := Generate(ctx, r, opts...)
	if err != nil {
		return "", err
	}

	return res.Text(), nil
}

// Generate run generate request for this model. Returns ModelResponse struct.
// TODO: Stream GenerateData with partial JSON
func GenerateData(ctx context.Context, r *registry.Registry, value any, opts ...GenerateOption) (*ModelResponse, error) {
	opts = append(opts, WithOutputType(value))

	resp, err := Generate(ctx, r, opts...)
	if err != nil {
		return nil, err
	}

	err = resp.Output(value)
	if err != nil {
		return nil, err
	}

	return resp, nil
}

// Name returns the name of the model.
func (m *modelActionDef) Name() string { return (*ModelAction)(m).Name() }

// Generate applies the [Action] to provided request.
func (m *modelActionDef) Generate(ctx context.Context, req *ModelRequest, cb ModelStreamCallback) (*ModelResponse, error) {
	if m == nil {
		return nil, errors.New("Model.Generate: generate called on a nil model; check that all models are defined")
	}

	return (*ModelAction)(m).Run(ctx, req, cb)
}

// cloneMessage creates a deep copy of the provided Message.
func cloneMessage(m *Message) *Message {
	if m == nil {
		return nil
	}

	bytes, err := json.Marshal(m)
	if err != nil {
		panic(fmt.Sprintf("failed to marshal message: %v", err))
	}

	var copy Message
	if err := json.Unmarshal(bytes, &copy); err != nil {
		panic(fmt.Sprintf("failed to unmarshal message: %v", err))
	}

	return &copy
}

// handleToolRequests processes any tool requests in the response, returning
// either a new request to continue the conversation or nil if no tool requests
// need handling.
func handleToolRequests(ctx context.Context, r *registry.Registry, req *ModelRequest, resp *ModelResponse, cb ModelStreamCallback) (*ModelRequest, *Message, error) {
	toolCount := 0
	for _, part := range resp.Message.Content {
		if part.IsToolRequest() {
			toolCount++
		}
	}

	if toolCount == 0 {
		return nil, nil, nil
	}

	type toolResult struct {
		index  int
		output any
		err    error
	}

	resultChan := make(chan toolResult)
	toolMessage := &Message{Role: RoleTool}
	revisedMessage := cloneMessage(resp.Message)

	for i, part := range resp.Message.Content {
		if !part.IsToolRequest() {
			continue
		}

		go func(idx int, p *Part) {
			toolReq := p.ToolRequest
			tool := LookupTool(r, toolReq.Name)
			if tool == nil {
				resultChan <- toolResult{idx, nil, fmt.Errorf("tool %q not found", toolReq.Name)}
				return
			}

			output, err := tool.RunRaw(ctx, toolReq.Input)
			if err != nil {
				var interruptErr *ToolInterruptError
				if errors.As(err, &interruptErr) {
					logger.FromContext(ctx).Debug("tool %q triggered an interrupt: %v", toolReq.Name, interruptErr.Metadata)
					revisedMessage.Content[idx] = &Part{
						ToolRequest: toolReq,
						Metadata: map[string]any{
							"interrupt": interruptErr.Metadata,
						},
					}
					resultChan <- toolResult{idx, nil, interruptErr}
					return
				}
				resultChan <- toolResult{idx, nil, fmt.Errorf("tool %q failed: %w", toolReq.Name, err)}
				return
			}

			revisedMessage.Content[idx] = &Part{
				ToolRequest: toolReq,
				Metadata: map[string]any{
					"pendingOutput": output,
				},
			}

			resultChan <- toolResult{idx, output, nil}
		}(i, part)
	}

	var toolResponses []*Part
	hasInterrupts := false
	for i := 0; i < toolCount; i++ {
		result := <-resultChan
		if result.err != nil {
			var interruptErr *ToolInterruptError
			if errors.As(result.err, &interruptErr) {
				hasInterrupts = true
				continue
			}
			return nil, nil, result.err
		}

		toolReq := resp.Message.Content[result.index].ToolRequest
		toolResponses = append(toolResponses, NewToolResponsePart(&ToolResponse{
			Name:   toolReq.Name,
			Ref:    toolReq.Ref,
			Output: result.output,
		}))
	}

	if hasInterrupts {
		return nil, revisedMessage, nil
	}

	toolMessage.Content = toolResponses

	if cb != nil {
		err := cb(ctx, &ModelResponseChunk{
			Content: toolMessage.Content,
			Role:    RoleTool,
		})
		if err != nil {
			return nil, nil, fmt.Errorf("streaming callback failed: %w", err)
		}
	}

	newReq := req
	newReq.Messages = append(append([]*Message{}, req.Messages...), resp.Message, toolMessage)

	return newReq, nil, nil
}

// conformOutput appends a message to the request indicating conformance to the expected schema.
func conformOutput(req *ModelRequest) error {
	if req.Output != nil && req.Output.Format == string(OutputFormatJSON) && len(req.Messages) > 0 {
		jsonBytes, err := json.Marshal(req.Output.Schema)
		if err != nil {
			return fmt.Errorf("expected schema is not valid: %w", err)
		}

		escapedJSON := strconv.Quote(string(jsonBytes))
		part := NewTextPart(fmt.Sprintf("Output should be in JSON format and conform to the following schema:\n\n```%s```", escapedJSON))
		req.Messages[len(req.Messages)-1].Content = append(req.Messages[len(req.Messages)-1].Content, part)
	}
	return nil
}

// validResponse check the message matches the expected schema.
// It will strip JSON markdown delimiters from the response.
func validResponse(ctx context.Context, resp *ModelResponse) (*Message, error) {
	msg, err := validMessage(resp.Message, resp.Request.Output)
	if err != nil {
		logger.FromContext(ctx).Debug("message did not match expected schema", "error", err.Error())
		return nil, errors.New("generation did not result in a message matching expected schema")
	}
	return msg, nil
}

// validMessage will validate the message against the expected schema.
// It will return an error if it does not match, otherwise it will return a message with JSON content and type.
func validMessage(m *Message, output *ModelOutputConfig) (*Message, error) {
	if output != nil && output.Format == string(OutputFormatJSON) {
		if m == nil {
			return nil, errors.New("message is empty")
		}
		if len(m.Content) == 0 {
			return nil, errors.New("message has no content")
		}

		for i, part := range m.Content {
			if !part.IsText() {
				continue
			}

			text := base.ExtractJSONFromMarkdown(part.Text)

			var schemaBytes []byte
			schemaBytes, err := json.Marshal(output.Schema)
			if err != nil {
				return nil, fmt.Errorf("expected schema is not valid: %w", err)
			}
			if err = base.ValidateRaw([]byte(text), schemaBytes); err != nil {
				return nil, err
			}

			m.Content[i] = NewJSONPart(text)
		}
	}
	return m, nil
}

// Text returns the contents of the first candidate in a
// [ModelResponse] as a string. It returns an empty string if there
// are no candidates or if the candidate has no message.
func (gr *ModelResponse) Text() string {
	if gr.Message == nil {
		return ""
	}
	return gr.Message.Text()
}

// History returns messages from the request combined with the response message
// to represent the conversation history.
func (gr *ModelResponse) History() []*Message {
	if gr.Message == nil {
		return gr.Request.Messages
	}
	return append(gr.Request.Messages, gr.Message)
}

// Output unmarshals structured JSON output into the provided
// struct pointer.
func (gr *ModelResponse) Output(v any) error {
	j := base.ExtractJSONFromMarkdown(gr.Text())
	if j == "" {
		return errors.New("unable to parse JSON from response text")
	}
	return json.Unmarshal([]byte(j), v)
}

// Text returns the text content of the [ModelResponseChunk]
// as a string. It returns an error if there is no Content
// in the response chunk.
func (c *ModelResponseChunk) Text() string {
	if len(c.Content) == 0 {
		return ""
	}
	if len(c.Content) == 1 {
		return c.Content[0].Text
	}
	var sb strings.Builder
	for _, p := range c.Content {
		sb.WriteString(p.Text)
	}
	return sb.String()
}

// Text returns the contents of a [Message] as a string. It
// returns an empty string if the message has no content.
func (m *Message) Text() string {
	if m == nil {
		return ""
	}
	if len(m.Content) == 0 {
		return ""
	}
	if len(m.Content) == 1 {
		return m.Content[0].Text
	}
	var sb strings.Builder
	for _, p := range m.Content {
		sb.WriteString(p.Text)
	}
	return sb.String()
}
