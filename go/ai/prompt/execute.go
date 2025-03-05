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

package prompt

import (
	"context"
	"errors"
	"fmt"
	"reflect"
	"strings"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/core/tracing"
	"github.com/firebase/genkit/go/internal/base"
)

// PromptRequest is a request to execute a prompt and
// pass the result to a [Model]. Any settings set here override settings specified by the prompt.
type PromptRequest struct {
	ModelName               string                     `json:"modelname,omitempty"`          // The name of the model to use.
	Model                   ai.Model                   `json:"model,omitempty"`              // The model to use.
	System                  string                     `json:"system,omitempty"`             // The System prompt. If this is non-empty, SystemFn should be nil.
	SystemFn                PromptFn                   `json:"-"`                            // The System prompt function. If this is set, System should be an empty string.
	Prompt                  string                     `json:"prompt,omitempty"`             // The User prompt. If this is non-empty, PromptFn should be nil.
	PromptFn                PromptFn                   `json:"-"`                            // The User prompt function. If this is set, Prompt should be an empty string.
	Messages                []*ai.Message              `json:"messages,omitempty"`           // The messages to add to the prompt. If this is set, MessagesFn should be an empty.
	MessagesFn              MessagesFn                 `json:"-"`                            // The messages function. If this is set, Messages should be an empty.
	Config                  *ai.GenerationCommonConfig `json:"config,omitempty"`             // Model configuration. If nil will be taken from the prompt config.
	Input                   any                        `json:"input,omitempty"`              // Input fields for the prompt. If not nil this should be a struct or pointer to a struct that matches the prompt's input schema.
	Context                 []*ai.Document             `json:"context,omitempty"`            // Context to pass to model, if any.
	ToolChoice              ai.ToolChoice              `json:"toolChoice,omitempty"`         // Whether tool calls are required, disabled, or optional for the prompt.
	MaxTurns                int                        `json:"maxTurns,omitempty"`           // Maximum number of tool call iterations for the prompt.
	ReturnToolRequests      bool                       `json:"returnToolRequests,omitempty"` // Whether to return tool requests instead of making the tool calls and continuing the generation.
	IsReturnToolRequestsSet bool                       `json:"-"`                            // Whether the ReturnToolRequests field was set (false is not enough information as to whether to override).
	Middleware              []ai.ModelMiddleware       `json:"-"`                            // Middleware to apply to the prompt
	Stream                  ai.ModelStreamingCallback  // Streaming callback function
}

// GenerateOption configures params for Generate function.
type GenerateOption = func(p *PromptRequest) error

// Execute renders a prompt, does variable substitution and
// passes the rendered template to the AI model specified by
// the prompt.
func (p *Prompt) Execute(ctx context.Context, opts ...GenerateOption) (*ai.ModelResponse, error) {
	tracing.SetCustomMetadataAttr(ctx, "subtype", "prompt")

	if p == nil {
		return nil, errors.New("prompt.Execute: execute called on a nil Prompt; check that all prompts are defined")
	}

	var pr PromptRequest
	for _, with := range opts {
		err := with(&pr)
		if err != nil {
			return nil, err
		}
	}

	// Let some messages in pr override those in the prompt config, before rendering.
	if len(pr.Messages) > 0 {
		p.Config.Messages = pr.Messages
	}
	if pr.MessagesFn != nil {
		p.Config.MessagesFn = pr.MessagesFn
	}

	mr, err := p.Render(ctx, pr.Input)
	if err != nil {
		return nil, err
	}

	// Set the rest of the overrides.
	if pr.Config != nil {
		mr.Config = pr.Config
	}
	if len(pr.Context) > 0 {
		mr.Context = pr.Context
	}
	if pr.ToolChoice != "" {
		mr.ToolChoice = pr.ToolChoice
	}

	var model ai.Model
	if p.Model != nil {
		model = p.Model
	}
	if pr.Model != nil {
		model = pr.Model
	}

	if model == nil {
		modelName := p.ModelName
		if pr.ModelName != "" {
			modelName = pr.ModelName
		}

		model, err = ai.LookupModelByName(p.registry, modelName)
		if err != nil {
			return nil, err
		}
	}

	maxTurns := p.Config.MaxTurns
	if pr.MaxTurns != 0 {
		maxTurns = pr.MaxTurns
	}

	returnToolRequests := p.Config.ReturnToolRequests
	if pr.IsReturnToolRequestsSet {
		returnToolRequests = pr.ReturnToolRequests
	}

	toolCfg := &ai.ToolConfig{
		MaxTurns:           maxTurns,
		ReturnToolRequests: returnToolRequests,
	}

	return model.Generate(ctx, p.registry, mr, pr.Middleware, toolCfg, pr.Stream)
}

