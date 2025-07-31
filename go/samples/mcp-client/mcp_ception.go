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
	"os/signal"
	"syscall"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/core/logger"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/googlegenai"
	"github.com/firebase/genkit/go/plugins/mcp"
)

// MCP-ception Example: Genkit serves itself through MCP!
// 1. Start a Go MCP server that exposes Genkit resources
// 2. Connect to that server as an MCP client
// 3. Use the resources from the server for AI generation

// Step 1: Create the MCP Server (runs in background)
func createMCPServer() {
	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer cancel()

	logger.FromContext(ctx).Info("🚀 Starting Genkit MCP Server...")

	// Initialize Genkit for the server
	g, err := genkit.Init(ctx)
	if err != nil {
		logger.FromContext(ctx).Error("Failed to initialize Genkit server", "error", err)
		os.Exit(1)
	}

	// Define a tool that generates creative content (this will be auto-exposed via MCP)
	genkit.DefineTool(g, "genkit-brainstorm", "Generate creative ideas about a topic",
		func(ctx *ai.ToolContext, input struct {
			Topic string `json:"topic" description:"The topic to brainstorm about"`
		}) (map[string]interface{}, error) {
			logger.FromContext(ctx.Context).Debug("Executing genkit-brainstorm tool", "topic", input.Topic)

			ideas := fmt.Sprintf(`💡 Creative Ideas for "%s":

1. Interactive Experience: Create an immersive, hands-on workshop
2. Digital Innovation: Develop a mobile app or web platform
3. Community Building: Start a local meetup or online community
4. Educational Content: Design a course or tutorial series
5. Collaborative Project: Partner with others for cross-pollination
6. Storytelling Approach: Create narratives around the topic
7. Gamification: Turn learning into an engaging game
8. Real-world Application: Find practical, everyday uses
9. Creative Challenge: Host competitions or hackathons
10. Multi-media Approach: Combine video, audio, and interactive elements

🎯 These ideas can be mixed, matched, and customized for "%s"!`, input.Topic, input.Topic)

			return map[string]interface{}{
				"topic": input.Topic,
				"ideas": ideas,
			}, nil
		})

	// Define a resource that contains Genkit knowledge (this will be auto-exposed via MCP)
	err = genkit.DefineResource(g, genkit.ResourceOptions{
		Name: "genkit-knowledge",
		URI:  "knowledge://genkit-docs",
	}, func(ctx context.Context, input core.ResourceInput) (genkit.ResourceOutput, error) {
		knowledge := `# Genkit Knowledge Base

## What is Genkit?
Genkit is Firebase's open-source framework for building AI-powered applications.

## Key Features:
- Multi-modal AI generation (text, images, audio)
- Tool calling and function execution
- RAG (Retrieval Augmented Generation) support
- Evaluation and testing frameworks
- Multi-language support (TypeScript, Go, Python)

## Popular Models:
- Google AI: Gemini 1.5 Flash, Gemini 2.0 Flash
- Vertex AI: All Gemini models
- OpenAI Compatible models via plugins

## Use Cases:
- Chatbots and conversational AI
- Content generation and editing
- Code analysis and generation
- Document processing and summarization
- Creative applications (story writing, brainstorming)

## Architecture:
Genkit follows a plugin-based architecture where models, retrievers, evaluators, and other components are provided by plugins.`

		return genkit.ResourceOutput{
			Content: []*ai.Part{ai.NewTextPart(knowledge)},
		}, nil
	})
	if err != nil {
		logger.FromContext(ctx).Error("Failed to create resource", "error", err)
		os.Exit(1)
	}

	// Create MCP server (automatically exposes all defined tools and resources)
	server := mcp.NewMCPServer(g, mcp.MCPServerOptions{
		Name:    "genkit-mcp-server",
		Version: "1.0.0",
	})

	logger.FromContext(ctx).Info("✅ Genkit MCP Server configured successfully")
	logger.FromContext(ctx).Info("📡 Starting MCP server on stdio...")
	logger.FromContext(ctx).Info("🔧 Tools:", "count", len(server.ListRegisteredTools()))
	logger.FromContext(ctx).Info("📚 Resources:", "count", len(server.ListRegisteredResources()))

	// Start the server
	if err := server.ServeStdio(); err != nil && err != context.Canceled {
		logger.FromContext(ctx).Error("MCP server failed", "error", err)
		os.Exit(1)
	}
}

