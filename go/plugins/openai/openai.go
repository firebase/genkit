// Package openai provides integration with OpenAI's chat completion models.
package openai

import (
	"context"
	"fmt"
	"os"
	"sync"
	"time"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/openai/client"
)

const (
	provider = "openai"
)

// state maintains the plugin's global state
var state struct {
	mu      sync.Mutex
	initted bool
	client  *client.Client
}

// ModelCapabilities defines supported features for different models
var supportedModels = map[string]ai.ModelInfo{
	"gpt-4": {
		Versions: []string{"gpt-4-turbo-preview", "gpt-4-0125-preview"},
		Supports: &ai.ModelInfoSupports{
			Multiturn:  true,
			Tools:      true,
			SystemRole: true,
			Media:      false,
		},
	},
	"gpt-3.5-turbo": {
		Versions: []string{"gpt-3.5-turbo-0125", "gpt-3.5-turbo"},
		Supports: &ai.ModelInfoSupports{
			Multiturn:  true,
			Tools:      true,
			SystemRole: true,
			Media:      false,
		},
	},
}

// Config holds the plugin configuration options
type Config struct {
	// APIKey is the OpenAI API key. If empty, OPENAI_API_KEY environment variable is used.
	APIKey string
	// BaseURL optionally overrides the default OpenAI API endpoint
	BaseURL string
	// Timeout optionally sets a custom timeout for API requests
	Timeout time.Duration
	// OrgID optionally sets an organization ID for API requests
	OrgID string
}

// Init initializes the OpenAI plugin with the provided configuration.
// After calling Init, the supported models are automatically registered.
func Init(ctx context.Context, g *genkit.Genkit, cfg *Config) error {
	state.mu.Lock()
	defer state.mu.Unlock()

	if state.initted {
		panic("openai.Init already called")
	}

	// Get API key from config or environment
	apiKey := cfg.GetAPIKey()
	if apiKey == "" {
		return fmt.Errorf("OpenAI requires setting OPENAI_API_KEY in the environment")
	}

	// Build the client
	builder := client.NewClient(apiKey)
	if cfg != nil {
		builder.WithBaseURL(cfg.BaseURL).
			WithTimeout(cfg.Timeout).
			WithOrganization(cfg.OrgID)
	}

	c, err := builder.Build()
	if err != nil {
		return fmt.Errorf("failed to initialize OpenAI client: %w", err)
	}

	state.client = c
	state.initted = true

	// Register supported models
	for model, info := range supportedModels {
		defineModel(g, model, info)
	}

	return nil
}

// Helper methods for Config
func (c *Config) GetAPIKey() string {
	if c != nil && c.APIKey != "" {
		return c.APIKey
	}
	return os.Getenv("OPENAI_API_KEY")
}

// defineModel registers a model with the Genkit framework
func defineModel(g *genkit.Genkit, name string, info ai.ModelInfo) ai.Model {
	meta := &ai.ModelInfo{
		Label:    "OpenAI - " + name,
		Supports: info.Supports,
		Versions: info.Versions,
	}

	return genkit.DefineModel(g, provider, name, meta, generate)
}

// generate handles the chat completion request
func generate(
	ctx context.Context,
	input *ai.ModelRequest,
	cb func(context.Context, *ai.ModelResponseChunk) error,
) (*ai.ModelResponse, error) {
	if cb != nil {
		return nil, fmt.Errorf("streaming not yet implemented")
	}

	state.mu.Lock()
	c := state.client
	state.mu.Unlock()

	if c == nil {
		return nil, fmt.Errorf("openai plugin not initialized")
	}

	// Build chat request
	chat := c.NewChat(input.Model)

	// Add messages
	for _, msg := range input.Messages {
		chat.AddMessage(client.Role(msg.Role), msg.Content.String())
	}

	// Apply configuration if provided
	if cfg := input.GetConfig(); cfg != nil {
		if cfg.Temperature != 0 {
			chat.WithTemperature(cfg.Temperature)
		}
		if cfg.MaxOutputTokens != 0 {
			chat.WithMaxCompletionTokens(cfg.MaxOutputTokens)
		}
		if len(cfg.StopSequences) > 0 {
			chat.WithStop(cfg.StopSequences)
		}
		if cfg.TopP != 0 {
			chat.WithTopP(cfg.TopP)
		}
	}

	// Execute request
	resp, err := chat.Execute(ctx)
	if err != nil {
		return nil, err
	}

	// Convert to Genkit response format
	return &ai.ModelResponse{
		Candidates: []*ai.Candidate{{
			Index: 0,
			Message: &ai.Message{
				Role:    ai.RoleAssistant,
				Content: ai.TextContent(resp.Choices[0].Message.Content),
			},
		}},
		Usage: &ai.Usage{
			InputTokens:  resp.Usage.PromptTokens,
			OutputTokens: resp.Usage.CompletionTokens,
			TotalTokens:  resp.Usage.TotalTokens,
		},
	}, nil
}

// Helper functions for external use
func Model(g *genkit.Genkit, name string) ai.Model {
	return genkit.LookupModel(g, provider, name)
}

func IsDefinedModel(g *genkit.Genkit, name string) bool {
	return genkit.IsDefinedModel(g, provider, name)
}
