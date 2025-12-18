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

type JokeRequest struct {
	Topic string `json:"topic"`
}

type Joke struct {
	Joke     string `json:"joke"`
	Category string `json:"category"`
}

type RecipeRequest struct {
	Dish                string   `json:"dish"`
	Cuisine             string   `json:"cuisine"`
	ServingSize         int      `json:"servingSize"`
	MaxPrepMinutes      int      `json:"maxPrepMinutes"`
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
	PrepTime     string        `json:"prepTime"`
	Difficulty   string        `json:"difficulty" jsonschema:"enum=easy,enum=medium,enum=hard"`
}

func main() {
	ctx := context.Background()

	// Initialize Genkit with the Google AI plugin. When you pass nil for the
	// Config parameter, the Google AI plugin will get the API key from the
	// GEMINI_API_KEY or GOOGLE_API_KEY environment variable, which is the recommended
	// practice.
	g := genkit.Init(ctx, genkit.WithPlugins(&googlegenai.GoogleAI{}))

	// Define schemas for the expected output types so that the .prompt files can reference them.
	// Alternatively, you can specify the JSON schema directly in the .prompt file.
	// Code-defined prompts do not need to have schemas defined in advance.
	genkit.DefineSchemaFor[JokeRequest](g)
	genkit.DefineSchemaFor[Joke](g)
	genkit.DefineSchemaFor[RecipeRequest](g)
	genkit.DefineSchemaFor[Recipe](g)

	// Define the prompts and flows.
	SimpleJokeWithDefinePrompt(ctx, g)
	SimpleJokeWithDotprompt(ctx, g)
	StructuredJokeWithDefineDataPrompt(ctx, g)
	StructuredJokeWithDotprompt(ctx, g)
	RecipeWithDefineDataPrompt(ctx, g)
	RecipeWithDotprompt(ctx, g)

	// Optionally, start a web server to make the flow callable via HTTP.
	mux := http.NewServeMux()
	for _, a := range genkit.ListFlows(g) {
		mux.HandleFunc("POST /"+a.Name(), genkit.Handler(a))
	}
	log.Fatal(server.Start(ctx, "127.0.0.1:8080", mux))
}

