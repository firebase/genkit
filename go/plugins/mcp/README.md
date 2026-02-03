# Genkit MCP Plugin

Model Context Protocol (MCP) integration for Go Genkit

Connect to MCP servers and expose Genkit tools as MCP servers.

## GenkitMCPClient - Single Server Connection

Connect to and use tools/prompts from a single MCP server:

```go
package main

import (
  "context"
  "log"

  "github.com/firebase/genkit/go/genkit"
  "github.com/firebase/genkit/go/plugins/mcp"
)

func main() {
  ctx := context.Background()
  g := genkit.Init(ctx)

  // Connect to the MCP everything server
  // NewClient uses the context to manage the connection lifecycle.
  client, err := mcp.NewClient(ctx, mcp.MCPClientOptions{
    Name: "everything-server",
    Stdio: &mcp.StdioConfig{
      Command: "npx",
      Args:    []string{"-y", "@modelcontextprotocol/server-everything"},
    },
  })
  if err != nil {
    log.Fatal(err)
  }

  // Get specific prompts from the everything server
  simplePrompt, err := client.GetPrompt(ctx, g, "simple-prompt", nil)
  if err != nil {
    log.Fatal(err)
  }

  // Get all available tools
  tools, err := client.GetActiveTools(ctx, g)
  if err != nil {
    log.Fatal(err)
  }
}
```

> **Note:** `NewGenkitMCPClient` is deprecated in favor of `NewClient`, which supports context propagation.

## MCPHost - Multiple Server Management

Manage connections to multiple MCP servers:

```go
package main

import (
    "context"
    "log"

    "github.com/firebase/genkit/go/genkit"
    "github.com/firebase/genkit/go/plugins/mcp"
)

func main() {
    ctx := context.Background()
    g := genkit.Init(ctx)

    // Create host with multiple servers
    host, err := mcp.NewMCPHost(g, mcp.MCPHostOptions{
        Name: "my-app",
        MCPServers: []mcp.MCPServerConfig{
            {
                Name: "everything",
                Config: mcp.MCPClientOptions{
                    Stdio: &mcp.StdioConfig{
                        Command: "npx",
                        Args: []string{"-y", "@modelcontextprotocol/server-everything"},
                    },
                },
            },
            {
                Name: "filesystem",
                Config: mcp.MCPClientOptions{
                    Stdio: &mcp.StdioConfig{
                        Command: "npx",
                        Args: []string{"@modelcontextprotocol/server-filesystem", "/tmp"},
                    },
                },
            },
        },
    })
    if err != nil {
        log.Fatal(err)
    }

    // Connect to new server at runtime
    err = host.Connect(ctx, g, "weather", mcp.MCPClientOptions{
        Name: "weather-server",
        Stdio: &mcp.StdioConfig{
            Command: "python",
            Args: []string{"weather_server.py"},
        },
    })
    if err != nil {
        log.Fatal(err)
    }

    // Temporarily disable/enable servers
    host.Disconnect(ctx, "weather")

    // Get tools from all active servers
    tools, err := host.GetActiveTools(ctx, g)
    if err != nil {
        log.Fatal(err)
    }
}
```

## GenkitMCPServer - Expose Genkit Tools

Turn your Genkit app into an MCP server that others can connect to:

```go
package main

import (
  "context"
  "log"

  "github.com/firebase/genkit/go/ai"
  "github.com/firebase/genkit/go/genkit"
  "github.com/firebase/genkit/go/plugins/mcp"
)

func main() {
  g := genkit.Init(context.Background())

  // Define tools and resources you want to expose
  genkit.DefineTool(g, "hello", "says hello", func(ctx *ai.ToolContext, input any) (string, error) {
      return "Hello from Genkit!", nil
  })

  // Create the MCP server
  server := mcp.NewMCPServer(g, mcp.MCPServerOptions{
    Name: "my-genkit-server",
    Version: "1.0.0",
  })

  // Start serving over Stdio
  // Use ServeStdioWithContext(ctx) for graceful shutdown support.
  if err := server.ServeStdio(); err != nil {
    log.Fatal(err)
  }
}
```

### Exposing as an HTTP Server (SSE)

You can also expose your Genkit tools over HTTP using Server-Sent Events (SSE):

```go
package main

import (
	"context"
	"log"
	"net/http"

	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/mcp"
)

func main() {
	g := genkit.Init(context.Background())

	// Define tools...

	server := mcp.NewMCPServer(g, mcp.MCPServerOptions{
		Name: "my-genkit-http-server",
	})

	handler, err := server.HTTPHandler()
	if err != nil {
		log.Fatal(err)
	}

	http.Handle("/mcp", handler)
	log.Printf("MCP server listening on http://localhost:8080/mcp")
	log.Fatal(http.ListenAndServe(":8080", nil))
}
```

## Testing Your Server

```bash
# Run your server
go run main.go

# Test with MCP Inspector
npx @modelcontextprotocol/inspector go run main.go
```

## Transport Options

### Stdio (Standard)

```go
Stdio: &mcp.StdioConfig{
    Command: "uvx",
    Args: []string{"mcp-server-time"},
    Env: []string{"DEBUG=1"},
}
```

### SSE (Web clients)

```go
SSE: &mcp.SSEConfig{
    BaseURL: "http://localhost:3000/sse",
    Headers: map[string]string{"Authorization": "Bearer token"},
}
```
