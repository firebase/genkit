# Middleware Demo

Demonstrates Genkit's middleware system at two levels:

1. **Call-time middleware** — attached per `generate()` call via `use=[...]`
2. **Model-level middleware** — baked into a model via `define_model(use=[...])`

## Features Demonstrated

| Feature | Flow | Description |
|---------|------|-------------|
| Logging Middleware | `logging_demo` | Log request metadata and response info |
| Request Modification | `request_modifier_demo` | Modify requests before they reach the model |
| Chained Middleware | `chained_middleware_demo` | Compose multiple middleware in a pipeline |

## ELI5: Key Concepts

| Concept | ELI5 |
|---------|------|
| **Middleware** | Code that runs before/after the AI call — like a security guard checking bags at the door |
| **`use=`** | Pass middleware to `ai.generate()` — like adding filters to a camera |
| **`next(req, ctx)`** | Pass the request to the next middleware — like passing a baton in a relay race |

## Quick Start

```bash
export GEMINI_API_KEY=your-api-key
./run.sh
```

Then open the Dev UI at http://localhost:4000.

## Flows

| Flow | What It Demonstrates |
|------|---------------------|
| `logging_demo` | Call-time middleware that logs request and response metadata |
| `request_modifier_demo` | Call-time middleware that modifies the request before the model sees it |
| `chained_middleware_demo` | Multiple call-time middleware composed in a pipeline |
| `model_level_middleware_demo` | Model-level middleware set via `define_model(use=[...])` |
| `combined_middleware_demo` | Both call-time and model-level middleware running together |

## How Middleware Works

### Call-Time Middleware

Passed directly to `generate()`. Runs first in the chain.

```python
response = await ai.generate(
    prompt='Hello',
    use=[logging_middleware, system_instruction_middleware],
)
```

### Model-Level Middleware

Baked into a model at registration time. Every caller gets it automatically.

```python
ai.define_model(
    name='custom/safe-model',
    fn=my_model_fn,
    use=[safety_middleware],
)

# safety_middleware runs automatically — no need for use=[...]
response = await ai.generate(model='custom/safe-model', prompt='Hello')
```

### Execution Order

When both are used, call-time middleware runs first, then model-level:

```
ai.generate(model='custom/safe-model', prompt=..., use=[call_mw])
       |
       v
   call_mw(req, ctx, next)        ← call-time middleware
       |
       v
   safety_mw(req, ctx, next)      ← model-level middleware
       |
       v
   my_model_fn(req, ctx)          ← model runner
       |
       v
   safety_mw returns response
       |
       v
   call_mw returns response
       |
       v
   Final response to caller
```

Middleware functions receive `(req, ctx, next)` and must call `next(req, ctx)`
to pass the request down the chain. They can modify the request before calling
next, or modify the response after.

## Development

The `run.sh` script uses `watchmedo` for hot reloading on file changes.
