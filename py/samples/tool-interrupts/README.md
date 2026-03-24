# Tool Interrupts

Human-in-the-loop: `ctx.interrupt()` pauses the tool; after `generate` returns, use **`your_tool.respond(interrupt, output)`** on the **decorated tool function** (and `response.interrupts`) to resume — not the low-level `tool_response` helper.

```bash
export GEMINI_API_KEY=your-api-key
uv sync
uv run src/main.py
```

This launches a small interactive CLI trivia session.

To inspect the same flow in Dev UI instead:

```bash
genkit start -- uv run src/main.py
```

Try `play_trivia`.
