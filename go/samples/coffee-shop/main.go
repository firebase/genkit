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

// This program can be manually tested like so:
//
// In development mode (with the environment variable GENKIT_ENV="dev"):
// Start the server listening on port 3100:
//
//	go run . &
//
// Tell it to run a flow:
//
//	curl -d '{"key":"/flow/simpleGreeting/simpleGreeting", "input":{"start": {"input":{"customerName": "John Doe"}}}}' http://localhost:3100/api/runAction
//
// In production mode (GENKIT_ENV missing or set to "prod"):
// Start the server listening on port 3400:
//
//	go run . &
//
// Tell it to run a flow:
//
//  curl -d '{"customerName": "Stimpy"}' http://localhost:3400/simpleGreeting

package main

import (
	"context"
	"fmt"
	"log"
	"os"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/dotprompt"
	"github.com/firebase/genkit/go/plugins/googleai"
	"github.com/firebase/genkit/go/plugins/localvec"
	"github.com/invopop/jsonschema"
)

const simpleGreetingPromptTemplate = `
You're a barista at a nice coffee shop.
A regular customer named {{customerName}} enters.
Greet the customer in one sentence, and recommend a coffee drink.
`

const simpleQaPromptTemplate = `
You're a helpful agent that answers the user's common questions based on the context provided.

Here is the user's query: {{query}}

Here is the context you should use: {{context}}

Please provide the best answer you can.
`

type simpleGreetingInput struct {
	CustomerName string `json:"customerName"`
}

type simpleQaInput struct {
	Question string `json:"question"`
}

type simpleQaPromptInput struct {
	Query   string `json:"query"`
	Context string `json:"context"`
}

const greetingWithHistoryPromptTemplate = `
{{role "user"}}
Hi, my name is {{customerName}}. The time is {{currentTime}}. Who are you?

{{role "model"}}
I am Barb, a barista at this nice underwater-themed coffee shop called Krabby Kooffee.
I know pretty much everything there is to know about coffee,
and I can cheerfully recommend delicious coffee drinks to you based on whatever you like.

{{role "user"}}
Great. Last time I had {{previousOrder}}.
I want you to greet me in one sentence, and recommend a drink.
`

type customerTimeAndHistoryInput struct {
	CustomerName  string `json:"customerName"`
	CurrentTime   string `json:"currentTime"`
	PreviousOrder string `json:"previousOrder"`
}

type testAllCoffeeFlowsOutput struct {
	Pass    bool     `json:"pass"`
	Replies []string `json:"replies,omitempty"`
	Error   string   `json:"error,omitempty"`
}

