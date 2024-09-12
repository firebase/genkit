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

## Gemini Files API

You can use files uploaded to the Gemini Files API with Genkit:

```js
import { GoogleAIFileManager } from '@google/generative-ai/server';

const fileManager = new GoogleAIFileManager(process.env.GOOGLE_GENAI_API_KEY);
const uploadResult = await fileManager.uploadFile(
  'path/to/file.jpg',
  {
    mimeType: 'image/jpeg',
    displayName: 'Your Image',
  }
);

const response = await generate({
  model: gemini15Flash,
  prompt: [
    {text: 'Describe this image:'},
    {media: {contentType: uploadResult.file.mimeType, url: uploadResult.file.uri}}
  ]
});
```

## Fine-tuning models

You can use models fine-tuned with the Google Gemini API.  Follow the instructions from the [Gemini API](https://ai.google.dev/gemini-api/docs/model-tuning/tutorial?_gl&lang=python) or fine-tune a model using [AI Studio](https://aistudio.corp.google.com/app/tune).

The tuning process uses a Base Model, for example `Gemini 1.5 Flash` and your provided examples to create a new tuned model.  Rememer the based model used, and copy the new model's id.

When calling the tuned model in Genkit, use the Base Model as the `model` parameter, and pass the tuned model's id as part of the `config` block. For example, if you used `Gemini 1.5 Flash` as the base model, and got model id `tunedModels/my-example-model-apbm8oqbvuv2` you can call it with a block like

```
const llmResponse = await generate({
  prompt: `Suggest an item for the menu of fish themed restruant`,
  model: gemini15Flash,
  config: {
    version: "tunedModels/my-example-model-apbm8oqbvuv2",
  },
});
```