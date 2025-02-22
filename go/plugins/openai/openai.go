package openai

import (
	"context"
	"fmt"
	"os"
	"sync"
)

const provider = "openai"

var state struct {
	mu      sync.Mutex
	initted bool
	apiKey  string
	baseURL string
}

type Config struct {
	// the API key to access OpenAI services
	APIKey string
	// Optional base URL override (for Azure OpenAI etc)
	BaseURL string
}

func Init(ctx context.Context, cfg *Config) error {
	state.mu.Lock()
	defer state.mu.Unlock()
	if state.initted {
		panic("openai.Init already called")
	}

	if cfg == nil {
		cfg = &Config{}
	}

	apiKey := cfg.APIKey
	if apiKey == "" {
		apiKey = os.Getenv("OPENAI_API_KEY")
		if apiKey == "" {
			return fmt.Errorf("OpenAI requires setting OPENAI_API_KEY in the environment")
		}
	}

	state.apiKey = apiKey
	state.baseURL = cfg.BaseURL
	if state.baseURL == "" {
		state.baseURL = "https://api.openai.com/v1"
	}
	state.initted = true

	// Define known models
	for model, info := range supportedModels {
		defineModel(g, model, info)
	}

	return nil
}
