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
	"fmt"
	"log"
	"os"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/googlegenai"
	"github.com/firebase/genkit/go/plugins/mcp"
)

// MCP Manager Example - connects to time server
func managerExample() {
	ctx := context.Background()

	// Initialize Genkit with Google AI
	g, err := genkit.Init(ctx, genkit.WithPlugins(&googlegenai.GoogleAI{}))
	if err != nil {
		log.Fatal(err)
	}

	// Create and connect to MCP time server
	manager, _ := mcp.NewMCPManager(mcp.MCPManagerOptions{
		Name: "time-example",
		MCPServers: []mcp.MCPServerConfig{
			{
				Name: "time",
				Config: mcp.MCPClientOptions{
					Name:    "mcp-time",
					Version: "1.0.0",
					Stdio: &mcp.StdioConfig{
						Command: "uvx",
						Args:    []string{"mcp-server-time", "--local-timezone=America/New_York"},
					},
				},
			},
		},
	})

	// Get tools and generate response
	tools, _ := manager.GetActiveTools(ctx, g)
	log.Printf("Found %d time tools", len(tools))

	var toolRefs []ai.ToolRef
	for _, tool := range tools {
		toolRefs = append(toolRefs, tool)
	}

	response, err := genkit.Generate(ctx, g,
		ai.WithModelName("googleai/gemini-2.5-pro-preview-05-06"),
		ai.WithPrompt("What time is it in New York and Tokyo?"),
		ai.WithTools(toolRefs...),
		ai.WithToolChoice(ai.ToolChoiceAuto),
	)
	if err != nil {
		log.Printf("Generation failed: %v", err)
	} else {
		log.Printf("Response: %s", response.Text())
	}

	// Disconnect from server
	manager.Disconnect("time")
	log.Println("Disconnected from time server")
}

// MCP Manager Multi-Server Example - connects to both time and fetch servers
func multiServerManagerExample() {
	ctx := context.Background()

	// Initialize Genkit with Google AI
	g, err := genkit.Init(ctx, genkit.WithPlugins(&googlegenai.GoogleAI{}))
	if err != nil {
		log.Fatal(err)
	}

	// Create MCP manager for multiple servers
	manager, _ := mcp.NewMCPManager(mcp.MCPManagerOptions{
		Name: "multi-server-example",
		MCPServers: []mcp.MCPServerConfig{
			{
				Name: "time",
				Config: mcp.MCPClientOptions{
					Name:    "mcp-time",
					Version: "1.0.0",
					Stdio: &mcp.StdioConfig{
						Command: "uvx",
						Args:    []string{"mcp-server-time", "--local-timezone=America/New_York"},
					},
				},
			},
			{
				Name: "fetch",
				Config: mcp.MCPClientOptions{
					Name:    "mcp-fetch",
					Version: "1.0.0",
					Stdio: &mcp.StdioConfig{
						Command: "uvx",
						Args:    []string{"mcp-server-fetch"},
					},
				},
			},
		},
	})

	// Get tools from all connected servers
	tools, _ := manager.GetActiveTools(ctx, g)
	log.Printf("Found %d tools from all servers", len(tools))

	var toolRefs []ai.ToolRef
	for _, tool := range tools {
		toolRefs = append(toolRefs, tool)
	}

	// Generate response using tools from multiple servers
	response, err := genkit.Generate(ctx, g,
		ai.WithModelName("googleai/gemini-2.5-pro-preview-05-06"),
		ai.WithPrompt("What time is it in New York? Also, fetch the latest news from https://httpbin.org/json and tell me what you find."),
		ai.WithTools(toolRefs...),
		ai.WithToolChoice(ai.ToolChoiceAuto),
	)
	if err != nil {
		log.Printf("Generation failed: %v", err)
	} else {
		log.Printf("Response: %s", response.Text())
	}

	// Disconnect from all servers
	manager.Disconnect("time")
	manager.Disconnect("fetch")
	log.Println("Disconnected from all servers")
}

