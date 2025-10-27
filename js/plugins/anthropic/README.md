![Firebase Genkit + Anthropic AI](https://github.com/BloomLabsInc/genkit-plugins/blob/main/assets/genkit-anthropic.png?raw=true)

<h1 align="center">Firebase Genkit <> Anthropic AI Plugin</h1>

<h4 align="center">Anthropic AI Community Plugin for Google Firebase Genkit</h4>

<div align="center">
   <img alt="Github lerna version" src="https://img.shields.io/github/lerna-json/v/BloomLabsInc/genkit-plugins?label=version">
   <img alt="NPM Downloads" src="https://img.shields.io/npm/dw/genkitx-anthropic">
   <img alt="GitHub Org's stars" src="https://img.shields.io/github/stars/BloomLabsInc?style=social">
   <img alt="GitHub License" src="https://img.shields.io/github/license/BloomLabsInc/genkit-plugins">
   <img alt="Static Badge" src="https://img.shields.io/badge/yes-a?label=maintained">
</div>

<div align="center">
   <img alt="GitHub Issues or Pull Requests" src="https://img.shields.io/github/issues/BloomLabsInc/genkit-plugins?color=blue">
   <img alt="GitHub Issues or Pull Requests" src="https://img.shields.io/github/issues-pr/BloomLabsInc/genkit-plugins?color=blue">
   <img alt="GitHub commit activity" src="https://img.shields.io/github/commit-activity/m/BloomLabsInc/genkit-plugins">
</div>

`genkitx-anthropic` is a community plugin for using Anthropic AI and all its supported models with [Firebase Genkit](https://github.com/firebase/genkit).

This Genkit plugin allows to use Anthropic AI models through their official APIs.

If you want to use Anthropic AI models through Google Vertex AI, please refer
to the [official Vertex AI plugin](https://www.npmjs.com/package/@genkit-ai/vertexai).

## Supported models

The plugin supports the most recent Anthropic models:
**Claude 3.7 Sonnet**, **Claude 3.5 Sonnet**, **Claude 3 Opus**, **Claude 3 Sonnet**, and **Claude 3 Haiku**.

## Installation

Install the plugin in your project with your favorite package manager:

- `npm install genkitx-anthropic`
- `yarn add genkitx-anthropic`

## Usage

### Initialize

```typescript
import { genkit } from 'genkit';
import { anthropic, claude35Sonnet } from 'genkitx-anthropic';

const ai = genkit({
  plugins: [anthropic({ apiKey: process.env.ANTHROPIC_API_KEY })],
  // specify a default model for generate here if you wish:
  model: claude35Sonnet,
});
```

### Basic examples

The simplest way to generate text is by using the `generate` method:

```typescript
const response = await ai.generate({
  model: claude3Haiku, // model imported from genkitx-anthropic
  prompt: 'Tell me a joke.',
});

console.log(response.text);
```

### Multi-modal prompt

```typescript
// ...intialize Genkit instance (as shown above)...

const response = await ai.generate({
  prompt: [
    { text: 'What animal is in the photo?' },
    { media: { url: imageUrl } },
  ],
  config: {
    // control of the level of visual detail when processing image embeddings
    // Low detail level also decreases the token usage
    visualDetailLevel: 'low',
  },
});
console.log(response.text);
```

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

## Contributing

Want to contribute to the project? That's awesome! Head over to our [Contribution Guidelines](CONTRIBUTING.md).

## Need support?

> \[!NOTE\]\
> This repository depends on Google's Firebase Genkit. For issues and questions related to Genkit, please refer to instructions available in [Genkit's repository](https://github.com/firebase/genkit).

Reach out by opening a discussion on [Github Discussions](https://github.com/BloomLabsInc/genkitx-openai/discussions).

## Credits

This plugin is proudly maintained by the team at [**Bloom Labs Inc**](https://github.com/BloomLabsInc). 🔥

## License

This project is licensed under the [Apache 2.0 License](https://github.com/BloomLabsInc/genkit-plugins/blob/main/LICENSE).
