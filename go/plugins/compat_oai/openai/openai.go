package openai

import (
	"context"
	"fmt"
	"os"
	"slices"
	"strings"
	"sync"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	openaiGo "github.com/openai/openai-go"
	"github.com/openai/openai-go/option"
)

const provider = "openai"

var (
	// BasicText describes model capabilities for text-only GPT models.
	BasicText = ai.ModelInfoSupports{
		Multiturn:  true,
		Tools:      true,
		SystemRole: true,
		Media:      false,
	}

	//  Multimodal describes model capabilities for multimodal GPT models.
	Multimodal = ai.ModelInfoSupports{
		Multiturn:  true,
		Tools:      true,
		SystemRole: true,
		Media:      true,
	}

	supportedModels = map[string]ai.ModelInfo{
		openaiGo.ChatModelGPT4oMini: {
			Label:    "GPT-4o-mini",
			Supports: &Multimodal,
		},
	}

	knownEmbedders = []string{
		openaiGo.EmbeddingModelTextEmbedding3Small,
		openaiGo.EmbeddingModelTextEmbedding3Large,
		openaiGo.EmbeddingModelTextEmbeddingAda002,
	}
)

// State management
var state struct {
	mu      sync.Mutex
	initted bool
	client  *openaiGo.Client
}

type Config struct {
	// The API key to access OpenAI services.
	// If empty, the value of OPENAI_API_KEY environment variable will be used
	APIKey string
}

func Init(ctx context.Context, g *genkit.Genkit, cfg *Config) error {
	if cfg == nil {
		cfg = &Config{}
	}

	state.mu.Lock()
	defer state.mu.Unlock()
	if state.initted {
		panic("openai.Init already called")
	}

	// fetch api key
	apiKey := cfg.APIKey
	if apiKey == "" {
		apiKey = os.Getenv("OPENAI_API_KEY")
		if apiKey == "" {
			return fmt.Errorf("OpenAI requires setting OPENAI_API_KEY in the environment or config")
		}
	}

	// create client
	client := openaiGo.NewClient(option.WithAPIKey(apiKey))
	state.client = client
	state.initted = true

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

// DefineModel defines a model in the registry
func DefineModel(g *genkit.Genkit, name string, info ai.ModelInfo) (ai.Model, error) {
	if !state.initted {
		panic("openai.Init not called")
	}

	// Strip provider prefix if present to check against supportedModels
	modelName := strings.TrimPrefix(name, provider+"/")

	if _, ok := supportedModels[modelName]; !ok {
		return nil, fmt.Errorf("unsupported model: %s", modelName)
	}

	return genkit.DefineModel(g, provider, name, &info, func(
		ctx context.Context,
		input *ai.ModelRequest,
		cb func(context.Context, *ai.ModelResponseChunk) error,
	) (*ai.ModelResponse, error) {
		generator := NewModelGenerator(state.client, modelName)

		// Configure the generator with input
		if input.Messages != nil {
			generator.WithMessages(input.Messages)
		}
		if input.Config != nil {
			generator.WithConfig(input.Config)
		}

		// Generate response
		resp, err := generator.Generate(ctx, cb)
		if err != nil {
			return nil, err
		}

		// Ensure response has required fields
		if resp == nil {
			resp = &ai.ModelResponse{}
		}
		if resp.Message == nil {
			resp.Message = &ai.Message{
				Role: ai.RoleModel,
			}
		}
		if resp.Usage == nil {
			resp.Usage = &ai.GenerationUsage{}
		}

		return resp, nil
	}), nil
}

// DefineEmbedder defines an embedder with a given name.
func DefineEmbedder(g *genkit.Genkit, name string) (ai.Embedder, error) {
	if !state.initted {
		panic("openai.Init not called")
	}

	if !slices.Contains(knownEmbedders, name) {
		return nil, fmt.Errorf("unsupported embedder: %s", name)
	}

	return genkit.DefineEmbedder(g, provider, name, func(ctx context.Context, input *ai.EmbedRequest) (*ai.EmbedResponse, error) {
		var data openaiGo.EmbeddingNewParamsInputArrayOfStrings
		for _, doc := range input.Documents {
			for _, p := range doc.Content {
				data = append(data, p.Text)
			}
		}

		params := openaiGo.EmbeddingNewParams{
			Input:          openaiGo.F[openaiGo.EmbeddingNewParamsInputUnion](data),
			Model:          openaiGo.F(name),
			EncodingFormat: openaiGo.F(openaiGo.EmbeddingNewParamsEncodingFormatFloat),
		}

		embeddingResp, err := state.client.Embeddings.New(ctx, params)
		if err != nil {
			return nil, err
		}

		resp := &ai.EmbedResponse{}
		for _, emb := range embeddingResp.Data {
			embedding := make([]float32, len(emb.Embedding))
			for i, val := range emb.Embedding {
				embedding[i] = float32(val)
			}
			resp.Embeddings = append(resp.Embeddings, &ai.DocumentEmbedding{Embedding: embedding})
		}
		return resp, nil
	}), nil
}

// IsDefinedEmbedder reports whether the named [Embedder] is defined by this plugin.
func IsDefinedEmbedder(g *genkit.Genkit, name string) bool {
	return genkit.IsDefinedEmbedder(g, provider, name)
}

// Embedder returns the [ai.Embedder] with the given name.
// It returns nil if the embedder was not defined.
func Embedder(g *genkit.Genkit, name string) ai.Embedder {
	return genkit.LookupEmbedder(g, provider, name)
}
