# Tool Interrupts

Human-in-the-loop: `ctx.interrupt()` and `tool_response()` let the model pause for user input, then continue.

```bash
export GEMINI_API_KEY=your-api-key
uv sync
genkit start -- uv run src/main.py
```

Dev UI at http://localhost:4000. Try the trivia flow.
