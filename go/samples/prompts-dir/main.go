// Copyright 2025 Google LLC
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
	"github.com/firebase/genkit/go/plugins/googlegenai"
)

func main() {
	ctx := context.Background()

	g, err := genkit.Init(ctx, genkit.WithPlugins(&googlegenai.GoogleAI{}))
	if err != nil {
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
