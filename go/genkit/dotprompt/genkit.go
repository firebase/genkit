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
	"errors"
	"reflect"
	"strings"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
)

// ActionInput is the input type of a prompt action.
// This should have all the fields of GenerateRequest other than
// Messages, Tools, and Output.
type ActionInput struct {
	// Input variables to substitute in the template.
	// TODO(ianlancetaylor) Not sure variables is the right name here.
	Variables map[string]any `json:"variables,omitempty"`
	// Number of candidates to return; if 0, 1 is used.
	Candidates int `json:"candidates,omitempty"`
	// Configuration.
	Config *ai.GenerationCommonConfig `json:"config,omitempty"`
	// The model to use. This overrides any model in the prompt.
	Model string `json:"model,omitempty"`
}

// BuildVariables returns a map for [ActionInput.Variables] based
// on a pointer to a struct value. The struct value should have
// JSON tags that correspond to the Prompt's input schema.
// Only exported fields of the struct will be used.
func (p *Prompt) BuildVariables(input any) (map[string]any, error) {
	v := reflect.ValueOf(input).Elem()
	if v.Kind() != reflect.Struct {
		return nil, errors.New("BuildVariables: not a pointer to a struct")
	}
	vt := v.Type()

	// TODO(ianlancetaylor): Verify the struct with p.Frontmatter.Schema.

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

// buildRequest prepares an [ai.GenerateRequest] based on the prompt,
// using the input variables and other information in the [ActionInput].
func (p *Prompt) buildRequest(input *ActionInput) (*ai.GenerateRequest, error) {
	req := &ai.GenerateRequest{}

	var err error
	if req.Messages, err = p.RenderMessages(input.Variables); err != nil {
		return nil, err
	}

	req.Candidates = input.Candidates
	if req.Candidates == 0 {
		req.Candidates = p.Candidates
	}
	if req.Candidates == 0 {
		req.Candidates = 1
	}

	req.Config = p.GenerationConfig
	req.Output = &ai.GenerateRequestOutput{
		Format: p.OutputFormat,
		Schema: p.OutputSchema,
	}
	req.Tools = p.Tools

	return req, nil
}

// Action returns a [genkit.Action] that executes the prompt.
// The returned Action will take an [ActionInput] that provides
// variables to substitute into the template text.
// It will then pass the rendered text to an AI generator,
// and return whatever the generator computes.
func (p *Prompt) Action() (*genkit.Action[*ActionInput, *ai.GenerateResponse, struct{}], error) {
	if p.Name == "" {
		return nil, errors.New("dotprompt: missing name")
	}
	name := p.Name
	if p.Variant != "" {
		name += "." + p.Variant
	}

	a := genkit.NewAction(name, nil, p.Execute)
	a.Metadata = map[string]any{
		"type":   "prompt",
		"prompt": p,
	}
	return a, nil
}

// Register registers an action to execute a prompt.
func (p *Prompt) Register() error {
	name := p.Name
	if name == "" {
		return errors.New("attempt to register unnamed prompt")
	}
	if p.Variant != "" {
		name += "." + p.Variant
	}

	action, err := p.Action()
	if err != nil {
		return err
	}

	genkit.RegisterAction(genkit.ActionTypePrompt, name, action)
	return nil
}

// Execute executes a prompt. It does variable substitution and
// passes the rendered template to the AI generator specified by
// the prompt.
func (p *Prompt) Execute(ctx context.Context, input *ActionInput) (*ai.GenerateResponse, error) {
	genkit.SetCustomMetadataAttr(ctx, "subtype", "prompt")

	genReq, err := p.buildRequest(input)
	if err != nil {
		return nil, err
	}

	generator := p.generator
	if generator == nil {
		model := p.Model
		if input.Model != "" {
			model = input.Model
		}
		if model == "" {
			return nil, errors.New("dotprompt action: model not specified")
		}
		provider, name, found := strings.Cut(model, "/")
		if !found {
			return nil, errors.New("dotprompt model not in provider/name format")
		}

		generator, err = ai.LookupGeneratorAction(provider, name)
		if err != nil {
			return nil, err
		}
	}

	resp, err := ai.Generate(ctx, generator, genReq, nil)
	if err != nil {
		return nil, err
	}

	return resp, nil
}
