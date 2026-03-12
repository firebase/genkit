# Google Context Caching

Cache large docs so follow-up queries reuse context. Saves latency and tokens for RAG/summarization.

```bash
export GEMINI_API_KEY=your-api-key
uv sync
genkit start -- uv run src/main.py
```

Dev UI at http://localhost:4000. Try `text_context_flow`.
