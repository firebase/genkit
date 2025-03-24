// Copyright 2025 Google LLC
// SPDX-License-Identifier: Apache-2.0

package vertexai

import (
	"context"
	"errors"
	"fmt"
	"os"
	"sync"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/internal/gemini"
	"google.golang.org/genai"
)

const (
	provider    = "vertexai"
	labelPrefix = "Vertex AI"
)

var (
	supportedModels = map[string]ai.ModelInfo{
		"gemini-1.5-flash": {
			Label: labelPrefix + " - " + "Gemini 1.5 Flash",
			Versions: []string{
				"gemini-1.5-flash-latest",
				"gemini-1.5-flash-001",
				"gemini-1.5-flash-002",
			},
			Supports: &gemini.Multimodal,
		},
		"gemini-1.5-pro": {
			Label: labelPrefix + " - " + "Gemini 1.5 Pro",
			Versions: []string{
				"gemini-1.5-pro-latest",
				"gemini-1.5-pro-001",
				"gemini-1.5-pro-002",
			},
			Supports: &gemini.Multimodal,
		},
		"gemini-2.0-flash": {
			Label: labelPrefix + " - " + "Gemini 2.0 Flash",
			Versions: []string{
				"gemini-2.0-flash-001",
			},
			Supports: &gemini.Multimodal,
		},
		"gemini-2.0-flash-lite": {
			Label: labelPrefix + " - " + "Gemini 2.0 Flash Lite",
			Versions: []string{
				"gemini-2.0-flash-lite-001",
			},
			Supports: &gemini.Multimodal,
		},
		"gemini-2.0-flash-lite-preview": {
			Label:    labelPrefix + " - " + "Gemini 2.0 Flash Lite Preview 02-05",
			Versions: []string{},
			Supports: &gemini.Multimodal,
		},
		"gemini-2.0-pro-exp-02-05": {
			Label:    labelPrefix + " - " + "Gemini 2.0 Pro Exp 02-05",
			Versions: []string{},
			Supports: &gemini.Multimodal,
		},
		"gemini-2.0-flash-thinking-exp-01-21": {
			Label:    labelPrefix + " - " + "Gemini 2.0 Flash Thinking Exp 01-21",
			Versions: []string{},
			Supports: &gemini.Multimodal,
		},
	}

	knownEmbedders = []string{
		"textembedding-gecko@003",
		"textembedding-gecko@002",
		"textembedding-gecko@001",
		"text-embedding-004",
		"textembedding-gecko-multilingual@001",
		"text-multilingual-embedding-002",
		"multimodalembedding",
	}
)

// VertexAI is a Genkit plugin for interacting with the Google Vertex AI service.
type VertexAI struct {
	ProjectID string // Google Cloud project to use for Vertex AI. If empty, the values of the environment variables GCLOUD_PROJECT and GOOGLE_CLOUD_PROJECT will be consulted, in that order.
	Location  string // Location of the Vertex AI service. The default is "us-central1".

	gclient *genai.Client // Client for the Vertex AI service.
	mu      sync.Mutex    // Mutex to control access.
	initted bool          // Whether the plugin has been initialized.
}

// Name returns the name of the plugin.
func (v *VertexAI) Name() string {
	return provider
}

// Init initializes the plugin and all known models and embedders.
// After calling Init, you may call [DefineModel] and [DefineEmbedder] to create
// and register any additional generative models and embedders
func (v *VertexAI) Init(ctx context.Context, g *genkit.Genkit) (err error) {
	if v == nil {
		v = &VertexAI{}
	}

	v.mu.Lock()
	defer v.mu.Unlock()
	defer func() {
		if err != nil {
			err = fmt.Errorf("vertexai.Init: %w", err)
		}
	}()

	if v.initted {
		return errors.New("plugin already initialized")
	}

	if v.ProjectID == "" {
		v.ProjectID = os.Getenv("GCLOUD_PROJECT")
	}
	if v.ProjectID == "" {
		v.ProjectID = os.Getenv("GOOGLE_CLOUD_PROJECT")
	}
	if v.ProjectID == "" {
		return fmt.Errorf("vertexai.Init: Vertex AI requires setting GCLOUD_PROJECT or GOOGLE_CLOUD_PROJECT in the environment")
	}
	if v.Location == "" {
		v.Location = "us-central1"
	}

	v.gclient, err = genai.NewClient(ctx, &genai.ClientConfig{
		Backend:  genai.BackendVertexAI,
		Project:  v.ProjectID,
		Location: v.Location,
		HTTPOptions: genai.HTTPOptions{
			Headers: gemini.GenkitClientHeader,
		},
	})
	if err != nil {
		return err
	}

	v.initted = true

	for model, info := range supportedModels {
		gemini.DefineModel(g, v.gclient, model, info)
	}

	for _, e := range knownEmbedders {
		gemini.DefineEmbedder(g, v.gclient, e)
	}

	return nil
}

//copy:sink defineModel from ../googleai/googleai.go
// DO NOT MODIFY below vvvv

// DefineModel defines an unknown model with the given name.
// The second argument describes the capability of the model.
// Use [IsDefinedModel] to determine if a model is already defined.
// After [Init] is called, only the known models are defined.
func (v *VertexAI) DefineModel(g *genkit.Genkit, name string, info *ai.ModelInfo) (ai.Model, error) {
	v.mu.Lock()
	defer v.mu.Unlock()
	if !v.initted {
		panic(provider + ".Init not called")
	}
	var mi ai.ModelInfo
	if info == nil {
		var ok bool
		mi, ok = supportedModels[name]
		if !ok {
			return nil, fmt.Errorf("%s.DefineModel: called with unknown model %q and nil ModelInfo", provider, name)
		}
	} else {
		// TODO: unknown models could also specify versions?
		mi = *info
	}
	return gemini.DefineModel(g, v.gclient, name, mi), nil
}

// IsDefinedModel reports whether the named [Model] is defined by this plugin.
func IsDefinedModel(g *genkit.Genkit, name string) bool {
	return genkit.IsDefinedModel(g, provider, name)
}

// DO NOT MODIFY above ^^^^
//copy:endsink defineModel

//copy:sink defineEmbedder from ../googleai/googleai.go
// DO NOT MODIFY below vvvv

// DefineEmbedder defines an embedder with a given name.
func (v *VertexAI) DefineEmbedder(g *genkit.Genkit, name string) ai.Embedder {
	v.mu.Lock()
	defer v.mu.Unlock()
	if !v.initted {
		panic(provider + ".Init not called")
	}
	return gemini.DefineEmbedder(g, v.gclient, name)
}

// IsDefinedEmbedder reports whether the named [Embedder] is defined by this plugin.
func IsDefinedEmbedder(g *genkit.Genkit, name string) bool {
	return genkit.LookupEmbedder(g, provider, name) != nil
}

// DO NOT MODIFY above ^^^^
//copy:endsink defineEmbedder

//copy:sink lookups from ../googleai/googleai.go
// DO NOT MODIFY below vvvv

// Model returns the [ai.Model] with the given name.
// It returns nil if the model was not defined.
func Model(g *genkit.Genkit, name string) ai.Model {
	return genkit.LookupModel(g, provider, name)
}

// Embedder returns the [ai.Embedder] with the given name.
// It returns nil if the embedder was not defined.
func Embedder(g *genkit.Genkit, name string) ai.Embedder {
	return genkit.LookupEmbedder(g, provider, name)
}

// DO NOT MODIFY above ^^^^
