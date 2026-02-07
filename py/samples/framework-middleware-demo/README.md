# Middleware Demo

Demonstrates Genkit's middleware system using the `use=` parameter on
`ai.generate()`. Middleware intercepts the request/response pipeline,
enabling logging, retries, request modification, and more.

## Quick Start

```bash
export GEMINI_API_KEY=your-api-key
./run.sh
```

Then open the Dev UI at http://localhost:4000.

## Flows

| Flow | What It Demonstrates |
|------|---------------------|
| `logging_demo` | Middleware that logs request metadata and response info |
| `request_modifier_demo` | Middleware that modifies the request before it reaches the model |
| `chained_middleware_demo` | Multiple middleware functions composed in a pipeline |

## How Middleware Works

```
ai.generate(prompt=..., use=[middleware_a, middleware_b])
       |
       v
   middleware_a(req, ctx, next)
       |
       v
   middleware_b(req, ctx, next)
       |
       v
   Model (actual API call)
       |
       v
   middleware_b returns response
       |
       v
   middleware_a returns response
       |
       v
   Final response to caller
```

Middleware functions receive `(req, ctx, next)` and must call `next(req, ctx)`
to pass the request down the chain. They can modify the request before calling
next, or modify the response after.

## Development

The `run.sh` script uses `watchmedo` for hot reloading on file changes.