// SimpleJokeWithDefinePrompt demonstrates defining a prompt in code using DefinePrompt
// with typed input via WithInputType. The prompt template uses Handlebars syntax to
// interpolate the input fields. Returns unstructured text output via streaming.
func SimpleJokeWithDefinePrompt(ctx context.Context, g *genkit.Genkit) {
	jokePrompt := genkit.DefinePrompt(
		g, "joke.code",
		ai.WithModel(googlegenai.ModelRef("gemini-2.5-flash", &genai.GenerateContentConfig{
			ThinkingConfig: &genai.ThinkingConfig{
				ThinkingBudget: genai.Ptr[int32](0),
			},
		})),
		ai.WithInputType(JokeRequest{Topic: "airplane food"}),
		ai.WithPrompt("Share a long joke about {{topic}}."),
	)

	genkit.DefineStreamingFlow(g, "simpleJokePromptFlow",
		func(ctx context.Context, topic string, sendChunk core.StreamCallback[string]) (string, error) {
			if topic == "" {
				topic = "airplane food"
			}
			stream := jokePrompt.ExecuteStream(ctx, ai.WithInput(map[string]any{"topic": topic}))
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
}

// SimpleJokeWithDotprompt demonstrates loading a prompt from a .prompt file using
// LoadPrompt. The prompt configuration (model, input schema, defaults) is defined in the
// file. Input is passed as a map since the .prompt file defines its own schema.
func SimpleJokeWithDotprompt(ctx context.Context, g *genkit.Genkit) {
	genkit.DefineStreamingFlow(g, "simpleJokeDotpromptFlow",
		func(ctx context.Context, topic string, sendChunk core.StreamCallback[string]) (string, error) {
			if topic == "" {
				topic = "airplane food"
			}
			jokePrompt := genkit.LookupPrompt(g, "joke")
			stream := jokePrompt.ExecuteStream(ctx, ai.WithInput(map[string]any{"topic": topic}))
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
}

// StructuredJokeWithDefineDataPrompt demonstrates DefineDataPrompt for strongly-typed
// input and output. The type parameters automatically configure input/output schemas
// and JSON output format. ExecuteStream returns typed chunks and final output.
func StructuredJokeWithDefineDataPrompt(ctx context.Context, g *genkit.Genkit) {
	jokePrompt := genkit.DefineDataPrompt[JokeRequest, *Joke](
		g, "structured-joke.code",
		ai.WithModel(googlegenai.ModelRef("gemini-2.5-flash", &genai.GenerateContentConfig{
			ThinkingConfig: &genai.ThinkingConfig{
				ThinkingBudget: genai.Ptr[int32](0),
			},
		})),
		ai.WithPrompt("Share a long joke about {{topic}}."),
	)

	genkit.DefineStreamingFlow(g, "structuredJokePromptFlow",
		func(ctx context.Context, input JokeRequest, sendChunk core.StreamCallback[*Joke]) (*Joke, error) {
			if input.Topic == "" {
				input.Topic = "airplane food"
			}
			stream := jokePrompt.ExecuteStream(ctx, input)
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
		},
	)
}

// StructuredJokeWithDotprompt demonstrates LookupDataPrompt to wrap a .prompt file
// with Go type information. The .prompt file references registered schemas by name
// (e.g., "schema: Joke"), which must be defined via DefineSchemaFor before loading.
func StructuredJokeWithDotprompt(ctx context.Context, g *genkit.Genkit) {
	genkit.DefineStreamingFlow(g, "structuredJokeDotpromptFlow",
		func(ctx context.Context, input JokeRequest, sendChunk core.StreamCallback[*Joke]) (*Joke, error) {
			if input.Topic == "" {
				input.Topic = "airplane food"
			}
			jokePrompt := genkit.LookupDataPrompt[JokeRequest, *Joke](g, "structured-joke")
			stream := jokePrompt.ExecuteStream(ctx, input)
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
		},
	)
}

// RecipeWithDefineDataPrompt demonstrates DefineDataPrompt with complex nested types
// and Handlebars conditionals/loops in the prompt template. The streaming flow applies
// default values before execution and streams partial ingredients as they arrive.
func RecipeWithDefineDataPrompt(ctx context.Context, g *genkit.Genkit) {
	recipePrompt := genkit.DefineDataPrompt[RecipeRequest, *Recipe](
		g, "recipe.code",
		ai.WithModel(googlegenai.ModelRef("gemini-2.5-flash", &genai.GenerateContentConfig{
			ThinkingConfig: &genai.ThinkingConfig{
				ThinkingBudget: genai.Ptr[int32](0),
			},
		})),
		ai.WithSystem("You are an experienced chef. Come up with easy, creative recipes."),
		ai.WithPrompt("Create a {{cuisine}} {{dish}} recipe for {{servingSize}} people that takes under {{maxPrepMinutes}} minutes to prepare. "+
			"{{#if dietaryRestrictions}}Dietary restrictions: {{#each dietaryRestrictions}}{{this}}{{#unless @last}}, {{/unless}}{{/each}}.{{/if}}"),
	)

	genkit.DefineStreamingFlow(g, "recipePromptFlow",
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
			filterNew := newIngredientFilter()
			stream := recipePrompt.ExecuteStream(ctx, input)
			for result, err := range stream {
				if err != nil {
					return nil, fmt.Errorf("could not generate recipe: %w", err)
				}
				if result.Done {
					return result.Output, nil
				} else if result.Chunk != nil {
					if newIngs := filterNew(result.Chunk.Ingredients); len(newIngs) > 0 {
						sendChunk(ctx, newIngs)
					}
				}
			}
			return nil, nil
		},
	)
}

// RecipeWithDotprompt demonstrates LookupDataPrompt with a .prompt file that uses
// multi-message format (system/user roles) and references registered schemas.
// Streams partial ingredients as they arrive via ExecuteStream.
func RecipeWithDotprompt(ctx context.Context, g *genkit.Genkit) {
	genkit.DefineStreamingFlow(g, "recipeDotpromptFlow",
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
			filterNew := newIngredientFilter()
			recipePrompt := genkit.LookupDataPrompt[RecipeRequest, *Recipe](g, "recipe")
			stream := recipePrompt.ExecuteStream(ctx, input)
			for result, err := range stream {
				if err != nil {
					return nil, fmt.Errorf("could not generate recipe: %w", err)
				}
				if result.Done {
					return result.Output, nil
				} else if result.Chunk != nil {
					if newIngs := filterNew(result.Chunk.Ingredients); len(newIngs) > 0 {
						sendChunk(ctx, newIngs)
					}
				}
			}
			return nil, nil
		},
	)
}

// newIngredientFilter is a helper function to filter out duplicate ingredients.
// This allows us to stream only new ingredients as they are identified, avoiding duplicates.
func newIngredientFilter() func([]*Ingredient) []*Ingredient {
	seen := map[string]struct{}{}
	return func(ings []*Ingredient) (newIngs []*Ingredient) {
		for _, ing := range ings {
			if _, ok := seen[ing.Name]; !ok {
				seen[ing.Name] = struct{}{}
				newIngs = append(newIngs, ing)
			}
		}
		return
	}
}
