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
		Name:     "server-a-docs",
		Template: "a://docs/{file}",
	}, func(ctx context.Context, input core.ResourceInput) (genkit.ResourceOutput, error) {
		return genkit.ResourceOutput{
			Content: []*ai.Part{ai.NewTextPart("Content from Server A")},
		}, nil
	})
	server := mcp.NewMCPServer(g, mcp.MCPServerOptions{Name: "server-a"})
	server.ServeStdio()
}
