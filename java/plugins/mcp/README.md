# Genkit MCP Plugin

This plugin enables Genkit to integrate with [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) servers, allowing you to use MCP tools and resources in your Genkit applications.

## Features

- Connect to multiple MCP servers simultaneously
- Support for STDIO transport (local processes) and HTTP/SSE transport (remote servers)
- Automatic conversion of MCP tools to Genkit tools
- Access MCP resources programmatically
- Seamless integration with Genkit's AI model workflows

## Installation

Add the MCP plugin dependency to your `pom.xml`:

```xml
<dependency>
    <groupId>com.google.genkit</groupId>
    <artifactId>genkit-plugin-mcp</artifactId>
    <version>${genkit.version}</version>
</dependency>
```

## Quick Start

### Basic Usage with STDIO Server

```java
import com.google.genkit.Genkit;
import com.google.genkit.plugins.mcp.MCPPlugin;
import com.google.genkit.plugins.mcp.MCPPluginOptions;
import com.google.genkit.plugins.mcp.MCPServerConfig;

// Create MCP plugin with a filesystem server
MCPPlugin mcpPlugin = MCPPlugin.create(MCPPluginOptions.builder()
    .name("my-mcp-host")
    .addServer("filesystem", MCPServerConfig.stdio(
        "npx", "-y", "@modelcontextprotocol/server-filesystem", "/tmp"))
    .build());

// Create Genkit with the MCP plugin
Genkit genkit = Genkit.builder()
    .plugin(mcpPlugin)
    .build();

// MCP tools are now available as Genkit tools
List<Tool<?, ?>> mcpTools = mcpPlugin.getTools();
```

### Using MCP Tools with AI Models

```java
import com.google.genkit.ai.GenerateOptions;
import com.google.genkit.ai.ModelResponse;

// Use MCP tools in AI-powered flows
Flow<String, String, Void> assistantFlow = genkit.defineFlow(
    "fileAssistant", String.class, String.class,
    (ctx, userRequest) -> {
        ModelResponse response = genkit.generate(GenerateOptions.builder()
            .model("openai/gpt-4o")
            .system("You are a helpful file assistant.")
            .prompt(userRequest)
            .tools(mcpPlugin.getTools())
            .build());
        return response.getText();
    });
```

### HTTP Server Connection

```java
MCPPlugin mcpPlugin = MCPPlugin.create(MCPPluginOptions.builder()
    .addServer("weather", MCPServerConfig.http("http://localhost:3001/mcp"))
    .build());
```

## Server Configuration

### STDIO Transport

Used for running local MCP servers as child processes:

```java
MCPServerConfig config = MCPServerConfig.builder()
    .command("npx")
    .args("-y", "@modelcontextprotocol/server-filesystem", "/allowed/path")
    .env("SOME_VAR", "value")  // Optional environment variables
    .build();
```

### HTTP Transport

Used for connecting to remote MCP servers:

```java
MCPServerConfig config = MCPServerConfig.http("http://localhost:3001/mcp");

// Or with builder for more options
MCPServerConfig config = MCPServerConfig.builder()
    .url("http://localhost:3001/mcp")
    .transportType(MCPServerConfig.TransportType.HTTP)
    .build();
```

### Streamable HTTP Transport

```java
MCPServerConfig config = MCPServerConfig.streamableHttp("http://localhost:3001/mcp");
```

## Plugin Options

```java
MCPPluginOptions options = MCPPluginOptions.builder()
    .name("my-mcp-host")                          // Host name for identification
    .addServer("server1", config1)                // Add servers
    .addServer("server2", config2)
    .requestTimeout(Duration.ofSeconds(30))        // Request timeout
    .rawToolResponses(false)                       // Process tool responses
    .build();
```

## Direct Tool Invocation

Call MCP tools directly without going through AI:

```java
// Call a specific tool
Object result = mcpPlugin.callTool("filesystem", "read_file", 
    Map.of("path", "/tmp/myfile.txt"));

// Get tools from a specific server
List<Tool<?, ?>> filesystemTools = mcpPlugin.getTools("filesystem");
```

## Resource Access

Access MCP resources programmatically:

```java
// List resources from a server
List<MCPResource> resources = mcpPlugin.getResources("filesystem");

// Read a resource
MCPResourceContent content = mcpPlugin.readResource("filesystem", "file:///tmp/data.txt");
String text = content.getText();
```

## Popular MCP Servers

Here are some commonly used MCP servers you can connect to:

| Server | Package | Description |
|--------|---------|-------------|
| Filesystem | `@modelcontextprotocol/server-filesystem` | File operations (read, write, list) |
| Everything | `@modelcontextprotocol/server-everything` | Demo server with various tools |
| Git | `@modelcontextprotocol/server-git` | Git repository operations |
| GitHub | `@modelcontextprotocol/server-github` | GitHub API access |
| Postgres | `@modelcontextprotocol/server-postgres` | PostgreSQL database access |
| Slack | `@modelcontextprotocol/server-slack` | Slack messaging |
| Memory | `@modelcontextprotocol/server-memory` | Knowledge graph memory |

## Example: Multi-Server Setup

```java
MCPPluginOptions options = MCPPluginOptions.builder()
    .name("multi-server-host")
    .addServer("files", MCPServerConfig.stdio(
        "npx", "-y", "@modelcontextprotocol/server-filesystem", "/data"))
    .addServer("git", MCPServerConfig.builder()
        .command("npx")
        .args("-y", "@modelcontextprotocol/server-git")
        .env("GIT_AUTHOR_NAME", "Genkit User")
        .build())
    .addServer("github", MCPServerConfig.builder()
        .command("npx")
        .args("-y", "@modelcontextprotocol/server-github")
        .env("GITHUB_TOKEN", System.getenv("GITHUB_TOKEN"))
        .build())
    .build();
```

## Cleanup

The plugin manages connections automatically, but you can manually disconnect:

```java
// Disconnect all servers
mcpPlugin.disconnect();

// Or add a shutdown hook
Runtime.getRuntime().addShutdownHook(new Thread(() -> {
    mcpPlugin.disconnect();
}));
```

## Error Handling

```java
try {
    Object result = mcpPlugin.callTool("filesystem", "read_file", 
        Map.of("path", "/nonexistent/file"));
} catch (GenkitException e) {
    logger.error("MCP tool call failed: {}", e.getMessage());
}
```

## Logging

The plugin uses SLF4J for logging. Configure your logging framework to see MCP-related logs:

```xml
<!-- logback.xml -->
<logger name="com.google.genkit.plugins.mcp" level="DEBUG"/>
```

## Requirements

- Java 17 or later
- Node.js and npm (for running MCP server packages via npx)
- Network access for HTTP-based MCP servers

## See Also

- [MCP Protocol Documentation](https://modelcontextprotocol.io/)
- [MCP Java SDK](https://github.com/modelcontextprotocol/java-sdk)
- [Available MCP Servers](https://github.com/modelcontextprotocol/servers)
