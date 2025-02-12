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
	"github.com/firebase/genkit/go/plugins/vertexai/modelgarden"
)

func main() {
	ctx := context.Background()

	g, err := genkit.New(nil)
	if err != nil {
		log.Fatal(err)
	}

	cfg := &modelgarden.Config{
		Location: "us-east5",
		Models:   []string{"claude-3-5-sonnet-v2"},
	}
	if err := modelgarden.Init(ctx, g, cfg); err != nil {
		log.Fatal(err)
	}

	// Define a simple flow that generates jokes about a given topic
	genkit.DefineFlow(g, "jokesFlow", func(ctx context.Context, input string) (string, error) {
		m := modelgarden.Model(g, modelgarden.AnthropicProvider, "claude-3-5-sonnet-v2")
		if m == nil {
			return "", errors.New("jokesFlow: failed to find model")
		}

		resp, err := genkit.Generate(ctx, g,
			ai.WithModel(m),
			ai.WithConfig(&ai.GenerationCommonConfig{
				Temperature: 0.1,
				Version:     "claude-3-5-sonnet-v2@20241022",
			}),
			ai.WithTextPrompt(fmt.Sprintf(`Tell silly short jokes about %s`, input)))
		if err != nil {
			return "", err
		}

		text := resp.Text()
		return text, nil
	})

	if err := g.Start(ctx, nil); err != nil {
		log.Fatal(err)
	}
}
