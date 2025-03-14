package openai

import (
	"context"
	"fmt"
	"os"
	"sync"

	"github.com/firebase/genkit/go/genkit"
	"github.com/openai/openai-go"
)

const provider = "openai"

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
