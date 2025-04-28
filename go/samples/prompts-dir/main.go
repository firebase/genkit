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

	g, err := genkit.Init(ctx,
		genkit.WithPlugins(&googlegenai.GoogleAI{}),
		genkit.WithPromptDir("prompts"),
	)
	if err != nil {
		log.Fatal(err)
	}

	type greetingStyle struct {
		Style    string `json:"style"`
		Location string `json:"location"`
		Name     string `json:"name"`
	}

	type greeting struct {
		Greeting string `json:"greeting"`
	}

	// Define a simple flow that prompts an LLM to generate greetings using a
	// given style.
	genkit.DefineFlow(g, "assistantGreetingFlow", func(ctx context.Context, input greetingStyle) (string, error) {
		// Look up the prompt by name
		prompt := genkit.LookupPrompt(g, "example")
		if prompt == nil {
			return "", errors.New("assistantGreetingFlow: failed to find prompt")
		}

		// Execute the prompt with the provided input
		resp, err := prompt.Execute(ctx, ai.WithInput(input))
		if err != nil {
			return "", err
		}

		var output greeting
		if err = resp.Output(&output); err != nil {
			return "", err
		}

		return output.Greeting, nil
	})

	<-ctx.Done()
}

// [END main]
