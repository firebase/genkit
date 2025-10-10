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

package modelgarden

import (
	"context"
	"fmt"
	"os"
	"sync"

	"github.com/anthropics/anthropic-sdk-go"
	"github.com/anthropics/anthropic-sdk-go/vertex"
	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/core/api"
	"github.com/firebase/genkit/go/genkit"

	ant "github.com/firebase/genkit/go/plugins/internal/anthropic"
)

const (
	provider = "vertexai"
)

type Anthropic struct {
	ProjectID string
	Location  string

	client  anthropic.Client
	mu      sync.Mutex
	initted bool
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

	projectID := a.ProjectID
	if projectID == "" {
		projectID = os.Getenv("GOOGLE_CLOUD_PROJECT")
		if projectID == "" {
			projectID = os.Getenv("GCLOUD_PROJECT")
			if projectID == "" {
				panic("Vertex AI Modelgarden requires setting GOOGLE_CLOUD_PROJECT or GCLOUD_PROJECT in the environment. You can get a project ID at https://console.cloud.google.com/home/dashboard")
			}
		}
	}

	location := a.Location
	if location == "" {
		location = os.Getenv("GOOGLE_CLOUD_LOCATION")
		if location == "" {
			location = os.Getenv("GOOGLE_CLOUD_REGION")
		}
		if location == "" {
			panic("Vertex AI Modelgarden requires setting GOOGLE_CLOUD_LOCATION or GOOGLE_CLOUD_REGION in the environment. You can get a location at https://cloud.google.com/vertex-ai/docs/general/locations")
		}
	}

	c := anthropic.NewClient(
		vertex.WithGoogleAuth(context.Background(), location, projectID),
	)

	a.initted = true
	a.client = c

	return []api.Action{}
}

// AnthropicModel returns the [ai.Model] with the given id.
// It returns nil if the model was not defined
func AnthropicModel(g *genkit.Genkit, id string) ai.Model {
	return genkit.LookupModel(g, api.NewName(provider, id))
}

// DefineModel adds the model to the registry
func (a *Anthropic) DefineModel(g *genkit.Genkit, name string, opts *ai.ModelOptions) (ai.Model, error) {
	if opts == nil {
		return nil, fmt.Errorf("DefineModel called with nil ai.ModelOptions")
	}
	return ant.DefineModel(g, a.client, provider, name, *opts), nil
}
