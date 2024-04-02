# Google Generative AI plugin

The Google Generative AI plugin provides interfaces to Google's Gemini models
through the [Gemini API](https://ai.google.dev/docs/gemini_api_overview).

## Configuration

To use this plugin, specify it when you call `configureGenkit()`:

```js
import { googleGenAI } from '@genkit-ai/google-genai';

export default configureGenkit({
  plugins: [googleGenAI()],
  // ...
});
```

The plugin requires an API key for the Gemini API, which you can get from
[Google AI Studio](https://aistudio.google.com/app/apikey).

Configure the plugin to use your API key by doing one of the following:

- Set the `GOOGLE_API_KEY` environment variable to your API key.

- Specify the API key when you initialize the plugin:

  ```js
  googleGenAI({ apiKey: yourKey });
  ```

  However, don't embed your API key directly in code! Use this feature only
  in conjunction with a service like Cloud Secret Manager or similar.

## Usage

This plugin statically exports references to its supported models:

```js
import { geminiPro, geminiProVision } from '@genkit-ai/google-genai';
```

You can use these references to specify which model `generate()` uses:

```js
const llmResponse = await generate({
  model: geminiPro,
  prompt: 'Tell me a joke.',
});
```
