// Copyright 2025 Google LLC
// SPDX-License-Identifier: Apache-2.0

package googlegenai

import (
	"context"
	"errors"
	"fmt"
	"os"
	"strings"
	"sync"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/genkit"

	"google.golang.org/genai"
)

const (
	googleAIProvider = "googleai"
	vertexAIProvider = "vertexai"

	googleAILabelPrefix = "Google AI"
	vertexAILabelPrefix = "Vertex AI"
)

// GoogleAI is a Genkit plugin for interacting with the Google AI service.
type GoogleAI struct {
	APIKey string // API key to access the service. If empty, the values of the environment variables GEMINI_API_KEY or GOOGLE_API_KEY will be consulted, in that order.

	gclient *genai.Client // Client for the Google AI service.
	mu      sync.Mutex    // Mutex to control access.
	initted bool          // Whether the plugin has been initialized.
}

// VertexAI is a Genkit plugin for interacting with the Google Vertex AI service.
type VertexAI struct {
	ProjectID string // Google Cloud project to use for Vertex AI. If empty, the value of the environment variable GOOGLE_CLOUD_PROJECT will be consulted.
	Location  string // Location of the Vertex AI service. If empty, GOOGLE_CLOUD_LOCATION and GOOGLE_CLOUD_REGION environment variables will be consulted, in that order.

	gclient *genai.Client // Client for the Vertex AI service.
	mu      sync.Mutex    // Mutex to control access.
	initted bool          // Whether the plugin has been initialized.
}

// Name returns the name of the plugin.
func (ga *GoogleAI) Name() string {
	return googleAIProvider
}

// Name returns the name of the plugin.
func (v *VertexAI) Name() string {
	return vertexAIProvider
}

// Init initializes the Google AI plugin and all known models and embedders.
// After calling Init, you may call [DefineModel] and [DefineEmbedder] to create
// and register any additional generative models and embedders
func (ga *GoogleAI) Init(ctx context.Context) []core.Action {
	if ga == nil {
		ga = &GoogleAI{}
	}
	ga.mu.Lock()
	defer ga.mu.Unlock()
	if ga.initted {
		panic("plugin already initialized")
	}

	apiKey := ga.APIKey
	if apiKey == "" {
		apiKey = os.Getenv("GEMINI_API_KEY")
		if apiKey == "" {
			apiKey = os.Getenv("GOOGLE_API_KEY")
		}
		if apiKey == "" {
			panic("Google AI requires setting GEMINI_API_KEY or GOOGLE_API_KEY in the environment. You can get an API key at https://ai.google.dev")
		}
	}

	gc := genai.ClientConfig{
		Backend: genai.BackendGeminiAPI,
		APIKey:  apiKey,
		HTTPOptions: genai.HTTPOptions{
			Headers: genkitClientHeader,
		},
	}

	client, err := genai.NewClient(ctx, &gc)
	if err != nil {
		panic(fmt.Errorf("GoogleAI.Init: %w", err))
	}
	ga.gclient = client
	ga.initted = true

	var actions []core.Action

	models, err := listModels(googleAIProvider)
	if err != nil {
		panic(fmt.Errorf("GoogleAI.Init: %w", err))
	}
	for n, mi := range models {
		model := newModel(ga.gclient, n, mi)
		actions = append(actions, model.(core.Action))
	}

	embedders, err := listEmbedders(gc.Backend)
	if err != nil {
		panic(fmt.Errorf("GoogleAI.Init: %w", err))
	}
	for e, eOpts := range embedders {
		embedder := newEmbedder(ga.gclient, e, &eOpts)
		actions = append(actions, embedder.(core.Action))
	}

	return actions
}

// Init initializes the VertexAI plugin and all known models and embedders.
// After calling Init, you may call [DefineModel] and [DefineEmbedder] to create
// and register any additional generative models and embedders
func (v *VertexAI) Init(ctx context.Context) []core.Action {
	if v == nil {
		v = &VertexAI{}
	}
	v.mu.Lock()
	defer v.mu.Unlock()
	if v.initted {
		panic("plugin already initialized")
	}

	projectID := v.ProjectID
	if projectID == "" {
		projectID = os.Getenv("GOOGLE_CLOUD_PROJECT")
		if projectID == "" {
			panic("Vertex AI requires setting GOOGLE_CLOUD_PROJECT in the environment. You can get a project ID at https://console.cloud.google.com/home/dashboard")
		}
	}

	location := v.Location
	if location == "" {
		location = os.Getenv("GOOGLE_CLOUD_LOCATION")
		if location == "" {
			location = os.Getenv("GOOGLE_CLOUD_REGION")
		}
		if location == "" {
			panic("Vertex AI requires setting GOOGLE_CLOUD_LOCATION or GOOGLE_CLOUD_REGION in the environment. You can get a location at https://cloud.google.com/vertex-ai/docs/general/locations")
		}
	}

	// Project and Region values gets validated by genai SDK upon client
	// creation
	gc := genai.ClientConfig{
		Backend:  genai.BackendVertexAI,
		Project:  v.ProjectID,
		Location: v.Location,
		HTTPOptions: genai.HTTPOptions{
			Headers: genkitClientHeader,
		},
	}

	client, err := genai.NewClient(ctx, &gc)
	if err != nil {
		panic(fmt.Errorf("VertexAI.Init: %w", err))
	}
	v.gclient = client
	v.initted = true

	var actions []core.Action

	models, err := listModels(vertexAIProvider)
	if err != nil {
		panic(fmt.Errorf("VertexAI.Init: %w", err))
	}
	for n, mi := range models {
		model := newModel(v.gclient, n, mi)
		actions = append(actions, model.(core.Action))
	}

	embedders, err := listEmbedders(gc.Backend)
	if err != nil {
		panic(fmt.Errorf("VertexAI.Init: %w", err))
	}
	for e, eOpts := range embedders {
		embedder := newEmbedder(v.gclient, e, &eOpts)
		actions = append(actions, embedder.(core.Action))
	}

	return actions
}

