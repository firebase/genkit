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
	g, err := genkit.Init(ctx)
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
	name := "gemma2"
	model := ollama.DefineModel(
		g,
		ollama.ModelDefinition{
			Name: name,
			Type: "chat", // "chat" or "generate"
		},
		&ai.ModelInfo{
			Label: name,
			Supports: &ai.ModelInfoSupports{
				Multiturn:  true,
				SystemRole: true,
				Tools:      false,
				Media:      false,
			},
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
