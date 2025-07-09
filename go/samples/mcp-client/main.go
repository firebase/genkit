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
	"os"
	"time"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/core/logger"
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
		logger.FromContext(ctx).Error("Failed to initialize Genkit", "error", err)
		return
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
	logger.FromContext(ctx).Info("Found MCP tools", "count", len(tools), "example", "time")

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
		logger.FromContext(ctx).Error("Generation failed", "error", err)
	} else {
		logger.FromContext(ctx).Info("Generation completed", "response", response.Text())
	}

	// Disconnect from server
	manager.Disconnect(ctx, "time")
	logger.FromContext(ctx).Info("Disconnected from MCP server", "server", "time")
}

// MCP Manager Multi-Server Example - connects to both time and fetch servers
func multiServerManagerExample() {
	ctx := context.Background()

	// Initialize Genkit with Google AI
	g, err := genkit.Init(ctx, genkit.WithPlugins(&googlegenai.GoogleAI{}))
	if err != nil {
		logger.FromContext(ctx).Error("Failed to initialize Genkit", "error", err)
		return
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
	logger.FromContext(ctx).Info("Found MCP tools from all servers", "count", len(tools), "servers", []string{"time", "fetch"})

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
		logger.FromContext(ctx).Error("Generation failed", "error", err)
	} else {
		logger.FromContext(ctx).Info("Generation completed", "response", response.Text())
	}

	// Disconnect from all servers
	manager.Disconnect(ctx, "time")
	manager.Disconnect(ctx, "fetch")
	logger.FromContext(ctx).Info("Disconnected from all MCP servers", "servers", []string{"time", "fetch"})
}

// MCP Client Example - connects to time server
func clientExample() {
	ctx := context.Background()

	// Initialize Genkit with Google AI
	g, err := genkit.Init(ctx, genkit.WithPlugins(&googlegenai.GoogleAI{}))
	if err != nil {
		logger.FromContext(ctx).Error("Failed to initialize Genkit", "error", err)
		return
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
		logger.FromContext(ctx).Error("Failed to create MCP client", "error", err)
		return
	}

	// Get tools and generate response
	tools, _ := client.GetActiveTools(ctx, g)
	logger.FromContext(ctx).Info("Found MCP time tools", "count", len(tools), "client", "mcp-time")

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
		logger.FromContext(ctx).Error("Generation failed", "error", err)
	} else {
		logger.FromContext(ctx).Info("Generation completed", "response", response.Text())
	}

	// Disconnect from server
	logger.FromContext(ctx).Info("Disconnecting from MCP server", "client", "mcp-time")
	client.Disconnect()
	logger.FromContext(ctx).Info("Disconnected from MCP server", "client", "mcp-time")
}

// MCP Client GetPrompt Example - connects to a server and uses prompts
func clientGetPromptExample() {
	ctx := context.Background()

	// Initialize Genkit with Google AI
	g, err := genkit.Init(ctx, genkit.WithPlugins(&googlegenai.GoogleAI{}))
	if err != nil {
		logger.FromContext(ctx).Error("Failed to initialize Genkit", "error", err)
		return
	}

	logger.FromContext(ctx).Info("Creating MCP client", "server", "everything")
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
		logger.FromContext(ctx).Error("Failed to create MCP client", "error", err)
		return
	}
	logger.FromContext(ctx).Info("MCP client created successfully", "client", "mcp-everything")

	// Get a specific prompt from the server
	logger.FromContext(ctx).Info("Getting prompt from MCP server", "prompt", "simple_prompt")
	prompt, err := client.GetPrompt(ctx, g, "simple_prompt", map[string]string{})
	if err != nil {
		logger.FromContext(ctx).Error("Failed to get prompt", "prompt", "simple_prompt", "error", err)
	} else {
		logger.FromContext(ctx).Info("Retrieved prompt successfully", "promptName", prompt.Name())

		// Execute the prompt directly
		logger.FromContext(ctx).Info("Executing prompt", "prompt", prompt.Name())
		response, err := prompt.Execute(ctx,
			ai.WithInput(map[string]interface{}{}),
			ai.WithModelName("googleai/gemini-2.5-pro-preview-05-06"),
		)
		if err != nil {
			logger.FromContext(ctx).Error("Prompt execution failed", "prompt", prompt.Name(), "error", err)
		} else {
			logger.FromContext(ctx).Info("Prompt execution completed", "prompt", prompt.Name(), "response", response.Text())
		}
	}
}

