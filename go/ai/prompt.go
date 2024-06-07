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

	"github.com/firebase/genkit/go/core"
)

// PromptRequest is a request to execute a prompt template and
// pass the result to a [ModelAction].
type PromptRequest struct {
	// Input fields for the prompt. If not nil this should be a struct
	// or pointer to a struct that matches the prompt's input schema.
	Variables any `json:"variables,omitempty"`
	// Number of candidates to return; if 0, will be taken
	// from the prompt config; if still 0, will use 1.
	Candidates int `json:"candidates,omitempty"`
	// Model configuration. If nil will be taken from the prompt config.
	Config *GenerationCommonConfig `json:"config,omitempty"`
	// Context to pass to model, if any.
	Context []any `json:"context,omitempty"`
	// The model to use. This overrides any model specified by the prompt.
	Model string `json:"model,omitempty"`
}

// A PromptAction is used to generate content from an AI model using a prompt.
type PromptAction = core.Action[*PromptRequest, *GenerateResponse, *Candidate]

// DefinePrompt register the given function as a prompt action,
// and returns a [PromptAction] that runs it.
func DefinePrompt(provider, name string, render func(context.Context, *PromptRequest, ModelStreamingCallback) (*GenerateResponse, error)) *PromptAction {
	metadata := map[string]any{
		"type":   "prompt",
		"prompt": true, // required by genkit UI
	}
	return core.DefineStreamingAction(provider, name, core.ActionTypePrompt, metadata, render)
}

// LookupPrompt looks up a [PromptAction] registered by [DefinePrompt].
// It returns nil if the prompt was not defined.
func LookupPrompt(provider, name string) *PromptAction {
	return core.LookupActionFor[*PromptRequest, *GenerateResponse, *Candidate](core.ActionTypePrompt, provider, name)
}

// Render applies a [PromptAction] to some input variables.
func Render(ctx context.Context, p *PromptAction, req *PromptRequest, cb ModelStreamingCallback) (*GenerateResponse, error) {
	return p.Run(ctx, req, cb)
}
