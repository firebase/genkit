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
//
// SPDX-License-Identifier: Apache-2.0

/*
Product Generator using Genkit and Dotprompt

This application demonstrates a structured product generation system that uses:
- Genkit: A framework for managing AI model interactions and prompts
- Dotprompt: A library for working with structured prompts and JSON schemas
- JSON Schema: For defining the structure of generated product data

The program:
1. Defines a ProductSchema struct for structured product data
2. Creates a mock AI model plugin that returns predefined product data
3. Generates and saves JSON schema files in a prompts directory
4. Creates a prompt template that takes a theme as input and outputs a product
5. Initializes Dotprompt with schema resolution capabilities
6. Executes the prompt with an "eco-friendly" theme
7. Parses the structured response and displays the generated product

The mock implementation simulates what would happen with a real AI model
by returning different products based on detected themes in the input.
This provides a testable framework for structured AI outputs conforming
to the defined schema.
*/

package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strings"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/google/dotprompt/go/dotprompt"
	"github.com/invopop/jsonschema"
)

// ProductSchema defines our product output structure
// This schema will be used for structured outputs from AI models
type ProductSchema struct {
	Name        string  `json:"name"`
	Description string  `json:"description"`
	Price       float64 `json:"price"`
	Category    string  `json:"category"`
	InStock     bool    `json:"inStock"`
}

// MockPlugin implements the genkit.Plugin interface
// It provides a custom model implementation for testing purposes
type MockPlugin struct{}

// Name returns the unique identifier for the plugin
func (p *MockPlugin) Name() string {
	return "mock"
}

// Init initializes the plugin with the Genkit instance
// It registers a mock model that returns predefined product data
func (p *MockPlugin) Init(ctx context.Context, g *genkit.Genkit) error {
	genkit.DefineModel(g, "mock", "product-model",
		&ai.ModelInfo{
			Label:    "Mock Product Model",
			Supports: &ai.ModelSupports{},
		},
		func(ctx context.Context, req *ai.ModelRequest, cb ai.ModelStreamCallback) (*ai.ModelResponse, error) {
			product := ProductSchema{
				Name:        "Eco-Friendly Bamboo Cutting Board",
				Description: "A sustainable cutting board made from 100% bamboo. Features a juice groove and handle.",
				Price:       29.99,
				Category:    "Kitchen Accessories",
				InStock:     true,
			}

			jsonBytes, err := json.Marshal(product)
			if err != nil {
				return nil, err
			}

			resp := &ai.ModelResponse{
				Message: &ai.Message{
					Role:    ai.RoleModel,
					Content: []*ai.Part{ai.NewTextPart(string(jsonBytes))},
				},
				FinishReason: ai.FinishReasonStop,
			}

			return resp, nil
		})

	return nil
}

