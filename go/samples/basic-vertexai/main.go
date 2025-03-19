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
	"github.com/firebase/genkit/go/plugins/google"
)

func main() {
	ctx := context.Background()

	g, err := genkit.Init(ctx)
	if err != nil {
		log.Fatal(err)
	}

	// Initialize the Google plugin. When you pass VertexAI=true
	// Config parameter, the Google plugin will look for the following
	// environment variables:
	// projectId: GOOGLE_CLOUD_PROJECT
	// location: GOOGLE_CLOUD_LOCATION then GOOGLE_CLOUD_REGION
	// These parameters could also be set in the plugin configuration.
	// If that's the case, there's no need to set VertexAI flag to true
	if err := google.Init(ctx, g, &google.Config{VertexAI: true}); err != nil {
		log.Fatal(err)
	}

	// Define a simple flow that generates jokes about a given topic
	genkit.DefineFlow(g, "jokesFlow", func(ctx context.Context, input string) (string, error) {
		m := google.Model(g, "gemini-2.0-flash")
		if m == nil {
			return "", errors.New("jokesFlow: failed to find model")
		}

		resp, err := genkit.Generate(ctx, g,
			ai.WithModel(m),
			ai.WithConfig(&ai.GenerationCommonConfig{
				Temperature: 1,
				Version:     "gemini-2.0-flash-001",
			}),
			ai.WithPromptText(fmt.Sprintf(`Tell silly short jokes about %s`, input)))
		if err != nil {
			return "", err
		}

		text := resp.Text()
		return text, nil
	})

	<-ctx.Done()
}
