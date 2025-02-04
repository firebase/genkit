// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package snippets

import (
	"context"
	"log"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/ollama"
)

func ollamaEx(ctx context.Context) error {
	g, err := genkit.New(nil)
	if err != nil {
		log.Fatal(err)
	}

	// [START init]
	// Init with Ollama's default local address.
	if err := ollama.Init(ctx, &ollama.Config{
		ServerAddress: "http://127.0.0.1:11434",
	}); err != nil {
		return err
	}
	// [END init]

	// [START definemodel]
	model := ollama.DefineModel(
		g,
		ollama.ModelDefinition{
			Name: "gemma2",
			Type: "chat", // "chat" or "generate"
		},
		&ai.ModelInfoSupports{
			Multiturn:  true,
			SystemRole: true,
			Tools:      false,
			Media:      false,
		},
	)
	// [END definemodel]

	// [START gen]
	text, err := genkit.GenerateText(ctx, g,
		ai.WithModel(model),
		ai.WithTextPrompt("Tell me a joke."))
	if err != nil {
		return err
	}
	// [END gen]

	_ = text

	return nil
}