// DefineModel defines an unknown model with the given name.
// The second argument describes the capability of the model.
// Use [IsDefinedModel] to determine if a model is already defined.
// After [Init] is called, only the known models are defined.
func (ga *GoogleAI) DefineModel(g *genkit.Genkit, name string, opts *ai.ModelOptions) (ai.Model, error) {
	ga.mu.Lock()
	defer ga.mu.Unlock()
	if !ga.initted {
		return nil, errors.New("GoogleAI plugin not initialized")
	}
	models, err := listModels(googleAIProvider)
	if err != nil {
		return nil, err
	}

	if opts == nil {
		var ok bool
		modelOpts, ok := models[name]
		if !ok {
			return nil, fmt.Errorf("GoogleAI.DefineModel: called with unknown model %q and nil ModelOptions", name)
		}
		opts = &modelOpts
	}

	return newModel(ga.gclient, name, *opts), nil
}

// DefineModel defines an unknown model with the given name.
// The second argument describes the capability of the model.
// Use [IsDefinedModel] to determine if a model is already defined.
// After [Init] is called, only the known models are defined.
func (v *VertexAI) DefineModel(g *genkit.Genkit, name string, opts *ai.ModelOptions) (ai.Model, error) {
	v.mu.Lock()
	defer v.mu.Unlock()
	if !v.initted {
		return nil, errors.New("VertexAI plugin not initialized")
	}
	models, err := listModels(vertexAIProvider)
	if err != nil {
		return nil, err
	}

	if opts == nil {
		var ok bool
		modelOpts, ok := models[name]
		if !ok {
			return nil, fmt.Errorf("VertexAI.DefineModel: called with unknown model %q and nil ModelOptions", name)
		}
		opts = &modelOpts
	}

	return newModel(v.gclient, name, *opts), nil
}

// DefineEmbedder defines an embedder with a given name.
func (ga *GoogleAI) DefineEmbedder(g *genkit.Genkit, name string, embedOpts *ai.EmbedderOptions) (ai.Embedder, error) {
	ga.mu.Lock()
	defer ga.mu.Unlock()
	if !ga.initted {
		return nil, errors.New("GoogleAI plugin not initialized")
	}
	return newEmbedder(ga.gclient, name, embedOpts), nil
}

// DefineEmbedder defines an embedder with a given name.
func (v *VertexAI) DefineEmbedder(g *genkit.Genkit, name string, embedOpts *ai.EmbedderOptions) (ai.Embedder, error) {
	v.mu.Lock()
	defer v.mu.Unlock()
	if !v.initted {
		return nil, errors.New("VertexAI plugin not initialized")
	}
	return newEmbedder(v.gclient, name, embedOpts), nil
}

// IsDefinedEmbedder reports whether the named [Embedder] is defined by this plugin.
func (ga *GoogleAI) IsDefinedEmbedder(g *genkit.Genkit, name string) bool {
	return genkit.LookupEmbedder(g, core.NewName(googleAIProvider, name)) != nil
}

// IsDefinedEmbedder reports whether the named [Embedder] is defined by this plugin.
func (v *VertexAI) IsDefinedEmbedder(g *genkit.Genkit, name string) bool {
	return genkit.LookupEmbedder(g, core.NewName(vertexAIProvider, name)) != nil
}

// GoogleAIModelRef creates a new ModelRef for a Google AI model with the given name and configuration.
func GoogleAIModelRef(name string, config *genai.GenerateContentConfig) ai.ModelRef {
	return ai.NewModelRef(googleAIProvider+"/"+name, config)
}

// VertexAIModelRef creates a new ModelRef for a Vertex AI model with the given name and configuration.
func VertexAIModelRef(name string, config *genai.GenerateContentConfig) ai.ModelRef {
	return ai.NewModelRef(vertexAIProvider+"/"+name, config)
}

// GoogleAIModel returns the [ai.Model] with the given name.
// It returns nil if the model was not defined.
func GoogleAIModel(g *genkit.Genkit, name string) ai.Model {
	return genkit.LookupModel(g, core.NewName(googleAIProvider, name))
}

