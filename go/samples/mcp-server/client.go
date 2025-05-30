// Run with: export GOOGLE_AI_API_KEY=your_key && go run client.go
package main

import (
	"context"
	"log"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/googlegenai"
	"github.com/firebase/genkit/go/plugins/mcp"
)

func client() {
	ctx := context.Background()

	// Initialize Genkit with Google AI
	g, err := genkit.Init(ctx, genkit.WithPlugins(&googlegenai.GoogleAI{}))
	if err != nil {
		log.Fatal(err)
	}

	// Connect to server
	client, err := mcp.NewGenkitMCPClient(mcp.MCPClientOptions{
		Name: "client",
		Stdio: &mcp.StdioConfig{
			Command: "go",
			Args:    []string{"run", "server.go"},
		},
	})
	if err != nil {
		log.Fatalf("Failed to connect: %v", err)
	}
	defer client.Disconnect()

	// Import tools
	tools, err := client.GetActiveTools(ctx, g)
	if err != nil {
		log.Fatalf("Failed to get tools: %v", err)
	}

	log.Printf("Connected! Tools: %v", getToolNames(tools))

	// Convert to ToolRef
	var toolRefs []ai.ToolRef
	for _, tool := range tools {
		toolRefs = append(toolRefs, tool)
	}

	// Use tools with AI
	log.Println("\n=== Demo: Fetch and summarize content ===")

	response, err := genkit.Generate(ctx, g,
		ai.WithModelName("googleai/gemini-2.5-pro-preview-05-06"),
		ai.WithPrompt("Fetch content from https://httpbin.org/json and give me a summary of what you find"),
		ai.WithTools(toolRefs...),
		ai.WithToolChoice(ai.ToolChoiceAuto),
	)

	if err != nil {
		log.Printf("Failed: %v", err)
	} else {
		log.Printf("\nResult:\n%s", response.Text())
	}
}

func getToolNames(tools []ai.Tool) []string {
	var names []string
	for _, tool := range tools {
		names = append(names, tool.Name())
	}
	return names
}