// buildVariables returns a map holding prompt field values based
// on a struct or a pointer to a struct. The struct value should have
// JSON tags that correspond to the Prompt's input schema.
// Only exported fields of the struct will be used.
func (p *Prompt) buildVariables(variables any) (map[string]any, error) {
	if variables == nil {
		return nil, nil
	}

	v := reflect.Indirect(reflect.ValueOf(variables))
	if v.Kind() == reflect.Map {
		return variables.(map[string]any), nil
	}
	if v.Kind() != reflect.Struct {
		return nil, errors.New("prompt.buildVariables: fields not a struct or pointer to a struct or a map")
	}
	vt := v.Type()

	// TODO: Verify the struct with p.Config.InputSchema.

	m := make(map[string]any)

fieldLoop:
	for i := 0; i < vt.NumField(); i++ {
		ft := vt.Field(i)
		if ft.PkgPath != "" {
			continue
		}

		jsonTag := ft.Tag.Get("json")
		jsonName, rest, _ := strings.Cut(jsonTag, ",")
		if jsonName == "" {
			jsonName = ft.Name
		}

		vf := v.Field(i)

		// If the field is the zero value, and omitempty is set,
		// don't pass it as a prompt input variable.
		if vf.IsZero() {
			for rest != "" {
				var key string
				key, rest, _ = strings.Cut(rest, ",")
				if key == "omitempty" {
					continue fieldLoop
				}
			}
		}

		m[jsonName] = vf.Interface()
	}

	return m, nil
}

// buildRequest prepares an [ai.ModelRequest] based on the prompt,
// using the input variables and other information in the [ai.PromptRequest].
func (p *Prompt) buildRequest(ctx context.Context, input any) (*ai.ModelRequest, error) {
	req := &ai.ModelRequest{}

	m, err := p.buildVariables(input)
	if err != nil {
		return nil, err
	}

	messages := []*ai.Message{}
	messages, err = RenderSystemPrompt(ctx, &p.Config, messages, m, input)
	if err != nil {
		return nil, err
	}

	messages, err = RenderMessages(ctx, &p.Config, messages, m, input)
	if err != nil {
		return nil, err
	}

	messages, err = RenderUserPrompt(ctx, &p.Config, messages, m, input)
	if err != nil {
		return nil, err
	}

	req.Messages = messages
	req.Config = p.GenerationConfig
	req.ToolChoice = p.ToolChoice

	var outputSchema map[string]any
	if p.OutputSchema != nil {
		outputSchema = base.SchemaAsMap(p.OutputSchema)
	}

	req.Output = &ai.ModelRequestOutput{
		Format: p.OutputFormat,
		Schema: outputSchema,
	}

	var tds []*ai.ToolDefinition
	for _, t := range p.Tools {
		tds = append(tds, t.Definition())
	}
	req.Tools = tds

	return req, nil
}

// WithInput adds input to pass to the model.
func WithInput(input any) GenerateOption {
	return func(p *PromptRequest) error {
		if p.Input != nil {
			return errors.New("prompt.WithInput: cannot set Input more than once")
		}
		p.Input = input
		return nil
	}
}

// WithMessages adds messages to the prompt.
func WithMessages(msgs []*ai.Message) GenerateOption {
	return func(p *PromptRequest) error {
		if p.MessagesFn != nil || len(p.Messages) > 0 {
			return errors.New("prompt.WithMessages: cannot set messages more than once")
		}
		p.Messages = msgs

		return nil
	}
}