func main() {
	apiKey := os.Getenv("GOOGLE_GENAI_API_KEY")
	if apiKey == "" {
		fmt.Fprintln(os.Stderr, "coffee-shop example requires setting GOOGLE_GENAI_API_KEY in the environment.")
		fmt.Fprintln(os.Stderr, "You can get an API key at https://ai.google.dev.")
		os.Exit(1)
	}

	if err := googleai.Init(context.Background(), "gemini-1.0-pro", apiKey); err != nil {
		log.Fatal(err)
	}

	simpleGreetingPrompt, err := dotprompt.Define("simpleGreeting", simpleGreetingPromptTemplate,
		&dotprompt.Config{
			Model:        "google-genai/gemini-1.0-pro",
			InputSchema:  jsonschema.Reflect(simpleGreetingInput{}),
			OutputFormat: ai.OutputFormatText,
		},
	)
	if err != nil {
		log.Fatal(err)
	}

	simpleGreetingFlow := genkit.DefineFlow("simpleGreeting", func(ctx context.Context, input *simpleGreetingInput, _ genkit.NoStream) (string, error) {
		vars, err := simpleGreetingPrompt.BuildVariables(input)
		if err != nil {
			return "", err
		}
		ai := &dotprompt.ActionInput{Variables: vars}
		resp, err := simpleGreetingPrompt.Execute(ctx, ai)
		if err != nil {
			return "", err
		}
		text, err := resp.Text()
		if err != nil {
			return "", fmt.Errorf("simpleGreeting: %v", err)
		}
		return text, nil
	})

	simpleQaPrompt, err := dotprompt.Define("simpleQaPrompt",
		simpleQaPromptTemplate,
		&dotprompt.Config{
			Model:        "google-genai/gemini-1.0-pro",
			InputSchema:  jsonschema.Reflect(simpleQaPromptInput{}),
			OutputFormat: ai.OutputFormatText,
		},
	)
	if err != nil {
		log.Fatal(err)
	}

	genkit.DefineFlow("simpleQaFlow", func(ctx context.Context, input *simpleQaInput, _ genkit.NoStream) (string, error) {
		d1 := ai.DocumentFromText("Paris is the capital of France", nil)
		d2 := ai.DocumentFromText("USA is the largest importer of coffee", nil)
		d3 := ai.DocumentFromText("Water exists in 3 states - solid, liquid and gas", nil)

		embedder, err := googleai.NewEmbedder(ctx, "embedding-001", apiKey)
		if err != nil {
			return "", err
		}
		localDb, err := localvec.New(ctx, "/tmp/", "simpleQa", embedder, nil)
		if err != nil {
			return "", err
		}

		indexerReq := &ai.IndexerRequest{
			Documents: []*ai.Document{d1, d2, d3},
		}
		localDb.Index(ctx, indexerReq)

		dRequest := ai.DocumentFromText(input.Question, nil)
		retrieverReq := &ai.RetrieverRequest{
			Document: dRequest,
		}
		response, err := localDb.Retrieve(ctx, retrieverReq)
		if err != nil {
			return "", err
		}

		var context string
		for _, d := range response.Documents {
			context += d.Content[0].Text() + "\n"
		}

		promptInput := &simpleQaPromptInput{
			Query:   input.Question,
			Context: context,
		}

		vars, err := simpleQaPrompt.BuildVariables(promptInput)
		if err != nil {
			return "", err
		}
		ai := &dotprompt.ActionInput{Variables: vars}
		resp, err := simpleQaPrompt.Execute(ctx, ai)
		if err != nil {
			return "", err
		}
		text, err := resp.Text()
		if err != nil {
			return "", fmt.Errorf("simpleQa: %v", err)
		}
		return text, nil
	})

	greetingWithHistoryPrompt, err := dotprompt.Define("greetingWithHistory", greetingWithHistoryPromptTemplate,
		&dotprompt.Config{
			Model:        "google-genai/gemini-1.0-pro",
			InputSchema:  jsonschema.Reflect(customerTimeAndHistoryInput{}),
			OutputFormat: ai.OutputFormatText,
		},
	)
	if err != nil {
		log.Fatal(err)
	}

	greetingWithHistoryFlow := genkit.DefineFlow("greetingWithHistory", func(ctx context.Context, input *customerTimeAndHistoryInput, _ genkit.NoStream) (string, error) {
		vars, err := greetingWithHistoryPrompt.BuildVariables(input)
		if err != nil {
			return "", err
		}
		ai := &dotprompt.ActionInput{Variables: vars}
		resp, err := greetingWithHistoryPrompt.Execute(ctx, ai)
		if err != nil {
			return "", err
		}
		text, err := resp.Text()
		if err != nil {
			return "", fmt.Errorf("greetingWithHistory: %v", err)
		}
		return text, nil
	})

	genkit.DefineFlow("testAllCoffeeFlows", func(ctx context.Context, _ struct{}, _ genkit.NoStream) (*testAllCoffeeFlowsOutput, error) {
		test1, err := genkit.RunFlow(ctx, simpleGreetingFlow, &simpleGreetingInput{
			CustomerName: "Sam",
		})
		if err != nil {
			out := &testAllCoffeeFlowsOutput{
				Pass:  false,
				Error: err.Error(),
			}
			return out, nil
		}
		test2, err := genkit.RunFlow(ctx, greetingWithHistoryFlow, &customerTimeAndHistoryInput{
			CustomerName:  "Sam",
			CurrentTime:   "09:45am",
			PreviousOrder: "Caramel Macchiato",
		})
		if err != nil {
			out := &testAllCoffeeFlowsOutput{
				Pass:  false,
				Error: err.Error(),
			}
			return out, nil
		}
		out := &testAllCoffeeFlowsOutput{
			Pass: true,
			Replies: []string{
				test1,
				test2,
			},
		}
		return out, nil
	})
	if err := genkit.StartFlowServer(""); err != nil {
		log.Fatal(err)
	}
}
