package main

import (
	"context"
	"fmt"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/mcp"
)

func main() {
	g, _ := genkit.Init(context.Background())

	// Resource that provides different content based on filename
	genkit.DefineResource(g, genkit.ResourceOptions{
		Name:     "content-provider",
		Template: "file://data/{filename}",
	}, func(ctx context.Context, input core.ResourceInput) (genkit.ResourceOutput, error) {
		filename := input.Variables["filename"]
		content := fmt.Sprintf("CONTENT_FROM_SERVER: This is %s with important data.", filename)
		return genkit.ResourceOutput{
			Content: []*ai.Part{ai.NewTextPart(content)},
		}, nil
	})

	server := mcp.NewMCPServer(g, mcp.MCPServerOptions{Name: "content-server"})
	server.ServeStdio()
}
