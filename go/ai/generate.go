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
	Generate(ctx context.Context, req *GenerateRequest, cb ModelStreamingCallback) (*GenerateResponse, error)
}

type modelActionDef core.Action[*GenerateRequest, *GenerateResponse, *GenerateResponseChunk]

type modelAction = core.Action[*GenerateRequest, *GenerateResponse, *GenerateResponseChunk]

// ModelStreamingCallback is the type for the streaming callback of a model.
type ModelStreamingCallback = func(context.Context, *GenerateResponseChunk) error

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
func DefineModel(provider, name string, metadata *ModelMetadata, generate func(context.Context, *GenerateRequest, ModelStreamingCallback) (*GenerateResponse, error)) Model {
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
	return core.LookupActionFor[*GenerateRequest, *GenerateResponse, *GenerateResponseChunk](atype.Model, provider, name) != nil
}

// LookupModel looks up a [Model] registered by [DefineModel].
// It returns nil if the model was not defined.
func LookupModel(provider, name string) Model {
	return (*modelActionDef)(core.LookupActionFor[*GenerateRequest, *GenerateResponse, *GenerateResponseChunk](atype.Model, provider, name))
}

// generateParams represents various params of the Generate call.
type generateParams struct {
	Request      *GenerateRequest
	Stream       ModelStreamingCallback
	History      []*Message
	SystemPrompt *Message
}

// GenerateOption configures params of the Generate call.
type GenerateOption func(req *generateParams) error

// WithTextPrompt adds a simple text user prompt to GenerateRequest.
func WithTextPrompt(prompt string) GenerateOption {
	return func(req *generateParams) error {
		req.Request.Messages = append(req.Request.Messages, NewUserTextMessage(prompt))
		return nil
	}
}

// WithSystemPrompt adds a simple text system prompt as the first message in GenerateRequest.
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

// WithMessages adds provided messages to GenerateRequest.
func WithMessages(messages ...*Message) GenerateOption {
	return func(req *generateParams) error {
		req.Request.Messages = append(req.Request.Messages, messages...)
		return nil
	}
}

// WithHistory adds provided history messages to the begining of GenerateRequest.Messages.
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

// WithConfig adds provided config to GenerateRequest.
func WithConfig(config any) GenerateOption {
	return func(req *generateParams) error {
		if req.Request.Config != nil {
			return errors.New("cannot set Request.Config (WithConfig) more than once")
		}
		req.Request.Config = config
		return nil
	}
}

// WithCandidates adds provided candidate count to GenerateRequest.
func WithCandidates(c int) GenerateOption {
	return func(req *generateParams) error {
		req.Request.Candidates = c
		return nil
	}
}

// WithContext adds provided context to GenerateRequest.
func WithContext(c ...any) GenerateOption {
	return func(req *generateParams) error {
		req.Request.Context = append(req.Request.Context, c...)
		return nil
	}
}

// WithTools adds provided tools to GenerateRequest.
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

// WithOutputSchema adds provided output schema to GenerateRequest.
func WithOutputSchema(schema any) GenerateOption {
	return func(req *generateParams) error {
		if req.Request.Output != nil && req.Request.Output.Schema != nil {
			return errors.New("cannot set Request.Output.Schema (WithOutputSchema) more than once")
		}
		if req.Request.Output == nil {
			req.Request.Output = &GenerateRequestOutput{}
			req.Request.Output.Format = OutputFormatJSON
		}
		req.Request.Output.Schema = base.SchemaAsMap(base.InferJSONSchemaNonReferencing(schema))
		return nil
	}
}

