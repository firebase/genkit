// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

// This program can be manually tested like so:
// Start the server listening on port 3100:
//
//	genkit start -o -- go run .

package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/compat_oai"
	"github.com/firebase/genkit/go/plugins/server"
	"github.com/openai/openai-go/option"
)

func main() {
	ctx := context.Background()

	oai := compat_oai.OpenAICompatible{
		Opts: []option.RequestOption{
			option.WithAPIKey(os.Getenv("ANTHROPIC_API_KEY")),
			option.WithBaseURL("https://api.anthropic.com/v1/"),
		},
		Provider: "anthropic",
	}
	g, err := genkit.Init(ctx, genkit.WithPlugins(&oai))
	if err != nil {
		log.Fatalf("failed to initialize OpenAICompatible: %v", err)
	}

	genkit.DefineFlow(g, "anthropic", func(ctx context.Context, subject string) (string, error) {

		sonnet37, err := oai.DefineModel(g, "claude-3-7-sonnet-20250219", "anthropic", ai.ModelInfo{Label: "Claude Sonnet", Supports: compat_oai.Multimodal.Supports})
		if err != nil {
			return "", err
		}
		prompt := fmt.Sprintf("tell me a joke about %s", subject)
		foo, err := genkit.Generate(ctx, g, ai.WithModel(sonnet37), ai.WithPromptText(prompt))
		if err != nil {
			return "", err
		}
		return fmt.Sprintf("foo: %s", foo.Text()), nil
	})

	mux := http.NewServeMux()
	for _, a := range genkit.ListFlows(g) {
		mux.HandleFunc("POST /"+a.Name(), genkit.Handler(a))
	}
	log.Fatal(server.Start(ctx, "127.0.0.1:8080", mux))
}
