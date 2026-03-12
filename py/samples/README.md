# Genkit Samples

```bash
cd py/samples/<sample-name>
uv sync
genkit start -- uv run src/main.py
```

(evaluators uses `main.py` at root; the rest use `src/main.py`)

Dev UI: http://localhost:4000. Most samples need `GEMINI_API_KEY`. See [plugins/README.md](../plugins/README.md) for provider setup.

## Samples

| Sample | What it shows |
|--------|----------------|
| **context** | Pass context through generate, flows, tools |
| **evaluators** | Custom regex + LLM evaluators for eval:run |
| **dynamic-tools** | Register tools at runtime |
| **output-formats** | text, json, array, enum, jsonl output |
| **middleware** | Intercept requests/responses on generate |
| **prompts** | .prompt files, templates, schemas |
| **tracing** | Spans appear as they start, not when done |
| **tool-interrupts** | Human-in-the-loop with ctx.interrupt() |
| **gemini-code-execution** | Gemini runs Python code |
| **gemini-context-caching** | Cache docs for faster repeats |
| **google-genai-media** | TTS, Imagen, Veo, Lyria |
| **vertexai-imagen** | Vertex AI image generation |
| **fastapi-bugbot** | Code review API with FastAPI |
| **flask-hello** | Flask + Genkit HTTP endpoints |
