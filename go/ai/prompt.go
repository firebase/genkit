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
	"maps"

	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/internal/atype"
	"github.com/invopop/jsonschema"
)

// A Prompt is used to render a prompt template,
// producing a [GenerateRequest] that may be passed to a [Model].
type Prompt core.Action[any, *GenerateRequest, struct{}]

// DefinePrompt takes a function that renders a prompt template
// into a [GenerateRequest] that may be passed to a [Model].
// The prompt expects some input described by inputSchema.
// DefinePrompt registers the function as an action,
// and returns a [Prompt] that runs it.
func DefinePrompt(provider, name string, metadata map[string]any, inputSchema *jsonschema.Schema, render func(context.Context, any) (*GenerateRequest, error)) *Prompt {
	mm := maps.Clone(metadata)
	if mm == nil {
		mm = make(map[string]any)
	}
	mm["type"] = "prompt"
	return (*Prompt)(core.DefineActionWithInputSchema(provider, name, atype.Prompt, mm, inputSchema, render))
}

// LookupPrompt looks up a [Prompt] registered by [DefinePrompt].
// It returns nil if the prompt was not defined.
func LookupPrompt(provider, name string) *Prompt {
	return (*Prompt)(core.LookupActionFor[any, *GenerateRequest, struct{}](atype.Prompt, provider, name))
}

// Render renders the [Prompt] with some input data.
func (p *Prompt) Render(ctx context.Context, input any) (*GenerateRequest, error) {
	return (*core.Action[any, *GenerateRequest, struct{}])(p).Run(ctx, input, nil)
}
