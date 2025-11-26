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
	"os"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/core/api"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/compat_oai"
	"github.com/openai/openai-go/option"
)

const (
	provider = "deepseek"
	baseURL  = "https://api.deepseek.com/v1"
)

type DeepSeek struct {
	Opts             []option.RequestOption
	openAICompatible compat_oai.OpenAICompatible
}

func (d *DeepSeek) Name() string {
	return provider
}

func (d *DeepSeek) Init(ctx context.Context) []api.Action {
	url := os.Getenv("DEEPSEEK_BASE_URL")
	if url == "" {
		url = baseURL
	}
	d.Opts = append([]option.RequestOption{option.WithBaseURL(url)}, d.Opts...)

	apiKey := os.Getenv("DEEPSEEK_API_KEY")
	if apiKey != "" {
		d.Opts = append([]option.RequestOption{option.WithAPIKey(apiKey)}, d.Opts...)
	}

	d.openAICompatible.Opts = d.Opts
	d.openAICompatible.Provider = provider

	return d.openAICompatible.Init(ctx)
}

func (d *DeepSeek) Model(g *genkit.Genkit, name string) ai.Model {
	return d.openAICompatible.Model(g, api.NewName(provider, name))
}

func (d *DeepSeek) DefineModel(g *genkit.Genkit, name string, opts ai.ModelOptions) ai.Model {
	return d.openAICompatible.DefineModel(provider, name, opts)
}

func (d *DeepSeek) ListActions(ctx context.Context) []api.ActionDesc {
	return d.openAICompatible.ListActions(ctx)
}

func (d *DeepSeek) ResolveAction(atype api.ActionType, name string) api.Action {
	return d.openAICompatible.ResolveAction(atype, name)
}