// WithMessagesFn sets the result of the callback function as messages on the prompt.
func WithMessagesFn(msgFn MessagesFn) GenerateOption {
	return func(p *PromptRequest) error {
		if p.MessagesFn != nil || len(p.Messages) > 0 {
			return errors.New("prompt.WithMessages: cannot set messages more than once")
		}
		p.MessagesFn = msgFn

		return nil
	}
}

// WithConfig adds model configuration. If nil will be taken from the prompt config.
func WithConfig(config *ai.GenerationCommonConfig) GenerateOption {
	return func(p *PromptRequest) error {
		if p.Config != nil {
			return errors.New("prompt.WithConfig: cannot set Config more than once")
		}
		p.Config = config
		return nil
	}
}

// WithContext add context to pass to model, if any.
func WithContext(docs ...*ai.Document) GenerateOption {
	return func(p *PromptRequest) error {
		if p.Context != nil {
			return errors.New("prompt.WithContext: cannot set Context more than once")
		}
		p.Context = docs
		return nil
	}
}

// WithModel adds the Model to use. This overrides any model specified by the prompt.
func WithModel(model ai.Model) GenerateOption {
	return func(p *PromptRequest) error {
		if p.ModelName != "" || p.Model != nil {
			return errors.New("prompt.WithModel: Model must be specified exactly once, either ModelName or Model")
		}
		p.Model = model
		return nil
	}
}

// WithModelName adds the name of the Model to use. This overrides any model specified by the prompt.
func WithModelName(model string) GenerateOption {
	return func(p *PromptRequest) error {
		if p.ModelName != "" || p.Model != nil {
			return errors.New("prompt.WithModelName: Model must be specified exactly once, either ModelName or Model")
		}
		p.ModelName = model
		return nil
	}
}

// WithStreaming adds a streaming callback to the generate request.
func WithStreaming(cb ai.ModelStreamingCallback) GenerateOption {
	return func(p *PromptRequest) error {
		if p.Stream != nil {
			return errors.New("prompt.WithStreaming: cannot set Stream more than once")
		}
		p.Stream = cb
		return nil
	}
}

// WithMaxTurns sets the maximum number of tool call iterations for the prompt.
func WithMaxTurns(maxTurns int) GenerateOption {
	return func(p *PromptRequest) error {
		if maxTurns <= 0 {
			return fmt.Errorf("prompt.WithMaxTurns: maxTurns must be greater than 0, got %d", maxTurns)
		}
		if p.MaxTurns != 0 {
			return errors.New("prompt.WithMaxTurns: cannot set MaxTurns more than once")
		}
		p.MaxTurns = maxTurns
		return nil
	}
}

// WithReturnToolRequests configures whether to return tool requests instead of making the tool calls and continuing the generation.
func WithReturnToolRequests(returnToolRequests bool) GenerateOption {
	return func(p *PromptRequest) error {
		if p.IsReturnToolRequestsSet {
			return errors.New("prompt.WithReturnToolRequests: cannot set ReturnToolRequests more than once")
		}
		p.ReturnToolRequests = returnToolRequests
		p.IsReturnToolRequestsSet = true
		return nil
	}
}

// WithToolChoice configures whether tool calls are required, disabled, or optional for the prompt.
func WithToolChoice(toolChoice ai.ToolChoice) GenerateOption {
	return func(p *PromptRequest) error {
		if p.ToolChoice != "" {
			return errors.New("prompt.WithToolChoice: cannot set ToolChoice more than once")
		}
		p.ToolChoice = toolChoice
		return nil
	}
}

// WithMiddleware adds middleware to the generate request.
func WithMiddleware(middleware ...ai.ModelMiddleware) GenerateOption {
	return func(p *PromptRequest) error {
		if p.Middleware != nil {
			return errors.New("prompt.WithMiddleware: cannot set Middleware more than once")
		}
		p.Middleware = middleware
		return nil
	}
}
