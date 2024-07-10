// Copyright 2024 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package snippets

import (
	"context"
	"encoding/base64"
	"fmt"
	"os"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/plugins/dotprompt"
	"github.com/firebase/genkit/go/plugins/vertexai"
)

func dot01() error {
	//!+dot01.1
	dotprompt.SetDirectory("prompts")
	prompt, err := dotprompt.Open("greeting")
	//!-dot01.1

	//!+dot01.2
	ctx := context.Background()

	// The .prompt file specifies vertexai/gemini-1.5-pro, so make sure it's set
	// up.
	// Default to the project in GCLOUD_PROJECT and the location "us-central1".
	vertexai.Init(ctx, nil)
	vertexai.DefineModel("gemini-1.5-pro", nil)

	type GreetingPromptInput struct {
		Location string `json:"location"`
		Style    string `json:"style"`
		Name     string `json:"name"`
	}
	response, err := prompt.Generate(
		ctx,
		&dotprompt.PromptRequest{
			Variables: GreetingPromptInput{
				Location: "the beach",
				Style:    "a fancy pirate",
				Name:     "Ed",
			},
		},
		nil,
	)
	if err != nil {
		return err
	}

	if responseText, err := response.Text(); err == nil {
		fmt.Println(responseText)
	}
	//!-dot01.2

	//!+dot01.3
	renderedPrompt, err := prompt.RenderText(map[string]any{
		"location": "a restaurant",
		"style":    "a pirate",
	})
	//!-dot01.3

	_ = renderedPrompt
	return nil
}

func dot02() {
	prompt, _ := dotprompt.Open("")
	type GreetingPromptInput struct {
		Location string `json:"location"`
		Style    string `json:"style"`
		Name     string `json:"name"`
	}

	//!+dot02
	// Make sure you set up the model you're using.
	vertexai.DefineModel("gemini-1.5-flash", nil)

	response, err := prompt.Generate(
		context.Background(),
		&dotprompt.PromptRequest{
			Variables: GreetingPromptInput{
				Location: "the beach",
				Style:    "a fancy pirate",
				Name:     "Ed",
			},
			Model: "vertexai/gemini-1.5-flash",
			Config: &ai.GenerationCommonConfig{
				Temperature: 1.0,
			},
		},
		nil,
	)
	//!-dot02

	_ = err
	_ = response
}

func dot03() error {
	//!+dot03
	dotprompt.SetDirectory("prompts")
	describeImagePrompt, err := dotprompt.Open("describe_image")
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
		context.Background(),
		&dotprompt.PromptRequest{Variables: DescribeImagePromptInput{
			PhotoUrl: dataURI,
		}},
		nil,
	)
	//!-dot03

	_ = response
	return nil
}

func dot04() {
	//!+dot04
	describeImagePrompt, err := dotprompt.OpenVariant("describe_image", "gemini15")
	//!-dot04
	_ = err
	_ = describeImagePrompt
}

func dot05() {
	isBetaTester := func(user string) bool {
		return true
	}
	user := "ken"

	//!+dot05
	var myPrompt *dotprompt.Prompt
	var err error
	if isBetaTester(user) {
		myPrompt, err = dotprompt.OpenVariant("describe_image", "gemini15")
	} else {
		myPrompt, err = dotprompt.Open("describe_image")
	}
	//!-dot05

	_ = err
	_ = myPrompt
}
