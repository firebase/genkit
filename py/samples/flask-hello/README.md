# Flask hello example

## Setup environment

### How to Get Your Gemini API Key

To use the Google GenAI plugin, you need a Gemini API key.

1.  **Visit AI Studio**: Go to [Google AI Studio](https://aistudio.google.com/).
2.  **Create API Key**: Click on "Get API key" and create a key in a new or existing Google Cloud project.

For more details, check out the [official documentation](https://ai.google.dev/gemini-api/docs/api-key).

Export the API key as env variable `GEMINI_API_KEY`:

```bash
export GEMINI_API_KEY=<Your api key>
```
## Run the sample

TODO

```bash
genkit start -- uv run flask --app src/main.py run
```

```bash
curl -X POST http://127.0.0.1:5000/chat -d '{"data": "banana"}' -H 'content-Type: application/json' -H 'accept: text/event-stream' -H 'Authorization: Pavel'
```
