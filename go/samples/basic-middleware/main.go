// Copyright 2026 Google LLC
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

// This sample demonstrates using Genkit middleware with flows. It defines a
// joke-generating flow that uses the Fallback middleware to automatically try
// an alternative model if the primary model fails.
//
// To run:
//
//	go run .
//
// In another terminal, test the flow:
//
//	curl -X POST http://localhost:8080/jokesFlow \
//	  -H "Content-Type: application/json" \
//	  -d '{"data": "bananas"}'
package main

import (
	"context"
	"log"
	"net/http"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/googlegenai"
	"github.com/firebase/genkit/go/plugins/middleware"
	"github.com/firebase/genkit/go/plugins/server"
	"google.golang.org/genai"
)

func main() {
	ctx := context.Background()

	// Initialize Genkit with the Google AI plugin and the Middleware plugin.
	// The Middleware plugin registers built-in middleware (Fallback, Retry, etc.)
	// that can be applied to Generate calls via ai.WithUse.
	g := genkit.Init(ctx, genkit.WithPlugins(&googlegenai.GoogleAI{}, &middleware.Middleware{}))

	// Define a flow that uses the Fallback middleware. If the primary model
	// (gemini-3.1-flash-preview) fails with a retryable error, the request is
	// automatically forwarded to the fallback model (gemini-2.5-flash).
	genkit.DefineFlow(g, "jokesFlow", func(ctx context.Context, input string) (string, error) {
		if input == "" {
			input = "airplane food"
		}

		return genkit.GenerateText(ctx, g,
			ai.WithModel(googlegenai.ModelRef("googleai/gemini-3.1-flash-preview", &genai.GenerateContentConfig{
				ThinkingConfig: &genai.ThinkingConfig{
					ThinkingBudget: genai.Ptr[int32](0),
				},
			})),
			ai.WithPrompt("Share a joke about %s.", input),
			ai.WithUse(&middleware.Fallback{
				Models: []ai.ModelRef{
					googlegenai.ModelRef("googleai/gemini-2.5-flash", nil),
				},
			}),
		)
	})

	mux := http.NewServeMux()
	for _, a := range genkit.ListFlows(g) {
		mux.HandleFunc("POST /"+a.Name(), genkit.Handler(a))
	}
	log.Fatal(server.Start(ctx, "127.0.0.1:8080", mux))
}