// VertexAIModel returns the [ai.Model] with the given name.
// It returns nil if the model was not defined.
func VertexAIModel(g *genkit.Genkit, name string) ai.Model {
	return genkit.LookupModel(g, core.NewName(vertexAIProvider, name))
}

// GoogleAIEmbedder returns the [ai.Embedder] with the given name.
// It returns nil if the embedder was not defined.
func GoogleAIEmbedder(g *genkit.Genkit, name string) ai.Embedder {
	return genkit.LookupEmbedder(g, core.NewName(googleAIProvider, name))
}

// VertexAIEmbedder returns the [ai.Embedder] with the given name.
// It returns nil if the embedder was not defined.
func VertexAIEmbedder(g *genkit.Genkit, name string) ai.Embedder {
	return genkit.LookupEmbedder(g, core.NewName(vertexAIProvider, name))
}

func (ga *GoogleAI) ListActions(ctx context.Context) []core.ActionDesc {
	actions := []core.ActionDesc{}
	models, err := listGenaiModels(ctx, ga.gclient)
	if err != nil {
		return nil
	}

	for _, name := range models.gemini {
		metadata := map[string]any{
			"model": map[string]any{
				"supports": map[string]any{
					"media":       true,
					"multiturn":   true,
					"systemRole":  true,
					"tools":       true,
					"toolChoice":  true,
					"constrained": true,
				},
				"versions": []string{},
				"stage":    string(ai.ModelStageStable),
			},
		}
		metadata["label"] = fmt.Sprintf("%s - %s", googleAILabelPrefix, name)

		actions = append(actions, core.ActionDesc{
			Type:     core.ActionTypeModel,
			Name:     fmt.Sprintf("%s/%s", googleAIProvider, name),
			Key:      fmt.Sprintf("/%s/%s/%s", core.ActionTypeModel, googleAIProvider, name),
			Metadata: metadata,
		})
	}

	for _, e := range models.embedders {
		actions = append(actions, core.ActionDesc{
			Type: core.ActionTypeEmbedder,
			Name: fmt.Sprintf("%s/%s", googleAIProvider, e),
			Key:  fmt.Sprintf("/%s/%s/%s", core.ActionTypeEmbedder, googleAIProvider, e),
		})
	}

	return actions
}

func (ga *GoogleAI) ResolveAction(atype core.ActionType, name string) core.Action {
	switch atype {
	case core.ActionTypeEmbedder:
		return newEmbedder(ga.gclient, name, &ai.EmbedderOptions{}).(core.Action)
	case core.ActionTypeModel:
		var supports *ai.ModelSupports
		if strings.Contains(name, "gemini") || strings.Contains(name, "gemma") {
			supports = &Multimodal
		}

		return newModel(ga.gclient, name, ai.ModelOptions{
			Label:    fmt.Sprintf("%s - %s", googleAILabelPrefix, name),
			Stage:    ai.ModelStageStable,
			Versions: []string{},
			Supports: supports,
		}).(core.Action)
	}

	return nil
}

func (v *VertexAI) ListActions(ctx context.Context) []core.ActionDesc {
	actions := []core.ActionDesc{}
	models, err := listGenaiModels(ctx, v.gclient)
	if err != nil {
		return nil
	}

	for _, name := range models.gemini {
		metadata := map[string]any{
			"model": map[string]any{
				"supports": map[string]any{
					"media":       true,
					"multiturn":   true,
					"systemRole":  true,
					"tools":       true,
					"toolChoice":  true,
					"constrained": true,
				},
				"versions": []string{},
				"stage":    string(ai.ModelStageStable),
			},
		}
		metadata["label"] = fmt.Sprintf("%s - %s", vertexAILabelPrefix, name)
		actions = append(actions, core.ActionDesc{
			Type:     core.ActionTypeModel,
			Name:     fmt.Sprintf("%s/%s", vertexAIProvider, name),
			Key:      fmt.Sprintf("/%s/%s/%s", core.ActionTypeModel, vertexAIProvider, name),
			Metadata: metadata,
		})
	}

	for _, e := range models.embedders {
		actions = append(actions, core.ActionDesc{
			Type: core.ActionTypeEmbedder,
			Name: fmt.Sprintf("%s/%s", vertexAIProvider, e),
			Key:  fmt.Sprintf("/%s/%s/%s", core.ActionTypeEmbedder, vertexAIProvider, e),
		})
	}

	return actions
}

func (v *VertexAI) ResolveAction(atype core.ActionType, name string) core.Action {
	switch atype {
	case core.ActionTypeEmbedder:
		return newEmbedder(v.gclient, name, &ai.EmbedderOptions{}).(core.Action)
	case core.ActionTypeModel:
		var supports *ai.ModelSupports
		if strings.Contains(name, "gemini") {
			supports = &Multimodal
		}

		return newModel(v.gclient, name, ai.ModelOptions{
			Label:    fmt.Sprintf("%s - %s", vertexAILabelPrefix, name),
			Stage:    ai.ModelStageStable,
			Versions: []string{},
			Supports: supports,
		}).(core.Action)
	}
	return nil
}
