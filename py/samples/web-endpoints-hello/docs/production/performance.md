# Performance

The sample includes several production-tuned performance features.

## Response cache

`src/cache.py` provides an in-memory TTL + LRU cache for idempotent
Genkit flows. This avoids redundant LLM API calls for identical inputs.

| Setting | Env var | Default | Description |
|---------|---------|---------|-------------|
| TTL | `CACHE_TTL` | `300` (5 min) | Seconds before entries expire |
| Max size | `CACHE_MAX_SIZE` | `1024` | Max entries (LRU eviction) |
| Enabled | `CACHE_ENABLED` | `true` | Enable/disable cache |

**How it works:**

1. Cache key = SHA-256(flow name + JSON-serialized Pydantic input)
2. On hit → return cached result (no LLM call)
3. On miss → execute flow, store result, evict LRU if over `max_size`
4. Per-key `asyncio.Lock` prevents cache stampedes (thundering herd)

**Statistics:**

```python
cache.stats()
# {"hits": 42, "misses": 10, "hit_rate": 0.8077, "size": 10, ...}
```

## Circuit breaker

`src/circuit_breaker.py` protects against cascading LLM API failures.

| Setting | Env var | Default | Description |
|---------|---------|---------|-------------|
| Failure threshold | `CB_FAILURE_THRESHOLD` | `5` | Consecutive failures before opening |
| Recovery timeout | `CB_RECOVERY_TIMEOUT` | `30` | Seconds before half-open probe |
| Enabled | `CB_ENABLED` | `true` | Enable/disable breaker |

**State machine:**

```
CLOSED ──[5 failures]──► OPEN ──[30s]──► HALF_OPEN
  ▲                                         │
  └───────[probe succeeds]──────────────────┘
                                            │
                            [probe fails]───► OPEN
```

When the circuit is **open**, requests fail immediately with a 503
response instead of waiting for LLM timeouts (120s). This:

- Prevents thread starvation
- Reduces cascading latency
- Saves API quota
- Returns fast errors to users

## Connection tuning

`src/connection.py` configures HTTP connection pools and timeouts:

| Setting | Value | Rationale |
|---------|-------|-----------|
| Keep-alive timeout | 75s | Exceeds typical LB idle timeout (60s) |
| LLM call timeout | 120s | Prevents indefinite hangs on slow models |
| Connection pool size | 100 | Handles burst traffic |
| Max keepalive connections | 20 | Limits open socket count |

## Rate limiting

`src/rate_limit.py` uses a token-bucket algorithm per client IP:

| Setting | Env var | Default | Description |
|---------|---------|---------|-------------|
| Rate | `RATE_LIMIT_DEFAULT` | `60/minute` | Requests per time window |

The token-bucket algorithm provides **smooth** rate limiting without
the boundary-burst problem of fixed-window approaches.

## Multi-worker deployment

For multi-core production deployments, use gunicorn:

```bash
WEB_CONCURRENCY=4 gunicorn -c gunicorn.conf.py 'src.asgi:create_app()'
```

| Setting | Env var | Default | Description |
|---------|---------|---------|-------------|
| Workers | `WEB_CONCURRENCY` | `2 * CPU + 1` | Worker processes (capped at 12) |
| Timeout | `WORKER_TIMEOUT` | `120` | Kill hung workers after this |
| Keep-alive | `KEEP_ALIVE` | `75` | Socket keep-alive timeout |
| Max requests | `MAX_REQUESTS` | `10000` | Recycle workers to prevent memory leaks |
| Jitter | `MAX_REQUESTS_JITTER` | `1000` | Randomize recycling |

## ASGI servers

Three high-performance ASGI servers are supported:

| Server | Language | Strengths |
|--------|----------|-----------|
| **uvicorn** (default) | Python (uvloop) | Mature, well-tested |
| **granian** | Rust | Fastest throughput, low memory |
| **hypercorn** | Python | HTTP/2, HTTP/3 support |

Select via `--server` CLI flag or `SERVER` env var.
