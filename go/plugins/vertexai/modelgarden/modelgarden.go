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

// modelgarden package is a plugin that aggregates and registers other provider plugins
// supported in Vertex AI Modelgarden
package modelgarden

import (
	"context"
	"fmt"

	"github.com/firebase/genkit/go/genkit"
)

type ProviderPlugin struct {
	name      string
	providers map[string]genkit.Plugin
}

func NewProviderPlugin(name string, providers ...genkit.Plugin) *ProviderPlugin {
	providerMap := map[string]genkit.Plugin{}

	for _, p := range providers {
		providerMap[p.Name()] = p
	}

	return &ProviderPlugin{
		name:      name,
		providers: providerMap,
	}
}

// Init initializes the Modelgarden plugin and all the registered provider plugins
// After calling Init, you may call the provider's [DefineModel] function to
// create and register any aditional generative model
func (pp *ProviderPlugin) Init(ctx context.Context, g *genkit.Genkit) error {
	for name, provider := range pp.providers {
		if err := provider.Init(ctx, g); err != nil {
			return fmt.Errorf("failed to initialize provider %q in %q: %w", name, pp.name, err)
		}
	}
	return nil
}

// Name returns the name of the plugin
func (pp *ProviderPlugin) Name() string {
	return pp.name
}

// WithProviders provides a list of provider plugins to initialize when creating the Modelgarden plugin.
// Each plugin's [Plugin.Init] method will be called sequentially during [Init].
func WithProviders(providers ...genkit.Plugin) genkit.Plugin {
	return NewProviderPlugin("modelgarden", providers...)
}
