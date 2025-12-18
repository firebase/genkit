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

package main

import (
	"context"
	"fmt"
	"log"
	"net/http"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/googlegenai"
	"github.com/firebase/genkit/go/plugins/server"
	"google.golang.org/genai"
)

type Joke struct {
	Joke     string `json:"joke"`
	Category string `json:"category"`
}

type RecipeRequest struct {
	Dish                string   `json:"dish"`
	Cuisine             string   `json:"cuisine,omitempty"`
	ServingSize         int      `json:"servingSize,omitempty"`
	MaxPrepMinutes      int      `json:"maxPrepMinutes,omitempty"`
	DietaryRestrictions []string `json:"dietaryRestrictions,omitempty"`
}

type Ingredient struct {
	Name     string `json:"name"`
	Amount   string `json:"amount"`
	Optional bool   `json:"optional,omitempty"`
}

type Recipe struct {
	Title        string        `json:"title"`
	Description  string        `json:"description,omitempty"`
	Ingredients  []*Ingredient `json:"ingredients"`
	Instructions []string      `json:"instructions"`
	PrepTime     string        `json:"prepTime,omitempty"`
	Difficulty   string        `json:"difficulty,omitempty" jsonschema:"enum=easy,enum=medium,enum=hard"`
}

func main() {
	ctx := context.Background()

	// Initialize Genkit with the Google AI plugin. When you pass nil for the
	// Config parameter, the Google AI plugin will get the API key from the
	// GEMINI_API_KEY or GOOGLE_API_KEY environment variable, which is the recommended
	// practice.
	g := genkit.Init(ctx, genkit.WithPlugins(&googlegenai.GoogleAI{}))

	// Define a streaming flow that generates jokes about a given topic.
	genkit.DefineStreamingFlow(g, "simpleJokesFlow",
		func(ctx context.Context, input string, sendChunk core.StreamCallback[string]) (string, error) {
			if input == "" {
				input = "airplane food"
			}

			stream := genkit.GenerateStream(ctx, g,
				ai.WithModel(googlegenai.ModelRef("gemini-2.5-flash", &genai.GenerateContentConfig{
					ThinkingConfig: &genai.ThinkingConfig{
						ThinkingBudget: genai.Ptr[int32](0),
					},
				})),
				ai.WithPrompt("Share a long joke about %s.", input),
			)

			for result, err := range stream {
				if err != nil {
					return "", fmt.Errorf("could not generate joke: %w", err)
				}
				if result.Done {
					return result.Response.Text(), nil
				} else {
					sendChunk(ctx, result.Chunk.Text())
				}
			}

			return "", nil
		},
	)

	// Define a streaming flow that generates jokes as structured output about a given topic.
	genkit.DefineStreamingFlow(g, "structuredJokesFlow",
		func(ctx context.Context, input string, sendChunk core.StreamCallback[*Joke]) (*Joke, error) {
			if input == "" {
				input = "airplane food"
			}

			stream := genkit.GenerateDataStream[*Joke](ctx, g,
				ai.WithModel(googlegenai.ModelRef("gemini-2.5-flash", &genai.GenerateContentConfig{
					ThinkingConfig: &genai.ThinkingConfig{
						ThinkingBudget: genai.Ptr[int32](0),
					},
				})),
				ai.WithPrompt("Share a long joke about %s.", input),
			)

			for result, err := range stream {
				if err != nil {
					return nil, fmt.Errorf("could not generate joke: %w", err)
				}
				if result.Done {
					return result.Output, nil
				} else {
					sendChunk(ctx, result.Chunk)
				}
			}

			return nil, nil
		})

	// Define a streaming flow that generates recipes. Streams ingredients as they're
	// identified, then returns the complete recipe with instructions.
	genkit.DefineStreamingFlow(g, "recipeFlow",
		func(ctx context.Context, input RecipeRequest, sendChunk core.StreamCallback[[]*Ingredient]) (*Recipe, error) {
			if input.Dish == "" {
				input.Dish = "pasta"
			}
			if input.Cuisine == "" {
				input.Cuisine = "Italian"
			}
			if input.ServingSize == 0 {
				input.ServingSize = 4
			}
			if input.MaxPrepMinutes == 0 {
				input.MaxPrepMinutes = 30
			}

			prompt := fmt.Sprintf(
				"Create a %s %s recipe for %d people that takes under %d minutes to prepare.",
				input.Cuisine, input.Dish, input.ServingSize, input.MaxPrepMinutes,
			)
			if len(input.DietaryRestrictions) > 0 {
				prompt += fmt.Sprintf(" Dietary restrictions: %v.", input.DietaryRestrictions)
			}

			stream := genkit.GenerateDataStream[*Recipe](ctx, g,
				ai.WithModel(googlegenai.ModelRef("gemini-2.5-flash", &genai.GenerateContentConfig{
					ThinkingConfig: &genai.ThinkingConfig{
						ThinkingBudget: genai.Ptr[int32](0),
					},
				})),
				ai.WithSystem("You are an experienced chef. Come up with easy, creative recipes."),
				ai.WithPrompt(prompt),
			)

			for result, err := range stream {
				if err != nil {
					return nil, fmt.Errorf("could not generate recipe: %w", err)
				}
				if result.Done {
					return result.Output, nil
				} else if result.Chunk != nil {
					sendChunk(ctx, result.Chunk.Ingredients)
				}
			}

			return nil, nil
		})

	// Optionally, start a web server to make the flow callable via HTTP.
	mux := http.NewServeMux()
	for _, a := range genkit.ListFlows(g) {
		mux.HandleFunc("POST /"+a.Name(), genkit.Handler(a))
	}
	log.Fatal(server.Start(ctx, "127.0.0.1:8080", mux))
}
