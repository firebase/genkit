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

### Beta API Limitations

The beta API surface provides access to experimental features, but some server-managed tool blocks are not yet supported by this plugin. The following beta API features will cause an error if encountered:

- `web_fetch_tool_result`
- `code_execution_tool_result`
- `bash_code_execution_tool_result`
- `text_editor_code_execution_tool_result`
- `mcp_tool_result`
- `mcp_tool_use`
- `container_upload`

Note that `server_tool_use` and `web_search_tool_result` ARE supported and work with both stable and beta APIs.

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

Want to contribute to the project? That's awesome! Head over to our [Contribution Guidelines](/CONTRIBUTING.md).

## Need support?

> [!NOTE]
> This repository depends on Google's Firebase Genkit. For issues and questions related to Genkit, please refer to instructions available in [Genkit's repository](https://github.com/firebase/genkit).


## Credits

This plugin is maintained by Google with acknowledgement to the community contributions from [Bloom Labs Inc](https://github.com/BloomLabsInc).

## License

This project is licensed under the [Apache 2.0 License](https://github.com/BloomLabsInc/genkit-plugins/blob/main/LICENSE).
