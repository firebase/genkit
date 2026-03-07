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
	"encoding/json"
	"fmt"
	"log"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/ollama"
)

func main() {
	ctx := context.Background()

	// Initialize Genkit with the Ollama plugin
	ollamaPlugin := &ollama.Ollama{
		ServerAddress: "http://localhost:11434", // Default Ollama server address
		Timeout:       60,                       // Response timeout in seconds
	}

	g := genkit.Init(ctx, genkit.WithPlugins(ollamaPlugin))

	// Define the Ollama model
	model := ollamaPlugin.DefineModel(g,
		ollama.ModelDefinition{
			Name: "llama3.1", // Choose an appropriate model
			Type: "chat",
		},
		nil)

	fmt.Println("=== Ollama Schema-less JSON Mode Example ===\n")
	fmt.Println("This example demonstrates how to request generic JSON output")
	fmt.Println("without specifying a schema. The model will return valid JSON")
	fmt.Println("but is not constrained to any specific structure.\n")

	// Example: Schema-less JSON mode
	fmt.Println("--- Requesting Generic JSON Output ---")
	fmt.Println("Setting format to 'json' without a schema...\n")

	// Request generic JSON output by setting Format to "json" without a Schema
	// The model will return valid JSON, but the structure is determined by the prompt
	resp, err := genkit.Generate(ctx, g,
		ai.WithModel(model),
		ai.WithMessages(
			ai.NewUserTextMessage(`List 3 popular programming languages with their key features.
Return the response as JSON with a "languages" array where each item has "name" and "features" fields.`),
		),
		ai.WithOutputConfig(&ai.ModelOutputConfig{
			Format: "json", // Request JSON output without schema constraints
			// Schema is nil/empty, so Ollama returns generic JSON
		}),
	)
	if err != nil {
		log.Fatalf("Error generating JSON output: %v", err)
	}

	// The response text contains valid JSON
	responseText := resp.Text()
	fmt.Printf("Raw JSON response:\n%s\n\n", responseText)

	// Parse the JSON response
	// Since we don't have a predefined schema, we use a generic map structure
	var result map[string]any
	if err := json.Unmarshal([]byte(responseText), &result); err != nil {
		log.Fatalf("Failed to parse JSON response: %v", err)
	}

	// Access the data dynamically
	fmt.Println("Parsed JSON data:")
	prettyJSON, err := json.MarshalIndent(result, "", "  ")
	if err != nil {
		log.Fatalf("Failed to format JSON: %v", err)
	}
	fmt.Println(string(prettyJSON))

	fmt.Println("\n✓ Successfully received and parsed generic JSON output!")
	fmt.Println("\nWhen to use schema-less JSON mode:")
	fmt.Println("  • You want valid JSON but don't need strict structure enforcement")
	fmt.Println("  • The output structure varies based on the prompt")
	fmt.Println("  • You're prototyping and want flexibility")
	fmt.Println("  • You'll handle dynamic JSON structures in your application")
	fmt.Println("\nWhen to use schema-based output instead:")
	fmt.Println("  • You need guaranteed structure for reliable parsing")
	fmt.Println("  • You want type-safe Go structs")
	fmt.Println("  • You're building production systems with strict data requirements")
}
