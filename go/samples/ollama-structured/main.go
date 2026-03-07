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
	"github.com/invopop/jsonschema"
)

// Person represents a person with basic information
type Person struct {
	Name        string   `json:"name" jsonschema:"required,description=Full name of the person"`
	Age         int      `json:"age" jsonschema:"required,description=Age in years"`
	Occupation  string   `json:"occupation" jsonschema:"required,description=Current job or profession"`
	Hobbies     []string `json:"hobbies" jsonschema:"required,description=List of hobbies and interests"`
	City        string   `json:"city" jsonschema:"required,description=City of residence"`
	Email       string   `json:"email,omitempty" jsonschema:"description=Email address if available"`
}

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

	fmt.Println("=== Ollama Structured Output Example ===\n")
	fmt.Println("This example demonstrates how to use JSON schemas with Ollama")
	fmt.Println("to get structured, type-safe responses from language models.\n")

	// Example 1: Schema-based structured output
	fmt.Println("--- Example 1: Schema-Based Structured Output ---")
	fmt.Println("Using a JSON schema to constrain the model's response...\n")

	// Step 1: Define a Go struct with the desired output structure
	// (Already defined above as Person struct)

	// Step 2: Convert the Go struct to a JSON schema
	// We use the jsonschema library to generate a schema from the struct
	reflector := jsonschema.Reflector{
		AllowAdditionalProperties: false,
		DoNotReference:            true,
	}
	schema := reflector.Reflect(&Person{})
	schemaBytes, err := json.Marshal(schema)
	if err != nil {
		log.Fatalf("Failed to marshal schema: %v", err)
	}

	// Convert the schema to a map for use with Genkit
	var schemaMap map[string]any
	if err := json.Unmarshal(schemaBytes, &schemaMap); err != nil {
		log.Fatalf("Failed to unmarshal schema: %v", err)
	}

	// Step 3: Use the schema with ModelRequest
	// The Output field tells Genkit to request structured output from Ollama
	resp, err := genkit.Generate(ctx, g,
		ai.WithModel(model),
		ai.WithMessages(
			ai.NewUserTextMessage("Generate information about a fictional software engineer named Alice who lives in San Francisco."),
		),
		ai.WithOutputConfig(&ai.ModelOutputConfig{
			Format: "json",
			Schema: schemaMap,
		}),
	)
	if err != nil {
		log.Fatalf("Error generating structured output: %v", err)
	}

	// Step 4: Parse the structured response
	// The response text contains JSON that conforms to our schema
	responseText := resp.Text()
	fmt.Printf("Raw JSON response:\n%s\n\n", responseText)

	// Parse the JSON into our Person struct
	var person Person
	if err := json.Unmarshal([]byte(responseText), &person); err != nil {
		log.Fatalf("Failed to parse response: %v", err)
	}

	// Now we have type-safe access to the structured data
	fmt.Printf("Parsed Person:\n")
	fmt.Printf("  Name: %s\n", person.Name)
	fmt.Printf("  Age: %d\n", person.Age)
	fmt.Printf("  Occupation: %s\n", person.Occupation)
	fmt.Printf("  City: %s\n", person.City)
	fmt.Printf("  Hobbies: %v\n", person.Hobbies)
	if person.Email != "" {
		fmt.Printf("  Email: %s\n", person.Email)
	}

	fmt.Println("\n✓ Successfully received and parsed structured output!")
	fmt.Println("\nKey Benefits:")
	fmt.Println("  • Guaranteed JSON structure matching your schema")
	fmt.Println("  • Type-safe parsing into Go structs")
	fmt.Println("  • No need for complex prompt engineering")
	fmt.Println("  • Reliable data extraction for downstream processing")
}