// MCP Client Example - connects to time server
func clientExample() {
	ctx := context.Background()

	// Initialize Genkit with Google AI
	g, err := genkit.Init(ctx, genkit.WithPlugins(&googlegenai.GoogleAI{}))
	if err != nil {
		log.Fatal(err)
	}

	// Create and connect to MCP time server
	client, err := mcp.NewGenkitMCPClient(mcp.MCPClientOptions{
		Name:    "mcp-time",
		Version: "1.0.0",
		Stdio: &mcp.StdioConfig{
			Command: "uvx",
			Args:    []string{"mcp-server-time", "--local-timezone=America/New_York"},
		},
	})
	if err != nil {
		log.Fatal(err)
	}

	// Get tools and generate response
	tools, _ := client.GetActiveTools(ctx, g)
	log.Printf("Found %d time tools", len(tools))

	var toolRefs []ai.ToolRef
	for _, tool := range tools {
		toolRefs = append(toolRefs, tool)
	}

	response, err := genkit.Generate(ctx, g,
		ai.WithModelName("googleai/gemini-2.5-pro-preview-05-06"),
		ai.WithPrompt("Convert the current time from New York to London timezone."),
		ai.WithTools(toolRefs...),
		ai.WithToolChoice(ai.ToolChoiceAuto),
	)
	if err != nil {
		log.Printf("Generation failed: %v", err)
	} else {
		log.Printf("Response: %s", response.Text())
	}

	// Disconnect from server
	log.Println("Disconnecting from server...")
	client.Disconnect()
	log.Println("Disconnected from server")
}

// MCP Client GetPrompt Example - connects to a server and uses prompts
func clientGetPromptExample() {
	ctx := context.Background()

	// Initialize Genkit with Google AI
	g, err := genkit.Init(ctx, genkit.WithPlugins(&googlegenai.GoogleAI{}))
	if err != nil {
		log.Fatal(err)
	}

	log.Println("Creating MCP client...")
	// Create and connect to MCP server (using everything server as example)
	client, err := mcp.NewGenkitMCPClient(mcp.MCPClientOptions{
		Name:    "mcp-everything",
		Version: "1.0.0",
		Stdio: &mcp.StdioConfig{
			Command: "npx",
			Args:    []string{"@modelcontextprotocol/server-everything", "stdio"},
		},
	})
	if err != nil {
		log.Fatal(err)
	}
	log.Println("MCP client created successfully")

	// Get a specific prompt from the server
	log.Println("Getting prompt from server...")
	prompt, err := client.GetPrompt(ctx, g, "simple_prompt", map[string]string{})
	if err != nil {
		log.Printf("Failed to get prompt: %v", err)
	} else {
		log.Printf("Retrieved prompt: %s", prompt.Name())

		// Execute the prompt directly
		log.Println("Executing prompt...")
		response, err := prompt.Execute(ctx,
			ai.WithInput(map[string]interface{}{}),
			ai.WithModelName("googleai/gemini-2.5-pro-preview-05-06"),
		)
		if err != nil {
			log.Printf("Prompt execution failed: %v", err)
		} else {
			log.Printf("Prompt response: %s", response.Text())
		}
	}
}

func main() {
	if len(os.Args) < 2 {
		fmt.Println("Usage: go run main.go [manager|multi|client|getprompt]")
		fmt.Println("  manager   - MCP Manager example with time server")
		fmt.Println("  multi     - MCP Manager example with multiple servers (time and fetch)")
		fmt.Println("  client    - MCP Client example with time server")
		fmt.Println("  getprompt - MCP Client GetPrompt example")
		os.Exit(1)
	}

	switch os.Args[1] {
	case "manager":
		log.Println("Running MCP Manager example...")
		managerExample()
	case "multi":
		log.Println("Running MCP Manager multi-server example...")
		multiServerManagerExample()
	case "client":
		log.Println("Running MCP Client example...")
		clientExample()
	case "getprompt":
		log.Println("Running MCP Client GetPrompt example...")
		clientGetPromptExample()
	default:
		fmt.Printf("Unknown example: %s\n", os.Args[1])
		fmt.Println("Use 'manager', 'multi', 'client', or 'getprompt'")
		os.Exit(1)
	}
}
