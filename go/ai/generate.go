// Copyright 2024 Google LLC
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

// Model represents a model that can perform content generation tasks.
type Model interface {
	// Name returns the registry name of the model.
	Name() string
	// Generate applies the [Model] to provided request, handling tool requests and handles streaming.
	Generate(ctx context.Context, r *registry.Registry, req *ModelRequest, mw []ModelMiddleware, toolCfg *ToolConfig, cb ModelStreamingCallback) (*ModelResponse, error)
}

// ModelFunc is a function that generates a model response.
type ModelFunc = core.StreamingFunc[*ModelRequest, *ModelResponse, *ModelResponseChunk]

// ModelMiddleware is middleware for model generate requests.
type ModelMiddleware = core.Middleware[*ModelRequest, *ModelResponse, *ModelResponseChunk]

// ModelAction is an action for model generation.
type ModelAction = core.ActionDef[*ModelRequest, *ModelResponse, *ModelResponseChunk]

type generateAction = core.ActionDef[*GenerateActionOptions, *ModelResponse, *ModelResponseChunk]

type modelActionDef core.ActionDef[*ModelRequest, *ModelResponse, *ModelResponseChunk]

// ModelStreamingCallback is the type for the streaming callback of a model.
type ModelStreamingCallback = func(context.Context, *ModelResponseChunk) error

// ToolConfig handles configuration around tool calls during generation.
type ToolConfig struct {
	MaxTurns           int
	ReturnToolRequests bool
}

// DefineGenerateAction defines a utility generate action.
func DefineGenerateAction(ctx context.Context, r *registry.Registry) *generateAction {
	return (*generateAction)(core.DefineStreamingAction(r, "", "generate", atype.Util, nil,
		func(ctx context.Context, req *GenerateActionOptions, cb ModelStreamingCallback) (output *ModelResponse, err error) {
			logger.FromContext(ctx).Debug("GenerateAction",
				"input", fmt.Sprintf("%#v", req))
			defer func() {
				logger.FromContext(ctx).Debug("GenerateAction",
					"output", fmt.Sprintf("%#v", output),
					"err", err)
			}()

			return tracing.RunInNewSpan(ctx, r.TracingState(), "generate", "util", false, req,
				func(ctx context.Context, input *GenerateActionOptions) (*ModelResponse, error) {
					model := LookupModel(r, "", req.Model)
					if model == nil {
						return nil, fmt.Errorf("model %q not found", req.Model)
					}

					toolDefs := make([]*ToolDefinition, len(req.Tools))
					for i, toolName := range req.Tools {
						toolDefs[i] = LookupTool(r, toolName).Definition()
					}

					modelReq := &ModelRequest{
						Messages:   req.Messages,
						Config:     req.Config,
						Tools:      toolDefs,
						ToolChoice: req.ToolChoice,
					}

					if req.Output != nil {
						modelReq.Output = &ModelRequestOutput{
							Format: req.Output.Format,
							Schema: req.Output.JsonSchema,
						}
					}

					if modelReq.Output != nil &&
						modelReq.Output.Schema != nil &&
						modelReq.Output.Format == "" {
						modelReq.Output.Format = OutputFormatJSON
					}

					maxTurns := 5
					if req.MaxTurns > 0 {
						maxTurns = req.MaxTurns
					}

					toolCfg := &ToolConfig{
						MaxTurns:           maxTurns,
						ReturnToolRequests: req.ReturnToolRequests,
					}

					return model.Generate(ctx, r, modelReq, nil, toolCfg, cb)
				})
		}))
}

// DefineModel registers the given generate function as an action, and returns a [Model] that runs it.
func DefineModel(
	r *registry.Registry,
	provider, name string,
	info *ModelInfo,
	generate ModelFunc,
) Model {
	metadataMap := map[string]any{}
	if info == nil {
		// Always make sure there's at least minimal metadata.
		info = &ModelInfo{
			Label:    name,
			Supports: &ModelInfoSupports{},
			Versions: []string{},
		}
	}
	if info.Label != "" {
		metadataMap["label"] = info.Label
	}
	supports := map[string]bool{
		"media":      info.Supports.Media,
		"multiturn":  info.Supports.Multiturn,
		"systemRole": info.Supports.SystemRole,
		"tools":      info.Supports.Tools,
		"toolChoice": info.Supports.ToolChoice,
	}
	metadataMap["supports"] = supports
	metadataMap["versions"] = info.Versions

	generate = core.ChainMiddleware(ValidateSupport(name, info.Supports))(generate)

	return (*modelActionDef)(core.DefineStreamingAction(r, provider, name, atype.Model, map[string]any{"model": metadataMap}, generate))
}

