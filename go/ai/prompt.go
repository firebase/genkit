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
	"github.com/firebase/genkit/go/core/logger"
	"github.com/firebase/genkit/go/internal/atype"
	"github.com/firebase/genkit/go/internal/registry"
)

// Prompt is a prompt template that can be executed to generate a model response.
type Prompt struct {
	promptOptions
	registry *registry.Registry
	action   core.ActionDef[any, *GenerateActionOptions, struct{}]
}

// DefinePrompt creates and registers a new Prompt.
func DefinePrompt(r *registry.Registry, name string, opts ...PromptOption) (*Prompt, error) {
	pOpts := &promptOptions{}
	for _, opt := range opts {
		err := opt.applyPrompt(pOpts)
		if err != nil {
			return nil, err
		}
	}

	p := &Prompt{
		registry:      r,
		promptOptions: *pOpts,
	}

	modelName := p.ModelName
	if modelName == "" && p.Model != nil {
		modelName = p.Model.Name()
	}

	meta := p.Metadata
	if meta == nil {
		meta = map[string]any{}
	}
	promptMeta := map[string]any{
		"prompt": map[string]any{
			"name":   name,
			"model":  modelName,
			"config": p.Config,
			"input":  map[string]any{"schema": p.InputSchema},
		},
	}
	maps.Copy(meta, promptMeta)

	p.action = *core.DefineActionWithInputSchema(r, provider, name, atype.Prompt, meta, p.InputSchema, p.buildRequest)
	return p, nil
}

// IsDefinedPrompt reports whether a [Prompt] is defined.
func IsDefinedPrompt(r *registry.Registry, provider, name string) bool {
	return LookupPrompt(r, provider, name) != nil
}

// LookupPrompt looks up a [Prompt] registered by [DefinePrompt].
// It returns nil if the prompt was not defined.
func LookupPrompt(r *registry.Registry, provider, name string) *Prompt {
	action := core.LookupActionFor[any, *GenerateActionOptions, struct{}](r, atype.Prompt, provider, name)
	if action == nil {
		return nil
	}
	return &Prompt{
		registry: r,
		action:   *action,
	}
}

// Name returns the name of the prompt.
func (p *Prompt) Name() string { return p.action.Name() }

// Execute renders a prompt, does variable substitution and
// passes the rendered template to the AI model specified by the prompt.
func (p *Prompt) Execute(ctx context.Context, opts ...PromptGenerateOption) (*ModelResponse, error) {
	if p == nil {
		return nil, errors.New("Prompt.Execute: execute called on a nil Prompt; check that all prompts are defined")
	}

	genOpts := &promptGenerateOptions{}
	for _, opt := range opts {
		err := opt.applyPromptGenerate(genOpts)
		if err != nil {
			return nil, err
		}
	}

	p.MessagesFn = mergeMessagesFn(p.MessagesFn, genOpts.MessagesFn)

	actionOpts, err := p.Render(ctx, genOpts.Input)
	if err != nil {
		return nil, err
	}

	if genOpts.Config != nil {
		actionOpts.Config = genOpts.Config
	}
	if len(genOpts.Documents) > 0 {
		actionOpts.Docs = genOpts.Documents
	}
	if genOpts.ToolChoice != "" {
		actionOpts.ToolChoice = genOpts.ToolChoice
	}

	modelName := genOpts.ModelName
	if modelName == "" && genOpts.Model != nil {
		modelName = genOpts.Model.Name()
	}
	if modelName == "" {
		modelName = p.ModelName
	}
	if modelName == "" && p.Model != nil {
		modelName = p.Model.Name()
	}
	actionOpts.Model = modelName

	if genOpts.MaxTurns != 0 {
		actionOpts.MaxTurns = genOpts.MaxTurns
	}

	if genOpts.IsReturnToolRequestsSet {
		actionOpts.ReturnToolRequests = genOpts.ReturnToolRequests
	}

	return GenerateWithRequest(ctx, p.registry, actionOpts, genOpts.Middleware, genOpts.Stream)
}

// Render renders the prompt template based on user input.
func (p *Prompt) Render(ctx context.Context, input any) (*GenerateActionOptions, error) {
	if p == nil {
		return nil, errors.New("Prompt.Render: called on a nil prompt; check that all prompts are defined")
	}

	if len(p.Middleware) > 0 {
		logger.FromContext(ctx).Warn(fmt.Sprintf("middleware set on prompt %q will be ignored during Prompt.Render", p.Name()))
	}

	return p.action.Run(ctx, input, nil)
}

// mergeMessagesFn merges two messages functions.
func mergeMessagesFn(promptFn, reqFn messagesFn) messagesFn {
	if reqFn == nil {
		return promptFn
	}

	if promptFn == nil {
		return reqFn
	}

	return func(ctx context.Context, input any) ([]*Message, error) {
		promptMsgs, err := promptFn(ctx, input)
		if err != nil {
			return nil, err
		}

		reqMsgs, err := reqFn(ctx, input)
		if err != nil {
			return nil, err
		}

		return append(promptMsgs, reqMsgs...), nil
	}
}

// buildVariables returns a map holding prompt field values based
// on a struct or a pointer to a struct. The struct value should have
// JSON tags that correspond to the Prompt's input schema.
// Only exported fields of the struct will be used.
func buildVariables(variables any) (map[string]any, error) {
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

// buildRequest prepares an [GenerateActionOptions] based on the prompt,
// using the input variables and other information in the [Prompt].
func (p *Prompt) buildRequest(ctx context.Context, input any) (*GenerateActionOptions, error) {
	m, err := buildVariables(input)
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

	var tools []string
	for _, t := range p.Tools {
		tools = append(tools, t.Definition().Name)
	}

	return &GenerateActionOptions{
		Config:             p.Config,
		ToolChoice:         p.ToolChoice,
		Model:              p.ModelName,
		MaxTurns:           p.MaxTurns,
		ReturnToolRequests: p.ReturnToolRequests,
		Messages:           messages,
		Tools:              tools,
		Output: &GenerateActionOutputConfig{
			Format:     string(p.OutputFormat),
			JsonSchema: p.OutputSchema,
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
