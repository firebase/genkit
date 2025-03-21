package openai

import (
	"context"
	"fmt"
	"os"
	"sync"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/openai/openai-go"
	"github.com/openai/openai-go/option"
)

const provider = "openai"

var (
	// support values defined from openai docs
	// https://platform.openai.com/docs/api-reference/chat
	gpt4Capabilities = ai.ModelInfoSupports{
		Multiturn:  true,
		Tools:      true,
		ToolChoice: true,
		SystemRole: true,
		Media:      false,
	}

	supportedModels = map[string]ai.ModelInfo{
		"gpt-4o-mini": {
			Label:    "GPT-4o-mini",
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

	// fetch api key
	apiKey := cfg.APIKey
	if apiKey == "" {
		apiKey = os.Getenv("OPENAI_API_KEY")
		if apiKey == "" {
			return fmt.Errorf("OpenAI requires setting OPENAI_API_KEY in the environment or config")
		}
	}

	// create client
	client := openai.NewClient(option.WithAPIKey(apiKey))
	state.client = client
	state.initted = true

	// define default models
	for model, info := range supportedModels {
		DefineModel(g, model, info)
	}

	return nil
}

// DefineModel defines a model in the registry
func DefineModel(g *genkit.Genkit, name string, info ai.ModelInfo) (ai.Model, error) {
	if !state.initted {
		panic("openai.Init not called")
	}

	if _, ok := supportedModels[name]; !ok {
		return nil, fmt.Errorf("unsupported model: %s", name)
	}

	return genkit.DefineModel(g, provider, name, &info, func(
		ctx context.Context,
		input *ai.ModelRequest,
		cb func(context.Context, *ai.ModelResponseChunk) error,
	) (*ai.ModelResponse, error) {
		generator := NewModelGenerator(state.client, name).WithMessages(input.Messages).WithConfig(input.Config)
		return generator.Generate(ctx, cb)
	}), nil
}
