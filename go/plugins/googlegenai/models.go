// Copyright 2025 Google LLC
// SPDX-License-Identifier: Apache-2.0

package googlegenai

import (
	"context"
	"fmt"
	"log"
	"slices"
	"strings"

	"github.com/firebase/genkit/go/ai"
	"google.golang.org/genai"
)

const (
	gemini15Flash   = "gemini-1.5-flash"
	gemini15Pro     = "gemini-1.5-pro"
	gemini15Flash8b = "gemini-1.5-flash-8b"

	gemini20Flash                = "gemini-2.0-flash"
	gemini20FlashExp             = "gemini-2.0-flash-exp"
	gemini20FlashLite            = "gemini-2.0-flash-lite"
	gemini20FlashLitePrev        = "gemini-2.0-flash-lite-preview"
	gemini20ProExp0205           = "gemini-2.0-pro-exp-02-05"
	gemini20FlashThinkingExp0121 = "gemini-2.0-flash-thinking-exp-01-21"
	gemini20FlashPrevImageGen    = "gemini-2.0-flash-preview-image-generation"

	gemini25FlashPreview0417 = "gemini-2.5-flash-preview-04-17"

	gemini25ProExp0325     = "gemini-2.5-pro-exp-03-25"
	gemini25ProPreview0325 = "gemini-2.5-pro-preview-03-25"
	gemini25ProPreview0506 = "gemini-2.5-pro-preview-05-06"

	imagen3Generate001     = "imagen-3.0-generate-001"
	imagen3Generate002     = "imagen-3.0-generate-002"
	imagen3FastGenerate001 = "imagen-3.0-fast-generate-001"
)

