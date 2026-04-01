# Dynamic Tools

Learn two related ideas:

- `ai.dynamic_tool()` creates a tool at runtime.
- `ai.run()` traces a plain async function as a named step.

```bash
export GEMINI_API_KEY=your-api-key
uv sync
uv run src/main.py
```

To inspect the same flows in Dev UI:

```bash
genkit start -- uv run src/main.py
```
