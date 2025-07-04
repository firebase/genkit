# Google Gemini Developer API plugin for Genkit

## Installing the plugin

```bash
npm i --save @genkit-ai/googleai
```

## Using the plugin

```ts
import { genkit } from 'genkit';
import { googleAI, gemini } from '@genkit-ai/googleai';

const ai = genkit({
  plugins: [googleAI()],
  model: gemini('gemini-1.5-flash'),
});

async () => {
  const { text } = ai.generate('hi Gemini!');
  console.log(text);
};
```

## Supported Models

This plugin supports a wide range of models including text generation, image generation, video generation, embeddings, and more. For a comprehensive list of supported models and usage examples, see [SUPPORTED_MODELS.md](./SUPPORTED_MODELS.md).

The plugin uses dynamic model discovery, so new models released through the Gemini API are often supported automatically without requiring plugin updates.

## Documentation

The sources for this package are in the main [Genkit](https://github.com/firebase/genkit) repo. Please file issues and pull requests against that repo.

Usage information and reference details can be found in [Genkit documentation](https://genkit.dev/docs/plugins/google-genai/).

License: Apache 2.0
