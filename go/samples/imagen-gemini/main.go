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
	"encoding/base64"
	"errors"
	"fmt"
	"log"
	"os"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/googlegenai"
)

func main() {
	ctx := context.Background()

	// Initialize Genkit with the Google AI plugin. When you pass nil for the
	// Config parameter, the Google AI plugin will get the API key from the
	// GEMINI_API_KEY or GOOGLE_API_KEY environment variable, which is the recommended
	// practice.
	g, err := genkit.Init(ctx, genkit.WithPlugins(&googlegenai.GoogleAI{}))
	if err != nil {
		log.Fatal(err)
	}

	// Define a simple flow that generates an image of a given topic
	genkit.DefineFlow(g, "imageFlow", func(ctx context.Context, input string) (string, error) {
		m := googlegenai.GoogleAIModel(g, "gemini-2.0-flash-exp")
		if m == nil {
			return "", errors.New("imageFlow: failed to find model")
		}

		if input == "" {
			input = `A little blue gopher with big eyes trying to learn Python,
				use a cartoon style, the story should be tragic because he
				chose the wrong programming language, the proper programing
				language for a gopher should be Go`
		}
		resp, err := genkit.Generate(ctx, g,
			ai.WithModel(m),
			ai.WithConfig(&googlegenai.GeminiConfig{
				Temperature: 0.5,
				ResponseModalities: []googlegenai.Modality{
					googlegenai.ImageMode,
					googlegenai.TextMode,
				},
			}),
			ai.WithPrompt(fmt.Sprintf(`generate a story about %s and for each scene, generate an image for it`, input)))
		if err != nil {
			return "", err
		}

		story := ""
		scene := 0
		for _, p := range resp.Message.Content {
			if p.IsMedia() {
				scene += 1
				err = base64toFile(p.Text, fmt.Sprintf("scene_%d.png", scene))
			}
			if p.IsText() {
				story += p.Text
			}
		}
		if err != nil {
			return "", err
		}

		return story, nil
	})

	<-ctx.Done()
}

func base64toFile(data, path string) error {
	dec, err := base64.StdEncoding.DecodeString(data)
	if err != nil {
		return err
	}
	f, err := os.Create(path)
	if err != nil {
		return err
	}
	defer f.Close()

	_, err = f.Write(dec)
	if err != nil {
		return err
	}

	return f.Sync()
}
