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
	"os"
	"os/signal"
	"syscall"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/googlegenai"
)

func main() {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// Handle SIGINT (Ctrl+C) for graceful shutdown
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, os.Interrupt, syscall.SIGTERM)
	go func() {
		<-sigCh
		log.Println("Received interrupt, shutting down...")
		cancel()
	}()

	// Initialize Genkit with the Google AI plugin. When you pass nil for the
	// Config parameter, the Google AI plugin will get the API key from the
	// GEMINI_API_KEY or GOOGLE_API_KEY environment variable, which is the recommended
	// practice.
	// Initialize Genkit with the Google AI plugin using an invalid API key
	g, err := genkit.Init(ctx, genkit.WithPlugins(&googlegenai.GoogleAI{
		APIKey: "invalid-key-12345", // Explicitly set invalid key
	}))
	if err != nil {
		log.Fatalf("Initialization failed: %v", err)
	}
	log.Println("Genkit initialized successfully")

	// Define a simple flow that generates jokes about a given topic
	jokesFlow := genkit.DefineFlow(g, "jokesFlow", func(ctx context.Context, input string) (string, error) {
		m := googlegenai.GoogleAIModel(g, "gemini-2.5-pro-preview-03-25")
		if m == nil {
			return "", errors.New("jokesFlow: failed to find model")
		}

		resp, err := genkit.Generate(ctx, g,
			ai.WithModel(m),
			ai.WithConfig(&googlegenai.GeminiConfig{
				Temperature: 1.0,
			}),
			ai.WithPrompt(`Tell silly short jokes about %s`, input))
		if err != nil {
			// Log detailed error
			log.Printf("Generate error: %v", err)
			return "", fmt.Errorf("failed to generate: %w", err)
		}

		text := resp.Text()
		return text, nil
	})

	// Execute the flow to trigger the 4xx error
	log.Println("Running jokesFlow with input 'cats'")
	result, err := jokesFlow.Run(ctx, "cats")
	if err != nil {
		log.Fatalf("Flow failed: %v", err)
	}
	log.Printf("Flow result: %s", result)
}
