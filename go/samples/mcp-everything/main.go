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
	"github.com/firebase/genkit/go/plugins/googlegenai"
	"github.com/firebase/genkit/go/plugins/mcp"
)

func main() {
	// Choose which sample to run
	// Uncomment the one you want to run

	runMCPEverything()
	//runMCPDecoupled()
	//runDirectToolTest()
}

// Example using the traditional plugin approach
func runMCPEverything() {
	log.Println("Starting MCP everything sample with plugin approach...")

	ctx := context.Background()

	log.Println("Initializing Google AI plugin...")
	// Initialize Google AI plugin for the model
	googleAIPlugin := &googlegenai.GoogleAI{}

	log.Println("Creating MCP client with 'everything' server...")
	// Create an MCP client with the "everything" server using the plugin approach
	client, err := mcp.NewGenkitMCPClient(mcp.MCPClientOptions{
		Name:    "everything",
		Version: "1.0.0",
		// Start the "everything" server as a child process using stdio transport
		Stdio: &mcp.StdioConfig{
			Command: "npx",
			Args:    []string{"@modelcontextprotocol/server-everything"},
		},
	})
	if err != nil {
		log.Fatalf("Failed to create MCP client: %v", err)
	}

	log.Println("MCP client is ready")

	log.Println("Initializing Genkit with plugins...")
	// Initialize Genkit with both plugins
	g, err := genkit.Init(ctx, genkit.WithPlugins(googleAIPlugin))
	if err != nil {
		log.Fatalf("Failed to initialize Genkit: %v", err)
	}

	// Get MCP tools
	log.Println("Getting MCP tools...")
	tools, err := client.GetActiveTools(ctx, g)
	if err != nil {
		log.Fatalf("Failed to get MCP tools: %v", err)
	}
	log.Printf("Found %d MCP tools", len(tools))

	// Create a generation with Gemini Pro and tools
	log.Println("Creating generation request with tools...")

	// Create generation options
	var genOptions []ai.GenerateOption
	genOptions = append(genOptions,
		ai.WithModelName("googleai/gemini-2.5-pro-preview-05-06"),
		ai.WithPrompt("Please use the 'everything_echo' tool to echo a message. You MUST provide the 'message' parameter with the exact value 'Hello from MCP!' as follows: { \"message\": \"Hello from MCP!\" }"),
		ai.WithToolChoice(ai.ToolChoiceAuto),
		ai.WithTools(
			genkit.LookupTool(g, "everything_echo"),
			genkit.LookupTool(g, "everything_add"),
		))

	// Generate the response with tools
	response, err := genkit.Generate(ctx, g, genOptions...)
	if err != nil {
		log.Fatalf("Failed to generate response: %v", err)
	}

	// Print the response
	log.Println("Generated response:")
	fmt.Println(response.Text())
}

// Test function to directly call the echo tool with the correct parameters
func runDirectToolTest() {
	log.Println("Starting direct tool test...")

	ctx := context.Background()

	// Create MCP client
	client, err := mcp.NewGenkitMCPClient(mcp.MCPClientOptions{
		Name:    "everything",
		Version: "1.0.0",
		Stdio: &mcp.StdioConfig{
			Command: "npx",
			Args:    []string{"@modelcontextprotocol/server-everything"},
		},
	})
	if err != nil {
		log.Fatalf("Failed to create MCP client: %v", err)
	}

	log.Println("MCP client is ready")

	// Initialize Genkit without Google AI plugin
	g, err := genkit.Init(ctx)
	if err != nil {
		log.Fatalf("Failed to initialize Genkit: %v", err)
	}

	// Get MCP tools
	log.Println("Getting MCP tools...")
	tools, err := client.GetActiveTools(ctx, g)
	if err != nil {
		log.Fatalf("Failed to get tools from MCP client: %v", err)
	}
	log.Printf("Found %d tools from MCP client", len(tools))

	// Find the echo tool directly from registry to test
	echoTool := genkit.LookupTool(g, "everything_echo")
	if echoTool == nil {
		log.Fatalf("Could not find the 'everything_echo' tool")
	}

	log.Println("Found echo tool, calling it directly...")

	// Create correct arguments with the required "message" parameter
	args := map[string]interface{}{
		"message": "Direct test message",
	}

	// Print the args
	argsJSON, _ := json.MarshalIndent(args, "", "  ")
	log.Printf("Calling echo tool with args: %s", argsJSON)

	// Call the tool directly using RunRaw method
	result, err := echoTool.RunRaw(ctx, args)
	if err != nil {
		log.Fatalf("Failed to call echo tool: %v", err)
	}

	// Print the result
	resultJSON, _ := json.MarshalIndent(result, "", "  ")
	log.Printf("Echo tool result: %s", resultJSON)
}
