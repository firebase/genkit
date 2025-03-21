// Copyright 2025 Google LLC
// SPDX-License-Identifier: Apache-2.0

package main

import (
	"context"
	"errors"
	"log"
	"os"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/googlegenai"
)

// duneQuestionInput is a question about Dune.
type duneQuestionInput struct {
	Question string `json:"question"`
	FilePath string `json:"path"`
}

func main() {
	ctx := context.Background()
	g, err := genkit.Init(ctx, genkit.WithDefaultModel("googleai/gemini-1.5-flash"))
	if err != nil {
		log.Fatal(err)
	}
	// Initialize the Google AI plugin. When you pass nil for the
	// Config parameter, the Google AI plugin will get the API key from the
	// GOOGLE_GENAI_API_KEY environment variable, which is the recommended
	// practice.
	if err := googlegenai.InitGoogleAI(ctx, g, nil); err != nil {
		log.Fatal(err)
	}

	genkit.DefineFlow(g, "duneFlowGeminiAI", func(ctx context.Context, input *duneQuestionInput) (string, error) {
		prompt := "What is the text I provided you with?"
		if input == nil {
			return "", errors.New("empty flow input, provide at least a source file to read")
		}
		if len(input.Question) > 0 {
			prompt = input.Question
		}

		textContent, err := os.ReadFile(input.FilePath)
		if err != nil {
			return "", err
		}

		// generate a request with a large text content to be cached
		resp, err := genkit.Generate(ctx, g, ai.WithConfig(&ai.GenerationCommonConfig{
			Temperature: 0.7,
			Version:     "gemini-1.5-flash-001",
		}),
			ai.WithMessages(
				ai.NewUserTextMessage(string(textContent)).WithCacheTTL(360),
			),
			ai.WithPromptText(prompt),
		)
		if err != nil {
			return "", nil
		}

		// use previous messages to keep the conversation going and keep
		// asking questions related to the large content that was cached
		resp, err = genkit.Generate(ctx, g, ai.WithConfig(&ai.GenerationCommonConfig{
			Temperature: 0.7,
			Version:     "gemini-1.5-flash-001",
		}),
			ai.WithMessages(resp.History()...),
			ai.WithPromptText("now rewrite the previous summary and make it look like a pirate wrote it"),
		)
		if err != nil {
			return "", nil
		}

		text := resp.Text()
		return text, nil
	})

	<-ctx.Done()
}
