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

package main

import (
	"context"
	"fmt"
	"log"
	"strings"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/internal/registry"
)

// Input type for our prompt
type GreetingInput struct {
	Name     string `json:"name"`
	Location string `json:"location"`
	Style    string `json:"style"`
}

func main() {
	// Initialize registry
	reg, err := registry.New()
	if err != nil {
		log.Fatal(err)
	}

	// Define a custom helper that converts text to uppercase
	upperHelper := func(text string) string {
		return strings.ToUpper(text)
	}

	// Define a partial for the header
	headerPartial := "# Welcome to {{location}}"

	// Define a partial for the greeting
	greetingPartial := "Hello {{#if name}}{{upper name}}{{else}}GUEST{{/if}}!"

	// Define our prompt using genkit's DefinePrompt
	prompt, err := ai.DefinePrompt(reg, "greeting",
		// Use WithPromptText to specify the template
		ai.WithPromptText(`
{{> header}}

{{> greeting}}

{{#if style}}
I'll be speaking in the style of {{style}} today.
{{/if}}

How may I assist you?
`),
		// Specify the input type
		ai.WithInputType(GreetingInput{}),
		// Register our custom helper and partials
		ai.WithConfig(map[string]any{
			"helpers": map[string]any{
				"upper": upperHelper,
			},
			"partials": map[string]string{
				"header":   headerPartial,
				"greeting": greetingPartial,
			},
		}),
	)
	if err != nil {
		log.Fatal(err)
	}

	// Use the prompt with some input
	input := GreetingInput{
		Name:     "Alice",
		Location: "Firebase Cafe",
		Style:    "a friendly barista",
	}

	response, err := prompt.Execute(context.Background(), ai.WithInput(input))
	if err != nil {
		log.Fatal(err)
	}

	fmt.Println("Generated response:")
	fmt.Println(response.Text())
}
