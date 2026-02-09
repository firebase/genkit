# Multi-Server Pattern

Run multiple ASGI applications concurrently on different ports, all managed by `ServerManager`.

## What This Demonstrates

**Core Concept**: Multiple independent HTTP servers in one process
- Each server runs on its own port
- Coordinated startup and shutdown
- Graceful SIGTERM/SIGINT handling

## Use Cases

1. **Public + Admin APIs**: Expose different endpoints on different ports
   - Public API on :3400 → External users
   - Admin API on :3401 → Internal dashboards

2. **HTTP + gRPC**: Run both protocols side-by-side
   - HTTP REST on :8080
   - gRPC on :50051

3. **Microservices in One Container**: Multiple services, one deployment
   - Users service on :3400
   - Orders service on :3401
   - Payments service on :3402

## Running the Sample

```bash
cd py/samples/web-multi-server
uv run python src/main.py
```

## Testing

```bash
# Public API (Port 3400)
curl http://localhost:3400/api/hello
curl http://localhost:3400/api/status

# Admin API (Port 3401)
curl http://localhost:3401/admin/metrics
curl http://localhost:3401/admin/config
```

## Architecture

```
┌────────────────────────────────────────────┐
│           ServerManager                    │
│  (coordinates lifecycle + shutdown)        │
└────────────────────────────────────────────┘
         │              │
         ▼              ▼
    ┌─────────┐    ┌─────────┐
    │ Public  │    │ Admin   │
    │ :3400   │    │ :3401   │
    └─────────┘    └─────────┘
```

All servers:
- Start together
- Stop together on Ctrl+C
- Automatic port fallback (e.g., if 3400 is busy, tries 3401-3409)

## Key Code

The pattern requires:

1. **Lifecycle class** (implements `AbstractBaseServer`)
2. **ServerConfig** with name, ports, host
3. **ServerManager** to coordinate everything

```python
servers = [
    Server(
        config=ServerConfig(name='public', port=3400, ports=range(3400, 3410)),
        lifecycle=PublicServerLifecycle(),
        adapter=UvicornAdapter(),
    ),
    Server(
        config=ServerConfig(name='admin', port=3401, ports=range(3401, 3411)),
        lifecycle=AdminServerLifecycle(),
        adapter=UvicornAdapter(),
    ),
]

manager = ServerManager()
await manager.run_all(servers)  # Blocks until SIGTERM
```

## When NOT to Use This

- **Simple single API**: Just use `create_flows_asgi_app()` (see `web-short-n-long`)
- **Need inter-process isolation**: Use separate containers instead
- **Different scaling needs**: Use Kubernetes services instead

## Related Samples

- [`web-short-n-long`](../web-short-n-long) - Single server deployment patterns
- [`web-flask-hello`](../web-flask-hello) - Flask integration
