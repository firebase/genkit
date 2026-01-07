# MCP Sample

This sample demonstrates using the MCP (Model Context Protocol) plugin with Genkit Python SDK.

## Setup environment

Obtain an API key from [ai.dev](https://ai.dev).

Export the API key as env variable `GEMINI\_API\_KEY` in your shell
configuration.

### Run the MCP Client/Host
```bash
cd py/samples/mcp
genkit start -- uv run src/main.py
```

This will:
1. Connect to the configured MCP servers
2. Execute sample flows demonstrating tool usage
3. Clean up connections on exit

### Run the MCP Client/Host
```bash
cd py/samples/mcp
genkit start -- uv run src/http_server.py
```

This will:
1. Connect to the configured MCP servers
2. Execute sample flows demonstrating tool usage
3. Clean up connections on exit

### Run the MCP Server
```bash
cd py/samples/mcp
genkit start -- uv run src/server.py
```

This starts an MCP server on stdio that other MCP clients can connect to.

## Requirements

- Python 3.10+
- `mcp` - Model Context Protocol Python SDK
- `genkit` - Genkit Python SDK
- `genkit-plugins-google-genai` - Google AI plugin for Genkit

## MCP Servers Used

The sample connects to these MCP servers (must be available):
- **mcp-server-git** - Install via `uvx mcp-server-git`
- **@modelcontextprotocol/server-filesystem** - Install via npm
- **@modelcontextprotocol/server-everything** - Install via npm

## Learn More

- [MCP Documentation](https://modelcontextprotocol.io/)
- [Genkit Python Documentation](https://firebase.google.com/docs/genkit)
- [MCP Plugin Source](../../plugins/mcp/)
