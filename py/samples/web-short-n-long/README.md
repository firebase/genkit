# Short-Lived vs Long-Running Deployment

The same `@ai.flow()` functions can be deployed in two fundamentally different ways.

## What This Demonstrates

**Core Concept**: Two execution modes for Genkit flows

1. **Short-lived** (CLI/batch): Run once and exit
2. **Long-running** (HTTP server): Start a server that handles requests forever

## Use Cases

### Short-Lived Mode
- **CLI tools**: `python script.py --user Alice`
- **Cron jobs**: Run every night at midnight
- **Batch processing**: Process a file and exit
- **Serverless functions**: AWS Lambda, Cloud Functions (one invocation per container start)

### Long-Running Mode
- **REST APIs**: Public-facing HTTP service
- **Cloud Run / App Engine**: Container stays up
- **Kubernetes pods**: Long-running replicas
- **Development**: Keep server running, test with `curl`

## Running the Sample

### Short-lived mode (run once and exit)
```bash
cd py/samples/web-short-n-long
export GEMINI_API_KEY=your-key-here
uv run python src/main.py
```

Output:
```
Running in short-lived mode...
Result: Hello, World! 🌍 ...
Exiting.
```

### Long-running mode (HTTP server)
```bash
uv run python src/main.py --server --port 3400
```

Then test with:
```bash
curl -X POST 'http://localhost:3400//flow/greet' \
  -H "Content-Type: application/json" \
  -d '{"data": {"name": "Alice"}}'
```

Response:
```json
{"result": "Hello, Alice! I hope you're having a wonderful day!"}
```

## Key Code

The same flow works in both modes:

```python
@ai.flow()
async def greet(input: GreetingInput) -> str:
    """Generate a friendly greeting."""
    resp = await ai.generate(prompt=f"Say a friendly hello to {input.name}")
    return resp.text


# Short mode: Call directly
async def run_once():
    result = await greet(GreetingInput(name="World"))
    print(result)


# Server mode: Expose as HTTP
async def run_server(port: int):
    app = create_flows_asgi_app(registry=ai.registry)
    config = uvicorn.Config(app, host='localhost', port=port)
    server = uvicorn.Server(config)
    await server.serve()


# Select mode based on CLI flag
if args.server:
    ai.run_main(run_server(args.port))
else:
    ai.run_main(run_once())
```

## Architecture Comparison

### Short-Lived
```
┌─────────────────────┐
│   CLI invocation    │
│  python main.py     │
└──────────┬──────────┘
           │
           ▼
      Run flow once
           │
           ▼
       Print result
           │
           ▼
         Exit (0)
```

### Long-Running
```
┌─────────────────────┐
│   HTTP Request      │
│ POST //flow/greet   │
└──────────┬──────────┘
           │
           ▼
    ┌────────────┐
    │   Server   │  ← Always running
    │  :3400     │
    └─────┬──────┘
          │
          ▼
      Run flow
          │
          ▼
    JSON response
```

## When to Use Each Mode

| Factor | Short-Lived | Long-Running |
|--------|-------------|--------------|
| **Invocation** | One-time task | Continuous requests |
| **Cost** | Pay per execution | Pay for uptime |
| **Startup** | Cold start every time | Warm (already running) |
| **State** | No state between runs | Can maintain state |
| **Examples** | Lambda, cron | Cloud Run, K8s |

## Related Samples

- [`web-multi-server`](../web-multi-server) - Run multiple servers in parallel
- [`web-flask-hello`](../web-flask-hello) - Flask integration
