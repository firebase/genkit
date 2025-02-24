// Copyright 2025 Google LLC
// SPDX-License-Identifier: Apache-2.0

package main

import (
	"context"
	"errors"
	"fmt"
	"log"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/vertexai/modelgarden"
	"github.com/firebase/genkit/go/plugins/vertexai/modelgarden/anthropic"
)

func main() {
	ctx := context.Background()

	g, err := genkit.New(nil)
	if err != nil {
		log.Fatal(err)
	}

	cfg := &modelgarden.Config{
		Location: "us-east5", // or us-central1
		Models:   []string{"claude-3-5-sonnet-v2", "claude-3-5-sonnet"},
	}
	if err := modelgarden.Init(ctx, g, cfg); err != nil {
		log.Fatal(err)
	}

	// Define a simple flow that generates jokes about a given topic
	genkit.DefineFlow(g, "jokesFlow", func(ctx context.Context, input string) (string, error) {
		m := modelgarden.Model(g, anthropic.ProviderName, "claude-3-5-sonnet-v2")
		if m == nil {
			return "", errors.New("jokesFlow: failed to find model")
		}

		resp, err := genkit.Generate(ctx, g,
			ai.WithModel(m),
			ai.WithConfig(&ai.GenerationCommonConfig{
				Temperature: 0.1,
				Version:     "claude-3-5-sonnet-v2@20241022",
			}),
			ai.WithTextPrompt(fmt.Sprintf(`Tell silly short jokes about %s`, input)))
		if err != nil {
			return "", err
		}

		text := resp.Text()
		return text, nil
	})

	if err := g.Start(ctx, nil); err != nil {
		log.Fatal(err)
	}
}
