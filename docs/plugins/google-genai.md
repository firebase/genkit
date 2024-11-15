# Google Generative AI plugin

The Google Generative AI plugin provides interfaces to Google's Gemini models
through the [Gemini API](https://ai.google.dev/docs/gemini_api_overview).

## Installation

```posix-terminal
npm i --save @genkit-ai/googleai
```

## Configuration

To use this plugin, specify it when you initialize Genkit:

```ts
import { genkit } from 'genkit';
import { googleAI } from '@genkit-ai/googleai';

const ai = genkit({
  plugins: [googleAI()],
});
```

The plugin requires an API key for the Gemini API, which you can get from
[Google AI Studio](https://aistudio.google.com/app/apikey).

Configure the plugin to use your API key by doing one of the following:

*   Set the `GOOGLE_GENAI_API_KEY` environment variable to your API key.
*   Specify the API key when you initialize the plugin:

    ```ts
    googleAI({ apiKey: yourKey });
    ```

    However, don't embed your API key directly in code! Use this feature only in
    conjunction with a service like Cloud Secret Manager or similar.

## Usage

This plugin statically exports references to its supported models:

```ts
import {
  gemini15Flash,
  gemini15Pro,
  textEmbedding004,
} from '@genkit-ai/googleai';
```

You can use these references to specify which model `generate()` uses:

```ts
const ai = genkit({
  plugins: [googleAI()],
  model: gemini15Flash,
});

const llmResponse = await ai.generate('Tell me a joke.');
```

or use embedders (ex. `textEmbedding004`) with `embed` or retrievers:

```ts
const ai = genkit({
  plugins: [googleAI()],
});

const embedding = await ai.embed({
  embedder: textEmbedding004,
  content: input,
});
```

## Gemini Files API

You can use files uploaded to the Gemini Files API with Genkit:

```ts
import { GoogleAIFileManager } from '@google/generative-ai/server';
import { genkit } from 'genkit';
import { googleAI } from '@genkit-ai/googleai';

const ai = genkit({
  plugins: [googleAI()],
});

const fileManager = new GoogleAIFileManager(process.env.GOOGLE_GENAI_API_KEY);
const uploadResult = await fileManager.uploadFile(
  'path/to/file.jpg',
  {
    mimeType: 'image/jpeg',
    displayName: 'Your Image',
  }
);

const response = await ai.generate({
  model: gemini15Flash,
  prompt: [
    {text: 'Describe this image:'},
    {media: {contentType: uploadResult.file.mimeType, url: uploadResult.file.uri}}
  ]
});
```

## Fine-tuned models

You can use models fine-tuned with the Google Gemini API.  Follow the
instructions from the
[Gemini API](https://ai.google.dev/gemini-api/docs/model-tuning/tutorial?lang=python)
or fine-tune a model using
[AI Studio](https://aistudio.corp.google.com/app/tune).

The tuning process uses a base model—for example, Gemini 1.5 Flash—and your
provided examples to create a new tuned model.  Remember the base model you
used, and copy the new model's ID.

When calling the tuned model in Genkit, use the base model as the `model`
parameter, and pass the tuned model's ID as part of the `config` block. For
example, if you used Gemini 1.5 Flash as the base model, and got the model ID
`tunedModels/my-example-model-apbm8oqbvuv2` you can call it with:

```ts
const ai = genkit({
  plugins: [googleAI()],
});

const llmResponse = await ai.generate({
  prompt: `Suggest an item for the menu of fish themed restruant`,
  model: gemini15Flash.withConfig({
    version: "tunedModels/my-example-model-apbm8oqbvuv2",
  }),
});
```
