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

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	oai_deepseek "github.com/firebase/genkit/go/plugins/compat_oai/deepseek"
	"github.com/firebase/genkit/go/plugins/server"
	"github.com/openai/openai-go"
)

func main() {
	ctx := context.Background()

	// DEEPSEEK_API_KEY and DEEPSEEK_BASE_URL environment values will be read automatically unless
	// they are provided via `option.RequestOption{}`
	ds := oai_deepseek.DeepSeek{}

	g := genkit.Init(ctx, genkit.WithPlugins(&ds))

	genkit.DefineFlow(g, "basic", func(ctx context.Context, subject string) (string, error) {
		dsChat := ds.Model(g, "deepseek-chat")

		prompt := fmt.Sprintf("tell me a short story joke about %s", subject)
		config := &openai.ChatCompletionNewParams{Temperature: openai.Float(0.5)}
		resp, err := genkit.Generate(ctx,
			g,
			ai.WithModel(dsChat),
			ai.WithPrompt(prompt),
			ai.WithConfig(config))
		if err != nil {
			return "", err
		}
		return resp.Text(), nil
	})

	mux := http.NewServeMux()
	for _, a := range genkit.ListFlows(g) {
		mux.HandleFunc("POST /"+a.Name(), genkit.Handler(a))
	}
	log.Fatal(server.Start(ctx, "127.0.0.1:8080", mux))
}
