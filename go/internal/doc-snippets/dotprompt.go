// Copyright 2025 Google LLC
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
//
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
	"github.com/firebase/genkit/go/plugins/googlegenai"
)

func dot01() error {
	ctx := context.Background()
	// [START dot01_1]
	g, err := genkit.Init(ctx, genkit.WithPromptDir("prompts"))
	if err != nil {
		log.Fatal(err)
	}
	prompt := genkit.LookupPrompt(g, "greeting")
	// [END dot01_1]

	// [START dot01_2]
	ctx = context.Background()

	// Default to the project in GCLOUD_PROJECT and the location "us-central1".
	(&googlegenai.VertexAI{}).Init(ctx, g)

	// The .prompt file specifies vertexai/gemini-2.0-flash, which is
	// automatically defined by Init(). However, if it specified a model that
	// isn't automatically loaded (such as a specific version), you would need
	// to define it here:
	// googlegenai.DefineModel("gemini-2.0-flash", &ai.ModelCapabilities{
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
	response, err := prompt.Execute(
		ctx,
		ai.WithInput(GreetingPromptInput{
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
	// [END dot01_3]

	return nil
}

func dot02() {
	ctx := context.Background()
	g, err := genkit.Init(ctx)
	if err != nil {
		log.Fatal(err)
	}

	prompt := genkit.LookupPrompt(g, "greeting")
	type GreetingPromptInput struct {
		Location string `json:"location"`
		Style    string `json:"style"`
		Name     string `json:"name"`
	}

	// [START dot02]
	// Make sure you set up the model you're using.
	googlegenai.VertexAIModel(g, "gemini-2.0-flash")

	response, err := prompt.Execute(
		context.Background(),
		ai.WithInput(GreetingPromptInput{
			Location: "the beach",
			Style:    "a fancy pirate",
			Name:     "Ed",
		}),
		ai.WithModelName("googlegenai/gemini-2.0-flash"),
		ai.WithConfig(&ai.GenerationCommonConfig{
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
	describeImagePrompt := genkit.LookupPrompt(g, "describe_image")
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
	response, err := describeImagePrompt.Execute(
		context.Background(),
		ai.WithInput(DescribeImagePromptInput{
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
	describeImagePrompt := genkit.LookupPrompt(g, "describe_image")
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

	// [START dot05]
	// [END dot05]

	_ = err
	_ = g
}
