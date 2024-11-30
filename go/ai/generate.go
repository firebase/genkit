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

package ai

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"slices"
	"strconv"
	"strings"

	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/core/logger"
	"github.com/firebase/genkit/go/internal/atype"
	"github.com/firebase/genkit/go/internal/base"
)

// Model represents a model that can perform content generation tasks.
type Model interface {
	// Name returns the registry name of the model.
	Name() string
	// Generate applies the [Model] to provided request, handling tool requests and handles streaming.
	Generate(ctx context.Context, req *ModelRequest, cb ModelStreamingCallback) (*ModelResponse, error)
}

type modelActionDef core.Action[*ModelRequest, *ModelResponse, *ModelResponseChunk]

type modelAction = core.Action[*ModelRequest, *ModelResponse, *ModelResponseChunk]

// ModelStreamingCallback is the type for the streaming callback of a model.
type ModelStreamingCallback = func(context.Context, *ModelResponseChunk) error

// ModelCapabilities describes various capabilities of the model.
type ModelCapabilities struct {
	Multiturn  bool // the model can handle multiple request-response interactions
	Media      bool // the model supports media as well as text input
	Tools      bool // the model supports tools
	SystemRole bool // the model supports a system prompt or role
}

// ModelMetadata is the metadata of the model, specifying things like nice user-visible label, capabilities, etc.
type ModelMetadata struct {
	Label    string
	Supports ModelCapabilities
}

// DefineModel registers the given generate function as an action, and returns a
// [Model] that runs it.
func DefineModel(provider, name string, metadata *ModelMetadata, generate func(context.Context, *ModelRequest, ModelStreamingCallback) (*ModelResponse, error)) Model {
	metadataMap := map[string]any{}
	if metadata == nil {
		// Always make sure there's at least minimal metadata.
		metadata = &ModelMetadata{
			Label: name,
		}
	}
	if metadata.Label != "" {
		metadataMap["label"] = metadata.Label
	}
	supports := map[string]bool{
		"media":      metadata.Supports.Media,
		"multiturn":  metadata.Supports.Multiturn,
		"systemRole": metadata.Supports.SystemRole,
		"tools":      metadata.Supports.Tools,
	}
	metadataMap["supports"] = supports

	return (*modelActionDef)(core.DefineStreamingAction(provider, name, atype.Model, map[string]any{
		"model": metadataMap,
	}, generate))
}

// IsDefinedModel reports whether a model is defined.
func IsDefinedModel(provider, name string) bool {
	return core.LookupActionFor[*ModelRequest, *ModelResponse, *ModelResponseChunk](atype.Model, provider, name) != nil
}

// LookupModel looks up a [Model] registered by [DefineModel].
// It returns nil if the model was not defined.
func LookupModel(provider, name string) Model {
	action := core.LookupActionFor[*ModelRequest, *ModelResponse, *ModelResponseChunk](atype.Model, provider, name)
	if action == nil {
		return nil
	}
	return (*modelActionDef)(action)
}

// generateParams represents various params of the Generate call.
type generateParams struct {
	Request      *ModelRequest
	Stream       ModelStreamingCallback
	History      []*Message
	SystemPrompt *Message
}

// GenerateOption configures params of the Generate call.
type GenerateOption func(req *generateParams) error

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
			return errors.New("cannot set system prompt (WithSystemPrompt) more than once")
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

// WithHistory adds provided history messages to the begining of ModelRequest.Messages.
// History messages will always be put first in the list of messages, with the
// exception of system prompt which will always be first.
// [WithMessages] and [WithTextPrompt] will insert messages after system prompt and history.
func WithHistory(history ...*Message) GenerateOption {
	return func(req *generateParams) error {
		if req.History != nil {
			return errors.New("cannot set history (WithHistory) more than once")
		}
		req.History = history
		return nil
	}
}

// WithConfig adds provided config to ModelRequest.
func WithConfig(config any) GenerateOption {
	return func(req *generateParams) error {
		if req.Request.Config != nil {
			return errors.New("cannot set Request.Config (WithConfig) more than once")
		}
		req.Request.Config = config
		return nil
	}
}

