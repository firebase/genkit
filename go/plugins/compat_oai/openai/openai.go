package openai

import (
	"context"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/compat_oai"
	openaiGo "github.com/openai/openai-go"
	"github.com/openai/openai-go/option"
)

var provider = "openai"

var (
	supportedModels = map[string]ai.ModelInfo{
		openaiGo.ChatModelGPT4oMini: {
			Label:    "GPT-4o-mini",
			Supports: &compat_oai.Multimodal,
		},
	}

	knownEmbedders = []string{
		openaiGo.EmbeddingModelTextEmbedding3Small,
		openaiGo.EmbeddingModelTextEmbedding3Large,
		openaiGo.EmbeddingModelTextEmbeddingAda002,
	}
)

func OpenAI(ctx context.Context, g *genkit.Genkit, opts ...option.RequestOption) error {
	err := compat_oai.OpenAICompatible(ctx, g, provider, opts...)
	if err != nil {
		panic(err)
	}

	// define default models
	for model, info := range supportedModels {
		DefineModel(g, model, info)
	}

	// define default embedders
	for _, embedder := range knownEmbedders {
		DefineEmbedder(g, embedder)
	}

	return nil
}

func Model(g *genkit.Genkit, name string) ai.Model {
	return compat_oai.Model(g, name, provider)
}

func DefineModel(g *genkit.Genkit, name string, info ai.ModelInfo) (ai.Model, error) {
	return compat_oai.DefineModel(g, name, info, provider)
}

func DefineEmbedder(g *genkit.Genkit, name string) (ai.Embedder, error) {
	return compat_oai.DefineEmbedder(g, name, provider)
}

func Embedder(g *genkit.Genkit, name string) ai.Embedder {
	return compat_oai.Embedder(g, name, provider)
}
