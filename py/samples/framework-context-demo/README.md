# Context Propagation Demo

Demonstrates how Genkit propagates context through the execution chain:
generate calls, flows, tools, and nested operations.

## Quick Start

```bash
export GEMINI_API_KEY=your-api-key
./run.sh
```

Then open the Dev UI at http://localhost:4000.

## Flows

| Flow | What It Demonstrates |
|------|---------------------|
| `context_in_generate` | Pass `context=` to `ai.generate()`, tool reads via `ctx.context` |
| `context_in_flow` | Flow receives `ActionRunContext`, reads `ctx.context` |
| `context_current_context` | Tool reads context via static `Genkit.current_context()` |
| `context_propagation_chain` | Context flows: flow -> generate -> tool -> nested generate -> nested tool |

## Testing Checklist

- [ ] `context_in_generate` -- Returns user-specific data based on `user_id` in context
- [ ] `context_in_flow` -- Shows context is accessible inside the flow itself
- [ ] `context_current_context` -- Shows `Genkit.current_context()` works from anywhere
- [ ] `context_propagation_chain` -- Verifies context survives multi-level nesting

## How Context Works

```
ai.generate(context={'user': {'id': 42}})
       |
       v
   ContextVar set with {'user': {'id': 42}}
       |
       +----> Tool reads ctx.context['user']['id']
       |
       +----> Genkit.current_context() reads same ContextVar
       |
       +----> Nested ai.generate() inherits context automatically
```

## Development

The `run.sh` script uses `watchmedo` for hot reloading on file changes.
