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
	"encoding/base64"
	"os"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/dotprompt"
	"github.com/invopop/jsonschema"
)

type imageURLInput struct {
	ImageURL string `json:"imageUrl"`
}

func setup05(ctx context.Context, gen, genVision *ai.ModelAction) error {
	readMenuPrompt, err := dotprompt.Define("s05_readMenu",
		`
		  Extract _all_ of the text, in order,
		  from the following image of a restaurant menu.

		  {{media url=imageUrl}}`,
		dotprompt.Config{
			ModelAction:  genVision,
			InputSchema:  jsonschema.Reflect(imageURLInput{}),
			OutputFormat: ai.OutputFormatText,
			GenerationConfig: &ai.GenerationCommonConfig{
				Temperature: 0.1,
			},
		},
	)
	if err != nil {
		return err
	}

	textMenuPrompt, err := dotprompt.Define("s05_textMenu",
		`
		  You are acting as Walt, a helpful AI assistant here at the restaurant.
		  You can answer questions about the food on the menu or any other questions
		  customers have about food in general.

		  Here is the text of today's menu to help you answer the customer's question:
		  {{menuText}}

		  Answer this customer's question:
		  {{question}}?
		`,
		dotprompt.Config{
			ModelAction:  gen,
			InputSchema:  textMenuQuestionInputSchema,
			OutputFormat: ai.OutputFormatText,
			GenerationConfig: &ai.GenerationCommonConfig{
				Temperature: 0.3,
			},
		},
	)
	if err != nil {
		return err
	}

	// Define a flow that takes an image, passes it to Gemini Vision Pro,
	// and extracts all of the text from the photo of the menu.
	// Note that this example uses a hard-coded image file, as image input
	// is not currently available in the Development UI runners.
	readMenuFlow := genkit.DefineFlow("s05_readMenuFlow",
		func(ctx context.Context, _ struct{}, _ genkit.NoStream) (string, error) {
			image, err := os.ReadFile("testdata/menu.jpeg")
			if err != nil {
				return "", err
			}
			data := make([]byte, base64.StdEncoding.EncodedLen(len(image)))
			base64.StdEncoding.Encode(data, image)
			imageDataURL := "data:image/jpeg;base64," + string(data)
			preq := &ai.PromptRequest{
				Variables: &imageURLInput{
					ImageURL: imageDataURL,
				},
			}
			presp, err := readMenuPrompt.Generate(ctx, preq, nil)
			if err != nil {
				return "", err
			}

			ret := presp.Candidates[0].Message.Content[0].Text
			return ret, nil
		},
	)

	// Define a flow that generates a response to the question.
	// Just returns the LLM's text response to the question.

	textMenuQuestionFlow := genkit.DefineFlow("s05_textMenuQuestion",
		func(ctx context.Context, input *textMenuQuestionInput, _ genkit.NoStream) (*answerOutput, error) {
			preq := &ai.PromptRequest{
				Variables: input,
			}
			presp, err := textMenuPrompt.Generate(ctx, preq, nil)
			if err != nil {
				return nil, err
			}
			ret := &answerOutput{
				Answer: presp.Candidates[0].Message.Content[0].Text,
			}
			return ret, nil
		},
	)

	// Define a third composite flow that chains the first two flows.

	genkit.DefineFlow("s05_visionMenuQuestion",
		func(ctx context.Context, input *menuQuestionInput, _ genkit.NoStream) (*answerOutput, error) {
			menuText, err := genkit.RunFlow(ctx, readMenuFlow, struct{}{})
			if err != nil {
				return nil, err
			}

			questionInput := &textMenuQuestionInput{
				MenuText: menuText,
				Question: input.Question,
			}
			return genkit.RunFlow(ctx, textMenuQuestionFlow, questionInput)
		},
	)

	return nil
}
