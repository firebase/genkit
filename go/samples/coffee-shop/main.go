// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

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
	"log"
	"net/http"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/dotprompt"
	"github.com/firebase/genkit/go/plugins/googleai"
	"github.com/firebase/genkit/go/plugins/server"
)

const simpleGreetingPromptTemplate = `
You're a barista at a nice coffee shop.
A regular customer named {{customerName}} enters.
Greet the customer in one sentence, and recommend a coffee drink.
`

const simpleStructuredGreetingPromptTemplate = `
You're a barista at a nice coffee shop.
A regular customer named {{customerName}} enters.
Greet the customer in one sentence.
Provide the name of the drink of the day, nothing else.
`

type simpleGreetingInput struct {
	CustomerName string `json:"customerName"`
}

type simpleGreetingOutput struct {
	CustomerName string `json:"customerName"`
	Greeting     string `json:"greeting,omitempty"`
	DrinkOfDay   string `json:"drinkOfDay"`
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
	ctx := context.Background()
	g, err := genkit.Init(ctx, genkit.WithDefaultModel("googleai/gemini-2.0-flash"))
	if err != nil {
		log.Fatalf("failed to create Genkit: %v", err)
	}

	if err := googleai.Init(context.Background(), g, nil); err != nil {
		log.Fatal(err)
	}

	m := googleai.Model(g, "gemini-2.0-flash")
	simpleGreetingPrompt, err := dotprompt.Define(g, "simpleGreeting2", simpleGreetingPromptTemplate,
		dotprompt.WithDefaultModel(m),
		dotprompt.WithInputType(simpleGreetingInput{}),
		dotprompt.WithOutputFormat(ai.OutputFormatText),
	)
	if err != nil {
		log.Fatal(err)
	}

	simpleGreetingFlow := genkit.DefineStreamingFlow(g, "simpleGreeting", func(ctx context.Context, input *simpleGreetingInput, cb func(context.Context, string) error) (string, error) {
		var callback func(context.Context, *ai.ModelResponseChunk) error
		if cb != nil {
			callback = func(ctx context.Context, c *ai.ModelResponseChunk) error {
				return cb(ctx, c.Text())
			}
		}
		resp, err := simpleGreetingPrompt.Generate(ctx,
			g,
			dotprompt.WithInput(input),
			dotprompt.WithStreaming(callback),
		)
		if err != nil {
			return "", err
		}
		return resp.Text(), nil
	})

	greetingWithHistoryPrompt, err := dotprompt.Define(g, "greetingWithHistory", greetingWithHistoryPromptTemplate,
		dotprompt.WithDefaultModel(m),
		dotprompt.WithInputType(customerTimeAndHistoryInput{}),
		dotprompt.WithOutputFormat(ai.OutputFormatText),
	)
	if err != nil {
		log.Fatal(err)
	}

	greetingWithHistoryFlow := genkit.DefineFlow(g, "greetingWithHistory", func(ctx context.Context, input *customerTimeAndHistoryInput) (string, error) {
		resp, err := greetingWithHistoryPrompt.Generate(ctx, g, dotprompt.WithInput(input))
		if err != nil {
			return "", err
		}
		return resp.Text(), nil
	})

	simpleStructuredGreetingPrompt, err := dotprompt.Define(g, "simpleStructuredGreeting", simpleStructuredGreetingPromptTemplate,
		dotprompt.WithDefaultModel(m),
		dotprompt.WithInputType(simpleGreetingInput{}),
		dotprompt.WithOutputType(simpleGreetingOutput{}),
	)
	if err != nil {
		log.Fatal(err)
	}

	genkit.DefineStreamingFlow(g, "simpleStructuredGreeting", func(ctx context.Context, input *simpleGreetingInput, cb func(context.Context, string) error) (string, error) {
		var callback func(context.Context, *ai.ModelResponseChunk) error
		if cb != nil {
			callback = func(ctx context.Context, c *ai.ModelResponseChunk) error {
				return cb(ctx, c.Text())
			}
		}
		resp, err := simpleStructuredGreetingPrompt.Generate(ctx, g,
			dotprompt.WithInput(input),
			dotprompt.WithStreaming(callback),
		)
		if err != nil {
			return "", err
		}
		return resp.Text(), nil
	})

	genkit.DefineFlow(g, "testAllCoffeeFlows", func(ctx context.Context, _ struct{}) (*testAllCoffeeFlowsOutput, error) {
		test1, err := simpleGreetingFlow.Run(ctx, &simpleGreetingInput{
			CustomerName: "Sam",
		})
		if err != nil {
			out := &testAllCoffeeFlowsOutput{
				Pass:  false,
				Error: err.Error(),
			}
			return out, nil
		}
		test2, err := greetingWithHistoryFlow.Run(ctx, &customerTimeAndHistoryInput{
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

	mux := http.NewServeMux()
	for _, a := range genkit.ListFlows(g) {
		mux.HandleFunc("POST /"+a.Name(), genkit.Handler(a))
	}
	log.Fatal(server.Start(ctx, "127.0.0.1:8080", mux))
}
