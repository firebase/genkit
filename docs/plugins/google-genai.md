# Google Generative AI plugin

The Google Generative AI plugin provides interfaces to Google's Gemini models
through the [Gemini API](https://ai.google.dev/docs/gemini_api_overview).

## Installation

```posix-terminal
npm i --save @genkit-ai/googleai
```

## Configuration

To use this plugin, specify it when you call `configureGenkit()`:

```js
import { googleAI } from '@genkit-ai/googleai';

export default configureGenkit({
  plugins: [googleAI()],
  // ...
});
```

The plugin requires an API key for the Gemini API, which you can get from
[Google AI Studio](https://aistudio.google.com/app/apikey).

Configure the plugin to use your API key by doing one of the following:

- Set the `GOOGLE_GENAI_API_KEY` environment variable to your API key.

- Specify the API key when you initialize the plugin:

  ```js
  googleAI({ apiKey: yourKey });
  ```

  However, don't embed your API key directly in code! Use this feature only
  in conjunction with a service like Cloud Secret Manager or similar.

Some models (like Gemini 1.5 Pro) are in preview and only aviable via the
`v1beta` API. You can specify the `apiVersion` to get access to those models:

```js
configureGenkit({
  plugins: [googleAI({ apiVersion: 'v1beta' })],
});
```

or you can specify multiple versions if you'd like to use different versions of
models at the same time.

```js
configureGenkit({
  plugins: [googleAI({ apiVersion: ['v1', 'v1beta'] })],
});
```

## Usage

This plugin statically exports references to its supported models:

```js
import {
  gemini15Flash,
  gemini15Pro,
  textEmbeddingGecko001,
} from '@genkit-ai/googleai';
```

You can use these references to specify which model `generate()` uses:

```js
const llmResponse = await generate({
  model: gemini15Flash,
  prompt: 'Tell me a joke.',
});
```

or use embedders (ex. `textEmbeddingGecko001`) with `embed` or retrievers:

```js
const embedding = await embed({
  embedder: textEmbeddingGecko001,
  content: input,
});
```
