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

// [START main]
package main

import (
	"context"
	"errors"
	"fmt"
	"log"

	// Import Genkit and the Google AI plugin
	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/googlegenai"
)

func main() {
	ctx := context.Background()

	// Initialize Genkit with the Google AI plugin. When you pass nil for the
	// Config parameter, the Google AI plugin will get the API key from the
	// GOOGLE_GENAI_API_KEY environment variable, which is the recommended
	// practice.
	g, err := genkit.Init(ctx, genkit.WithPlugins(&googlegenai.GoogleAI{}))
	if err != nil {
		log.Fatal(err)
	}

	// Define a simple flow that prompts an LLM to generate menu suggestions.
	genkit.DefineFlow(g, "menuSuggestionFlow", func(ctx context.Context, input string) (string, error) {
		// The Google AI API provides access to several generative models. Here,
		// we specify gemini-1.5-flash.
		m := googlegenai.GoogleAIModel(g, "gemini-1.5-flash")
		if m == nil {
			return "", errors.New("menuSuggestionFlow: failed to find model")
		}

		// Construct a request and send it to the model API (Google AI).
		resp, err := genkit.Generate(ctx, g,
			ai.WithModel(m),
			ai.WithConfig(&ai.GenerationCommonConfig{Temperature: 1}),
			ai.WithPrompt(fmt.Sprintf(`Suggest an item for the menu of a %s themed restaurant`, input)))
		if err != nil {
			return "", err
		}

		// Handle the response from the model API. In this sample, we just
		// convert it to a string. but more complicated flows might coerce the
		// response into structured output or chain the response into another
		// LLM call.
		text := resp.Text()
		return text, nil
	})

	<-ctx.Done()
}

// [END main]
