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
		Name:     "company-policy",
		Template: "docs://policy/{section}",
	}, func(ctx context.Context, input core.ResourceInput) (genkit.ResourceOutput, error) {
		return genkit.ResourceOutput{
			Content: []*ai.Part{ai.NewTextPart("VACATION_POLICY: Employees get 20 days vacation per year.")},
		}, nil
	})
	server := mcp.NewMCPServer(g, mcp.MCPServerOptions{Name: "test"})
	server.ServeStdio()
}
