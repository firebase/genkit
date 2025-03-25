// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

// [START main]
package main

import (
	"context"
	"errors"
	"log"

	// Import Genkit and the Google AI plugin
	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/googleai"
)

func main() {
	ctx := context.Background()

	g, err := genkit.Init(ctx)
	if err != nil {
		log.Fatal(err)
	}

	// Initialize the Google AI plugin. When you pass nil for the
	// Config parameter, the Google AI plugin will get the API key from the
	// GOOGLE_GENAI_API_KEY environment variable, which is the recommended
	// practice.
	if err := googleai.Init(ctx, g, nil); err != nil {
		log.Fatal(err)
	}

	// Define a simple flow that prompts an LLM to generate menu suggestions.
	genkit.DefineFlow(g, "menuSuggestionFlow", func(ctx context.Context, input any) (string, error) {

		// Look up the prompt by name
		prompt := genkit.LookupPrompt(g, "local", "example")
		if prompt == nil {
			return "", errors.New("menuSuggestionFlow: failed to find prompt")
		}

		// Execute the prompt with the provided input
		resp, err := prompt.Execute(ctx, ai.WithInput(input))
		if err != nil {
			return "", err
		}
		text := resp.Text()
		return text, nil
	})

	<-ctx.Done()
}

// [END main]
