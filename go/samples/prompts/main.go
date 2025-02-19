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
	"encoding/json"
	"fmt"
	"log"
	"math"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/ai/prompt"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/vertexai"
)

func main() {
	ctx := context.Background()
	g, err := genkit.New(nil)
	if err != nil {
		log.Fatal(err)
	}

	if err := vertexai.Init(ctx, g, nil); err != nil {
		log.Fatal(err)
	}

	SimplePrompt(ctx, g)
	PromptWithInput(ctx, g)
	PromptWithOutputType(ctx, g)
	PromptWithTool(ctx, g)
	PromptWithMessageHistory(ctx, g)
	PromptWithExecuteOverrides(ctx, g)
	PromptWithFunctions(ctx, g)
}

func SimplePrompt(ctx context.Context, g *genkit.Genkit) {
	m := vertexai.Model(g, "gemini-1.5-flash")

	// Define prompt with default model and system text. Can be overridden on execute.
	helloPrompt, err := genkit.DefinePrompt(
		g,
		"prompts",
		"SimplePrompt",
		prompt.WithDefaultModel(m),
		prompt.WithDefaultSystemText("You are a helpful AI assistant named Walt"),
	)

	if err != nil {
		log.Fatal(err)
	}

	// Call the model
	resp, err := helloPrompt.Execute(ctx)
	if err != nil {
		log.Fatal(err)
	}

	fmt.Print(resp.Text())
}

func PromptWithInput(ctx context.Context, g *genkit.Genkit) {
	m := vertexai.Model(g, "gemini-1.5-flash")

	type HelloPromptInput struct {
		UserName string
	}

	// Define prompt with input type.
	helloPrompt, err := genkit.DefinePrompt(
		g,
		"prompts",
		"PromptWithInput",
		prompt.WithDefaultModel(m),
		prompt.WithInputType(HelloPromptInput{}),
		prompt.WithDefaultSystemText("You are a helpful AI assistant named Walt. Say hello to {{UserName}}."),
	)

	if err != nil {
		log.Fatal(err)
	}

	// Call the model with input.
	resp, err := helloPrompt.Execute(ctx, prompt.WithInput(HelloPromptInput{UserName: "Bob"}))
	if err != nil {
		log.Fatal(err)
	}

	fmt.Print(resp.Text())
}

func PromptWithOutputType(ctx context.Context, g *genkit.Genkit) {
	m := vertexai.Model(g, "gemini-1.5-flash")

	type CountryList struct {
		Countries []string
	}

	// Define prompt with output type.
	helloPrompt, err := genkit.DefinePrompt(
		g,
		"prompts",
		"PromptWithOutputType",
		prompt.WithDefaultModel(m),
		prompt.WithOutputType(CountryList{}),
		prompt.WithDefaultConfig(&ai.GenerationCommonConfig{Temperature: 0.5}),
		prompt.WithDefaultSystemText("You are a geography teacher. When asked a question about geography, return a list of countries that match the question."),
	)

	if err != nil {
		log.Fatal(err)
	}

	// Call the model with prompt.
	resp, err := helloPrompt.Execute(ctx, prompt.WithPrompt("Give me the 10 biggest countries in the world by habitants."))
	if err != nil {
		log.Fatal(err)
	}

	var countryList CountryList
	err = json.Unmarshal([]byte(resp.Text()), &countryList)
	if err != nil {
		log.Fatal(err)
	}

	for _, country := range countryList.Countries {
		fmt.Println(country)
	}
}

