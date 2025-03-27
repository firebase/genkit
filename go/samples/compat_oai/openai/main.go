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
	"github.com/firebase/genkit/go/plugins/compat_oai/openai"
	"github.com/firebase/genkit/go/plugins/server"
	"github.com/openai/openai-go/option"
)

func main() {
	ctx := context.Background()
	g, err := genkit.Init(ctx)
	if err != nil {
		log.Fatalf("failed to create Genkit: %v", err)
	}

	apiKey := os.Getenv("OPENAI_API_KEY")
	apiKeyOption := option.WithAPIKey(apiKey)
	oai := openai.OpenAI{
		Opts: []option.RequestOption{apiKeyOption},
	}

	oai.Init(ctx, g)
	genkit.WithPlugins(&oai)

	genkit.DefineFlow(g, "basic", func(ctx context.Context, subject string) (string, error) {
		gpt4o, err := oai.DefineModel(g, "gpt-4o", ai.ModelInfo{Label: "GPT-4o", Supports: compat_oai.Multimodal.Supports})
		if err != nil {
			return "", err
		}
		prompt := fmt.Sprintf("tell me a joke about %s", subject)
		foo, err := genkit.Generate(ctx, g, ai.WithModel(gpt4o), ai.WithPromptText(prompt))
		if err != nil {
			return "", err
		}
		return fmt.Sprintf("foo: %s", foo.Text()), nil
	})

	genkit.DefineFlow(g, "defined-model", func(ctx context.Context, subject string) (string, error) {
		gpt4oMini := oai.Model(g, "gpt-4o-mini")
		if err != nil {
			return "", err
		}
		prompt := fmt.Sprintf("tell me a joke about %s", subject)
		foo, err := genkit.Generate(ctx, g, ai.WithModel(gpt4oMini), ai.WithPromptText(prompt))
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
