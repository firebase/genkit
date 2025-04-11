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
	oai "github.com/firebase/genkit/go/plugins/compat_oai/openai"
	"github.com/firebase/genkit/go/plugins/server"
	"github.com/openai/openai-go"
	"github.com/openai/openai-go/option"
)

func main() {
	ctx := context.Background()

	oai := oai.OpenAI{
		Opts: []option.RequestOption{
			option.WithAPIKey(os.Getenv("OPENAI_API_KEY")),
		},
	}
	g, err := genkit.Init(ctx, genkit.WithPlugins(&oai))
	if err != nil {
		log.Fatalf("failed to create Genkit: %v", err)
	}

	genkit.DefineFlow(g, "basic", func(ctx context.Context, subject string) (string, error) {
		gpt4o := oai.Model(g, "gpt-4o")

		prompt := fmt.Sprintf("tell me a joke about %s", subject)
		config := &openai.ChatCompletionNewParams{Temperature: openai.F(0.5), MaxTokens: openai.F(int64(100))}
		foo, err := genkit.Generate(ctx, g, ai.WithModel(gpt4o), ai.WithPromptText(prompt), ai.WithConfig(config))
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
		config := &ai.GenerationCommonConfig{Temperature: 0.5}
		foo, err := genkit.Generate(ctx, g, ai.WithModel(gpt4oMini), ai.WithPromptText(prompt), ai.WithConfig(config))
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
