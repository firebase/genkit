// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package snippets

import (
	"context"
	"encoding/base64"
	"fmt"
	"log"
	"os"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/dotprompt"
	"github.com/firebase/genkit/go/plugins/vertexai"
)

func dot01() error {
	ctx := context.Background()
	// [START dot01_1]
	g, err := genkit.Init(ctx, genkit.WithPromptDir("prompts"))
	if err != nil {
		log.Fatal(err)
	}
	prompt, err := dotprompt.Open(g, "greeting")
	// [END dot01_1]

	// [START dot01_2]
	ctx = context.Background()

	// Default to the project in GCLOUD_PROJECT and the location "us-central1".
	vertexai.Init(ctx, g, nil)

	// The .prompt file specifies vertexai/gemini-2.0-flash, which is
	// automatically defined by Init(). However, if it specified a model that
	// isn't automatically loaded (such as a specific version), you would need
	// to define it here:
	// vertexai.DefineModel("gemini-2.0-flash", &ai.ModelCapabilities{
	// 	Multiturn:  true,
	// 	Tools:      true,
	// 	SystemRole: true,
	// 	Media:      false,
	// })

	type GreetingPromptInput struct {
		Location string `json:"location"`
		Style    string `json:"style"`
		Name     string `json:"name"`
	}
	response, err := prompt.Generate(
		ctx, g,
		dotprompt.WithInput(GreetingPromptInput{
			Location: "the beach",
			Style:    "a fancy pirate",
			Name:     "Ed",
		}),
		nil,
	)
	if err != nil {
		return err
	}

	fmt.Println(response.Text())
	// [END dot01_2]

	// [START dot01_3]
	renderedPrompt, err := prompt.RenderText(map[string]any{
		"location": "a restaurant",
		"style":    "a pirate",
	})
	// [END dot01_3]

	_ = renderedPrompt
	return nil
}

func dot02() {
	ctx := context.Background()
	g, err := genkit.Init(ctx)
	if err != nil {
		log.Fatal(err)
	}

	prompt, _ := dotprompt.Open(g, "greeting")
	type GreetingPromptInput struct {
		Location string `json:"location"`
		Style    string `json:"style"`
		Name     string `json:"name"`
	}

	// [START dot02]
	// Make sure you set up the model you're using.
	vertexai.DefineModel(g, "gemini-2.0-flash", nil)

	response, err := prompt.Generate(
		context.Background(),
		g,
		dotprompt.WithInput(GreetingPromptInput{
			Location: "the beach",
			Style:    "a fancy pirate",
			Name:     "Ed",
		}),
		dotprompt.WithModelName("vertexai/gemini-2.0-flash"),
		dotprompt.WithConfig(&ai.GenerationCommonConfig{
			Temperature: 1.0,
		}),
		nil,
	)
	// [END dot02]

	_ = err
	_ = response
}

func dot03() error {
	// [START dot03]
	ctx := context.Background()
	g, err := genkit.Init(ctx, genkit.WithPromptDir("prompts"))
	if err != nil {
		log.Fatal(err)
	}
	describeImagePrompt, err := dotprompt.Open(g, "describe_image")
	if err != nil {
		return err
	}

	imageBytes, err := os.ReadFile("img.jpg")
	if err != nil {
		return err
	}
	encodedImage := base64.StdEncoding.EncodeToString(imageBytes)
	dataURI := "data:image/jpeg;base64," + encodedImage

	type DescribeImagePromptInput struct {
		PhotoUrl string `json:"photo_url"`
	}
	response, err := describeImagePrompt.Generate(
		context.Background(), g,
		dotprompt.WithInput(DescribeImagePromptInput{
			PhotoUrl: dataURI,
		}),
		nil,
	)
	// [END dot03]

	_ = response
	return nil
}

func dot04() {
	ctx := context.Background()
	g, err := genkit.Init(ctx)
	if err != nil {
		log.Fatal(err)
	}

	// [START dot04]
	describeImagePrompt, err := dotprompt.OpenVariant(g, "describe_image", "geminipro")
	// [END dot04]
	_ = err
	_ = describeImagePrompt
}

func dot05() {
	ctx := context.Background()
	g, err := genkit.Init(ctx, genkit.WithPromptDir("prompts"))
	if err != nil {
		log.Fatal(err)
	}

	isBetaTester := func(user string) bool {
		return true
	}
	user := "ken"

	// [START dot05]
	var myPrompt *dotprompt.Prompt
	if isBetaTester(user) {
		myPrompt, err = dotprompt.OpenVariant(g, "describe_image", "geminipro")
	} else {
		myPrompt, err = dotprompt.Open(g, "describe_image")
	}
	// [END dot05]

	_ = err
	_ = myPrompt
}
