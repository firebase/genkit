# Context Sample

Shows how to pass request-scoped data (request IDs, user info, feature flags)
through `ai.generate()` into flows and tools without manually plumbing arguments.

```bash
export GEMINI_API_KEY=your-api-key
uv sync
genkit start -- uv run src/main.py
```

Open Dev UI at [http://localhost:4000](http://localhost:4000) and run:

- `context_in_generate`
- `context_in_flow`
- `context_propagation_chain`
