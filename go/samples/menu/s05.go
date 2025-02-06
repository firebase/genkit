// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package main

import (
	"context"
	"encoding/base64"
	"os"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/dotprompt"
)

type imageURLInput struct {
	ImageURL string `json:"imageUrl"`
}

func setup05(g *genkit.Genkit, gen, genVision ai.Model) error {
	readMenuPrompt, err := dotprompt.Define(g, "s05_readMenu",
		`
		  Extract _all_ of the text, in order,
		  from the following image of a restaurant menu.

		  {{media url=imageUrl}}`,
		dotprompt.WithDefaultModel(genVision),
		dotprompt.WithInputType(imageURLInput{}),
		dotprompt.WithOutputFormat(ai.OutputFormatText),
		dotprompt.WithDefaultConfig(&ai.GenerationCommonConfig{
			Temperature: 0.1,
		}),
	)
	if err != nil {
		return err
	}

	textMenuPrompt, err := dotprompt.Define(g, "s05_textMenu",
		`
		  You are acting as Walt, a helpful AI assistant here at the restaurant.
		  You can answer questions about the food on the menu or any other questions
		  customers have about food in general.

		  Here is the text of today's menu to help you answer the customer's question:
		  {{menuText}}

		  Answer this customer's question:
		  {{question}}?
		`,
		dotprompt.WithDefaultModel(gen),
		dotprompt.WithInputType(textMenuQuestionInput{}),
		dotprompt.WithOutputFormat(ai.OutputFormatText),
		dotprompt.WithDefaultConfig(&ai.GenerationCommonConfig{
			Temperature: 0.3,
		}),
	)
	if err != nil {
		return err
	}

	// Define a flow that takes an image, passes it to Gemini Vision Pro,
	// and extracts all of the text from the photo of the menu.
	// Note that this example uses a hard-coded image file, as image input
	// is not currently available in the Development UI runners.
	readMenuFlow := genkit.DefineFlow(g, "s05_readMenuFlow",
		func(ctx context.Context, _ struct{}) (string, error) {
			image, err := os.ReadFile("testdata/menu.jpeg")
			if err != nil {
				return "", err
			}
			data := make([]byte, base64.StdEncoding.EncodedLen(len(image)))
			base64.StdEncoding.Encode(data, image)
			imageDataURL := "data:image/jpeg;base64," + string(data)

			presp, err := readMenuPrompt.Generate(ctx, g,
				dotprompt.WithInput(&imageURLInput{
					ImageURL: imageDataURL,
				}))
			if err != nil {
				return "", err
			}

			ret := presp.Message.Content[0].Text
			return ret, nil
		},
	)

	// Define a flow that generates a response to the question.
	// Just returns the LLM's text response to the question.
	textMenuQuestionFlow := genkit.DefineFlow(g, "s05_textMenuQuestion",
		func(ctx context.Context, input *textMenuQuestionInput) (*answerOutput, error) {
			presp, err := textMenuPrompt.Generate(ctx, g, dotprompt.WithInput(input), nil)
			if err != nil {
				return nil, err
			}
			ret := &answerOutput{
				Answer: presp.Message.Content[0].Text,
			}
			return ret, nil
		},
	)

	// Define a third composite flow that chains the first two flows.

	genkit.DefineFlow(g, "s05_visionMenuQuestion",
		func(ctx context.Context, input *menuQuestionInput) (*answerOutput, error) {
			menuText, err := readMenuFlow.Run(ctx, struct{}{})
			if err != nil {
				return nil, err
			}

			questionInput := &textMenuQuestionInput{
				MenuText: menuText,
				Question: input.Question,
			}
			return textMenuQuestionFlow.Run(ctx, questionInput)
		},
	)

	return nil
}
