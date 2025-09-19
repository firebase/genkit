package main

import (
	"context"
	"log"
	"os"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/compat_oai"
	"github.com/openai/openai-go"
	"github.com/openai/openai-go/option"
)

func main() {
	apiKey := os.Getenv("OPENROUTER_API_KEY")
	if apiKey == "" {
		log.Fatalf("no OPENROUTER_API_KEY environment variable set")
	}

	opts := []option.RequestOption{
		option.WithAPIKey(apiKey),
		option.WithBaseURL("https://openrouter.ai/api/v1"),
	}

	plugin := &compat_oai.OpenAICompatible{
		Opts:     opts,
		Provider: "openrouter",
	}

	g := genkit.Init(context.Background(),
		genkit.WithPlugins(plugin),
		genkit.WithDefaultModel("openrouter/tngtech/deepseek-r1t2-chimera:free"),
	)

	prompt := "tell me a joke"
	config := &openai.ChatCompletionNewParams{
		Temperature: openai.Float(0.7),
		MaxTokens:   openai.Int(1000),
		TopP:        openai.Float(0.9),
	}

	resp, err := genkit.Generate(context.Background(), g, ai.WithConfig(config), ai.WithPrompt(prompt))
	if err != nil {
		log.Fatalf("failed generating: %v", err)
	}

	log.Println("resp: ", resp.Text())
}
