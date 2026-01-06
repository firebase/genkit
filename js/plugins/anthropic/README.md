# Firebase Genkit + Anthropic AI

<h1 align="center">Firebase Genkit <> Anthropic AI Plugin</h1>

<h4 align="center">Anthropic AI plugin for Google Firebase Genkit</h4>

`@genkit-ai/anthropic` is the official Anthropic plugin for [Firebase Genkit](https://github.com/firebase/genkit). It supersedes the earlier community package `genkitx-anthropic` and is now maintained by Google.

## Supported models

The plugin supports the most recent Anthropic models: **Claude Haiku 4.5**, **Claude Sonnet 4.5**, and **Claude Opus 4.5**. Additionally, the plugin supports all of the [non-retired older models](https://platform.claude.com/docs/en/about-claude/model-deprecations#model-status).

## Installation

Install the plugin in your project with your favorite package manager:

- `npm install @genkit-ai/anthropic`
- `yarn add @genkit-ai/anthropic`
- `pnpm add @genkit-ai/anthropic`

## Usage

### Initialize

```typescript
import { genkit } from 'genkit';
import { anthropic } from '@genkit-ai/anthropic';

const ai = genkit({
  plugins: [anthropic({ apiKey: process.env.ANTHROPIC_API_KEY })],
  // specify a default model for generate here if you wish:
  model: anthropic.model('claude-sonnet-4-5'),
});
```

### Basic examples

The simplest way to generate text is by using the `generate` method:

```typescript
const response = await ai.generate({
  model: anthropic.model('claude-haiku-4-5'),
  prompt: 'Tell me a joke.',
});

console.log(response.text);
```

### Multi-modal prompt

```typescript
// ...initialize Genkit instance (as shown above)...

const response = await ai.generate({
  prompt: [
    { text: 'What animal is in the photo?' },
    { media: { url: imageUrl } },
  ],
});
console.log(response.text);
```

### Extended thinking

Claude 4.5 models can expose their internal reasoning. Enable it per-request with the Anthropic thinking config and read the reasoning from the response:

```typescript
const response = await ai.generate({
  prompt: 'Walk me through your reasoning for Fermat’s little theorem.',
  config: {
    thinking: {
      enabled: true,
      budgetTokens: 4096, // Must be >= 1024 and less than max_tokens
    },
  },
});

console.log(response.text);       // Final assistant answer
console.log(response.reasoning);  // Summarized thinking steps
```

When thinking is enabled, request bodies sent through the plugin include the `thinking` payload (`{ type: 'enabled', budget_tokens: … }`) that Anthropic's API expects, and streamed responses deliver `reasoning` parts as they arrive so you can render the chain-of-thought incrementally.

### MCP (Model Context Protocol) Tools

The beta API supports connecting to MCP servers, allowing Claude to use external tools hosted on MCP-compatible servers. This feature requires the beta API.

```typescript
const response = await ai.generate({
  model: anthropic.model('claude-sonnet-4-5'),
  prompt: 'Search for TypeScript files in my project',
  config: {
    apiVersion: 'beta',
    mcp_servers: [
      {
        type: 'url',
        url: 'https://your-mcp-server.com/v1',
        name: 'filesystem',
        authorization_token: process.env.MCP_TOKEN, // Optional
      },
    ],
    mcp_toolsets: [
      {
        type: 'mcp_toolset',
        mcp_server_name: 'filesystem',
        default_config: { enabled: true },
        // Optionally configure specific tools:
        configs: {
          search_files: { enabled: true },
          delete_files: { enabled: false }, // Disable dangerous tools
        },
      },
    ],
  },
});

// Access MCP tool usage from the response
const mcpToolUse = response.message?.content.find(
  (part) => part.custom?.anthropicMcpToolUse
);
if (mcpToolUse) {
  console.log('MCP tool used:', mcpToolUse.custom.anthropicMcpToolUse);
}
```

**Response Structure:**

When Claude uses an MCP tool, the response contains parts for both tool invocation and results:

**Tool Invocation (`mcp_tool_use`):**
- `text`: Human-readable description of the tool invocation
- `custom.anthropicMcpToolUse`: Structured tool use data
  - `id`: Unique tool use identifier
  - `name`: Full tool name (server/tool)
  - `serverName`: MCP server name
  - `toolName`: Tool name on the server
  - `input`: Tool input parameters

**Tool Result (`mcp_tool_result`):**
- `text`: Human-readable result (prefixed with `[ERROR]` if execution failed)
- `custom.anthropicMcpToolResult`: Structured result data
  - `toolUseId`: Reference to the original tool use
  - `isError`: Boolean indicating if the tool execution failed
  - `content`: The tool execution result

```typescript
// Access MCP tool results from the response
const mcpToolResult = response.message?.content.find(
  (part) => part.custom?.anthropicMcpToolResult
);
if (mcpToolResult?.custom?.anthropicMcpToolResult) {
  const result = mcpToolResult.custom.anthropicMcpToolResult;
  if (result.isError) {
    console.error('MCP tool failed:', result.content);
  } else {
    console.log('MCP tool result:', result.content);
  }
}
```

**Note:** MCP tools are server-managed - they execute on Anthropic's infrastructure, not locally. The response will include both the tool invocation (`mcp_tool_use`) and results (`mcp_tool_result`) as they occur.

**Configuration Validation:**

The plugin validates MCP configuration at runtime:
- MCP server URLs must use HTTPS protocol
- MCP server names must be unique
- MCP toolsets must reference servers defined in `mcp_servers`
- Each MCP server must be referenced by exactly one toolset

### Beta API Limitations

The beta API surface provides access to experimental features, but some server-managed tool blocks are not yet supported by this plugin. The following beta API features will cause an error if encountered:

- `web_fetch_tool_result`
- `code_execution_tool_result`
- `bash_code_execution_tool_result`
- `text_editor_code_execution_tool_result`
- `container_upload`

Note that `server_tool_use`, `web_search_tool_result`, `mcp_tool_use`, and `mcp_tool_result` ARE supported and work with the beta API.

### Within a flow

```typescript
import { z } from 'genkit';

// ...initialize Genkit instance (as shown above)...

export const jokeFlow = ai.defineFlow(
  {
    name: 'jokeFlow',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (subject) => {
    const llmResponse = await ai.generate({
      prompt: `tell me a joke about ${subject}`,
    });
    return llmResponse.text;
  }
);
```

### Direct model usage (without Genkit instance)

The plugin supports Genkit Plugin API v2, which allows you to use models directly without initializing the full Genkit framework:

```typescript
import { anthropic } from '@genkit-ai/anthropic';

// Create a model reference directly
const claude = anthropic.model('claude-sonnet-4-5');

// Use the model directly
const response = await claude({
  messages: [
    {
      role: 'user',
      content: [{ text: 'Tell me a joke.' }],
    },
  ],
});

console.log(response);
```

You can also create model references using the plugin's `model()` method:

```typescript
import { anthropic } from '@genkit-ai/anthropic';

// Create model references
const claudeHaiku45 = anthropic.model('claude-haiku-4-5');
const claudeSonnet45 = anthropic.model('claude-sonnet-4-5');
const claudeOpus45 = anthropic.model('claude-opus-4-5');

// Use the model reference directly
const response = await claudeSonnet45({
  messages: [
    {
      role: 'user',
      content: [{ text: 'Hello!' }],
    },
  ],
});
```

This approach is useful for:

- Framework developers who need raw model access
- Testing models in isolation
- Using Genkit models in non-Genkit applications

## Acknowledgements

This plugin builds on the community work published as [`genkitx-anthropic`](https://github.com/BloomLabsInc/genkit-plugins/blob/main/plugins/anthropic/README.md) by Bloom Labs Inc. Their Apache 2.0–licensed implementation provided the foundation for this maintained package.

## Contributing

Want to contribute to the project? That's awesome! Head over to our [Contribution Guidelines](CONTRIBUTING.md).

## Need support?

> [!NOTE]
> This repository depends on Google's Firebase Genkit. For issues and questions related to Genkit, please refer to instructions available in [Genkit's repository](https://github.com/firebase/genkit).


## Credits

This plugin is maintained by Google with acknowledgement to the community contributions from [Bloom Labs Inc](https://github.com/BloomLabsInc).

## License

This project is licensed under the [Apache 2.0 License](https://github.com/BloomLabsInc/genkit-plugins/blob/main/LICENSE).
