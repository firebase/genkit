// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

// Parts of this file are copied into vertexai, because the code is identical
// except for the import path of the Gemini SDK.
//go:generate go run ../../internal/cmd/copy -dest ../vertexai googleai.go

package googleai

import (
	"context"
	"fmt"
	"os"
	"sync"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/internal"
	"github.com/firebase/genkit/go/plugins/internal/gemini"
	"github.com/firebase/genkit/go/plugins/internal/uri"

	googleai "github.com/google/generative-ai-go/genai"
	"google.golang.org/api/option"
	"google.golang.org/genai"
)

const (
	provider    = "googleai"
	labelPrefix = "Google AI"
)

var state struct {
	gclient *genai.Client
	// TODO: prediction client should use the genai module but embedding support
	// is not enabled yet
	pclient *googleai.Client
	mu      sync.Mutex
	initted bool
}

var (
	supportedModels = map[string]ai.ModelInfo{
		"gemini-1.5-flash": {
			Versions: []string{
				"gemini-1.5-flash-latest",
				"gemini-1.5-flash-001",
				"gemini-1.5-flash-002",
			},
			Supports: &gemini.Multimodal,
		},
		"gemini-1.5-pro": {
			Versions: []string{
				"gemini-1.5-pro-latest",
				"gemini-1.5-pro-001",
				"gemini-1.5-pro-002",
			},
			Supports: &gemini.Multimodal,
		},
		"gemini-1.5-flash-8b": {
			Versions: []string{
				"gemini-1.5-flash-8b-latest",
				"gemini-1.5-flash-8b-001",
			},
			Supports: &gemini.Multimodal,
		},
		"gemini-2.0-flash": {
			Versions: []string{
				"gemini-2.0-flash-001",
			},
			Supports: &gemini.Multimodal,
		},
		"gemini-2.0-flash-lite": {
			Versions: []string{
				"gemini-2.0-flash-lite-001",
			},
			Supports: &gemini.Multimodal,
		},
		"gemini-2.0-pro-exp-02-05": {
			Versions: []string{},
			Supports: &gemini.Multimodal,
		},
		"gemini-2.0-flash-thinking-exp-01-21": {
			Versions: []string{},
			Supports: &gemini.Multimodal,
		},
	}

	knownEmbedders = []string{
		"text-embedding-004",
		"embedding-001",
	}
)

// Config is the configuration for the plugin.
type Config struct {
	// The API key to access the service.
	// If empty, the values of the environment variables GOOGLE_GENAI_API_KEY
	// and GOOGLE_API_KEY will be consulted, in that order.
	APIKey string
	// Options to the Google AI client.
	ClientOptions []option.ClientOption
}

// Init initializes the plugin and all known models and embedders.
// After calling Init, you may call [DefineModel] and [DefineEmbedder] to create
// and register any additional generative models and embedders
func Init(ctx context.Context, g *genkit.Genkit, cfg *Config) (err error) {
	if cfg == nil {
		cfg = &Config{}
	}
	state.mu.Lock()
	defer state.mu.Unlock()
	if state.initted {
		panic("googleai.Init already called")
	}
	defer func() {
		if err != nil {
			err = fmt.Errorf("googleai.Init: %w", err)
		}
	}()

	apiKey := cfg.APIKey
	if apiKey == "" {
		apiKey = os.Getenv("GOOGLE_GENAI_API_KEY")
		if apiKey == "" {
			apiKey = os.Getenv("GOOGLE_API_KEY")
		}
		if apiKey == "" {
			return fmt.Errorf("Google AI requires setting GOOGLE_GENAI_API_KEY or GOOGLE_API_KEY in the environment. You can get an API key at https://ai.google.dev")
		}
	}

	opts := append([]option.ClientOption{
		option.WithAPIKey(apiKey),
		googleai.WithClientInfo("genkit-go", internal.Version),
	},
		cfg.ClientOptions...,
	)

	client, err := genai.NewClient(ctx, &genai.ClientConfig{
		APIKey:  apiKey,
		Backend: genai.BackendGeminiAPI,
	})
	if err != nil {
		return err
	}

	pclient, err := googleai.NewClient(ctx, opts...)
	if err != nil {
		return err
	}

	state.gclient = client
	state.pclient = pclient
	state.initted = true
	for model, details := range supportedModels {
		defineModel(g, model, details)
	}
	for _, e := range knownEmbedders {
		defineEmbedder(g, e)
	}
	return nil
}

//copy:start vertexai.go defineModel

