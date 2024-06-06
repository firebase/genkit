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
	"github.com/firebase/genkit/go/core/tracing"
)

// buildVariables returns a map holding prompt field values based
// on a struct or a pointer to a struct. The struct value should have
// JSON tags that correspond to the Prompt's input schema.
// Only exported fields of the struct will be used.
func (p *Prompt) buildVariables(variables any) (map[string]any, error) {
	if variables == nil {
		return nil, nil
	}

	v := reflect.Indirect(reflect.ValueOf(variables))
	if v.Kind() != reflect.Struct {
		return nil, errors.New("dotprompt: fields not a struct or pointer to a struct")
	}
	vt := v.Type()

	// TODO(ianlancetaylor): Verify the struct with p.Config.InputSchema.

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
// using the input variables and other information in the [ai.PromptRequest].
func (p *Prompt) buildRequest(pr *ai.PromptRequest) (*ai.GenerateRequest, error) {
	req := &ai.GenerateRequest{}

	m, err := p.buildVariables(pr.Variables)
	if err != nil {
		return nil, err
	}
	if req.Messages, err = p.RenderMessages(m); err != nil {
		return nil, err
	}

	req.Candidates = pr.Candidates
	if req.Candidates == 0 {
		req.Candidates = p.Candidates
	}
	if req.Candidates == 0 {
		req.Candidates = 1
	}

	req.Config = pr.Config
	if req.Config == nil {
		req.Config = p.GenerationConfig
	}

	req.Context = pr.Context

	req.Output = &ai.GenerateRequestOutput{
		Format: p.OutputFormat,
		Schema: p.OutputSchema,
	}

	req.Tools = p.Tools

	return req, nil
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

	ai.RegisterPrompt("dotprompt", name, p)

	return nil
}

// Generate executes a prompt. It does variable substitution and
// passes the rendered template to the AI generator specified by
// the prompt.
//
// This implements the [ai.Prompt] interface.
func (p *Prompt) Generate(ctx context.Context, pr *ai.PromptRequest, cb func(context.Context, *ai.Candidate) error) (*ai.GenerateResponse, error) {
	tracing.SetCustomMetadataAttr(ctx, "subtype", "prompt")

	genReq, err := p.buildRequest(pr)
	if err != nil {
		return nil, err
	}

	generator := p.Generator
	if generator == nil {
		model := p.Model
		if pr.Model != "" {
			model = pr.Model
		}
		if model == "" {
			return nil, errors.New("dotprompt execution: model not specified")
		}
		provider, name, found := strings.Cut(model, "/")
		if !found {
			return nil, errors.New("dotprompt model not in provider/name format")
		}

		generator, err = ai.LookupGenerator(provider, name)
		if err != nil {
			return nil, err
		}
	}

	resp, err := ai.Generate(ctx, generator, genReq, cb)
	if err != nil {
		return nil, err
	}

	return resp, nil
}
