# Multipart Tools Sample

This sample demonstrates **multipart tool support** (`tool.v2`), which allows
tools to return both structured output and rich content parts.

## What are Multipart Tools?

Regular tools return a single output value. Multipart tools can return:

- **`output`** — structured data (the typed output, same as regular tools)
- **`content`** — a list of rich content parts (text, media, etc.)

This mirrors the JS SDK's `defineTool({ multipart: true })`.

## Key Concepts

| Concept              | Description                                              |
|----------------------|----------------------------------------------------------|
| `@ai.tool()`         | Regular tool — returns a single output value              |
| `@ai.tool(multipart=True)` | Multipart tool — returns `{output?, content?}` dict |
| `ActionKind.TOOL`    | Action kind for regular tools                             |
| `ActionKind.TOOL_V2` | Action kind for multipart tools                           |
| Dual registration    | Regular tools are also registered under `tool.v2`         |

## Running

```bash
export GEMINI_API_KEY="your-key"
./run.sh
```

Or with the Dev UI:

```bash
genkit start -- uv run src/main.py
```

## Testing

From the Dev UI, run the `multipart_search` flow with an input like:
```json
"python async programming"
```

The flow will use:
1. A **regular tool** (`get_summary`) — returns a simple string
2. A **multipart tool** (`search_with_sources`) — returns both a summary and
   source citations as content parts