// IsDefinedModel reports whether a model is defined.
func IsDefinedModel(r *registry.Registry, provider, name string) bool {
	return core.LookupActionFor[*ModelRequest, *ModelResponse, *ModelResponseChunk](r, atype.Model, provider, name) != nil
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

// generateParams represents various params of the Generate call.
type generateParams struct {
	Request            *ModelRequest
	Model              Model
	Stream             ModelStreamingCallback
	History            []*Message
	SystemPrompt       *Message
	MaxTurns           int
	ReturnToolRequests bool
	Middleware         []ModelMiddleware
}

// GenerateOption configures params of the Generate call.
type GenerateOption func(req *generateParams) error

// WithModel sets the model to use for the generate request.
func WithModel(m Model) GenerateOption {
	return func(req *generateParams) error {
		req.Model = m
		return nil
	}
}

// WithTextPrompt adds a simple text user prompt to ModelRequest.
func WithTextPrompt(prompt string) GenerateOption {
	return func(req *generateParams) error {
		req.Request.Messages = append(req.Request.Messages, NewUserTextMessage(prompt))
		return nil
	}
}

// WithSystemPrompt adds a simple text system prompt as the first message in ModelRequest.
// System prompt will always be put first in the list of messages.
func WithSystemPrompt(prompt string) GenerateOption {
	return func(req *generateParams) error {
		if req.SystemPrompt != nil {
			return errors.New("generate.WithSystemPrompt: cannot set system prompt more than once")
		}
		req.SystemPrompt = NewSystemTextMessage(prompt)
		return nil
	}
}

// WithMessages adds provided messages to ModelRequest.
func WithMessages(messages ...*Message) GenerateOption {
	return func(req *generateParams) error {
		req.Request.Messages = append(req.Request.Messages, messages...)
		return nil
	}
}

// WithHistory adds provided history messages to the beginning of
// ModelRequest.Messages.  History messages will always be put first in the list
// of messages, with the exception of system prompt which will always be first.
// [WithMessages] and [WithTextPrompt] will insert messages after system prompt
// and history.
func WithHistory(history ...*Message) GenerateOption {
	return func(req *generateParams) error {
		if req.History != nil {
			return errors.New("generate.WithHistory: cannot set history more than once")
		}
		req.History = history
		return nil
	}
}

// WithConfig adds provided config to ModelRequest.
func WithConfig(config any) GenerateOption {
	return func(req *generateParams) error {
		if req.Request.Config != nil {
			return errors.New("generate.WithConfig: cannot set config more than once")
		}
		req.Request.Config = config
		return nil
	}
}

// WithContext adds provided documents to ModelRequest.
func WithContext(docs ...*Document) GenerateOption {
	return func(req *generateParams) error {
		if req.Request.Context != nil {
			return errors.New("generate.WithContext: cannot set context more than once")
		}
		req.Request.Context = docs
		return nil
	}
}

// WithTools adds provided tools to ModelRequest.
func WithTools(tools ...Tool) GenerateOption {
	return func(req *generateParams) error {
		if req.Request.Tools != nil {
			return errors.New("generate.WithTools: cannot set tools more than once")
		}
		var toolDefs []*ToolDefinition
		for _, t := range tools {
			toolDefs = append(toolDefs, t.Definition())
		}
		req.Request.Tools = toolDefs
		return nil
	}
}

// WithOutputSchema adds provided output schema to ModelRequest.
func WithOutputSchema(schema any) GenerateOption {
	return func(req *generateParams) error {
		if req.Request.Output != nil && req.Request.Output.Schema != nil {
			return errors.New("generate.WithOutputSchema: cannot set output schema more than once")
		}
		if req.Request.Output == nil {
			req.Request.Output = &ModelRequestOutput{}
			req.Request.Output.Format = OutputFormatJSON
		}
		req.Request.Output.Schema = base.SchemaAsMap(base.InferJSONSchemaNonReferencing(schema))
		return nil
	}
}

// WithOutputFormat adds provided output format to ModelRequest.
func WithOutputFormat(format OutputFormat) GenerateOption {
	return func(req *generateParams) error {
		if req.Request.Output == nil {
			req.Request.Output = &ModelRequestOutput{}
		}
		req.Request.Output.Format = format
		return nil
	}
}

// WithStreaming adds a streaming callback to the generate request.
func WithStreaming(cb ModelStreamingCallback) GenerateOption {
	return func(req *generateParams) error {
		if req.Stream != nil {
			return errors.New("generate.WithStreaming: cannot set streaming callback more than once")
		}
		req.Stream = cb
		return nil
	}
}

// WithMaxTurns sets the maximum number of tool call iterations for the generate request.
func WithMaxTurns(maxTurns int) GenerateOption {
	return func(req *generateParams) error {
		if maxTurns <= 0 {
			return fmt.Errorf("maxTurns must be greater than 0, got %d", maxTurns)
		}
		if req.MaxTurns != 0 {
			return errors.New("generate.WithMaxTurns: cannot set MaxTurns more than once")
		}
		req.MaxTurns = maxTurns
		return nil
	}
}

// WithReturnToolRequests configures whether to return tool requests instead of making the tool calls and continuing the generation.
func WithReturnToolRequests(returnToolRequests bool) GenerateOption {
	return func(req *generateParams) error {
		if req.ReturnToolRequests {
			return errors.New("generate.WithReturnToolRequests: cannot set ReturnToolRequests more than once")
		}
		req.ReturnToolRequests = returnToolRequests
		return nil
	}
}

// WithToolChoice configures whether tool calls are required, disabled, or optional for the generate request.
func WithToolChoice(toolChoice ToolChoice) GenerateOption {
	return func(req *generateParams) error {
		if req.Request.ToolChoice != "" {
			return errors.New("generate.WithToolChoice: cannot set ToolChoice more than once")
		}
		req.Request.ToolChoice = toolChoice
		return nil
	}
}

// WithMiddleware adds middleware to the generate request.
func WithMiddleware(middleware ...ModelMiddleware) GenerateOption {
	return func(req *generateParams) error {
		if req.Middleware != nil {
			return errors.New("generate.WithMiddleware: cannot set Middleware more than once")
		}
		req.Middleware = middleware
		return nil
	}
}

// Generate run generate request for this model. Returns ModelResponse struct.
func Generate(ctx context.Context, r *registry.Registry, opts ...GenerateOption) (*ModelResponse, error) {
	req := &generateParams{
		Request: &ModelRequest{},
	}

	for _, with := range opts {
		err := with(req)
		if err != nil {
			return nil, err
		}
	}

	if req.Model == nil {
		return nil, errors.New("model is required")
	}

	var modelVersion string
	if config, ok := req.Request.Config.(*GenerationCommonConfig); ok {
		modelVersion = config.Version
	}

	if modelVersion != "" {
		ok, err := validateModelVersion(r, modelVersion, req)
		if !ok {
			return nil, err
		}
	}

	if req.History != nil {
		prev := req.Request.Messages
		req.Request.Messages = req.History
		req.Request.Messages = append(req.Request.Messages, prev...)
	}
	if req.SystemPrompt != nil {
		prev := req.Request.Messages
		req.Request.Messages = []*Message{req.SystemPrompt}
		req.Request.Messages = append(req.Request.Messages, prev...)
	}
	if req.MaxTurns == 0 {
		req.MaxTurns = 1
	}

	toolCfg := &ToolConfig{
		MaxTurns:           req.MaxTurns,
		ReturnToolRequests: req.ReturnToolRequests,
	}

	return req.Model.Generate(ctx, r, req.Request, req.Middleware, toolCfg, req.Stream)
}

// validateModelVersion checks in the registry the action of the
// given model version and determines whether its supported or not.
func validateModelVersion(r *registry.Registry, v string, req *generateParams) (bool, error) {
	parts := strings.Split(req.Model.Name(), "/")
	if len(parts) != 2 {
		return false, errors.New("wrong model name")
	}

	m := LookupModel(r, parts[0], parts[1])
	if m == nil {
		return false, fmt.Errorf("model %s not found", v)
	}

	// at the end, a Model is an action so type conversion is required
	if a, ok := m.(*modelActionDef); ok {
		if !(modelVersionSupported(v, (*ModelAction)(a).Desc().Metadata)) {
			return false, fmt.Errorf("version %s not supported", v)
		}
	} else {
		return false, errors.New("unable to validate model version")
	}

	return true, nil
}

// modelVersionSupported iterates over model's metadata to find the requested
// supported model version
func modelVersionSupported(modelVersion string, modelMetadata map[string]any) bool {
	if md, ok := modelMetadata["model"].(map[string]any); ok {
		for _, v := range md["versions"].([]string) {
			if modelVersion == v {
				return true
			}
		}
	}
	return false
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
	opts = append(opts, WithOutputSchema(value))
	resp, err := Generate(ctx, r, opts...)
	if err != nil {
		return nil, err
	}
	err = resp.UnmarshalOutput(value)
	if err != nil {
		return nil, err
	}
	return resp, nil
}

// Generate applies the [Action] to provided request, handling tool requests and handles streaming.
func (m *modelActionDef) Generate(ctx context.Context, r *registry.Registry, req *ModelRequest, mw []ModelMiddleware, toolCfg *ToolConfig, cb ModelStreamingCallback) (*ModelResponse, error) {
	if m == nil {
		return nil, errors.New("Generate called on a nil Model; check that all models are defined")
	}

	if toolCfg == nil {
		toolCfg = &ToolConfig{
			MaxTurns:           1,
			ReturnToolRequests: false,
		}
	}

	if req.Tools != nil {
		toolNames := make(map[string]bool)
		for _, tool := range req.Tools {
			if toolNames[tool.Name] {
				return nil, fmt.Errorf("duplicate tool name found: %q", tool.Name)
			}
			toolNames[tool.Name] = true
		}
	}

	if err := conformOutput(req); err != nil {
		return nil, err
	}

	handler := core.ChainMiddleware(mw...)((*ModelAction)(m).Run)

	currentTurn := 0
	for {
		resp, err := handler(ctx, req, cb)
		if err != nil {
			return nil, err
		}

		msg, err := validResponse(ctx, resp)
		if err != nil {
			return nil, err
		}
		resp.Message = msg

		toolCount := 0
		for _, part := range resp.Message.Content {
			if part.IsToolRequest() {
				toolCount++
			}
		}
		if toolCount == 0 || toolCfg.ReturnToolRequests {
			return resp, nil
		}

		if currentTurn+1 > toolCfg.MaxTurns {
			return nil, fmt.Errorf("exceeded maximum tool call iterations (%d)", toolCfg.MaxTurns)
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

func (i *modelActionDef) Name() string { return (*ModelAction)(i).Name() }

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
func handleToolRequests(ctx context.Context, r *registry.Registry, req *ModelRequest, resp *ModelResponse, cb ModelStreamingCallback) (*ModelRequest, *Message, error) {
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
	if req.Output != nil && req.Output.Format == OutputFormatJSON && len(req.Messages) > 0 {
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
func validMessage(m *Message, output *ModelRequestOutput) (*Message, error) {
	if output != nil && output.Format == OutputFormatJSON {
		if m == nil {
			return nil, errors.New("message is empty")
		}
		if len(m.Content) == 0 {
			return nil, errors.New("message has no content")
		}

		text := base.ExtractJSONFromMarkdown(m.Text())
		var schemaBytes []byte
		schemaBytes, err := json.Marshal(output.Schema)
		if err != nil {
			return nil, fmt.Errorf("expected schema is not valid: %w", err)
		}
		if err = base.ValidateRaw([]byte(text), schemaBytes); err != nil {
			return nil, err
		}
		// TODO: Verify that it okay to replace all content with JSON.
		m.Content = []*Part{NewJSONPart(text)}
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

// UnmarshalOutput unmarshals structured JSON output into the provided
// struct pointer.
func (gr *ModelResponse) UnmarshalOutput(v any) error {
	j := base.ExtractJSONFromMarkdown(gr.Text())
	if j == "" {
		return errors.New("unable to parse JSON from response text")
	}
	json.Unmarshal([]byte(j), v)
	return nil
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
