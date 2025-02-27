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
	"errors"
	"fmt"
	"log"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/googleai"
)

func main() {
	ctx := context.Background()

	g, err := genkit.Init(ctx)
	if err != nil {
		log.Fatal(err)
	}

	// Initialize the Google AI plugin. When you pass nil for the
	// Config parameter, the Google AI plugin will get the API key from the
	// GOOGLE_GENAI_API_KEY environment variable, which is the recommended
	// practice.
	if err := googleai.Init(ctx, g, nil); err != nil {
		log.Fatal(err)
	}

	// Define a simple flow that generates jokes about a given topic
	genkit.DefineFlow(g, "jokesFlow", func(ctx context.Context, input string) (string, error) {
		m := googleai.Model(g, "gemini-2.0-flash")
		if m == nil {
			return "", errors.New("jokesFlow: failed to find model")
		}

		resp, err := genkit.Generate(ctx, g,
			ai.WithModel(m),
			ai.WithConfig(&ai.GenerationCommonConfig{
				Temperature: 1,
				Version:     "gemini-1.5-flash-002",
			}),
			ai.WithTextPrompt(fmt.Sprintf(`Tell silly short jokes about %s`, input)))
		if err != nil {
			return "", err
		}

		text := resp.Text()
		return text, nil
	})

	<-ctx.Done()
}
