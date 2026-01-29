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

### Monitoring and Running

For an enhanced development experience, use the provided `run.sh` script to start the sample with automatic reloading:

```bash
./run.sh
```

This script uses `watchmedo` to monitor changes in:
- `src/` (Python logic)
- `../../packages` (Genkit core)
- `../../plugins` (Genkit plugins)
- File patterns: `*.py`, `*.prompt`, `*.json`

Changes will automatically trigger a restart of the sample. You can also pass command-line arguments directly to the script, e.g., `./run.sh --some-flag`.

## Run the sample

TODO

```bash
genkit start -- uv run flask --app src/main.py run
```

```bash
curl -X POST http://127.0.0.1:5000/chat -d '{"data": "banana"}' -H 'content-Type: application/json' -H 'accept: text/event-stream' -H 'Authorization: Pavel'
```

## Testing This Demo

1. **Test the API endpoint**:
   ```bash
   # Basic request
   curl -X POST http://localhost:5000/chat \
     -H "Content-Type: application/json" \
     -d '{"prompt": "Hello, who are you?"}'

   # With authorization header (username context)
   curl -X POST http://localhost:5000/chat \
     -H "Content-Type: application/json" \
     -H "Authorization: JohnDoe" \
     -d '{"prompt": "What is my name?"}'
   ```

2. **Test via DevUI** at http://localhost:4000:
   - [ ] Run the `chat` flow
   - [ ] Verify response is generated

3. **Expected behavior**:
   - POST /chat returns AI-generated response
   - Authorization header is passed as username in context
   - Flow can access username via `ctx.context.get("username")`
