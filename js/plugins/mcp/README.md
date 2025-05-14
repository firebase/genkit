# Genkit MCP

> [!WARNING]  
> This plugin is experimental, meaning it may not be supported long-term and APIs are subject to more often breaking changes.

This plugin provides integration between Genkit and the [Model Context Protocol](https://modelcontextprotocol.io) (MCP). MCP is an open standard allowing developers to build "servers" which provide tools, resources, and prompts to clients. Genkit MCP allows Genkit developers to:
- Consume MCP tools, prompts, and resources as a client using `createMcpManager` or `createMcpClient`.
- Provide Genkit tools and prompts as an MCP server using `createMcpServer`.

## Installation

To get started, you'll need Genkit and the MCP plugin:

```bash
npm i genkit genkitx-mcp
```

## MCP Client Manager

To connect to one or more MCP servers, you use the `createMcpManager` function. This function returns a `GenkitMcpManager` instance that manages connections to the configured MCP servers.

```ts
import { genkit } from 'genkit';
import { createMcpManager } from 'genkitx-mcp';

// Example: Configure a client manager for a local filesystem server
// and a hypothetical remote Git server.
const ALLOWED_DIRS = ['/Users/yourusername/Desktop'];

const mcpManager = createMcpManager({
  name: 'myMcpClients', // A name for the manager plugin itself
  mcpServers: {
    // Each key (e.g., 'fs', 'git') becomes a namespace for the server's tools.
    fs: {
        command: 'npx',
        args: ['-y', '@modelcontextprotocol/server-everything', ...ALLOWED_DIRS],
    },
    git: { // Configuration for a second MCP server (hypothetical)
      url: 'http://localhost:8080/mcp',
      // disabled: true, // Optionally disable a server
    },
  },
});

const ai = genkit({
  plugins: [
    /* ... install plugins such as model providers ...*/
  ],
});


// Retrieve tools from all active MCP servers
const mcpTools = await mcpManager.getActiveTools(genkit);

// Provide MCP tools to the model of your choice.
const response = await ai.generate({
  model: gemini15Flash,
  prompt: 'What are the last 5 commits in the repo `/home/yourusername/Desktop/test-repo/?`',
  tools: mcpTools,
});

console.log(response.text);
```

The `createMcpManager` function initializes a `GenkitMcpClientManager` instance, which handles the lifecycle and communication with the defined MCP servers.

### `createMcpManager()` Options

-   **`name`**: (optional, string) A name for the client manager plugin itself. Defaults to 'genkitx-mcp'.
-   **`version`**: (optional, string) The version of the client manager plugin. Defaults to "1.0.0".
-   **`mcpServers`**: (required, object) An object where each key is a client-side name (namespace) for an MCP server, and the value is the configuration for that server.
    Each server configuration object can include:
    -   **`rawToolResponses`**: (optional, boolean) If `true`, tool responses from this server are returned in their raw MCP format; otherwise, they are processed for Genkit compatibility. Defaults to `false`.
    -   **`disabled`**: (optional, boolean) If `true`, this server connection will not be attempted. Defaults to `false`.
    -   One of the following server connection configurations:
        -   Parameters for launching a local server process using the stdio MCP transport.
            -   **`command`**: (required, string) Shell command path for launching the MCP server (e.g., `npx`, `python`).
            -   **`args`**: (optional, string[]) Array of string arguments to pass to the command.
            -   **`env`**: (optional, Record<string, string>) Key-value object of environment variables.
        -   **`url`**: (string) The URL of a remote server to connect to using the SSE MCP transport.
        -   **`serverWebsocketUrl`**: (string) The URL of a remote server to connect to using the WebSocket MCP transport.
        -   **`transport`**: An existing MCP transport object for connecting to the server.

Most MCP servers are built to run as spawned processes on the same machine using the `stdio` transport. When you supply the `serverProcess` option, you are specifying the command, arguments, and environment variables for spawning the server as a subprocess.

### [Deprecated] `mcpClient()`

Note: This method is deprecated, please use `createMcpClient` or `createMcpManager` instead.

For simpler scenarios involving a single MCP server, or for backward compatibility, the legacy `mcpClient()` function is still available:

```ts
import { mcpClient } from 'genkitx-mcp/legacy'; // Note the import path

const legacyFilesystemClient = mcpClient({
  name: 'filesystemLegacy',
  serverProcess: { /* ... */ },
});
```
This function takes similar options to a single server configuration within `createMcpManager` (e.g., `name`, `version`, `serverProcess`, `rawToolResponses`) and directly returns a Genkit plugin for that single client. It is recommended to use `createMcpManager` for new projects.

### Using MCP Actions

The Genkit MCP client manager, through its `getActiveTools()` method, discovers available tools from each connected and enabled server. These tools can then be provided to Genkit models for use in generation requests. Resources and MCP Tools are both wrapped as GenkitTools. 

<!-- TODO: Note about MCP prompts. -->

To access resources provided by an MCP server, special `list_resources` and `read_resource` tools are dynamically created and retrieved for each server by the manager.

All MCP actions (tools, prompts, resources) are namespaced under the key you provide for that server in the `mcpServers` configuration. For example, if you have a server configured with the key `fs` in `mcpServers`, its `read_file` tool would be accessible as `fs/read_file`, and its resource listing tool as `fs/list_resources`.

### Tool Responses

MCP tools return a `content` array as opposed to a structured response like most Genkit tools. The Genkit MCP plugin attempts to parse and coerce returned content:

1. If content is text and valid JSON, the JSON is parsed and returned.
2. If content is text and not valid JSON, the text is returned.
3. If content has a single non-text part, it is returned.
4. If content has multiple/mixed parts, the full content response is returned.

## MCP Server

You can also expose all of the tools and prompts from a Genkit instance as an MCP server using the `createMcpServer` function.

```ts
import { genkit, z } from 'genkit';
import { createMcpServer } from 'genkitx-mcp'; // Updated import

const ai = genkit({});

ai.defineTool(
  {
    name: 'add',
    description: 'add two numbers together',
    inputSchema: z.object({ a: z.number(), b: z.number() }),
    outputSchema: z.number(),
  },
  async ({ a, b }) => {
    return a + b;
  }
);

ai.definePrompt(
  {
    name: "happy",
    description: "everybody together now",
    input: {
      schema: z.object({
        action: z.string().default("clap your hands").optional(),
      }),
    },
  },
  `If you're happy and you know it, {{action}}.`
);

// Use createMcpServer
const server = createMcpServer(ai, { name: 'example_server', version: '0.0.1' });
server.start(); // Starts with stdio transport by default
```

The `createMcpServer` function returns a `GenkitMcpServer` instance. The `start()` method on this instance will start an MCP server (using the stdio transport by default) that exposes all registered Genkit tools and prompts. To start the server with a different MCP transport, you can pass the transport instance to the `start()` method (e.g., `server.start(customMcpTransport)`).

### `createMcpServer()` Options
- **`name`**: (required, string) The name you want to give your server for MCP inspection.
- **`version`**: (optional, string) The version your server will advertise to clients. Defaults to "1.0.0".

The legacy `mcpServer()` function is deprecated; please use `createMcpServer()` instead.

### Known Limitations

- MCP prompts are only able to take string parameters, so inputs to schemas must be objects with only string property values.
- MCP prompts only support `user` and `model` messages. `system` messages are not supported.
- MCP prompts only support a single "type" within a message so you can't mix media and text in the same message.

### Testing your MCP server

You can test your MCP server using the official inspector. For example, if your server code compiled into `dist/index.js`, you could run:

    npx @modelcontextprotocol/inspector dist/index.js

Once you start the inspector, you can list prompts and actions and test them out manually.
