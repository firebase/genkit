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

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/googlegenai"
	"github.com/firebase/genkit/go/plugins/mcp"
)

func main() {
	// Choose which sample to run
	// Uncomment the one you want to run

	runMCPEverything()
	//runMCPToolCalling()
}

func runMCPEverything() {
	log.Println("Starting MCP everything sample...")

	ctx := context.Background()

	// Initialize the MCP plugin with the "everything" server
	// The "everything" server provides a variety of sample tools

	log.Println("Creating MCP plugin instance...")
	// Create the MCP plugin instance (trivial initialization)
	mcpPlugin := &mcp.MCP{}

	log.Println("Initializing Google AI plugin...")
	// Initialize Google AI plugin for the model
	googleAIPlugin := &googlegenai.GoogleAI{}

	log.Println("Initializing Genkit with plugins...")
	// Initialize Genkit with both plugins
	g, err := genkit.Init(ctx, genkit.WithPlugins(googleAIPlugin, mcpPlugin))
	if err != nil {
		log.Fatalf("Failed to initialize Genkit: %v", err)
	}

	log.Println("Creating MCP client with 'everything' server...")
	// Now create an MCP client with the "everything" server
	_, err = mcpPlugin.NewClient(mcp.MCPClientOptions{
		ServerName: "everything",
		Version:    "1.0.0",
		// Start the "everything" server as a child process using npx
		ServerProcess: &mcp.StdioConfig{
			Command: "npx",
			Args:    []string{"@modelcontextprotocol/server-everything"},
		},
	}, g)
	if err != nil {
		log.Fatalf("Failed to create MCP client: %v", err)
	}

	log.Println("Getting Gemini model...")
	// Get a model to use
	model := googlegenai.GoogleAIModel(g, "gemini-1.5-pro")
	if model == nil {
		log.Fatal("Failed to get Gemini model")
	}

	log.Println("Setting up tool references...")
	// Define the explicit tool references to use with the model
	// Based on our tool listing, we know that "echo" is available
	echoTool := ai.ToolName("echo")

	log.Println("Creating system and user messages...")
	// Create system message that instructs the model to use the echo tool
	systemMsg := ai.NewSystemTextMessage(
		"You are a helpful assistant that can echo messages back. " +
			"When asked to echo something, use the 'echo' tool with a parameter named 'message' " +
			"that contains the text to echo.")

	// Create user message asking to echo text
	userMsg := ai.NewUserTextMessage("Please echo this message: Hello, world!")

	fmt.Println("Chat session started...")
	fmt.Println("User: Please echo this message: Hello, world!")

	log.Println("Generating initial response...")
	// Generate response with the explicit reference to the MCP tool
	resp, err := genkit.Generate(ctx, g,
		ai.WithModel(model),
		ai.WithMessages(systemMsg, userMsg),
		// Make the specific tool available by referencing it explicitly
		ai.WithTools(echoTool),
		ai.WithToolChoice(ai.ToolChoiceAuto),
	)

	if err != nil {
		log.Fatalf("Error generating response: %v", err)
	}

	// Print the final response
	fmt.Println("\nAssistant:", resp.Text())

	log.Println("Processing follow-up message...")
	// Now demonstrate a follow-up message in the chat
	followupMsg := ai.NewUserTextMessage("Thanks! Now can you echo: The quick brown fox jumps over the lazy dog.")
	fmt.Println("\nUser: Thanks! Now can you echo: The quick brown fox jumps over the lazy dog.")

	completeHistoryAfterFirstTurn := append(resp.Request.Messages, resp.Message)

	// Now add the new user message for the follow-up
	messagesForFollowup := append(completeHistoryAfterFirstTurn, followupMsg)

	log.Println("Generating follow-up response...")
	// Generate a follow-up response with all previous context and the explicit tool reference
	followupResp, err := genkit.Generate(ctx, g,
		ai.WithModel(model),
		ai.WithMessages(messagesForFollowup...),
		// Make the specific tool available by referencing it explicitly again
		ai.WithTools(echoTool),
		ai.WithToolChoice(ai.ToolChoiceAuto),
	)

	if err != nil {
		log.Fatalf("Error generating follow-up response: %v", err)
	}

	// Print the final response
	fmt.Println("\nAssistant:", followupResp.Text())
}