// MCP Client Streamable HTTP Example - connects to a server via Streamable HTTP transport
func clientStreamableHTTPExample() {
	ctx := context.Background()

	// Initialize Genkit with Google AI
	g, err := genkit.Init(ctx, genkit.WithPlugins(&googlegenai.GoogleAI{}))
	if err != nil {
		logger.FromContext(ctx).Error("Failed to initialize Genkit", "error", err)
		return
	}

	logger.FromContext(ctx).Info("Creating MCP client with Streamable HTTP transport", "server", "everything")
	// Create and connect to MCP server using Streamable HTTP transport
	// Note: Start the server with: npx @modelcontextprotocol/server-everything streamableHttp --port 3001
	// This will start the server on http://localhost:3001
	client, err := mcp.NewGenkitMCPClient(mcp.MCPClientOptions{
		Name:    "mcp-everything-http",
		Version: "1.0.0",
		StreamableHTTP: &mcp.StreamableHTTPConfig{
			BaseURL: "http://localhost:3001",
			Headers: map[string]string{
				"User-Agent": "genkit-mcp-client/1.0.0",
			},
			Timeout: 30 * time.Second, // Optional timeout
		},
	})
	if err != nil {
		logger.FromContext(ctx).Error("Failed to create MCP client with Streamable HTTP", "error", err)
		return
	}
	logger.FromContext(ctx).Info("MCP client with Streamable HTTP created successfully", "client", "mcp-everything-http")

	// Get tools and generate response
	tools, _ := client.GetActiveTools(ctx, g)
	logger.FromContext(ctx).Info("Found MCP tools via Streamable HTTP", "count", len(tools), "client", "mcp-everything-http")

	var toolRefs []ai.ToolRef
	for _, tool := range tools {
		toolRefs = append(toolRefs, tool)
	}

	// Generate response using tools from the HTTP server
	response, err := genkit.Generate(ctx, g,
		ai.WithModelName("googleai/gemini-2.0-flash-exp"),
		ai.WithPrompt("Use the echo tool to repeat the message 'Hello from Streamable HTTP!' and then use the add tool to calculate 15 + 27."),
		ai.WithTools(toolRefs...),
		ai.WithToolChoice(ai.ToolChoiceAuto),
	)
	if err != nil {
		logger.FromContext(ctx).Error("Generation failed", "error", err)
	} else {
		logger.FromContext(ctx).Info("Generation completed", "response", response.Text())
	}

	// Disconnect from server
	logger.FromContext(ctx).Info("Disconnecting from MCP server", "client", "mcp-everything-http")
	client.Disconnect()
	logger.FromContext(ctx).Info("Disconnected from MCP server", "client", "mcp-everything-http")
}

func main() {
	if len(os.Args) < 2 {
		fmt.Println("Usage: go run main.go [manager|multi|client|getprompt|streamablehttp|test]")
		fmt.Println("  manager        - MCP Manager example with time server")
		fmt.Println("  multi          - MCP Manager example with multiple servers (time and fetch)")
		fmt.Println("  client         - MCP Client example with time server")
		fmt.Println("  getprompt      - MCP Client GetPrompt example")
		fmt.Println("  streamablehttp - MCP Client Streamable HTTP example")
		os.Exit(1)
	}

	ctx := context.Background()

	switch os.Args[1] {
	case "manager":
		logger.FromContext(ctx).Info("Running MCP Manager example")
		managerExample()
	case "multi":
		logger.FromContext(ctx).Info("Running MCP Manager multi-server example")
		multiServerManagerExample()
	case "client":
		logger.FromContext(ctx).Info("Running MCP Client example")
		clientExample()
	case "getprompt":
		logger.FromContext(ctx).Info("Running MCP Client GetPrompt example")
		clientGetPromptExample()
	case "streamablehttp":
		logger.FromContext(ctx).Info("Running MCP Client Streamable HTTP example")
		clientStreamableHTTPExample()
	default:
		fmt.Printf("Unknown example: %s\n", os.Args[1])
		fmt.Println("Use 'manager', 'multi', 'client', 'getprompt', or 'streamablehttp'")
		os.Exit(1)
	}
}
