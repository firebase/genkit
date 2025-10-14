// Copyright 2025 Google LLC
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
//
// SPDX-License-Identifier: Apache-2.0

package anthropic

import (
	"context"
	"fmt"
	"os"
	"sync"

	"github.com/anthropics/anthropic-sdk-go"
	"github.com/anthropics/anthropic-sdk-go/option"
	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/core/api"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/internal/base"
	ant "github.com/firebase/genkit/go/plugins/internal/anthropic"
	"github.com/invopop/jsonschema"
)

const (
	provider             = "anthropic"
	anthropicLabelPrefix = "Anthropic"
)

type Anthropic struct {
	APIKey  string // If not provided, defaults to ANTHROPIC_API_KEY
	BaseURL string // Optional. If not provided, defaults to ANTHROPIC_BASE_URL

	aclient anthropic.Client // Anthropic client
	mu      sync.Mutex       // Mutex to control access
	initted bool             // Whether the plugin has been initialized
}

func (a *Anthropic) Name() string {
	return provider
}

func (a *Anthropic) Init(ctx context.Context) []api.Action {
	if a == nil {
		a = &Anthropic{}
	}

	a.mu.Lock()
	defer a.mu.Unlock()
	if a.initted {
		panic("plugin already initialized")
	}

	apiKey := a.APIKey
	if apiKey == "" {
		apiKey = os.Getenv("ANTHROPIC_API_KEY")
	}
	if apiKey == "" {
		panic("Anthropic requires setting ANTHROPIC_API_KEY in the environment")
	}

	opts := []option.RequestOption{option.WithAPIKey(apiKey)}

	baseURL := a.BaseURL
	if baseURL == "" {
		baseURL = os.Getenv("ANTHROPIC_BASE_URL")
	}
	if baseURL != "" {
		opts = append(opts, option.WithBaseURL(baseURL))
	}

	ac := anthropic.NewClient(opts...)
	a.aclient = ac
	a.initted = true

	return []api.Action{}
}

func (a *Anthropic) DefineModel(g *genkit.Genkit, name string, opts *ai.ModelOptions) (ai.Model, error) {
	return ant.DefineModel(g, a.aclient, name, *opts), nil
}

func (a *Anthropic) IsDefinedModel(g *genkit.Genkit, name string) bool {
	return genkit.LookupModel(g, name) != nil
}

func (a *Anthropic) ListActions(ctx context.Context) []api.ActionDesc {
	actions := []api.ActionDesc{}

	models, err := listModels(ctx, &a.aclient)
	if err != nil {
		return nil
	}

	for _, name := range models {
		model := newModel(a.aclient, name, defaultClaudeOpts)
		if actionDef, ok := model.(api.Action); ok {
			actions = append(actions, actionDef.Desc())
		}
	}

	return actions
}

// ResolveAction resolves an action with the given name
func (a *Anthropic) ResolveAction(atype api.ActionType, id string) api.Action {
	switch atype {
	case api.ActionTypeModel:
		return newModel(a.aclient, id, ai.ModelOptions{
			Label:    fmt.Sprintf("%s - %s", anthropicLabelPrefix, id),
			Stage:    ai.ModelStageStable,
			Versions: []string{},
			Supports: defaultClaudeOpts.Supports,
		}).(api.Action)
	}
	return nil
}

// newModel creates a model wihout registering it
func newModel(client anthropic.Client, name string, opts ai.ModelOptions) ai.Model {
	config := &anthropic.MessageNewParams{}

	meta := &ai.ModelOptions{
		Label:        opts.Label,
		Supports:     opts.Supports,
		Versions:     opts.Versions,
		ConfigSchema: configToMap(config),
		Stage:        opts.Stage,
	}

	fn := func(
		ctx context.Context,
		input *ai.ModelRequest,
		cb func(context.Context, *ai.ModelResponseChunk) error,
	) (*ai.ModelResponse, error) {
		return ant.Generate(ctx, client, name, input, cb)
	}

	return ai.NewModel(api.NewName(provider, name), meta, fn)
}

// configToMap converts a config struct to a map[string]any.
func configToMap(config any) map[string]any {
	r := jsonschema.Reflector{
		DoNotReference:             true, // Prevent $ref usage
		AllowAdditionalProperties:  false,
		ExpandedStruct:             true,
		RequiredFromJSONSchemaTags: true,
	}
	schema := r.Reflect(config)
	result := base.SchemaAsMap(schema)
	return result
}
