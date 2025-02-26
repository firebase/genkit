// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package snippets

import (
	"context"
	"errors"
	"fmt"
	"log"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/invopop/jsonschema"
)

func pr01() {
	ctx := context.Background()
	g, err := genkit.Init(ctx)
	if err != nil {
		log.Fatal(err)
	}

	model := genkit.LookupModel(g, "googleai", "gemini-1.5-flash")

	// [START pr01]
	genkit.Generate(context.Background(), g,
		ai.WithModel(model),
		ai.WithTextPrompt("You are a helpful AI assistant named Walt."))
	// [END pr01]
}

// [START hello]
func helloPrompt(name string) *ai.Part {
	prompt := fmt.Sprintf("You are a helpful AI assistant named Walt. Say hello to %s.", name)
	return ai.NewTextPart(prompt)
}

// [END hello]

func pr02() {
	ctx := context.Background()
	g, err := genkit.Init(ctx)
	if err != nil {
		log.Fatal(err)
	}

	model := genkit.LookupModel(g, "googleai", "gemini-1.5-flash")

	// [START pr02]
	response, err := genkit.GenerateText(context.Background(), g,
		ai.WithModel(model),
		ai.WithMessages(ai.NewUserMessage(helloPrompt("Fred"))))
	// [END pr02]

	if err == nil {
		_ = response
	}
}

func pr03() error {
	ctx := context.Background()
	g, err := genkit.Init(ctx)
	if err != nil {
		log.Fatal(err)
	}

	model := genkit.LookupModel(g, "googleai", "gemini-1.5-flash")

	// [START pr03_1]
	type HelloPromptInput struct {
		UserName string
	}
	helloPrompt := genkit.DefinePrompt(
		g,
		"prompts",
		"helloPrompt",
		nil, // Additional model config
		jsonschema.Reflect(&HelloPromptInput{}),
		func(ctx context.Context, input any) (*ai.ModelRequest, error) {
			params, ok := input.(HelloPromptInput)
			if !ok {
				return nil, errors.New("input doesn't satisfy schema")
			}
			prompt := fmt.Sprintf(
				"You are a helpful AI assistant named Walt. Say hello to %s.",
				params.UserName)
			return &ai.ModelRequest{Messages: []*ai.Message{
				{Content: []*ai.Part{ai.NewTextPart(prompt)}},
			}}, nil
		},
	)
	// [END pr03_1]

	// [START pr03_2]
	request, err := helloPrompt.Render(context.Background(), HelloPromptInput{UserName: "Fred"})
	if err != nil {
		return err
	}
	response, err := genkit.GenerateWithRequest(context.Background(), g, model, request, nil, nil, nil)
	// [END pr03_2]

	_ = response
	_ = err
	return nil
}
