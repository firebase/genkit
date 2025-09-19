package main

import (
	"context"
	"log"
	"os"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"

	oai "github.com/firebase/genkit/go/plugins/compat_oai"
	"github.com/openai/openai-go"
)

func main() {
	ctx := context.Background()
	apiKey := os.Getenv("OPENROUTER_API_KEY")
	if apiKey == "" {
		log.Fatalf("OPENROUTER_API_KEY environment variable not set")
	}

	g := genkit.Init(ctx, genkit.WithPlugins(&oai.OpenAICompatible{
		Provider: "openrouter",
		APIKey:   apiKey,
		BaseURL:  "https://openrouter.ai/api/v1",
	}),
		genkit.WithDefaultModel("openrouter/tngtech/deepseek-r1t2-chimera:free"))

	prompt := "tell me a joke"
	config := &openai.ChatCompletionNewParams{
		Temperature: openai.Float(0.7),
		MaxTokens:   openai.Int(1000),
		TopP:        openai.Float(0.9),
	}

	resp, err := genkit.Generate(context.Background(), g,
		ai.WithConfig(config),
		ai.WithPrompt(prompt))
	if err != nil {
		log.Fatalf("failed generating: %v", err)
	}

	log.Println("Joke:", resp.Text())
}
