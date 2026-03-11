# Middleware Demo

Middleware wraps the generate flow so you can add retries, fallback models, observability, audit logs, or request shaping—without touching your prompts or flows.

**What you can do:**
- **Retry** on transient failures (`retry()`)
- **Fallback** to another model if the primary fails (`fallback()`)
- **Observe** each turn, model call, and tool run (e.g. trace, metrics)
- **Audit** tool calls for compliance
- **Shape** requests (inject context, sanitize) or responses (post-process)

This sample shows an **optimized agent**: turn limit, brevity nudge (fewer tokens), resilient tools (graceful degradation when a tool fails), and retries. Run it a few times—the weather tool fails ~40% of the time, but the agent keeps going.

```bash
GEMINI_API_KEY=your-key uv run python src/main.py
```
