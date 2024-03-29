# OpenAI plugin

The OpenAI plugin provides interfaces to several OpenAI generative models
through the [OpenAI API](https://platform.openai.com/):

- GPT 3.5 Turbo, GPT 4, GPT 4 Turbo, and GPT 4 Vision text generation
- Dall-E 3 image generation
- `text-embedding-3-small` and `text-embedding-3-large` embedding generation

## Configuration

To use this plugin, specify it when you call `configureGenkit()`:

```js
import { openAI } from '@genkit-ai/plugin-openai';

export default configureGenkit({
  plugins: [openAI()],
});
```

This plugin requires that you specify your OpenAI API key. To do so, you have
two options:

- Specify it in your Genkit configuration: `openAI({ apiKey: "your_api_key" })`
- Set the `OPENAI_API_KEY` environment variable.

## Usage

This plugin statically exports references to its supported generative AI models:

```js
import {
  gpt35Turbo,
  gpt4,
  gpt4Turbo,
  gpt4Vision,
  dallE3,
} from '@genkit-ai/plugin-openai';
```

You can use these references to specify which model `generate()` uses:

```js
const llmResponse = await generate({
  model: gpt35Turbo,
  prompt: 'What should I do when I visit Melbourne?',
});
```

This plugin also statically exports references to OpenAI's text embedding
models:

```js
import {
  textEmbedding3Small,
  textEmbedding3Large,
} from '@genkit-ai/plugin-openai';
```

You can use these references to specify which embedder an indexer or retriever
uses. For example, if you use Chroma DB:

```js
configureGenkit({
  plugins: [
    chroma([
      {
        embedder: textEmbedding3Small,
        collectionName: 'my-collection',
      },
    ]),
  ],
});
```

Or you can generate an embedding directly:

```js
const embedding = await embed({
  embedder: textEmbedding3Small,
  content: 'How many widgets do you have in stock?',
});
```
