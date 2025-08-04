package main

import (
	"context"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/mcp"
)

func main() {
	g, _ := genkit.Init(context.Background())
	genkit.DefineResource(g, genkit.ResourceOptions{
		Name:     "test-docs",
		Template: "file://test/{filename}",
	}, func(ctx context.Context, input core.ResourceInput) (genkit.ResourceOutput, error) {
		return genkit.ResourceOutput{
			Content: []*ai.Part{ai.NewTextPart("test content")},
		}, nil
	})
	server := mcp.NewMCPServer(g, mcp.MCPServerOptions{Name: "test"})
	server.ServeStdio()
}
