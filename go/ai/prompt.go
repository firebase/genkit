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
	"maps"
	"reflect"
	"strings"

	"github.com/aymerick/raymond"
	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/core/tracing"
	"github.com/firebase/genkit/go/internal/atype"
	"github.com/firebase/genkit/go/internal/registry"
)

type Prompt struct {
	promptOptions
	registry     *registry.Registry
	action       core.ActionDef[any, *ModelRequest, struct{}]
	Name         string            // Name of the prompt.
	Description  string            // Prompt description.
	Template     *raymond.Template // Parsed prompt template.
	TemplateText string            // Original prompt template text.
}

// DefinePrompt creates and registers a new Prompt.
func DefinePrompt(r *registry.Registry, provider, name string, opts ...PromptOption) (*Prompt, error) {
	p := &Prompt{
		registry: r,
	}

	pOpts := &promptOptions{}
	for _, opt := range opts {
		err := opt.applyPrompt(pOpts)
		if err != nil {
			return nil, err
		}
	}
	p.promptOptions = *pOpts

	if p.ModelName != "" && p.Model != nil {
		return nil, errors.New("prompt.Define: config must specify exactly one of ModelName and Model")
	}

	var renderFn renderFn = p.buildRequest
	if p.RenderFn != nil {
		renderFn = p.RenderFn
	}

	// TODO: Undo clearing of the Version once Monaco Editor supports newer than JSON schema draft-07.
	if p.InputSchema != nil {
		p.InputSchema.Version = ""
	}

	// TODO: Set metadata from options.
	metadata := map[string]any{
		"prompt": map[string]any{
			"name":     p.Name,
			"input":    map[string]any{"schema": p.InputSchema},
			"output":   map[string]any{"format": p.OutputFormat},
			"template": p.TemplateText,
		},
	}

	p.action = *core.DefineActionWithInputSchema(r, provider, name, atype.Prompt, metadata, p.InputSchema, renderFn)
	return p, nil
}

// Render renders the prompt template based on user input.
func (p *Prompt) Render(ctx context.Context, input any) (*ModelRequest, error) {
	if p == nil {
		return nil, errors.New("prompt.Render: called on a nil Prompt; check that all prompts are defined")
	}
	return p.action.Run(ctx, input, nil)
}

// IsDefinedPrompt reports whether a [Prompt] is defined.
func IsDefinedPrompt(r *registry.Registry, provider, name string) bool {
	return LookupPrompt(r, provider, name) != nil
}

// LookupPrompt looks up a [Prompt] registered by [DefinePrompt].
// It returns nil if the prompt was not defined.
func LookupPrompt(r *registry.Registry, provider, name string) *Prompt {
	action := core.LookupActionFor[any, *ModelRequest, struct{}](r, atype.Prompt, provider, name)
	p := &Prompt{
		action: *action,
	}
	return p
}

