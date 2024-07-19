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
	// [START dot01_1]
	dotprompt.SetDirectory("prompts")
	prompt, err := dotprompt.Open("greeting")
	// [END dot01_1]

	// [START dot01_2]
	ctx := context.Background()

	// Default to the project in GCLOUD_PROJECT and the location "us-central1".
	vertexai.Init(ctx, nil)

	// The .prompt file specifies vertexai/gemini-1.5-flash, which is
	// automatically defined by Init(). However, if it specified a model that
	// isn't automatically loaded (such as a specific version), you would need
	// to define it here:
	// vertexai.DefineModel("gemini-1.0-pro-002", &ai.ModelCapabilities{
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
	prompt, _ := dotprompt.Open("")
	type GreetingPromptInput struct {
		Location string `json:"location"`
		Style    string `json:"style"`
		Name     string `json:"name"`
	}

	// [START dot02]
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
	// [END dot02]

	_ = err
	_ = response
}

func dot03() error {
	// [START dot03]
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
	// [END dot03]

	_ = response
	return nil
}

func dot04() {
	// [START dot04]
	describeImagePrompt, err := dotprompt.OpenVariant("describe_image", "geminipro")
	// [END dot04]
	_ = err
	_ = describeImagePrompt
}

func dot05() {
	isBetaTester := func(user string) bool {
		return true
	}
	user := "ken"

	// [START dot05]
	var myPrompt *dotprompt.Prompt
	var err error
	if isBetaTester(user) {
		myPrompt, err = dotprompt.OpenVariant("describe_image", "geminipro")
	} else {
		myPrompt, err = dotprompt.Open("describe_image")
	}
	// [END dot05]

	_ = err
	_ = myPrompt
}
