# Realtime Tracing Demo

Spans appear in DevUI **as they start** (not when they complete). Watch `realtime_demo` in the Traces tab—each step shows up immediately.

## Run

```bash
cd py/samples/framework-realtime-tracing-demo
genkit start -- uv run src/main.py
```

Open DevUI at http://localhost:4000 and invoke `realtime_demo`.
