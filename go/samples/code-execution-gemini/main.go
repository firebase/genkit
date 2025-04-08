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
	"strings"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/googlegenai"
)

func main() {
	ctx := context.Background()

	// Initialize Genkit with Google AI plugin
	g, err := genkit.Init(ctx, genkit.WithPlugins(&googlegenai.GoogleAI{}))
	if err != nil {
		log.Fatal(err)
	}

	// Define a flow to demonstrate code execution
	genkit.DefineFlow(g, "codeExecutionFlow", func(ctx context.Context, _ any) (string, error) {
		m := googlegenai.GoogleAIModel(g, "gemini-1.5-pro")
		if m == nil {
			return "", errors.New("failed to find model")
		}

		problem := "find the sum of first 5 prime numbers"
		fmt.Printf("Problem: %s\n", problem)

		// Generate response with code execution enabled
		fmt.Println("Sending request to Gemini...")
		resp, err := genkit.Generate(ctx, g,
			ai.WithModel(m),
			ai.WithConfig(&googlegenai.GeminiConfig{
				Temperature:   0.2,
				CodeExecution: true,
			}),
			ai.WithPrompt(problem))
		if err != nil {
			return "", err
		}

		// Parse and display the code execution parts
		fmt.Println("\n=== CODE EXECUTION RESULTS ===")
		msg := resp.Message

		for _, part := range msg.Content {
			if part.IsCustom() {
				if codeExec, ok := part.Custom["codeExecutionResult"]; ok {
					result := codeExec.(map[string]any)
					fmt.Println("\nExecution result:")
					fmt.Println("Status:", result["outcome"])
					fmt.Println("Output:")
					fmt.Println(formatOutput(result["output"].(string)))
				} else if execCode, ok := part.Custom["executableCode"]; ok {
					code := execCode.(map[string]any)
					fmt.Println("Language: ", code["language"])
					fmt.Println("```" + code["language"].(string))
					fmt.Println(code["code"])
					fmt.Println("```")
				}
			} else if part.IsText() {
				fmt.Println("\nExplanation:")
				fmt.Println(part.Text)
			}
		}

		fmt.Println("\n=== COMPLETE RESPONSE ===")
		text := resp.Text()
		fmt.Println(text)

		return text, nil
	})
	<-ctx.Done()
}

// formatOutput adds indentation to execution output for readability
func formatOutput(output string) string {
	if strings.TrimSpace(output) == "" {
		return "  <no output>"
	}

	lines := strings.Split(output, "\n")
	for i, line := range lines {
		lines[i] = "  " + line
	}
	return strings.Join(lines, "\n")
}
