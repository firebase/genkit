// Copyright 2025 Google LLC
// SPDX-License-Identifier: Apache-2.0

package modelgarden

import (
	"sync"

	"cloud.google.com/go/vertexai/genai"
	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/plugins/internal/gemini"
)

const (
	provider    = "vertexai"
	labelPrefix = "Claude"
)

var state struct {
	gclient, pclient *genai.Client
	mu               sync.Mutex
	initted          bool
}

var supportedModels = map[string]ai.ModelInfo{
	"claude-3-5-sonnet-v2": {
		Label:    "Vertex AI Model Garden - Claude 3.5 Sonnet",
		Supports: &gemini.Multimodal,
		Versions: []string{"claude-3-5-sonnet-v2@20241022"},
	},
	"claude-3-5-sonnet": {
		Label:    "Vertex AI Model Garden - Claude 3.5 Sonnet",
		Supports: &gemini.Multimodal,
		Versions: []string{"claude-3-5-sonnet@20240620"},
	},
	"claude-3-sonnet": {
		Label:    "Vertex AI Model Garden - Claude 3 Sonnet",
		Supports: &gemini.Multimodal,
		Versions: []string{"claude-3-sonnet@20240229"},
	},
	"claude-3-haiku": {
		Label:    "Vertex AI Model Garden - Claude 3 Haiku",
		Supports: &gemini.Multimodal,
		Versions: []string{"claude-3-haiku@20240307"},
	},
	"claude-3-opus": {
		Label:    "Vertex AI Model Garden - Claude 3 Opus",
		Supports: &gemini.Multimodal,
		Versions: []string{"claude-3-opus@20240229"},
	},
}