// WithContext adds provided context to ModelRequest.
func WithContext(c ...any) GenerateOption {
	return func(req *generateParams) error {
		req.Request.Context = append(req.Request.Context, c...)
		return nil
	}
}

// WithTools adds provided tools to ModelRequest.
func WithTools(tools ...Tool) GenerateOption {
	return func(req *generateParams) error {
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
			return errors.New("cannot set Request.Output.Schema (WithOutputSchema) more than once")
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
			return errors.New("cannot set streaming callback (WithStreaming) more than once")
		}
		req.Stream = cb
		return nil
	}
}

// Generate run generate request for this model. Returns ModelResponse struct.
func Generate(ctx context.Context, m Model, opts ...GenerateOption) (*ModelResponse, error) {
	req := &generateParams{
		Request: &ModelRequest{},
	}
	for _, with := range opts {
		err := with(req)
		if err != nil {
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

	return m.Generate(ctx, req.Request, req.Stream)
}

// GenerateText run generate request for this model. Returns generated text only.
func GenerateText(ctx context.Context, m Model, opts ...GenerateOption) (string, error) {
	res, err := Generate(ctx, m, opts...)
	if err != nil {
		return "", err
	}

	return res.Text(), nil
}

// Generate run generate request for this model. Returns ModelResponse struct.
// TODO: Stream GenerateData with partial JSON
func GenerateData(ctx context.Context, m Model, value any, opts ...GenerateOption) (*ModelResponse, error) {
	opts = append(opts, WithOutputSchema(value))
	resp, err := Generate(ctx, m, opts...)
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
func (m *modelActionDef) Generate(ctx context.Context, req *ModelRequest, cb ModelStreamingCallback) (*ModelResponse, error) {
	if m == nil {
		return nil, errors.New("Generate called on a nil Model; check that all models are defined")
	}
	if err := conformOutput(req); err != nil {
		return nil, err
	}

	a := (*core.Action[*ModelRequest, *ModelResponse, *ModelResponseChunk])(m)
	for {
		resp, err := a.Run(ctx, req, cb)
		if err != nil {
			return nil, err
		}

		msg, err := validResponse(ctx, resp)
		if err != nil {
			return nil, err
		}
		resp.Message = msg

		newReq, err := handleToolRequest(ctx, req, resp)
		if err != nil {
			return nil, err
		}
		if newReq == nil {
			return resp, nil
		}

		req = newReq
	}
}

func (i *modelActionDef) Name() string { return (*modelAction)(i).Name() }

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
	if err == nil {
		return msg, nil
	} else {
		logger.FromContext(ctx).Debug("message did not match expected schema", "error", err.Error())
		return nil, errors.New("generation did not result in a message matching expected schema")
	}
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

// handleToolRequest checks if a tool was requested by a model.
// If a tool was requested, this runs the tool and returns an
// updated ModelRequest. If no tool was requested this returns nil.
func handleToolRequest(ctx context.Context, req *ModelRequest, resp *ModelResponse) (*ModelRequest, error) {
	msg := resp.Message
	if msg == nil || len(msg.Content) == 0 {
		return nil, nil
	}
	part := msg.Content[0]
	if !part.IsToolRequest() {
		return nil, nil
	}

	toolReq := part.ToolRequest
	tool := LookupTool(toolReq.Name)
	if tool == nil {
		return nil, fmt.Errorf("tool %v not found", toolReq.Name)
	}
	to, err := tool.RunRaw(ctx, toolReq.Input)
	if err != nil {
		return nil, err
	}

	toolResp := &Message{
		Content: []*Part{
			NewToolResponsePart(&ToolResponse{
				Name: toolReq.Name,
				Output: map[string]any{
					"response": to,
				},
			}),
		},
		Role: RoleTool,
	}

	// Copy the ModelRequest rather than modifying it.
	rreq := *req
	rreq.Messages = append(slices.Clip(rreq.Messages), msg, toolResp)

	return &rreq, nil
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

// History returns messages from the request combined with the reponse message
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
