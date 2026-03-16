# Middleware

Intercept requests and responses with `use=` on `ai.generate()`. Add retries, logging, rate limiting.

```bash
export GEMINI_API_KEY=your-api-key
uv sync
genkit start -- uv run src/main.py
```

Dev UI at http://localhost:4000. Try `logging_demo`, `chained_middleware_demo`.
