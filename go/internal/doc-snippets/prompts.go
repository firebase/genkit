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
	"errors"
	"fmt"
	"log"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
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
		ai.WithPrompt("You are a helpful AI assistant named Walt."))
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
	helloPrompt, err := genkit.DefinePrompt(
		g,
		"helloPrompt",
		ai.WithModel(model),
		ai.WithInputType(HelloPromptInput{}),
		ai.WithSystemFn(func(ctx context.Context, input any) (string, error) {
			params, ok := input.(HelloPromptInput)
			if !ok {
				return "", errors.New("input doesn't satisfy schema")
			}
			prompt := fmt.Sprintf(
				"You are a helpful AI assistant named Walt. Say hello to %s.",
				params.UserName)
			return prompt, nil
		}),
	)
	// [END pr03_1]

	// [START pr03_2]
	request, err := helloPrompt.Render(context.Background(), HelloPromptInput{UserName: "Fred"})
	if err != nil {
		return err
	}
	response, err := genkit.GenerateWithRequest(context.Background(), g, request, nil, nil)
	// [END pr03_2]

	_ = response
	_ = err
	return nil
}
