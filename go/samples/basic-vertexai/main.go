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
	"github.com/firebase/genkit/go/plugins/google"
)

func main() {
	ctx := context.Background()

	g, err := genkit.Init(ctx)
	if err != nil {
		log.Fatal(err)
	}

	// Initialize the Google plugin. When you pass VertexAI=true
	// Config parameter, the Google plugin will look for the following
	// environment variables:
	// projectId: GOOGLE_CLOUD_PROJECT
	// location: GOOGLE_CLOUD_LOCATION then GOOGLE_CLOUD_REGION
	// These parameters could also be set in the plugin configuration.
	// If that's the case, there's no need to set VertexAI flag to true
	if err := google.Init(ctx, g, &google.Config{VertexAI: true}); err != nil {
		log.Fatal(err)
	}

	// Define a simple flow that generates jokes about a given topic
	genkit.DefineFlow(g, "jokesFlow", func(ctx context.Context, input string) (string, error) {
		m := google.Model(g, "gemini-2.0-flash")
		if m == nil {
			return "", errors.New("jokesFlow: failed to find model")
		}

		resp, err := genkit.Generate(ctx, g,
			ai.WithModel(m),
			ai.WithConfig(&ai.GenerationCommonConfig{
				Temperature: 1,
				Version:     "gemini-2.0-flash-001",
			}),
			ai.WithPromptText(fmt.Sprintf(`Tell silly short jokes about %s`, input)))
		if err != nil {
			return "", err
		}

		text := resp.Text()
		return text, nil
	})

	<-ctx.Done()
}