func PromptWithTool(ctx context.Context, g *genkit.Genkit) {
	m := vertexai.Model(g, "gemini-1.5-flash")

	gablorkenTool := genkit.DefineTool(g, "gablorken", "use when need to calculate a gablorken",
		func(ctx *ai.ToolContext, input struct {
			Value float64
			Over  float64
		}) (float64, error) {
			return math.Pow(input.Value, input.Over), nil
		},
	)

	// Define prompt with tool and tool settings.
	helloPrompt, err := genkit.DefinePrompt(
		g,
		"prompts",
		"PromptWithTool",
		prompt.WithDefaultModel(m),
		prompt.WithDefaultToolChoice(ai.ToolChoiceRequired),
		prompt.WithDefaultMaxTurns(1),
		prompt.WithTools(gablorkenTool),
	)

	if err != nil {
		log.Fatal(err)
	}

	// Call the model with prompt
	resp, err := helloPrompt.Execute(ctx, prompt.WithPrompt("what is a gablorken of 2 over 3.5?"))
	if err != nil {
		log.Fatal(err)
	}

	fmt.Print(resp.Text())
}

func PromptWithMessageHistory(ctx context.Context, g *genkit.Genkit) {
	m := vertexai.Model(g, "gemini-1.5-flash")

	// Define prompt with default messages prepended.
	helloPrompt, err := genkit.DefinePrompt(
		g,
		"prompts",
		"PromptWithMessageHistory",
		prompt.WithDefaultModel(m),
		prompt.WithDefaultMessages([]*ai.Message{
			{
				Role:    ai.RoleUser,
				Content: []*ai.Part{ai.NewTextPart("Hi, my name is Bob")},
			},
			{
				Role:    ai.RoleModel,
				Content: []*ai.Part{ai.NewTextPart("Hi, my name is Walt, what can I help you with?")},
			},
		}),
		prompt.WithDefaultSystemText("You are a helpful AI assistant named Walt"),
	)

	if err != nil {
		log.Fatal(err)
	}

	// Call the model
	resp, err := helloPrompt.Execute(ctx, prompt.WithPrompt("So Walt, What is my name?"))
	if err != nil {
		log.Fatal(err)
	}

	fmt.Print(resp.Text())
}

func PromptWithExecuteOverrides(ctx context.Context, g *genkit.Genkit) {
	m := vertexai.Model(g, "gemini-1.5-flash")

	// Define prompt with default settings.
	helloPrompt, err := genkit.DefinePrompt(
		g,
		"prompts",
		"PromptWithExecuteOverrides",
		prompt.WithDefaultModel(m),
		prompt.WithDefaultSystemText("You are a helpful AI assistant named Walt"),
		prompt.WithDefaultPrompt("Hello"),
	)

	if err != nil {
		log.Fatal(err)
	}

	// Call the model and override default
	resp, err := helloPrompt.Execute(ctx,
		prompt.WithModel(vertexai.Model(g, "gemini-1.5-pro")),
		prompt.WithSystemText("You are a helpful AI assistant named Bob"),
		prompt.WithPrompt("What is your name?"))
	if err != nil {
		log.Fatal(err)
	}

	fmt.Print(resp.Text())
}

func PromptWithFunctions(ctx context.Context, g *genkit.Genkit) {
	m := vertexai.Model(g, "gemini-1.5-flash")

	type HelloPromptInput struct {
		UserName string
	}

	// Define prompt.
	helloPrompt, err := genkit.DefinePrompt(
		g,
		"prompts",
		"PromptWithFunctions",
		prompt.WithDefaultModel(m),
		prompt.WithDefaultSystemText(func(ctx context.Context, input any) (string, error) {
			return "You are a helpful AI assistant named Walt. Say hello to {{Name}}", nil
		}),
		prompt.WithDefaultPrompt(func(ctx context.Context, input any) (string, error) {
			var p HelloPromptInput
			switch param := input.(type) {
			case HelloPromptInput:
				p = param
			}
			return fmt.Sprintf("Hello Walt, my name is  %s", p.UserName), nil
		}),
	)

	if err != nil {
		log.Fatal(err)
	}

	// Call the model
	resp, err := helloPrompt.Execute(ctx, prompt.WithInput(HelloPromptInput{UserName: "Bob"}))
	if err != nil {
		log.Fatal(err)
	}

	fmt.Print(resp.Text())
}
