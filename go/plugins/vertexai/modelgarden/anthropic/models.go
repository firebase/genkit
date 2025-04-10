package anthropic

import (
	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/plugins/internal"
)

// supported anthropic models
var anthropicModels = map[string]ai.ModelInfo{
	"claude-3-5-sonnet-v2": {
		Label:    "Vertex AI Model Garden - Claude 3.5 Sonnet",
		Supports: &internal.Multimodal,
		Versions: []string{"claude-3-5-sonnet-v2@20241022"},
	},
	"claude-3-5-sonnet": {
		Label:    "Vertex AI Model Garden - Claude 3.5 Sonnet",
		Supports: &internal.Multimodal,
		Versions: []string{"claude-3-5-sonnet@20240620"},
	},
	"claude-3-sonnet": {
		Label:    "Vertex AI Model Garden - Claude 3 Sonnet",
		Supports: &internal.Multimodal,
		Versions: []string{"claude-3-sonnet@20240229"},
	},
	"claude-3-haiku": {
		Label:    "Vertex AI Model Garden - Claude 3 Haiku",
		Supports: &internal.Multimodal,
		Versions: []string{"claude-3-haiku@20240307"},
	},
	"claude-3-opus": {
		Label:    "Vertex AI Model Garden - Claude 3 Opus",
		Supports: &internal.Multimodal,
		Versions: []string{"claude-3-opus@20240229"},
	},
	"claude-3-7-sonnet": {
		Label:    "Vertex AI Model Garden - Claude 3.7 Sonnet",
		Supports: &internal.Multimodal,
		Versions: []string{"claude-3-7-sonnet@20250219"},
	},
}