// DefineModel defines an unknown model with the given name.
// The second argument describes the capability of the model.
// Use [IsDefinedModel] to determine if a model is already defined.
// After [Init] is called, only the known models are defined.
func DefineModel(g *genkit.Genkit, name string, info *ai.ModelInfo) (ai.Model, error) {
	state.mu.Lock()
	defer state.mu.Unlock()
	if !state.initted {
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
	return defineModel(g, name, mi), nil
}

// requires state.mu
func defineModel(g *genkit.Genkit, name string, info ai.ModelInfo) ai.Model {
	meta := &ai.ModelInfo{
		Label:    labelPrefix + " - " + name,
		Supports: info.Supports,
		Versions: info.Versions,
	}
	return genkit.DefineModel(g, provider, name, meta, func(
		ctx context.Context,
		input *ai.ModelRequest,
		cb func(context.Context, *ai.ModelResponseChunk) error,
	) (*ai.ModelResponse, error) {
		return gemini.Generate(ctx, state.gclient, name, input, cb)
	})
}

// IsDefinedModel reports whether the named [Model] is defined by this plugin.
func IsDefinedModel(g *genkit.Genkit, name string) bool {
	return genkit.IsDefinedModel(g, provider, name)
}

//copy:stop

//copy:start vertexai.go defineEmbedder

// DefineEmbedder defines an embedder with a given name.
func DefineEmbedder(g *genkit.Genkit, name string) ai.Embedder {
	state.mu.Lock()
	defer state.mu.Unlock()
	if !state.initted {
		panic(provider + ".Init not called")
	}
	return defineEmbedder(g, name)
}

// IsDefinedEmbedder reports whether the named [Embedder] is defined by this plugin.
func IsDefinedEmbedder(g *genkit.Genkit, name string) bool {
	return genkit.IsDefinedEmbedder(g, provider, name)
}

//copy:stop

// requires state.mu
func defineEmbedder(g *genkit.Genkit, name string) ai.Embedder {
	return genkit.DefineEmbedder(g, provider, name, func(ctx context.Context, input *ai.EmbedRequest) (*ai.EmbedResponse, error) {
		em := state.pclient.EmbeddingModel(name)
		// TODO: set em.TaskType from EmbedRequest.Options?
		batch := em.NewBatch()
		for _, doc := range input.Documents {
			parts, err := convertGoogleAIParts(doc.Content)
			if err != nil {
				return nil, err
			}
			batch.AddContent(parts...)
		}
		bres, err := em.BatchEmbedContents(ctx, batch)
		if err != nil {
			return nil, err
		}
		var res ai.EmbedResponse
		for _, emb := range bres.Embeddings {
			res.Embeddings = append(res.Embeddings, &ai.DocumentEmbedding{Embedding: emb.Values})
		}
		return &res, nil
	})
}

// convertGoogleAIParts converts a slice of *ai.Part to a slice of googleai.Part.
// NOTE: to be removed once go-genai SDK supports embeddings
func convertGoogleAIParts(parts []*ai.Part) ([]googleai.Part, error) {
	res := make([]googleai.Part, 0, len(parts))
	for _, p := range parts {
		part, err := convertGoogleAIPart(p)
		if err != nil {
			return nil, err
		}
		res = append(res, part)
	}
	return res, nil
}

// convertGoogleAIPart converts *ai.Part to a googleai.Part.
// NOTE: to be removed once go-genai SDK supports embeddings
func convertGoogleAIPart(p *ai.Part) (googleai.Part, error) {
	switch {
	case p.IsText():
		return googleai.Text(p.Text), nil
	case p.IsMedia():
		contentType, data, err := uri.Data(p)
		if err != nil {
			return nil, err
		}
		return googleai.Blob{MIMEType: contentType, Data: data}, nil
	case p.IsData():
		panic(fmt.Sprintf("%s does not support Data parts", provider))
	case p.IsToolResponse():
		toolResp := p.ToolResponse
		var output map[string]any
		if m, ok := toolResp.Output.(map[string]any); ok {
			output = m
		} else {
			output = map[string]any{
				"name":    toolResp.Name,
				"content": toolResp.Output,
			}
		}
		fr := googleai.FunctionResponse{
			Name:     toolResp.Name,
			Response: output,
		}
		return fr, nil
	case p.IsToolRequest():
		toolReq := p.ToolRequest
		var input map[string]any
		if m, ok := toolReq.Input.(map[string]any); ok {
			input = m
		} else {
			input = map[string]any{
				"input": toolReq.Input,
			}
		}
		fc := googleai.FunctionCall{
			Name: toolReq.Name,
			Args: input,
		}
		return fc, nil
	default:
		panic("unknown part type in a request")
	}
}

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
