# Middleware Demo

Middleware wraps model calls—each time the LLM is invoked, whether from a simple generate, a flow, or a multi-turn run with tools. (Tool execution runs separately.) Use it to add retries, fallback models, or custom logic without changing prompts or flows.

This sample shows built-ins: `retry()` for transient failures and `fallback()` to switch models on error.

```bash
GEMINI_API_KEY=your-key uv run python src/main.py
```
