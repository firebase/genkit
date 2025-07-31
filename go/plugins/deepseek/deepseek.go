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

package deepseek

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"sync"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/internal"

	deepseek "github.com/cohesion-org/deepseek-go"
)

const (
	provider            = "deepseek"
	deepseekLabelPrefix = "DeepSeek"
)

type DeepSeek struct {
	APIKey string // DeepSeek API key, if not provided env var DEEPSEEK_API_KEY is looked up

	dsclient *deepseek.Client
	mu       sync.Mutex
	initted  bool
}

// Name returns the name of the plugin
func (d *DeepSeek) Name() string {
	return provider
}

// Init initializes the DeepSeek plugin and all its known models
func (d *DeepSeek) Init(ctx context.Context, g *genkit.Genkit) (err error) {
	if d == nil {
		d = &DeepSeek{}
	}
	d.mu.Lock()
	defer d.mu.Unlock()
	if d.initted {
		return errors.New("plugin already initialized")
	}
	defer func() {
		if err != nil {
			err = fmt.Errorf("DeepSeek.Init: %w", err)
		}
	}()

	apiKey := d.APIKey
	if apiKey == "" {
		apiKey = os.Getenv("DEEPSEEK_API_KEY")
		if apiKey == "" {
			return fmt.Errorf("DeepSeek requires setting DEEPSEEK_API_KEY environment variable")
		}
	}

	dsc := deepseek.NewClient(apiKey)
	if dsc == nil {
		return errors.New("unable to create deepseek client")
	}
	d.dsclient = dsc
	d.initted = true

	return nil
}

// Model returns the [ai.Model] with the given name
func (d *DeepSeek) Model(g *genkit.Genkit, name string) ai.Model {
	return genkit.LookupModel(g, provider, name)
}

// DefineModel defines an unknown model with the given name
func (d *DeepSeek) DefineModel(g *genkit.Genkit, name string, info ai.ModelInfo) (ai.Model, error) {
	return defineModel(g, *d.dsclient, provider, name, info), nil
}

// ListActions lists all resolvable actions by the plugin
func (d *DeepSeek) ListActions(ctx context.Context) []core.ActionDesc {
	actions := []core.ActionDesc{}
	models, err := listModels(ctx, *d.dsclient)
	if err != nil {
		return nil
	}

	for _, name := range models {
		metadata := map[string]any{
			"model": map[string]any{
				"supports": map[string]any{
					"media":       true,
					"multiturn":   true,
					"systemRole":  true,
					"tools":       true,
					"toolChoice":  true,
					"constrained": "no-tools",
				},
				"versions": []string{},
				"stage":    string(ai.ModelStageStable),
			},
		}
		metadata["label"] = fmt.Sprintf("%s - %s", deepseekLabelPrefix, name)
		actions = append(actions, core.ActionDesc{
			Type:     core.ActionTypeModel,
			Name:     fmt.Sprintf("%s/%s", provider, name),
			Key:      fmt.Sprintf("/%s/%s/%s", core.ActionTypeModel, provider, name),
			Metadata: metadata,
		})

	}

	return actions
}

// ResolveAction resolves all available actions from the plugin
func (d *DeepSeek) ResolveAction(g *genkit.Genkit, atype core.ActionType, name string) error {
	switch atype {
	case core.ActionTypeModel:
		defineModel(g, *d.dsclient, provider, name, ai.ModelInfo{
			Label:    fmt.Sprintf("%s - %s", deepseekLabelPrefix, name),
			Stage:    ai.ModelStageStable,
			Versions: []string{},
			Supports: &internal.Multimodal,
		})
	}
	return nil
}

// defineModel defines a model in the Genkit core
func defineModel(g *genkit.Genkit, client deepseek.Client, provider, name string, info ai.ModelInfo) ai.Model {
	return genkit.DefineModel(g, provider, name, &info, func(
		ctx context.Context,
		input *ai.ModelRequest,
		cb func(context.Context, *ai.ModelResponseChunk) error,
	) (*ai.ModelResponse, error) {
		return generate(ctx, client, name, input, cb)
	})
}

// listModels fetches the official deepseek models from the API
func listModels(ctx context.Context, client deepseek.Client) ([]string, error) {
	apiModels, err := deepseek.ListAllModels(&client, ctx)
	if err != nil {
		return nil, err
	}
	models := []string{}
	for _, m := range apiModels.Data {
		if m.Object != "model" && m.OwnedBy != "deepseek" {
			continue
		}
	}

	return models, nil
}

func generate(ctx context.Context, client deepseek.Client, model string, input *ai.ModelRequest, cb func(context.Context, *ai.ModelResponseChunk) error,
) (*ai.ModelResponse, error) {
	req, err := configFromRequest(input)
	if err != nil {
		return nil, err
	}

	// Genkit primitive fields must be used instead of deepseek config fields
	// i.e.: system prompt, tools, cached content, response schema
	if req.Model != "" {
		return nil, errors.New("model must be set using Genkit feature: ai.WithModelName() or ai.WithModel()")
	}
	if req.Messages != nil {
		return nil, errors.New("messages must be set using Genkit feature: ai.WithMessages()")
	}
	if req.ResponseFormat != nil {
		return nil, errors.New("response format must be set using Genkit feature: ai.WithOutputType()")
	}
	if req.ToolChoice != nil {
		return nil, errors.New("tool choice must be set using Genkit feature: ai.WithToolChoice()")
	}
	if req.Tools != nil {
		return nil, errors.New("tools must be set using Genkit feature: ai.WithTools()")
	}

	// constrained generation
	hasOutput := input.Output != nil
	isJsonFormat := hasOutput && input.Output.Format == "json"
	isJsonContentType := hasOutput && input.Output.ContentType == "application/json"
	req.JSONMode = isJsonFormat || isJsonContentType

	req.Model = model
	// create messages, roles, tools and translate parts

	return nil, nil
}

func configFromRequest(input *ai.ModelRequest) (*deepseek.ChatCompletionRequest, error) {
	var config deepseek.ChatCompletionRequest

	switch cfg := input.Config.(type) {
	case deepseek.ChatCompletionRequest:
		config = cfg
	case *deepseek.ChatCompletionRequest:
		config = *cfg
	case map[string]any:
		if err := mapToStruct(cfg, config); err != nil {
			return nil, err
		}
	case nil:
	default:
		return nil, fmt.Errorf("unexpected config type: %T", input.Config)
	}

	return &config, nil
}

// mapToStruct unmarshals a map[String]any to the expected type
func mapToStruct(m map[string]any, v any) error {
	jsonData, err := json.Marshal(m)
	if err != nil {
		return err
	}
	return json.Unmarshal(jsonData, v)
}