// Step 2: Create the MCP Client that connects to our server
func mcpCeptionDemo() {
	ctx := context.Background()

	logger.FromContext(ctx).Info("🎭 === MCP-CEPTION DEMO ===")
	logger.FromContext(ctx).Info("🎯 Genkit will connect to itself via MCP!")

	// Initialize Genkit with Google AI for the client
	g, err := genkit.Init(ctx,
		genkit.WithPlugins(&googlegenai.GoogleAI{}),
		genkit.WithDefaultModel("googleai/gemini-2.0-flash"),
	)
	if err != nil {
		log.Fatalf("Failed to initialize Genkit client: %v", err)
	}

	logger.FromContext(ctx).Info("🔌 Connecting to our own MCP server...")
	logger.FromContext(ctx).Info("💡 Make sure to run 'go run mcp_ception.go server' in another terminal first!")

	// Create MCP Host that connects to our Genkit server
	host, err := mcp.NewMCPHost(g, mcp.MCPHostOptions{
		Name: "mcp-ception-host",
		MCPServers: []mcp.MCPServerConfig{
			{
				Name: "genkit-server",
				Config: mcp.MCPClientOptions{
					Name:    "genkit-mcp-server",
					Version: "1.0.0",
					Stdio: &mcp.StdioConfig{
						Command: "go",
						Args:    []string{"run", "mcp_ception.go", "server"},
					},
				},
			},
		},
	})
	if err != nil {
		logger.FromContext(ctx).Error("Failed to create MCP host", "error", err)
		return
	}

	// Get resources from our Genkit server
	logger.FromContext(ctx).Info("📚 Getting resources from Genkit MCP server...")
	resources, err := host.GetActiveResources(ctx)
	if err != nil {
		logger.FromContext(ctx).Error("Failed to get resources", "error", err)
		return
	}

	logger.FromContext(ctx).Info("✅ Retrieved resources from ourselves!", "count", len(resources))

	// DEBUG: Let's examine what resources we actually got
	for i, resource := range resources {
		logger.FromContext(ctx).Info("🔍 DEBUG Resource details", "index", i, "name", resource.Name())
		// Test if the resource matches our target URI
		matches := resource.Matches("knowledge://genkit-docs")
		logger.FromContext(ctx).Info("🔍 Resource URI matching", "matches_target_uri", matches)
	}

	// Get tools from our Genkit server
	logger.FromContext(ctx).Info("🔧 Getting tools from Genkit MCP server...")
	tools, err := host.GetActiveTools(ctx, g)
	if err != nil {
		logger.FromContext(ctx).Error("Failed to get tools", "error", err)
		return
	}

	logger.FromContext(ctx).Info("✅ Retrieved tools from ourselves!", "count", len(tools))

	// Convert tools to refs
	var toolRefs []ai.ToolRef
	for _, tool := range tools {
		toolRefs = append(toolRefs, tool)
	}

	// Step 3: Use resources and tools from our own server for AI generation
	logger.FromContext(ctx).Info("🤖 Asking AI about Genkit using our own MCP resources...")

	// THE CORRECT WAY: Use ai.NewResourcePart to explicitly reference the resource
	logger.FromContext(ctx).Info("🔍 DEBUG Generation call", "resource_count", len(resources), "tool_count", len(toolRefs))

	response, err := genkit.Generate(ctx, g,
		ai.WithMessages(ai.NewUserMessage(
			ai.NewTextPart("Based on this Genkit knowledge:"),
			ai.NewResourcePart("knowledge://genkit-docs"), // ← FIXED: Explicit resource reference!
			ai.NewTextPart("What are the key features of Genkit and what models does it support?\n\nAlso, use the brainstorm tool to generate ideas for \"AI-powered cooking assistant\""),
		)),
		ai.WithResources(resources), // Makes resources available for lookup
		ai.WithTools(toolRefs...),   // Using tools from our own server!
		ai.WithToolChoice(ai.ToolChoiceAuto),
	)
	if err != nil {
		logger.FromContext(ctx).Error("AI generation failed", "error", err)
		return
	}

	logger.FromContext(ctx).Info("🎉 MCP-CEPTION SUCCESS!")
	logger.FromContext(ctx).Info("✨ Genkit used itself via MCP to answer questions!")
	fmt.Printf("\n🤖 AI Response using our own MCP resources:\n%s\n\n", response.Text())

	// Clean disconnect (skip for now to avoid hanging)
	logger.FromContext(ctx).Info("✅ MCP-ception complete! 🎭")
}

func main() {
	if len(os.Args) < 2 {
		fmt.Println("Usage: go run mcp_ception.go [server|demo]")
		fmt.Println("  server - Run as MCP server (exposes Genkit resources)")
		fmt.Println("  demo   - Run MCP-ception demo (connects to server)")
		os.Exit(1)
	}

	switch os.Args[1] {
	case "server":
		createMCPServer()
	case "demo":
		mcpCeptionDemo()
	default:
		fmt.Printf("Unknown command: %s\n", os.Args[1])
		fmt.Println("Use 'server' or 'demo'")
		os.Exit(1)
	}
}
