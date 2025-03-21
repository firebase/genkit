// Copyright 2025 Google LLC
// SPDX-License-Identifier: Apache-2.0

package google

import (
	"fmt"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/plugins/internal/gemini"
	"google.golang.org/genai"
)

const (
	gemini15Flash   = "gemini-1.5-flash"
	gemini15Pro     = "gemini-1.5-pro"
	gemini15Flash8b = "gemini-1.5-flash-8b"

	gemini20Flash                = "gemini-2.0-flash"
	gemini20FlashLite            = "gemini-2.0-flash-lite"
	gemini20FlashLitePrev        = "gemini-2.0-flash-lite-preview"
	gemini20ProExp0205           = "gemini-2.0-pro-exp-02-05"
	gemini20FlashThinkingExp0121 = "gemini-2.0-flash-thinking-exp-01-21"
)

var (
	// eventually, vertexAI and googleAI models will match, in the meantime,
	// keep them sepparated
	vertexAIModels = []string{
		gemini15Flash,
		gemini15Pro,
		gemini20Flash,
		gemini20FlashLite,
		gemini20FlashLitePrev,
		gemini20ProExp0205,
		gemini20FlashThinkingExp0121,
	}

	googleAIModels = []string{
		gemini15Flash,
		gemini15Pro,
		gemini15Flash8b,
		gemini20Flash,
		gemini20FlashLitePrev,
		gemini20ProExp0205,
		gemini20FlashThinkingExp0121,
	}

	supportedGeminiModels = map[string]ai.ModelInfo{
		gemini15Flash: {
			Label: " - " + "Gemini 1.5 Flash",
			Versions: []string{
				"gemini-1.5-flash-latest",
				"gemini-1.5-flash-001",
				"gemini-1.5-flash-002",
			},
			Supports: &gemini.Multimodal,
		},
		gemini15Pro: {
			Label: " - " + "Gemini 1.5 Pro",
			Versions: []string{
				"gemini-1.5-pro-latest",
				"gemini-1.5-pro-001",
				"gemini-1.5-pro-002",
			},
			Supports: &gemini.Multimodal,
		},
		gemini15Flash8b: {
			Label: " - " + "Gemini 1.5 Flash 8B",
			Versions: []string{
				"gemini-1.5-flash-8b-latest",
				"gemini-1.5-flash-8b-001",
			},
			Supports: &gemini.Multimodal,
		},
		gemini20Flash: {
			Label: " - " + "Gemini 2.0 Flash",
			Versions: []string{
				"gemini-2.0-flash-001",
			},
			Supports: &gemini.Multimodal,
		},
		gemini20FlashLite: {
			Label: " - " + "Gemini 2.0 Flash Lite",
			Versions: []string{
				"gemini-2.0-flash-lite-001",
			},
			Supports: &gemini.Multimodal,
		},
		gemini20FlashLitePrev: {
			Label:    " - " + "Gemini 2.0 Flash Lite Preview 02-05",
			Versions: []string{},
			Supports: &gemini.Multimodal,
		},
		gemini20ProExp0205: {
			Label:    " - " + "Gemini 2.0 Pro Exp 02-05",
			Versions: []string{},
			Supports: &gemini.Multimodal,
		},
		gemini20FlashThinkingExp0121: {
			Label:    " - " + "Gemini 2.0 Flash Thinking Exp 01-21",
			Versions: []string{},
			Supports: &gemini.Multimodal,
		},
	}

	googleAIEmbedders = []string{
		"text-embedding-004",
		"embedding-001",
	}

	vertexAIEmbedders = []string{
		"textembedding-gecko@003",
		"textembedding-gecko@002",
		"textembedding-gecko@001",
		"text-embedding-004",
		"textembedding-gecko-multilingual@001",
		"text-multilingual-embedding-002",
		"multimodalembedding",
	}
)

// getSupportedModels returns a map of supported models and their capabilities
// based on the detected backend
func getSupportedModels(backend genai.Backend) (map[string]*ai.ModelInfo, error) {
	var provider string
	names := []string{}

	switch backend {
	case genai.BackendGeminiAPI:
		provider = googleAILabelPrefix
		names = googleAIModels
	case genai.BackendVertexAI:
		provider = vertexAILabelPrefix
		names = vertexAIModels
	default:
		return nil, fmt.Errorf("unknown provider detected %s", backend)
	}

	models := make(map[string]*ai.ModelInfo, 0)
	for _, n := range names {
		m, ok := supportedGeminiModels[n]
		if !ok {
			return nil, fmt.Errorf("model %s not found for provider %s", n, provider)
		}
		models[n] = &ai.ModelInfo{
			Label:    provider + m.Label,
			Versions: m.Versions,
			Supports: m.Supports,
		}
	}
	return models, nil
}

// getSupportedEmbedders returns a list of supported embedders based on the
// detected backend
func getSupportedEmbedders(backend genai.Backend) ([]string, error) {
	embedders := []string{}

	switch backend {
	case genai.BackendGeminiAPI:
		embedders = googleAIEmbedders
	case genai.BackendVertexAI:
		embedders = vertexAIEmbedders
	default:
		return nil, fmt.Errorf("embedders for backend %s not found", backend)
	}

	return embedders, nil
}