func main() {
	ctx := context.Background()

	cwd, _ := os.Getwd()
	promptDir := filepath.Join(cwd, "prompts")

	if _, err := os.Stat(promptDir); os.IsNotExist(err) {
		if err := os.MkdirAll(promptDir, 0755); err != nil {
			log.Fatalf("Failed to create prompt directory: %v", err)
		}
	}

	schemaFilePath := filepath.Join(promptDir, "_schema_ProductSchema.partial.prompt")

	reflector := jsonschema.Reflector{}
	schema := reflector.Reflect(ProductSchema{})

	// Structure the schema according to what Dotprompt expects
	schemaWrapper := struct {
		Schema      string                        `json:"$schema"`
		Ref         string                        `json:"$ref"`
		Definitions map[string]*jsonschema.Schema `json:"$defs"`
	}{
		Schema: "https://json-schema.org/draft/2020-12/schema",
		Ref:    "#/$defs/ProductSchema",
		Definitions: map[string]*jsonschema.Schema{
			"ProductSchema": schema,
		},
	}

	schemaJSON, err := json.MarshalIndent(schemaWrapper, "", "  ")
	if err != nil {
		log.Fatalf("Failed to marshal schema: %v", err)
	}

	if err := os.WriteFile(schemaFilePath, schemaJSON, 0644); err != nil {
		log.Fatalf("Failed to write schema file: %v", err)
	}

	// Create prompt file with schema reference
	promptFilePath := filepath.Join(promptDir, "product_generator.prompt")
	promptContent := "---\n" +
		"input:\n" +
		"  schema:\n" +
		"    theme: string\n" +
		"output:\n" +
		"  schema: ProductSchema\n" +
		"---\n" +
		"Generate a product that fits the {{theme}} theme.\n" +
		"Make sure to provide a detailed description and appropriate pricing."

	if err := os.WriteFile(promptFilePath, []byte(promptContent), 0644); err != nil {
		log.Fatalf("Failed to write prompt file: %v", err)
	}

	// Testing with dotprompt directly
	dp := dotprompt.NewDotprompt(&dotprompt.DotpromptOptions{
		Schemas: map[string]*jsonschema.Schema{},
	})

	// Register external schema lookup function
	dp.RegisterExternalSchemaLookup(func(schemaName string) any {
		if schemaName == "ProductSchema" {
			return schema
		}
		return nil
	})

	metadata := map[string]any{
		"output": map[string]any{
			"schema": "ProductSchema",
		},
	}

	if err = dp.ResolveSchemaReferences(metadata); err != nil {
		log.Fatalf("Schema resolution failed: %v", err)
	}

	// Define our schema with Genkit
	genkit.DefineSchema("ProductSchema", ProductSchema{})

	// Initialize Genkit with our prompt directory
	g, err := genkit.Init(ctx,
		genkit.WithPromptDir(promptDir),
		genkit.WithDefaultModel("mock/default-model"))
	if err != nil {
		log.Fatalf("Failed to initialize Genkit: %v", err)
	}

	// Define a mock model to respond to prompts
	genkit.DefineModel(g, "mock", "default-model",
		&ai.ModelInfo{
			Label:    "Mock Default Model",
			Supports: &ai.ModelSupports{},
		},
		func(ctx context.Context, req *ai.ModelRequest, cb ai.ModelStreamCallback) (*ai.ModelResponse, error) {
			// Extract theme from the request to customize the response
			theme := "generic"
			if len(req.Messages) > 0 {
				lastMsg := req.Messages[len(req.Messages)-1]
				if lastMsg.Role == ai.RoleUser {
					for _, part := range lastMsg.Content {
						if part.IsText() && strings.Contains(part.Text, "eco-friendly") {
							theme = "eco-friendly"
						}
					}
				}
			}

			// Generate appropriate product based on theme
			var product ProductSchema
			if theme == "eco-friendly" {
				product = ProductSchema{
					Name:        "Eco-Friendly Bamboo Cutting Board",
					Description: "A sustainable cutting board made from 100% bamboo. Features a juice groove and handle.",
					Price:       29.99,
					Category:    "Kitchen Accessories",
					InStock:     true,
				}
			} else {
				product = ProductSchema{
					Name:        "Classic Stainless Steel Water Bottle",
					Description: "Durable 24oz water bottle with vacuum insulation. Keeps drinks cold for 24 hours.",
					Price:       24.99,
					Category:    "Drinkware",
					InStock:     true,
				}
			}

			jsonBytes, err := json.Marshal(product)
			if err != nil {
				return nil, err
			}

			resp := &ai.ModelResponse{
				Message: &ai.Message{
					Role:    ai.RoleModel,
					Content: []*ai.Part{ai.NewTextPart(string(jsonBytes))},
				},
				FinishReason: ai.FinishReasonStop,
			}

			return resp, nil
		})

	// Look up and execute the prompt
	productPrompt := genkit.LookupPrompt(g, "local", "product_generator")
	if productPrompt == nil {
		log.Fatalf("Prompt 'product_generator' not found")
	}

	input := map[string]any{
		"theme": "eco-friendly kitchen gadgets",
	}

	resp, err := productPrompt.Execute(ctx, ai.WithInput(input))
	if err != nil {
		log.Fatalf("Failed to execute prompt: %v", err)
	}

	// Parse the structured response into our Go struct
	var product ProductSchema
	if err := resp.Output(&product); err != nil {
		log.Fatalf("Failed to parse response: %v", err)
	}

	fmt.Println("\nGenerated Product:")
	fmt.Printf("Name: %s\n", product.Name)
	fmt.Printf("Description: %s\n", product.Description)
	fmt.Printf("Price: $%.2f\n", product.Price)
	fmt.Printf("Category: %s\n", product.Category)
	fmt.Printf("In Stock: %v\n", product.InStock)
}
