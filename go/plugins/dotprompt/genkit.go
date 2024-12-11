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

package dotprompt

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"reflect"
	"strings"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/core/tracing"
)

// PromptRequest is a request to execute a dotprompt template and
// pass the result to a [Model].
type PromptRequest struct {
	// Input fields for the prompt. If not nil this should be a struct
	// or pointer to a struct that matches the prompt's input schema.
	Input any `json:"input,omitempty"`
	// Model configuration. If nil will be taken from the prompt config.
	Config *ai.GenerationCommonConfig `json:"config,omitempty"`
	// Context to pass to model, if any.
	Context []any `json:"context,omitempty"`
	// The model to use. This overrides any model specified by the prompt.
	Model ai.Model `json:"model,omitempty"`
	// The name of the model to use. This overrides any model specified by the prompt.
	ModelName string `json:"modelname,omitempty"`
	// Streaming callback function
	Stream ai.ModelStreamingCallback
}

// GenerateOption configures params for Generate function
type GenerateOption func(p *PromptRequest) error

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
		return nil, errors.New("dotprompt: fields not a struct or pointer to a struct or a map")
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
	if req.Messages, err = p.RenderMessages(m); err != nil {
		return nil, err
	}

	req.Config = p.GenerationConfig

	var outputSchema map[string]any
	if p.OutputSchema != nil {
		jsonBytes, err := p.OutputSchema.MarshalJSON()
		if err != nil {
			return nil, fmt.Errorf("failed to marshal output schema JSON: %w", err)
		}
		err = json.Unmarshal(jsonBytes, &outputSchema)
		if err != nil {
			return nil, fmt.Errorf("failed to unmarshal output schema JSON: %w", err)
		}
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

// Register registers an action to render a prompt.
func (p *Prompt) Register() error {
	if p.prompt != nil {
		return nil
	}

	name := p.Name
	if name == "" {
		return errors.New("attempt to register unnamed prompt")
	}
	if p.Variant != "" {
		name += "." + p.Variant
	}

	// TODO: Undo clearing of the Version once Monaco Editor supports newer than JSON schema draft-07.
	if p.InputSchema != nil {
		p.InputSchema.Version = ""
	}

	metadata := map[string]any{
		"prompt": map[string]any{
			"name":     p.Name,
			"input":    map[string]any{"schema": p.InputSchema},
			"output":   map[string]any{"format": p.OutputFormat},
			"template": p.TemplateText,
		},
	}
	p.prompt = ai.DefinePrompt("dotprompt", name, metadata, p.Config.InputSchema, p.buildRequest)

	return nil
}

// Generate executes a prompt. It does variable substitution and
// passes the rendered template to the AI model specified by
// the prompt.
//
// This implements the [ai.Prompt] interface.
func (p *Prompt) Generate(ctx context.Context, opts ...GenerateOption) (*ai.ModelResponse, error) {
	tracing.SetCustomMetadataAttr(ctx, "subtype", "prompt")
	var pr PromptRequest

	for _, with := range opts {
		err := with(&pr)
		if err != nil {
			return nil, err
		}
	}

	var mr *ai.ModelRequest
	var err error
	if p.prompt != nil {
		mr, err = p.prompt.Render(ctx, pr.Input)
	} else {
		mr, err = p.buildRequest(ctx, pr.Input)
	}
	if err != nil {
		return nil, err
	}

	// Let some fields in pr override those in the prompt config.
	if pr.Config != nil {
		mr.Config = pr.Config
	}
	if len(pr.Context) > 0 {
		mr.Context = pr.Context
	}

	// Setting the model on generate, overrides the model defined on the prompt
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
		if modelName == "" {
			return nil, errors.New("dotprompt execution: model not specified")
		}
		provider, name, found := strings.Cut(modelName, "/")
		if !found {
			return nil, errors.New("dotprompt model not in provider/name format")
		}

		model = ai.LookupModel(provider, name)
		if model == nil {
			return nil, fmt.Errorf("no model named %q for provider %q", name, provider)
		}
	}

	resp, err := model.Generate(ctx, mr, pr.Stream)
	if err != nil {
		return nil, err
	}

	return resp, nil
}

// GenerateText runs generate request for this prompt. Returns generated text only.
func (p *Prompt) GenerateText(ctx context.Context, opts ...GenerateOption) (string, error) {
	res, err := p.Generate(ctx, opts...)
	if err != nil {
		return "", err
	}

	return res.Text(), nil
}

// GenerateData runs generate request for this prompt. Returns ModelResponse struct.
// TODO: Stream GenerateData with partial JSON
func (p *Prompt) GenerateData(ctx context.Context, value any, opts ...GenerateOption) (*ai.ModelResponse, error) {
	with := WithOutputType(value)
	err := with(p)
	if err != nil {
		return nil, err
	}

	resp, err := p.Generate(ctx, opts...)
	if err != nil {
		return nil, err
	}
	err = resp.UnmarshalOutput(value)
	if err != nil {
		return nil, err
	}
	return resp, nil
}

// WithInput adds input to pass to the model.
func WithInput(input any) GenerateOption {
	return func(p *PromptRequest) error {
		if p.Input != nil {
			return errors.New("dotprompt.WithInput: cannot set Input more than once")
		}
		p.Input = input
		return nil
	}
}

// WithConfig adds model configuration. If nil will be taken from the prompt config.
func WithConfig(config *ai.GenerationCommonConfig) GenerateOption {
	return func(p *PromptRequest) error {
		if p.Config != nil {
			return errors.New("dotprompt.WithConfig: cannot set Config more than once")
		}
		p.Config = config
		return nil
	}
}

// WithContext add context to pass to model, if any.
func WithContext(context []any) GenerateOption {
	return func(p *PromptRequest) error {
		if p.Context != nil {
			return errors.New("dotprompt.WithContext: cannot set Context more than once")
		}
		p.Context = context
		return nil
	}
}

// WithModel adds the Model to use. This overrides any model specified by the prompt.
func WithModel(model ai.Model) GenerateOption {
	return func(p *PromptRequest) error {
		if p.ModelName != "" || p.Model != nil {
			return errors.New("dotprompt.WithModel: Model must be specified exactly once, either ModelName or Model")
		}
		p.Model = model
		return nil
	}
}

// WithModelName adds the name of the Model to use. This overrides any model specified by the prompt.
func WithModelName(model string) GenerateOption {
	return func(p *PromptRequest) error {
		if p.ModelName != "" || p.Model != nil {
			return errors.New("dotprompt.WithModelName: Model must be specified exactly once, either ModelName or Model")
		}
		p.ModelName = model
		return nil
	}
}

// WithStreaming adds a streaming callback to the generate request.
func WithStreaming(cb ai.ModelStreamingCallback) GenerateOption {
	return func(g *PromptRequest) error {
		if g.Stream != nil {
			return errors.New("dotprompt.WithStreaming: cannot set Stream more than once")
		}
		g.Stream = cb
		return nil
	}
}
