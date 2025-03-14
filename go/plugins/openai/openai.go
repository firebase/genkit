package openai

import (
	"context"
	"fmt"
	"os"
	"sync"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/openai/openai-go"
)

const provider = "openai"

// Supported model capabilities
var (
	gpt4Capabilities = ai.ModelInfoSupports{
		Multiturn:  true,
		Tools:      true,
		ToolChoice: true,
		SystemRole: true,
		Media:      false,
	}

	supportedModels = map[string]ai.ModelInfo{
		"gpt-4": {
			Label:    "GPT-4",
			Supports: &gpt4Capabilities,
		},
		"gpt-3.5-turbo": {
			Label:    "GPT-3.5 Turbo",
			Supports: &gpt4Capabilities,
		},
	}
)

// State management
var state struct {
	mu      sync.Mutex
	initted bool
	client  *openai.Client
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

	apiKey := cfg.APIKey
	if apiKey == "" {
		apiKey = os.Getenv("OPENAI_API_KEY")
		if apiKey == "" {
			return fmt.Errorf("OpenAI requires setting OPENAI_API_KEY in the environment or config")
		}
	}

	client := openai.NewClient(apiKey)
	state.client = client
	state.initted = true

	// Define default models
	for model, info := range supportedModels {
		DefineModel(g, model, info)
	}

	return nil
}

// DefineModel defines a model in the registry
func DefineModel(g *genkit.Genkit, name string, info ai.ModelInfo) ai.Model {
	state.mu.Lock()
	defer state.mu.Unlock()
	if !state.initted {
		panic("openai.Init not called")
	}

	return genkit.DefineModel(g, provider, name, &info, func(
		ctx context.Context,
		input *ai.ModelRequest,
		cb func(context.Context, *ai.ModelResponseChunk) error,
	) (*ai.ModelResponse, error) {
		return generate(ctx, state.client, name, input, cb)
	})
}

// Model returns the model with the given name
func Model(g *genkit.Genkit, name string) ai.Model {
	return genkit.LookupModel(g, provider, name)
}
