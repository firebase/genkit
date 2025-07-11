# Genkit MCP

This plugin provides integration between Genkit and the [Model Context Protocol](https://modelcontextprotocol.io) (MCP). MCP is an open standard allowing developers to build "servers" which provide tools, resources, and prompts to clients. Genkit MCP allows Genkit developers to:
- Consume MCP tools, prompts, and resources as a client using `createMcpHost` or `createMcpClient`.
- Provide Genkit tools and prompts as an MCP server using `createMcpServer`.

## Installation

To get started, you'll need Genkit and the MCP plugin:

```bash
npm i genkit @genkit-ai/mcp
```

## MCP Host

To connect to one or more MCP servers, you use the `createMcpHost` function. This function returns a `GenkitMcpHost` instance that manages connections to the configured MCP servers.

```ts
import { genkit } from 'genkit';
import { createMcpHost } from '@genkit-ai/mcp';

// Example: Configure a MCP host for a local filesystem server
// and a hypothetical remote Git server.
const ALLOWED_DIRS = ['/Users/yourusername/Desktop'];

const mcpHost = createMcpHost({
  name: 'myMcpClients', // A name for the host plugin itself
  mcpServers: {
    // Each key (e.g., 'fs', 'git') becomes a namespace for the server's tools.
    fs: {
        command: 'npx',
        args: ['-y', '@modelcontextprotocol/server-filesystem', ...ALLOWED_DIRS],
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
const mcpTools = await McpHost.getActiveTools(genkit);

// Provide MCP tools to the model of your choice.
const response = await ai.generate({
  model: googleAI.model('gemini-2.0-flash'),
  prompt: 'What are the last 5 commits in the repo `/home/yourusername/Desktop/test-repo/?`',
  tools: mcpTools,
});

console.log(response.text);
```

The `createMcpHost` function initializes a `GenkitMcpHost` instance, which handles the lifecycle and communication with the defined MCP servers.

### `createMcpHost()` Options

-   **`name`**: (optional, string) A name for the MCP host plugin itself. Defaults to 'genkitx-mcp'.
-   **`version`**: (optional, string) The version of the MCP host plugin. Defaults to "1.0.0".
-   **`rawToolResponses`**: (optional, boolean) If `true`, tool responses from this server are returned in their raw MCP format; otherwise, they are processed for Genkit compatibility. Defaults to `false`.
-   **`mcpServers`**: (required, object) An object where each key is a client-side name (namespace) for an MCP server, and the value is the configuration for that server.
    
    Each server configuration object can include:
    -   **`disabled`**: (optional, boolean) If `true`, this server connection will not be attempted. Defaults to `false`.
    -   One of the following server connection configurations:
        -   Parameters for launching a local server process using the stdio MCP transport.
            -   **`command`**: (required, string) Shell command path for launching the MCP server (e.g., `npx`, `python`).
            -   **`args`**: (optional, string[]) Array of string arguments to pass to the command.
            -   **`env`**: (optional, Record<string, string>) Key-value object of environment variables.
        -   **`url`**: (string) The URL of a remote server to connect to using the Streamable HTTP MCP transport.
        -   **`transport`**: An existing MCP transport object for connecting to the server.


## MCP Client (Single Server)

For scenarios where you only need to connect to a single MCP server, or prefer to manage client instances individually, you can use `createMcpClient`.

```ts
import { genkit } from 'genkit';
import { createMcpClient } from '@genkit-ai/mcp';

const myFsClient = createMcpClient({
  name: 'myFileSystemClient', // A unique name for this client instance
  command: 'npx',
  args: ['-y', '@modelcontextprotocol/server-everything', '/Users/yourusername/Documents'],
  // rawToolResponses: true, // Optional: get raw MCP responses
});

// In your Genkit configuration:
genkit({
  plugins: [
    /* ... other plugins ... */
    // Individual clients are not Genkit plugins themselves.
  ],
});

async function runSingleClient() {
  // Retrieve tools from this specific client
  const fsTools = await myFsClient.getActiveTools(genkit);

  const response = await genkit.generate({
    model: googleAI.model('gemini-2.0-flash'), // Replace with your model
    prompt: 'List files in my Documents folder.',
    tools: fsTools,
  });
  console.log(response.text);
}

runSingleClient();
```

### `createMcpClient()` Options

The `createMcpClient` function takes an `McpClientOptions` object:
-   **`name`**: (required, string) A unique name for this client instance. This name will be used as the namespace for its tools and prompts.
-   **`version`**: (optional, string) Version for this client instance. Defaults to "1.0.0".
-   Plus, all options from `McpServerConfig` (see `disabled`, `rawToolResponses`, and transport configurations under `createMcpHost` options).

### Using MCP Actions (Tools, Prompts)

Both `GenkitMcpHost` (via `getActiveTools()`) and `GenkitMcpClient` (via `getActiveTools()`) discover available tools from their connected and enabled MCP server(s). These tools are standard Genkit `ToolAction` instances and can be provided to Genkit models.

MCP prompts can be fetched using `McpHost.getPrompt(serverName, promptName)` or `mcpClient.getPrompt(promptName)`. These return an `ExecutablePrompt`.

All MCP actions (tools, prompts, resources) are namespaced.
- For `createMcpHost`, the namespace is the key you provide for that server in the `mcpServers` configuration (e.g., `localFs/read_file`).
- For `createMcpClient`, the namespace is the `name` you provide in its options (e.g., `myFileSystemClient/list_resources`).

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
import { createMcpServer } from '@genkit-ai/mcp'; // Updated import

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
// Setup (async) then starts with stdio transport by default
server.setup().then(() => server.start())
```

The `createMcpServer` function returns a `GenkitMcpServer` instance. The `start()` method on this instance will start an MCP server (using the stdio transport by default) that exposes all registered Genkit tools and prompts. To start the server with a different MCP transport, you can pass the transport instance to the `start()` method (e.g., `server.start(customMcpTransport)`).

### `createMcpServer()` Options
- **`name`**: (required, string) The name you want to give your server for MCP inspection.
- **`version`**: (optional, string) The version your server will advertise to clients. Defaults to "1.0.0".

### Known Limitations

- MCP prompts are only able to take string parameters, so inputs to schemas must be objects with only string property values.
- MCP prompts only support `user` and `model` messages. `system` messages are not supported.
- MCP prompts only support a single "type" within a message so you can't mix media and text in the same message.

### Testing your MCP server

You can test your MCP server using the official inspector. For example, if your server code compiled into `dist/index.js`, you could run:

    npx @modelcontextprotocol/inspector dist/index.js

Once you start the inspector, you can list prompts and actions and test them out manually.
