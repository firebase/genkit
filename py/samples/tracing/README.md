# Tracing

Spans show up in Dev UI as they start, not when they finish. For long flows with many steps.

```bash
export GEMINI_API_KEY=your-api-key
uv sync
genkit start -- uv run src/main.py
```

Dev UI at http://localhost:4000. Run `realtime_demo` and watch the Traces tab.