// Execute renders a prompt, does variable substitution and
// passes the rendered template to the AI model specified by
// the prompt.
func (p *Prompt) Execute(ctx context.Context, opts ...PromptRequestOption) (*ModelResponse, error) {
	tracing.SetCustomMetadataAttr(ctx, "subtype", "prompt")

	if p == nil {
		return nil, errors.New("prompt.Execute: execute called on a nil Prompt; check that all prompts are defined")
	}

	reqOpts := &promptGenerateOptions{}
	for _, opt := range opts {
		err := opt.applyPromptRequest(reqOpts)
		if err != nil {
			return nil, err
		}
	}

	if reqOpts.MessagesFn != nil {
		p.MessagesFn = reqOpts.MessagesFn
	}

	mr, err := p.Render(ctx, reqOpts.Input)
	if err != nil {
		return nil, err
	}

	// Set the rest of the overrides.
	if reqOpts.Config != nil {
		mr.Config = reqOpts.Config
	}
	if len(reqOpts.Context) > 0 {
		mr.Context = reqOpts.Context
	}
	if reqOpts.ToolChoice != "" {
		mr.ToolChoice = reqOpts.ToolChoice
	}

	var model Model
	if p.Model != nil {
		model = p.Model
	}
	if reqOpts.Model != nil {
		model = reqOpts.Model
	}

	if model == nil {
		modelName := p.ModelName
		if reqOpts.ModelName != "" {
			modelName = reqOpts.ModelName
		}

		model, err = LookupModelByName(p.registry, modelName)
		if err != nil {
			return nil, err
		}
	}

	maxTurns := p.MaxTurns
	if reqOpts.MaxTurns != 0 {
		maxTurns = reqOpts.MaxTurns
	}

	returnToolRequests := p.ReturnToolRequests
	if reqOpts.IsReturnToolRequestsSet {
		returnToolRequests = reqOpts.ReturnToolRequests
	}

	toolCfg := &ToolConfig{
		MaxTurns:           maxTurns,
		ReturnToolRequests: returnToolRequests,
	}

	return model.Generate(ctx, p.registry, mr, reqOpts.Middleware, toolCfg, reqOpts.Stream)
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

// buildRequest prepares an [ModelRequest] based on the prompt,
// using the input variables and other information in the [PromptRequest].
func (p *Prompt) buildRequest(ctx context.Context, input any) (*ModelRequest, error) {
	m, err := p.buildVariables(input)
	if err != nil {
		return nil, err
	}

	messages := []*Message{}
	messages, err = renderSystemPrompt(ctx, p.promptOptions, messages, m, input)
	if err != nil {
		return nil, err
	}

	messages, err = renderMessages(ctx, p.promptOptions, messages, m, input)
	if err != nil {
		return nil, err
	}

	messages, err = renderUserPrompt(ctx, p.promptOptions, messages, m, input)
	if err != nil {
		return nil, err
	}

	var tds []*ToolDefinition
	for _, t := range p.Tools {
		tds = append(tds, t.Definition())
	}

	return &ModelRequest{
		Messages:   messages,
		Config:     p.Config,
		ToolChoice: p.ToolChoice,
		Tools:      tds,
		Output: &ModelRequestOutput{
			Format: p.OutputFormat,
			Schema: p.OutputSchema,
		},
	}, nil
}

// renderSystemPrompt renders a system prompt message.
func renderSystemPrompt(ctx context.Context, opts promptOptions, messages []*Message, input map[string]any, raw any) ([]*Message, error) {
	if opts.SystemFn == nil {
		return messages, nil
	}

	templateText, err := opts.SystemFn(ctx, raw)
	if err != nil {
		return nil, err
	}

	rendered, err := renderDotprompt(templateText, input, opts.DefaultInput)
	if err != nil {
		return nil, err
	}

	if rendered != "" {
		messages = append(messages, NewSystemTextMessage(rendered))
	}

	return messages, nil
}

// renderUserPrompt renders a user prompt message.
func renderUserPrompt(ctx context.Context, opts promptOptions, messages []*Message, input map[string]any, raw any) ([]*Message, error) {
	if opts.PromptFn == nil {
		return messages, nil
	}

	templateText, err := opts.PromptFn(ctx, raw)
	if err != nil {
		return nil, err
	}

	rendered, err := renderDotprompt(templateText, input, opts.DefaultInput)
	if err != nil {
		return nil, err
	}

	if rendered != "" {
		messages = append(messages, NewUserTextMessage(rendered))
	}

	return messages, nil
}

// renderMessages renders a slice of messages.
func renderMessages(ctx context.Context, opts promptOptions, messages []*Message, input map[string]any, raw any) ([]*Message, error) {
	if opts.MessagesFn == nil {
		return messages, nil
	}

	msgs, err := opts.MessagesFn(ctx, raw)
	if err != nil {
		return nil, err
	}

	for _, msg := range msgs {
		for _, part := range msg.Content {
			if part.IsText() {
				rendered, err := renderDotprompt(part.Text, input, opts.DefaultInput)
				if err != nil {
					return nil, err
				}
				msg.Content[0].Text = rendered
			}
		}
	}

	return append(messages, msgs...), nil
}

const rolePrefix = "<<<dotprompt:role:"
const roleSuffix = ">>>"
const mediaPrefix = "<<<dotprompt:media:url"
const mediaSuffix = ">>>"

// jsonHelper is an undocumented template execution helper.
func jsonHelper(v any, options *raymond.Options) raymond.SafeString {
	indent := 0
	if indentArg := options.HashProp("indent"); indentArg != nil {
		indent, _ = indentArg.(int)
	}
	var data []byte
	var err error
	if indent == 0 {
		data, err = json.Marshal(v)
	} else {
		data, err = json.MarshalIndent(v, "", strings.Repeat(" ", indent))
	}
	if err != nil {
		return raymond.SafeString(err.Error())
	}
	return raymond.SafeString(data)
}

// roleHelper changes roles.
func roleHelper(role string) raymond.SafeString {
	return raymond.SafeString(rolePrefix + role + roleSuffix)
}

// mediaHelper inserts media.
func mediaHelper(options *raymond.Options) raymond.SafeString {
	url := options.HashStr("url")
	contentType := options.HashStr("contentType")
	add := url
	if contentType != "" {
		add += " " + contentType
	}
	return raymond.SafeString(mediaPrefix + add + mediaSuffix)
}

// templateHelpers is the helpers supported by all dotprompt templates.
var templateHelpers = map[string]any{
	"json":  jsonHelper,
	"role":  roleHelper,
	"media": mediaHelper,
}

// RenderMessages executes the prompt's template and converts it into messages.
// This just runs the template; it does not call a model.
func renderDotprompt(templateText string, variables map[string]any, defaultInput map[string]any) (string, error) {
	template, err := raymond.Parse(templateText)
	if err != nil {
		return "", fmt.Errorf("prompt.renderDotprompt: failed to parse: %w", err)
	}
	template.RegisterHelpers(templateHelpers)

	if defaultInput != nil {
		nv := make(map[string]any)
		maps.Copy(nv, defaultInput)
		maps.Copy(nv, variables)
		variables = nv
	}
	str, err := template.Exec(variables)
	if err != nil {
		return "", err
	}
	return str, nil
}
