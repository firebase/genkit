// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package snippets

import (
	"context"
	"encoding/base64"
	"fmt"
	"log"
	"os"

	// [START import]
	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/vertexai"
	// [END import]
)

// Globals for simplification only.
// Bad style: don't do this.
var ctx = context.Background()
var gemini15pro ai.Model

func m1() error {
	ctx := context.Background()
	g, err := genkit.Init(ctx)
	if err != nil {
		log.Fatal(err)
	}

	// [START init]
	// Default to the value of GCLOUD_PROJECT for the project,
	// and "us-central1" for the location.
	// To specify these values directly, pass a vertexai.Config value to Init.
	if err := vertexai.Init(ctx, g, nil); err != nil {
		return err
	}
	// [END init]

	// [START model]
	model := vertexai.Model(g, "gemini-1.5-flash")
	// [END model]

	// [START call]
	responseText, err := genkit.GenerateText(ctx, g, ai.WithModel(model), ai.WithTextPrompt("Tell me a joke."))
	if err != nil {
		return err
	}
	fmt.Println(responseText)
	// [END call]
	return nil
}

func opts() error {
	ctx := context.Background()
	g, err := genkit.Init(ctx)
	if err != nil {
		log.Fatal(err)
	}
	model := vertexai.Model(g, "gemini-1.5-flash")

	// [START options]
	response, err := genkit.Generate(ctx, g,
		ai.WithModel(model),
		ai.WithTextPrompt("Tell me a joke about dogs."),
		ai.WithConfig(ai.GenerationCommonConfig{
			Temperature:     1.67,
			StopSequences:   []string{"cat"},
			MaxOutputTokens: 3,
		}))
	// [END options]

	_ = response
	if err != nil {
		log.Fatal(err)
	}
	return nil
}

func streaming() error {
	ctx := context.Background()
	g, err := genkit.Init(ctx)
	if err != nil {
		log.Fatal(err)
	}
	// [START streaming]
	response, err := genkit.Generate(ctx, g,
		ai.WithModel(gemini15pro),
		ai.WithTextPrompt("Tell a long story about robots and ninjas."),
		// stream callback
		ai.WithStreaming(
			func(ctx context.Context, grc *ai.ModelResponseChunk) error {
				fmt.Printf("Chunk: %s\n", grc.Text())
				return nil
			}))
	if err != nil {
		return err
	}

	// You can also still get the full response.
	fmt.Println(response.Text())

	// [END streaming]
	return nil
}

func multi() error {
	ctx := context.Background()
	g, err := genkit.Init(ctx)
	if err != nil {
		log.Fatal(err)
	}

	// [START multimodal]
	imageBytes, err := os.ReadFile("img.jpg")
	if err != nil {
		return err
	}
	encodedImage := base64.StdEncoding.EncodeToString(imageBytes)

	resp, err := genkit.Generate(ctx, g,
		ai.WithModel(gemini15pro),
		ai.WithMessages(
			ai.NewUserMessage(
				ai.NewTextPart("Describe the following image."),
				ai.NewMediaPart("", "data:image/jpeg;base64,"+encodedImage))))
	// [END multimodal]
	if err != nil {
		return err
	}
	_ = resp
	return nil
}

func tools() error {
	ctx := context.Background()
	g, err := genkit.Init(ctx)
	if err != nil {
		log.Fatal(err)
	}
	// [START tools]
	myJokeTool := genkit.DefineTool(
		g,
		"myJoke",
		"useful when you need a joke to tell",
		func(ctx *ai.ToolContext, input *any) (string, error) {
			return "haha Just kidding no joke! got you", nil
		},
	)

	response, err := genkit.Generate(ctx, g,
		ai.WithModel(gemini15pro),
		ai.WithTextPrompt("Tell me a joke."),
		ai.WithTools(myJokeTool))
	// [END tools]
	_ = response
	return err
}

func history() error {
	ctx := context.Background()
	g, err := genkit.Init(ctx)
	if err != nil {
		log.Fatal(err)
	}
	var prompt string
	// [START hist1]
	history := []*ai.Message{{
		Content: []*ai.Part{ai.NewTextPart(prompt)},
		Role:    ai.RoleUser,
	}}

	response, err := genkit.Generate(ctx, g,
		ai.WithModel(gemini15pro),
		ai.WithMessages(history...))
	// [END hist1]
	_ = err
	// [START hist2]
	history = append(history, response.Message)
	// [END hist2]

	// [START hist3]
	history = append(history, &ai.Message{
		Content: []*ai.Part{ai.NewTextPart(prompt)},
		Role:    ai.RoleUser,
	})

	response, err = genkit.Generate(ctx, g,
		ai.WithModel(gemini15pro),
		ai.WithMessages(history...))
	// [END hist3]
	// [START hist4]
	history = []*ai.Message{{
		Content: []*ai.Part{ai.NewTextPart("Talk like a pirate.")},
		Role:    ai.RoleSystem,
	}}
	// [END hist4]
	return nil
}
