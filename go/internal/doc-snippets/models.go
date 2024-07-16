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

	// [START import]
	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/plugins/vertexai"
	// [END import]
)

// Globals for simplification only.
// Bad style: don't do this.
var ctx = context.Background()
var gemini15pro *ai.Model

func m1() error {
	// [START init]
	// Default to the value of GCLOUD_PROJECT for the project,
	// and "us-central1" for the location.
	// To specify these values directly, pass a vertexai.Config value to Init.
	if err := vertexai.Init(ctx, nil); err != nil {
		return err
	}
	// [END init]

	// [START model]
	gemini15pro := vertexai.Model("gemini-1.5-pro")
	// [END model]

	// [START call]
	request := ai.GenerateRequest{Messages: []*ai.Message{
		{Content: []*ai.Part{ai.NewTextPart("Tell me a joke.")}},
	}}
	response, err := gemini15pro.Generate(ctx, &request, nil)
	if err != nil {
		return err
	}

	responseText, err := response.Text()
	if err != nil {
		return err
	}
	fmt.Println(responseText)
	// [END call]
	return nil
}

func opts() error {
	// [START options]
	request := ai.GenerateRequest{
		Messages: []*ai.Message{
			{Content: []*ai.Part{ai.NewTextPart("Tell me a joke about dogs.")}},
		},
		Config: ai.GenerationCommonConfig{
			Temperature:     1.67,
			StopSequences:   []string{"abc"},
			MaxOutputTokens: 3,
		},
	}
	// [END options]
	_ = request
	return nil
}

func streaming() error {
	// [START streaming]
	request := ai.GenerateRequest{Messages: []*ai.Message{
		{Content: []*ai.Part{ai.NewTextPart("Tell a long story about robots and ninjas.")}},
	}}
	response, err := gemini15pro.Generate(
		ctx,
		&request,
		func(ctx context.Context, grc *ai.GenerateResponseChunk) error {
			text, err := grc.Text()
			if err != nil {
				return err
			}
			fmt.Printf("Chunk: %s\n", text)
			return nil
		})
	if err != nil {
		return err
	}

	// You can also still get the full response.
	responseText, err := response.Text()
	if err != nil {
		return err
	}
	fmt.Println(responseText)

	// [END streaming]
	return nil
}

func multi() error {
	// [START multimodal]
	imageBytes, err := os.ReadFile("img.jpg")
	if err != nil {
		return err
	}
	encodedImage := base64.StdEncoding.EncodeToString(imageBytes)

	request := ai.GenerateRequest{Messages: []*ai.Message{
		{Content: []*ai.Part{
			ai.NewTextPart("Describe the following image."),
			ai.NewMediaPart("", "data:image/jpeg;base64,"+encodedImage),
		}},
	}}
	gemini15pro.Generate(ctx, &request, nil)
	// [END multimodal]
	return nil
}

func tools() error {
	// [START tools]
	myJoke := &ai.ToolDefinition{
		Name:        "myJoke",
		Description: "useful when you need a joke to tell",
		InputSchema: make(map[string]any),
		OutputSchema: map[string]any{
			"joke": "string",
		},
	}
	ai.DefineTool(
		myJoke,
		nil,
		func(ctx context.Context, input map[string]any) (map[string]any, error) {
			return map[string]any{"joke": "haha Just kidding no joke! got you"}, nil
		},
	)

	request := ai.GenerateRequest{
		Messages: []*ai.Message{
			{Content: []*ai.Part{ai.NewTextPart("Tell me a joke.")},
				Role: ai.RoleUser},
		},
		Tools: []*ai.ToolDefinition{myJoke},
	}
	response, err := gemini15pro.Generate(ctx, &request, nil)
	// [END tools]
	_ = response
	return err
}

func history() error {
	var prompt string
	// [START hist1]
	history := []*ai.Message{{
		Content: []*ai.Part{ai.NewTextPart(prompt)},
		Role:    ai.RoleUser,
	}}

	request := ai.GenerateRequest{Messages: history}
	response, err := gemini15pro.Generate(context.Background(), &request, nil)
	// [END hist1]
	_ = err
	// [START hist2]
	history = append(history, response.Candidates[0].Message)
	// [END hist2]

	// [START hist3]
	history = append(history, &ai.Message{
		Content: []*ai.Part{ai.NewTextPart(prompt)},
		Role:    ai.RoleUser,
	})

	request = ai.GenerateRequest{Messages: history}
	response, err = gemini15pro.Generate(ctx, &request, nil)
	// [END hist3]
	// [START hist4]
	history = []*ai.Message{{
		Content: []*ai.Part{ai.NewTextPart("Talk like a pirate.")},
		Role:    ai.RoleSystem,
	}}
	// [END hist4]
	return nil
}
