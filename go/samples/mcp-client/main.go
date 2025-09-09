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

// MCP Host Example - connects to time server and demonstrates both tools and resources
func managerExample() {
	ctx := context.Background()

	// Initialize Genkit with Google AI
	g := genkit.Init(ctx, genkit.WithPlugins(&googlegenai.GoogleAI{}))

	// Create and connect to MCP time server
	host, _ := mcp.NewMCPHost(g, mcp.MCPHostOptions{
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

	// Get tools and resources from MCP servers
	tools, _ := host.GetActiveTools(ctx, g)
	logger.FromContext(ctx).Info("Found MCP tools", "count", len(tools), "example", "time")

	// Get detached resources from MCP servers (not auto-registered)
	allResources, err := host.GetActiveResources(ctx)
	if err != nil {
		logger.FromContext(ctx).Warn("Failed to get MCP resources", "error", err)
	} else {
		logger.FromContext(ctx).Info("Successfully got detached MCP resources", "count", len(allResources))
		// Resources can be used via ai.WithResources() in generate calls
		logger.FromContext(ctx).Info("Resources can be used in prompts via ai.WithResources()")
	}

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
	host.Disconnect(ctx, "time")
	logger.FromContext(ctx).Info("Disconnected from MCP server", "server", "time")
}

// MCP Host Multi-Server Example - connects to both time and fetch servers, demonstrates tools and resources
func multiServerManagerExample() {
	ctx := context.Background()

	// Initialize Genkit with Google AI
	g := genkit.Init(ctx, genkit.WithPlugins(&googlegenai.GoogleAI{}))

	// Create MCP host for multiple servers
	host, _ := mcp.NewMCPHost(g, mcp.MCPHostOptions{
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

	// Get tools and resources from all connected servers
	tools, _ := host.GetActiveTools(ctx, g)
	logger.FromContext(ctx).Info("Found MCP tools from all servers", "count", len(tools), "servers", []string{"time", "fetch"})

	// Get detached resources from all MCP servers
	allResources2, err := host.GetActiveResources(ctx)
	if err != nil {
		logger.FromContext(ctx).Warn("Failed to get MCP resources from servers", "error", err)
	} else {
		logger.FromContext(ctx).Info("Successfully got detached MCP resources from all servers", "count", len(allResources2), "servers", []string{"time", "fetch"})
	}

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
	host.Disconnect(ctx, "time")
	host.Disconnect(ctx, "fetch")
	logger.FromContext(ctx).Info("Disconnected from all MCP servers", "servers", []string{"time", "fetch"})
}

// MCP Client Example - connects to time server
func clientExample() {
	ctx := context.Background()

	// Initialize Genkit with Google AI
	g := genkit.Init(ctx, genkit.WithPlugins(&googlegenai.GoogleAI{}))

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
	g := genkit.Init(ctx, genkit.WithPlugins(&googlegenai.GoogleAI{}))

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
	g := genkit.Init(ctx, genkit.WithPlugins(&googlegenai.GoogleAI{}))

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

// MCP Resources Example - demonstrates how to connect to servers and actually use their resources
func resourcesExample() {
	ctx := context.Background()

	// Initialize Genkit with Google AI plugin and default model
	g := genkit.Init(ctx,
		genkit.WithPlugins(&googlegenai.GoogleAI{}),
		genkit.WithDefaultModel("googleai/gemini-2.0-flash"),
	)

	logger.FromContext(ctx).Info("Starting MCP Resources demonstration")

	// === Example 1: Connect to a server that actually provides resources ===
	logger.FromContext(ctx).Info("Creating MCP client for everything server (has sample resources)")
	// This server actually provides sample resources we can read
	everythingClient, err := mcp.NewGenkitMCPClient(mcp.MCPClientOptions{
		Name:    "mcp-everything",
		Version: "1.0.0",
		Stdio: &mcp.StdioConfig{
			Command: "npx",
			Args:    []string{"@modelcontextprotocol/server-everything", "stdio"},
		},
	})
	if err != nil {
		logger.FromContext(ctx).Warn("Failed to create everything MCP client (install: npm install -g @modelcontextprotocol/server-everything)", "error", err)
	} else {
		logger.FromContext(ctx).Info("Everything MCP client created successfully")

		// Get detached resources from the everything server (without auto-registering)
		resources, err := everythingClient.GetActiveResources(ctx)
		if err != nil {
			logger.FromContext(ctx).Warn("Failed to get everything server resources", "error", err)
		} else {
			logger.FromContext(ctx).Info("Got detached resources from everything server", "count", len(resources))

			// Demonstrate the streamlined UX: use resources directly in generate calls
			if len(resources) > 0 {
				logger.FromContext(ctx).Info("Demonstrating streamlined resource usage...")

				// Limit resources to avoid overwhelming the model (just use first 3 for demo)
				limitedResources := resources
				if len(resources) > 3 {
					limitedResources = resources[:3]
					logger.FromContext(ctx).Info("Limiting to first 3 resources for demo", "total", len(resources), "using", len(limitedResources))
				}

				// Example: Use MCP resources in an AI generation call
				response, err := genkit.Generate(ctx, g,
					ai.WithMessages(ai.NewUserMessage(
						ai.NewTextPart("List the available resources and describe what each one contains."),
						// Resource references will be resolved automatically from the detached resources
					)),
					ai.WithResources(limitedResources...),
				)
				if err != nil {
					logger.FromContext(ctx).Warn("Failed to generate with MCP resources", "error", err)
				} else {
					logger.FromContext(ctx).Info("Generated response using MCP resources", "response", response.Text())
				}

				// Show available resource names for reference
				logger.FromContext(ctx).Info("Available resources:")
				for i, resource := range resources {
					logger.FromContext(ctx).Info("Resource available",
						"index", i,
						"name", resource.Name())
					// Only show first few for demo
					if i >= 2 {
						logger.FromContext(ctx).Info("... and more resources available")
						break
					}
				}
			} else {
				logger.FromContext(ctx).Info("No resources available from everything server")
			}
		}

		// Disconnect from everything server
		everythingClient.Disconnect()
		logger.FromContext(ctx).Info("Disconnected from everything server")
	}

	// === Example 2: Simple resource workflow ===
	// Create a detached resource from your own code that you can use in AI generation
	configResource := genkit.NewResource("app-config", &ai.ResourceOptions{
		URI: "config://app.json",
	}, func(ctx context.Context, input *ai.ResourceInput) (*ai.ResourceOutput, error) {
		config := `{"app": "MyApp", "version": "1.0", "features": ["auth", "chat"]}`
		return &ai.ResourceOutput{
			Content: []*ai.Part{ai.NewTextPart(config)},
		}, nil
	})

	response, err := genkit.Generate(ctx, g,
		ai.WithMessages(
			ai.NewUserMessage(
				ai.NewTextPart("Here's my config, what features does it have?"),
				ai.NewResourcePart("config://app.json"),
			),
		),
		ai.WithResources(configResource), // Pass detached resource
	)

	if err == nil {
		logger.FromContext(ctx).Info("Resource workflow complete", "response", response.Text())
	}

	logger.FromContext(ctx).Info("MCP Resources demonstration completed")
}

func main() {
	if len(os.Args) < 2 {
		fmt.Println("Usage: go run main.go [manager|multi|client|getprompt|streamablehttp|resources]")
		fmt.Println("  manager        - MCP Host example with time server (tools & resources)")
		fmt.Println("  multi          - MCP Host example with multiple servers (tools & resources)")
		fmt.Println("  client         - MCP Client example with time server")
		fmt.Println("  getprompt      - MCP Client GetPrompt example")
		fmt.Println("  streamablehttp - MCP Client Streamable HTTP example")
		fmt.Println("  resources      - MCP Resources example (filesystem & demo server)")
		os.Exit(1)
	}

	ctx := context.Background()

	switch os.Args[1] {
	case "manager":
		logger.FromContext(ctx).Info("Running MCP Host example")
		managerExample()
	case "multi":
		logger.FromContext(ctx).Info("Running MCP Host multi-server example")
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
	case "resources":
		logger.FromContext(ctx).Info("Running MCP Resources example")
		resourcesExample()
	default:
		fmt.Printf("Unknown example: %s\n", os.Args[1])
		fmt.Println("Use 'manager', 'multi', 'client', 'getprompt', 'streamablehttp', or 'resources'")
		os.Exit(1)
	}
}