// WithOutputFormat adds provided output format to GenerateRequest.
func WithOutputFormat(format OutputFormat) GenerateOption {
	return func(req *generateParams) error {
		if req.Request.Output == nil {
			req.Request.Output = &GenerateRequestOutput{}
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

// Generate run generate request for this model. Returns GenerateResponse struct.
func Generate(ctx context.Context, m Model, opts ...GenerateOption) (*GenerateResponse, error) {
	req := &generateParams{
		Request: &GenerateRequest{},
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

// Generate run generate request for this model. Returns GenerateResponse struct.
// TODO: Stream GenerateData with partial JSON
func GenerateData(ctx context.Context, m Model, value any, opts ...GenerateOption) (*GenerateResponse, error) {
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
func (m *modelActionDef) Generate(ctx context.Context, req *GenerateRequest, cb ModelStreamingCallback) (*GenerateResponse, error) {
	if m == nil {
		return nil, errors.New("Generate called on a nil Model; check that all models are defined")
	}
	if err := conformOutput(req); err != nil {
		return nil, err
	}

	a := (*core.Action[*GenerateRequest, *GenerateResponse, *GenerateResponseChunk])(m)
	for {
		resp, err := a.Run(ctx, req, cb)
		if err != nil {
			return nil, err
		}

		candidates, err := validCandidates(ctx, resp)
		if err != nil {
			return nil, err
		}
		resp.Candidates = candidates

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
func conformOutput(req *GenerateRequest) error {
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

// validCandidates finds all candidates that match the expected schema.
// It will strip JSON markdown delimiters from the response.
func validCandidates(ctx context.Context, resp *GenerateResponse) ([]*Candidate, error) {
	var candidates []*Candidate
	for i, c := range resp.Candidates {
		c, err := validCandidate(c, resp.Request.Output)
		if err == nil {
			candidates = append(candidates, c)
		} else {
			logger.FromContext(ctx).Debug("candidate did not match expected schema", "index", i, "error", err.Error())
		}
	}
	if len(candidates) == 0 {
		return nil, errors.New("generation resulted in no candidates matching expected schema")
	}
	return candidates, nil
}

// validCandidate will validate the candidate's response against the expected schema.
// It will return an error if it does not match, otherwise it will return a candidate with JSON content and type.
func validCandidate(c *Candidate, output *GenerateRequestOutput) (*Candidate, error) {
	if output != nil && output.Format == OutputFormatJSON {
		if c.Message == nil {
			return nil, errors.New("candidate has no message")
		}
		if len(c.Message.Content) == 0 {
			return nil, errors.New("candidate message has no content")
		}

		text := base.ExtractJsonFromMarkdown(c.Text())
		var schemaBytes []byte
		schemaBytes, err := json.Marshal(output.Schema)
		if err != nil {
			return nil, fmt.Errorf("expected schema is not valid: %w", err)
		}
		if err = base.ValidateRaw([]byte(text), schemaBytes); err != nil {
			return nil, err
		}
		// TODO: Verify that it okay to replace all content with JSON.
		c.Message.Content = []*Part{NewJSONPart(text)}
	}
	return c, nil
}

// handleToolRequest checks if a tool was requested by a model.
// If a tool was requested, this runs the tool and returns an
// updated GenerateRequest. If no tool was requested this returns nil.
func handleToolRequest(ctx context.Context, req *GenerateRequest, resp *GenerateResponse) (*GenerateRequest, error) {
	if len(resp.Candidates) == 0 {
		return nil, nil
	}
	msg := resp.Candidates[0].Message
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

	// Copy the GenerateRequest rather than modifying it.
	rreq := *req
	rreq.Messages = append(slices.Clip(rreq.Messages), msg, toolResp)

	return &rreq, nil
}

// Text returns the contents of the first candidate in a
// [GenerateResponse] as a string. It returns an empty string if there
// are no candidates or if the candidate has no message.
func (gr *GenerateResponse) Text() string {
	if len(gr.Candidates) == 0 {
		return ""
	}
	return gr.Candidates[0].Text()
}

// History returns messages from the request combined with the reponse message
// to represent the conversation history.
func (gr *GenerateResponse) History() []*Message {
	if len(gr.Candidates) == 0 {
		return gr.Request.Messages
	}
	return append(gr.Request.Messages, gr.Candidates[0].Message)
}

// UnmarshalOutput unmarshals structured JSON output into the provided
// struct pointer.
func (gr *GenerateResponse) UnmarshalOutput(v any) error {
	j := base.ExtractJsonFromMarkdown(gr.Text())
	if j == "" {
		return errors.New("unable to parse JSON from response text")
	}
	json.Unmarshal([]byte(j), v)
	return nil
}

// Text returns the text content of the [GenerateResponseChunk]
// as a string. It returns an error if there is no Content
// in the response chunk.
func (c *GenerateResponseChunk) Text() string {
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

// Text returns the contents of a [Candidate] as a string. It
// returns an empty string if the candidate has no message.
func (c *Candidate) Text() string {
	msg := c.Message
	if msg == nil {
		return ""
	}
	if len(msg.Content) == 0 {
		return ""
	}
	if len(msg.Content) == 1 {
		return msg.Content[0].Text
	}
	var sb strings.Builder
	for _, p := range msg.Content {
		sb.WriteString(p.Text)
	}
	return sb.String()
}
