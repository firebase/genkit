// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package main

import (
	"context"
	"math"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	oai_deepseek "github.com/firebase/genkit/go/plugins/compat_oai/deepseek"
	"github.com/openai/openai-go"
)

func main() {
	ctx := context.Background()

	// DEEPSEEK_API_KEY and DEEPSEEK_BASE_URL environment values will be read automatically unless
	// they are provided via `option.RequestOption{}`
	g := genkit.Init(ctx,
		genkit.WithPlugins(&oai_deepseek.DeepSeek{}),
		genkit.WithDefaultModel("deepseek/deepseek-chat"))

	// Define a tool for calculating gablorkens
	gablorkenTool := genkit.DefineTool(g, "gablorken", "use when need to calculate a gablorken",
		func(ctx *ai.ToolContext, input struct {
			Value float64
			Over  float64
		},
		) (float64, error) {
			return math.Pow(input.Value, input.Over), nil
		},
	)

	genkit.DefineStreamingFlow(g, "streaming tool", func(ctx context.Context, input any, cb ai.ModelStreamCallback) (string, error) {
		config := &openai.ChatCompletionNewParams{Temperature: openai.Float(0.5)}
		resp, err := genkit.Generate(ctx,
			g,
			//			ai.WithModel(dsChat),
			ai.WithPrompt("calculate the gablorken of value 3 over 5"),
			ai.WithTools(gablorkenTool),
			ai.WithStreaming(cb),
			ai.WithConfig(config))
		if err != nil {
			return "", err
		}
		return resp.Text(), nil
	})

	<-ctx.Done()
}