var (
	// eventually, Vertex AI and Google AI models will match, in the meantime,
	// keep them sepparated
	vertexAIModels = []string{
		gemini15Flash,
		gemini15Pro,
		gemini20Flash,
		gemini20FlashLite,
		gemini20FlashLitePrev,
		gemini20ProExp0205,
		gemini20FlashThinkingExp0121,
		gemini20FlashPrevImageGen,
		gemini25FlashPreview0417,
		gemini25ProExp0325,
		gemini25ProPreview0325,
		gemini25ProPreview0506,

		imagen3Generate001,
		imagen3Generate002,
		imagen3FastGenerate001,
	}

	googleAIModels = []string{
		gemini15Flash,
		gemini15Pro,
		gemini15Flash8b,
		gemini20Flash,
		gemini20FlashExp,
		gemini20FlashLitePrev,
		gemini20ProExp0205,
		gemini20FlashThinkingExp0121,
		gemini20FlashPrevImageGen,
		gemini25FlashPreview0417,
		gemini25ProExp0325,
		gemini25ProPreview0325,
		gemini25ProPreview0506,

		imagen3Generate002,
	}

	// Gemini models with native image support generation
	imageGenModels = []string{
		gemini20FlashPrevImageGen,
	}

	supportedGeminiModels = map[string]ai.ModelInfo{
		gemini15Flash: {
			Label: "Gemini 1.5 Flash",
			Versions: []string{
				"gemini-1.5-flash-latest",
				"gemini-1.5-flash-001",
				"gemini-1.5-flash-002",
			},
			Supports: &Multimodal,
			Stage:    ai.ModelStageStable,
		},
		gemini15Pro: {
			Label: "Gemini 1.5 Pro",
			Versions: []string{
				"gemini-1.5-pro-latest",
				"gemini-1.5-pro-001",
				"gemini-1.5-pro-002",
			},
			Supports: &Multimodal,
			Stage:    ai.ModelStageStable,
		},
		gemini15Flash8b: {
			Label: "Gemini 1.5 Flash 8B",
			Versions: []string{
				"gemini-1.5-flash-8b-latest",
				"gemini-1.5-flash-8b-001",
			},
			Supports: &Multimodal,
			Stage:    ai.ModelStageStable,
		},
		gemini20Flash: {
			Label: "Gemini 2.0 Flash",
			Versions: []string{
				"gemini-2.0-flash-001",
			},
			Supports: &Multimodal,
			Stage:    ai.ModelStageStable,
		},
		gemini20FlashExp: {
			Label:    "Gemini 2.0 Flash Exp",
			Versions: []string{},
			Supports: &Multimodal,
			Stage:    ai.ModelStageUnstable,
		},
		gemini20FlashLite: {
			Label: "Gemini 2.0 Flash Lite",
			Versions: []string{
				"gemini-2.0-flash-lite-001",
			},
			Supports: &Multimodal,
			Stage:    ai.ModelStageStable,
		},
		gemini20FlashLitePrev: {
			Label:    "Gemini 2.0 Flash Lite Preview 02-05",
			Versions: []string{},
			Supports: &Multimodal,
			Stage:    ai.ModelStageUnstable,
		},
		gemini20ProExp0205: {
			Label:    "Gemini 2.0 Pro Exp 02-05",
			Versions: []string{},
			Supports: &Multimodal,
			Stage:    ai.ModelStageUnstable,
		},
		gemini20FlashThinkingExp0121: {
			Label:    "Gemini 2.0 Flash Thinking Exp 01-21",
			Versions: []string{},
			Supports: &Multimodal,
			Stage:    ai.ModelStageUnstable,
		},
		gemini20FlashPrevImageGen: {
			Label:    "Gemini 2.0 Flash Preview Image Generation",
			Versions: []string{},
			Supports: &Multimodal,
			Stage:    ai.ModelStageUnstable,
		},
		gemini25FlashPreview0417: {
			Label:    "Gemini 2.5 Flash Preview 04-17",
			Versions: []string{},
			Supports: &Multimodal,
			Stage:    ai.ModelStageUnstable,
		},
		gemini25ProExp0325: {
			Label:    "Gemini 2.5 Pro Exp 03-25",
			Versions: []string{},
			Supports: &Multimodal,
			Stage:    ai.ModelStageUnstable,
		},
		gemini25ProPreview0325: {
			Label:    "Gemini 2.5 Pro Preview 03-25",
			Versions: []string{},
			Supports: &Multimodal,
			Stage:    ai.ModelStageUnstable,
		},
		gemini25ProPreview0506: {
			Label:    "Gemini 2.5 Pro Preview 05-06",
			Versions: []string{},
			Supports: &Multimodal,
			Stage:    ai.ModelStageUnstable,
		},
	}

	supportedImagenModels = map[string]ai.ModelInfo{
		imagen3Generate001: {
			Label:    "Imagen 3 Generate 001",
			Versions: []string{},
			Supports: &Media,
			Stage:    ai.ModelStageStable,
		},
		imagen3Generate002: {
			Label:    "Imagen 3 Generate 002",
			Versions: []string{},
			Supports: &Media,
			Stage:    ai.ModelStageStable,
		},
		imagen3FastGenerate001: {
			Label:    "Imagen 3 Fast Generate 001",
			Versions: []string{},
			Supports: &Media,
			Stage:    ai.ModelStageStable,
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

// listModels returns a map of supported models and their capabilities
// based on the detected backend
func listModels(provider string) (map[string]ai.ModelInfo, error) {
	var names []string
	var prefix string

	switch provider {
	case googleAIProvider:
		names = googleAIModels
		prefix = googleAILabelPrefix
	case vertexAIProvider:
		names = vertexAIModels
		prefix = vertexAILabelPrefix
	default:
		return nil, fmt.Errorf("unknown provider detected %s", provider)
	}

	models := make(map[string]ai.ModelInfo, 0)
	for _, n := range names {
		var m ai.ModelInfo
		var ok bool
		if strings.HasPrefix(n, "image") {
			m, ok = supportedImagenModels[n]
		} else {
			m, ok = supportedGeminiModels[n]
		}
		if !ok {
			return nil, fmt.Errorf("model %s not found for provider %s", n, provider)
		}
		models[n] = ai.ModelInfo{
			Label:    prefix + " - " + m.Label,
			Versions: m.Versions,
			Supports: m.Supports,
		}
	}

	return models, nil
}

// listEmbedders returns a list of supported embedders based on the
// detected backend
func listEmbedders(backend genai.Backend) ([]string, error) {
	var embedders []string

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

// genaiModels collects all the available models in go-genai SDK
// TODO: add veo models
type genaiModels struct {
	gemini    []string
	imagen    []string
	embedders []string
}

// listGenaiModels returns a list of supported models and embedders from the
// Go Genai SDK
func listGenaiModels(ctx context.Context, client *genai.Client) (genaiModels, error) {
	models := genaiModels{}
	allowedModels := []string{"gemini", "gemma"}
	allowedImagenModels := []string{"imagen"}

	for item, err := range client.Models.All(ctx) {
		var name string
		var description string
		if err != nil {
			log.Fatal(err)
		}
		if !strings.HasPrefix(item.Name, "models/") {
			continue
		}
		description = strings.ToLower(item.Description)
		if strings.Contains(description, "deprecated") {
			continue
		}

		name = strings.TrimPrefix(item.Name, "models/")
		if slices.Contains(item.SupportedActions, "embedContent") {
			models.embedders = append(models.embedders, name)
			continue
		}

		found := slices.ContainsFunc(allowedModels, func(s string) bool {
			return strings.Contains(name, s)
		})
		// filter out: Aqa, Text-bison, Chat, learnlm
		if found {
			models.gemini = append(models.gemini, name)
			continue
		}

		found = slices.ContainsFunc(allowedImagenModels, func(s string) bool {
			return strings.Contains(name, s)
		})
		// filter out: Aqa, Text-bison, Chat, learnlm
		if found {
			models.imagen = append(models.imagen, name)
			continue
		}
	}

	return models, nil
}
