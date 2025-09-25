package main

import (
	"context"
	"fmt"
	"log"
	"os"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/compat_oai/xai"
)

func main() {
	apiKey := os.Getenv("XAI_API_KEY")
	if apiKey == "" {
		log.Fatal("XAI_API_KEY not provided")
	}

	ctx := context.Background()

	// x := &xai.XAi{
	// 	Opts: []option.RequestOption{
	// 		option.WithAPIKey(apiKey),
	// 	},
	// }

	g := genkit.Init(ctx,
		genkit.WithPlugins(&xai.XAi{}),
		genkit.WithDefaultModel("xai/grok-3"),
	)

	resp, err := genkit.Generate(ctx, g, ai.WithPrompt("Tell me a fact about Firebase Genkit"))
	if err != nil {
		log.Fatalf("failed to generate response: %v", err)
	}

	fmt.Print(resp.Text())
}
