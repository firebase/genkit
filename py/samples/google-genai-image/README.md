# Google Gemini Image Generation

This sample uses the Gemini API for image generation. This sample uses the
experimental Gemini model, which is available for now only in the Gemini API,
not in Vertex AI api. If you need to run it on Vertex AI, please, refer to
the Imagen sample.

Prerequisites:
* The `genkit` package.

### How to Get Your Gemini API Key

To use the Google GenAI plugin, you need a Gemini API key.

1.  **Visit AI Studio**: Go to [Google AI Studio](https://aistudio.google.com/).
2.  **Create API Key**: Click on "Get API key" and create a key in a new or existing Google Cloud project.

For more details, check out the [official documentation](https://ai.google.dev/gemini-api/docs/api-key).

To run this sample:

1. Install the `genkit` package.
2. Set the `GEMINI_API_KEY` environment variable to your Gemini API key.

```bash
export GEMINI_API_KEY=<Your api key>
```

3. Run the sample.

## Run the sample

TODO

```bash
uv run src/main.py
```
