// Copyright 2025 Google LLC
// SPDX-License-Identifier: Apache-2.0

// This sample demonstrates how to use embedded prompts with genkit.
// Prompts are embedded directly into the binary using Go's embed package,
// which allows you to ship a self-contained binary without needing to
// distribute prompt files separately.

// [START main]
package main

import (
	"context"
	"embed"
	"errors"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/googlegenai"
)

// Embed the prompts directory into the binary.
// The //go:embed directive makes the prompts available at compile time.
//
//go:embed prompts/*
var promptsFS embed.FS

func main() {
	ctx := context.Background()

	g := genkit.Init(ctx,
		genkit.WithPlugins(&googlegenai.GoogleAI{}),
		genkit.WithPromptFS(promptsFS, "prompts"),
	)

	type greetingStyle struct {
		Style    string `json:"style"`
		Location string `json:"location"`
		Name     string `json:"name"`
	}

	type greeting struct {
		Greeting string `json:"greeting"`
	}

	genkit.DefineFlow(g, "assistantGreetingFlow", func(ctx context.Context, input greetingStyle) (string, error) {
		prompt := genkit.LookupPrompt(g, "example")
		if prompt == nil {
			return "", errors.New("assistantGreetingFlow: failed to find prompt")
		}

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
