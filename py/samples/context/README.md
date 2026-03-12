# Context

Pass request IDs, user info, or feature flags through `ai.generate()` into flows and tools. No manual threading.

```bash
export GEMINI_API_KEY=your-api-key
uv sync
genkit start -- uv run src/main.py
```

Dev UI at http://localhost:4000. Try `context_in_generate`, `context_propagation_chain`.
