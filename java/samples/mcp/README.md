# Genkit MCP Sample

This sample demonstrates how to use the Genkit MCP (Model Context Protocol) plugin to integrate with MCP servers.

## Prerequisites

1. **Java 17+** - Ensure you have Java 17 or later installed
2. **Node.js and npm** - Required for running MCP servers via `npx`
3. **OpenAI API Key** - Set the `OPENAI_API_KEY` environment variable

## Quick Start

1. Set your OpenAI API key:
   ```bash
   export OPENAI_API_KEY=your-api-key-here
   ```

2. Run the sample:
   ```bash
   ./run.sh
   # Or directly with Maven:
   mvn exec:java
   ```

3. The sample will start with:
   - HTTP server on port 8080
   - Reflection server on port 3100 (for Genkit Dev UI)
   - MCP connections to filesystem and everything servers

## Available Flows

### listMcpTools
Lists all available MCP tools from connected servers.
```bash
curl -X POST http://localhost:8080/listMcpTools \
  -H 'Content-Type: application/json' -d 'null'
```

### fileAssistant
AI-powered file operations assistant that can read, write, and list files.
```bash
curl -X POST http://localhost:8080/fileAssistant \
  -H 'Content-Type: application/json' \
  -d '"List all files in the temp directory"'
```

### readFile
Directly read a file using the MCP filesystem tool.
```bash
curl -X POST http://localhost:8080/readFile \
  -H 'Content-Type: application/json' \
  -d '"/tmp/test.txt"'
```

### listResources
List resources from a specific MCP server.
```bash
curl -X POST http://localhost:8080/listResources \
  -H 'Content-Type: application/json' \
  -d '"filesystem"'
```

### toolExplorer
AI assistant with access to all MCP tools.
```bash
curl -X POST http://localhost:8080/toolExplorer \
  -H 'Content-Type: application/json' \
  -d '"Generate a random UUID"'
```

### mcpStatus
Get the status of all connected MCP servers.
```bash
curl -X POST http://localhost:8080/mcpStatus \
  -H 'Content-Type: application/json' -d 'null'
```

### writeReadDemo
Demo that writes content to a file and reads it back.
```bash
curl -X POST http://localhost:8080/writeReadDemo \
  -H 'Content-Type: application/json' \
  -d '"Hello from Genkit MCP!"'
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key for model access | (required) |
| `MCP_ALLOWED_DIR` | Directory the filesystem server can access | `/tmp` |

### MCP Servers Used

This sample connects to two MCP servers:

1. **filesystem** (`@modelcontextprotocol/server-filesystem`)
   - Provides file read/write/list operations
   - Limited to the `MCP_ALLOWED_DIR` directory for security

2. **everything** (`@modelcontextprotocol/server-everything`)
   - Demo server with various tool types (echo, random, etc.)
   - Useful for testing MCP integration

## MCP Server Sample

This sample also includes `MCPServerSample`, which demonstrates how to **expose** Genkit tools as an MCP server.

### Running the MCP Server

```bash
# Run directly
mvn exec:java -Dexec.mainClass="com.google.genkit.samples.MCPServerSample"

# Or build and run the JAR
mvn package -DskipTests
java -jar target/genkit-mcp-sample-1.0.0-SNAPSHOT-server.jar
```

### Using with Claude Desktop

Add to your `~/.config/claude/claude_desktop_config.json` (macOS) or similar on other platforms:

```json
{
  "mcpServers": {
    "genkit-tools": {
      "command": "java",
      "args": ["-jar", "/absolute/path/to/genkit-mcp-sample-1.0.0-SNAPSHOT-server.jar"]
    }
  }
}
```

### Available Tools

The MCP server exposes these demonstration tools:

| Tool | Description |
|------|-------------|
| `calculator` | Basic math operations (add, subtract, multiply, divide) |
| `get_weather` | Mock weather data for any location |
| `get_datetime` | Current date/time in various formats |
| `greet` | Personalized greeting generator |
| `translate_mock` | Mock translation tool |

## Code Examples

### Adding Your Own MCP Server

```java
MCPPluginOptions mcpOptions = MCPPluginOptions.builder()
    .name("my-app")
    .addServer("filesystem", MCPServerConfig.stdio(
        "npx", "-y", "@modelcontextprotocol/server-filesystem", "/path/to/files"))
    .addServer("github", MCPServerConfig.builder()
        .command("npx")
        .args("-y", "@modelcontextprotocol/server-github")
        .env("GITHUB_TOKEN", System.getenv("GITHUB_TOKEN"))
        .build())
    .addServer("remote", MCPServerConfig.http("http://mcp-server.example.com:3001/mcp"))
    .build();

MCPPlugin mcpPlugin = MCPPlugin.create(mcpOptions);
```

### Creating Your Own MCP Server

```java
// Define tools with Genkit
Genkit genkit = Genkit.builder().build();

genkit.defineTool("my_tool", "My custom tool",
    Map.of("type", "object", "properties", Map.of(
        "input", Map.of("type", "string")
    )),
    (Class<Map<String, Object>>) (Class<?>) Map.class,
    (ctx, input) -> {
        return Map.of("result", "processed: " + input.get("input"));
    });

genkit.init();

// Create and start MCP server
MCPServer mcpServer = new MCPServer(genkit.getRegistry(),
    MCPServerOptions.builder()
        .name("my-server")
        .version("1.0.0")
        .build());

mcpServer.start();  // Uses STDIO transport
    (ctx, input) -> {
        List<Tool<?, ?>> tools = mcpPlugin.getTools();
        
        ModelResponse response = genkit.generate(GenerateOptions.builder()
            .model("openai/gpt-4o")
            .prompt(input)
            .tools(tools)
            .build());
        
        return response.getText();
    });
```

### Direct Tool Calls

```java
// Write a file
mcpPlugin.callTool("filesystem", "write_file", 
    Map.of("path", "/tmp/hello.txt", "content", "Hello World!"));

// Read it back
Object content = mcpPlugin.callTool("filesystem", "read_file",
    Map.of("path", "/tmp/hello.txt"));
```

## Troubleshooting

### "Command not found: npx"
Ensure Node.js and npm are installed and in your PATH.

### Connection timeouts
Check that the MCP server package can be downloaded via npm. You may need to configure proxy settings.

### Permission denied errors
Make sure the `MCP_ALLOWED_DIR` directory exists and is writable.

### Tools not appearing
Check the logs for MCP connection errors. Increase log level for more details:
```xml
<logger name="com.google.genkit.plugins.mcp" level="DEBUG"/>
```

## Learn More

- [MCP Plugin Documentation](../../plugins/mcp/README.md)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Available MCP Servers](https://github.com/modelcontextprotocol/servers)
