# web-endpoints-hello — Sample Guidelines

## Overview

This is a **self-contained, template-ready** Genkit endpoints sample. It
demonstrates all the ways to expose Genkit flows: REST (ASGI) and gRPC.
It can be copied out of the monorepo and used as a standalone project starter.

## Self-Contained Design

All scripts and dependencies are local — the sample does **not** reference
files outside its directory:

- `scripts/_common.sh` — Shared shell utilities (local copy)
- `scripts/jaeger.sh` — Jaeger container management (podman preferred, docker fallback)
- `scripts/generate_proto.sh` — Regenerate gRPC stubs from proto definition
- `scripts/eject.sh` — Eject from monorepo into standalone project (pins deps, updates CI)
- `setup.sh` — Installs all development tools (uv, just, podman/docker, genkit CLI)
- `Containerfile` — Distroless container image (multi-stage, nonroot)
- `deploy_*.sh` — Platform-specific deployment scripts
- `run.sh` — Main entry point for running the app (REST + gRPC, passes `--debug`)

### Using as a Template

```bash
cp -r web-endpoints-hello my-project
cd my-project
./scripts/eject.sh                     # Auto-detect version, pin deps, update CI
./scripts/eject.sh --version 0.5.0     # Pin to a specific version
./scripts/eject.sh --name my-project   # Also rename the project
./scripts/eject.sh --dry-run           # Preview changes without modifying files
```

The eject script handles all monorepo isolation automatically:

1. Pins `genkit` and `genkit-plugin-*` dependencies to a release version
2. Updates `working-directory` in `.github/workflows/*.yml` from monorepo path to `.`
3. Renames the project (optional, via `--name`)
4. Regenerates the lockfile (`uv lock`)

Then install and run:

```bash
cp local.env.example .local.env   # Configure local dev overrides
just dev                          # Start app + Jaeger
```

## Development Workflow

The dev workflow is designed to be seamless:

1. `./setup.sh` — One-time setup: installs uv, just, podman/docker, genkit CLI
2. `just dev` — Auto-starts Jaeger (uses podman or docker), then the app
3. `just stop` — Kills all services (app, DevUI, Jaeger)

### Key Commands

| Command | What it does |
|---------|-------------|
| `just dev` | Start app + Jaeger (with tracing, passes `--debug`) |
| `just dev-litestar` | Same, with Litestar framework |
| `just dev-quart` | Same, with Quart framework |
| `just prod` | Multi-worker production server (gunicorn) |
| `just stop` | Stop all services |
| `just test` | Run pytest |
| `just coverage` | Run tests with coverage (terminal + HTML) |
| `just coverage-open` | Run coverage and open HTML report |
| `just lint` | Run all lint checks (mirrors workspace `bin/lint`) |
| `just eject` | Eject from monorepo into standalone project |
| `just eject-dry-run` | Preview eject changes |
| `./run.sh` | Start app only (no Jaeger, passes `--debug`) |

## Architecture

```
src/
├── __init__.py          # Package docstring
├── app_init.py          # Genkit instance + cloud telemetry auto-detection
├── asgi.py              # ASGI app factory for gunicorn (multi-worker)
├── cache.py             # TTL + LRU response cache (stampede protection)
├── circuit_breaker.py   # Async-safe circuit breaker for LLM API protection
├── config.py            # Settings via pydantic-settings + CLI args (secure defaults)
├── connection.py        # Connection pool / keep-alive tuning
├── flows.py             # Genkit flow definitions (with cache + breaker)
├── generated/           # Protobuf + gRPC stubs (auto-generated)
├── grpc_server.py       # gRPC service + logging/rate-limit interceptors
├── log_config.py        # Structured logging (Rich/JSON + structlog + secret masking)
├── main.py              # Entry point: resilience → security → start servers
├── rate_limit.py        # Token-bucket rate limiting (ASGI + gRPC)
├── resilience.py        # Shared cache + circuit breaker singletons
├── schemas.py           # Pydantic models with Field constraints
├── security.py          # ASGI security middleware stack (see below)
├── sentry_init.py       # Optional Sentry error tracking
├── server.py            # ASGI server helpers (granian/uvicorn/hypercorn)
├── telemetry.py         # OpenTelemetry setup + framework instrumentation
└── frameworks/
    ├── fastapi_app.py   # FastAPI adapter (debug gates Swagger UI)
    ├── litestar_app.py  # Litestar adapter (debug gates OpenAPI docs)
    └── quart_app.py     # Quart adapter
gunicorn.conf.py         # Gunicorn config for multi-worker production
protos/
└── genkit_sample.proto  # gRPC service definition
```

## Frameworks & Servers

- **REST Frameworks**: FastAPI (default), Litestar, Quart — selected via `--framework`
- **ASGI Servers**: uvicorn (default), granian, hypercorn — selected via `--server`
- **gRPC Server**: runs in parallel on `:50051` (disable with `--no-grpc`)
- Each framework adapter in `src/frameworks/` provides a `create_app(ai, *, debug)` factory

## Tracing

OpenTelemetry is a **required** dependency (not optional). `just dev` auto-starts
Jaeger and passes `--otel-endpoint http://localhost:4318` so every request
produces a trace visible at `http://localhost:16686`.

## Testing

Tests live in `tests/` and require `pythonpath = ["."]` in `pyproject.toml`
(already configured) so `from src.* import ...` works from any working directory.

```bash
just test               # Run all tests
uv run pytest tests/    # Same, without just
```

## Performance & Resilience

- **Response cache** — In-memory TTL + LRU cache for idempotent flows (`src/cache.py`). Per-key `asyncio.Lock` coalescing prevents cache stampedes. Configurable via `CACHE_TTL`, `CACHE_MAX_SIZE`, `CACHE_ENABLED`.
- **Circuit breaker** — Async-safe protection against cascading LLM API failures (`src/circuit_breaker.py`). States: CLOSED → OPEN → HALF_OPEN. Gated half-open probes. Configurable via `CB_FAILURE_THRESHOLD`, `CB_RECOVERY_TIMEOUT`.
- **Connection tuning** — Keep-alive (75s) exceeds LB idle timeout (60s) to prevent 502s. LLM timeout (120s) prevents indefinite hangs. Pool sizes tuned via env vars.
- **Multi-worker** — `gunicorn.conf.py` + `src/asgi.py` for multi-process production deployments. `just prod` shortcut. Worker recycling prevents memory leaks.
- **Request ID** — `X-Request-ID` header on every request/response, bound to structlog context for log correlation (`src/security.py`).
- **JSON logging** — `LOG_FORMAT=json` (production default) for log aggregators (`src/log_config.py`). Override to `console` in `local.env`.
- **Readiness probe** — Separate `/ready` endpoint for k8s readiness probes. Exempt from rate limiting.

## Security — Secure by Default

The sample follows a **secure-by-default** philosophy: every default is
chosen so that a fresh deployment with zero configuration is locked down.
Development convenience requires explicit opt-in via `--debug` or `DEBUG=true`.

### Debug mode

A single flag gates all development-only features:

| Feature | `debug=false` (default) | `debug=true` |
|---------|-----------------------|-------------|
| Swagger UI (`/docs`, `/redoc`) | Disabled | Enabled |
| OpenAPI schema (`/openapi.json`) | Disabled | Enabled |
| gRPC reflection | Disabled | Enabled |
| Content-Security-Policy | `default-src none` (strict) | Relaxed for Swagger CDN |
| CORS (when unconfigured) | Same-origin only | `*` (wildcard) |
| Log format (when unconfigured) | `json` (structured) | `console` (colored) |
| Trusted hosts warning | Logs warning at startup | Suppressed |

Activate: `--debug` CLI flag, `DEBUG=true` env var, or `run.sh` (passes
`--debug` automatically).

**Never set `DEBUG=true` in production.** The `run.sh` dev script passes
`--debug` automatically; production entry points (gunicorn, Cloud Run,
Kubernetes) should never set it.

### `debug=False` security invariants

When modifying any code that uses the `debug` flag, verify that
`debug=False` (production) **always** picks the more restrictive option.
This checklist covers every location where `debug` is checked:

| Module | What `debug=False` does | What to verify |
|--------|------------------------|----------------|
| `security.py` `SecurityHeadersMiddleware` | Strict CSP: `default-src none` | Never use the relaxed CDN allowlist in production |
| `security.py` `ExceptionMiddleware` | Returns generic `"Internal server error"` | Never expose exception type or traceback to clients |
| `security.py` `apply_security_middleware` | CORS origins default to `[]` (same-origin) | Never fall back to `["*"]` when `debug=False` |
| `security.py` trusted hosts warning | Logs a warning when `TRUSTED_HOSTS` is empty | Warning fires in production, not in debug |
| `fastapi_app.py` | `docs_url=None`, `redoc_url=None`, `openapi_url=None` | Swagger UI and OpenAPI schema are disabled |
| `litestar_app.py` | `enabled_endpoints=set()` | All doc endpoints are disabled |
| `quart_app.py` | `debug` accepted but unused (no built-in Swagger) | No security impact; verify no future code adds a gate |
| `grpc_server.py` | gRPC reflection not registered | API schema not exposed to unauthenticated clients |
| `main.py` log format | Keeps `log_format="json"` (no colored console) | Never switch to `console` unless `debug=True` |
| `config.py` | `debug: bool = False` | Default is `False`; CLI uses `action="store_true"` |

**Rule:** Every `if debug:` block must enable a development convenience
(not a security feature). Every `if not debug:` block must enforce
a security restriction or emit a security warning. If a new feature
needs `debug`, add it to this table and the debug mode matrix above.

### Secure defaults vs development overrides

| Setting | Production default | Dev override (`local.env`) |
|---------|-------------------|--------------------------|
| `DEBUG` | `false` | `true` |
| `CORS_ALLOWED_ORIGINS` | `""` (same-origin) | `*` |
| `LOG_FORMAT` | `json` | `console` |
| `TRUSTED_HOSTS` | `""` (warns at startup) | (empty OK in dev) |
| `RATE_LIMIT_DEFAULT` | `60/minute` | (same) |
| `MAX_BODY_SIZE` | `1048576` (1 MB) | (same) |

### Security features

| Feature | Module | What it does |
|---------|--------|-------------|
| **OWASP security headers** | `security.py` | CSP, X-Frame-Options, HSTS, Referrer-Policy, etc. via `secure` library |
| **CORS** | `security.py` | Same-origin by default; explicit allowlist in production |
| **Rate limiting** | `rate_limit.py` | Token-bucket per client IP (REST 429 + gRPC RESOURCE_EXHAUSTED) |
| **Body size limit** | `security.py` | 413 on oversized payloads before parsing (prevents memory exhaustion) |
| **Per-request timeout** | `security.py` | Returns 504 on expiry; configurable via settings/CLI |
| **Global exception handler** | `security.py` | Returns JSON 500; no tracebacks to clients in production |
| **Secret masking in logs** | `log_config.py` | structlog processor redacts API keys, tokens, passwords, DSNs |
| **HTTP access logging** | `security.py` | Logs method, path, status, duration for every request |
| **Server header suppression** | `security.py` | Removes `Server` header to prevent version fingerprinting |
| **Cache-Control: no-store** | `security.py` | Prevents intermediaries/browsers from caching API responses |
| **HSTS** | `security.py` | Conditional on HTTPS; configurable `max-age` |
| **GZip compression** | `security.py` | Via Starlette `GZipMiddleware`; configurable minimum size |
| **Input validation** | `schemas.py` | Pydantic `Field` constraints on all inputs (max_length, pattern, etc.) |
| **Request ID** | `security.py` | UUID4 generation/propagation, structlog binding, response echo |
| **Trusted hosts** | `security.py` | Host-header validation (warns if unconfigured in production) |
| **gRPC interceptors** | `grpc_server.py` | Logging + rate limiting + max message size + debug-only reflection |
| **Circuit breaker** | `circuit_breaker.py` | Fail fast on LLM API degradation (prevents cascading failures) |
| **Cache stampede protection** | `cache.py` | Per-key request coalescing (prevents thundering herd) |
| **Graceful shutdown** | `main.py` / `grpc_server.py` | SIGTERM handling with configurable grace period (default: 10s) |
| **Structured logging** | `log_config.py` | JSON by default (production); console override for dev; secret masking |
| **Sentry** | `sentry_init.py` | Optional error tracking (`SENTRY_DSN`); PII stripped |
| **Platform telemetry** | `app_init.py` | Auto-detects GCP/AWS/Azure; guarded `try/except ImportError` |
| **License checks** | `justfile` | `just licenses` validates dependency licenses via `liccheck` |
| **Vulnerability scanning** | `justfile` | `just audit` checks for CVEs via `pip-audit` + `pysentry-rs` |
| **Distroless container** | `Containerfile` | No shell, nonroot (uid 65534), ~50 MB, no package manager |

All middleware is framework-agnostic (pure ASGI) and applied in
`apply_security_middleware()`.

### ASGI middleware stack order

Middleware is applied inside-out in `apply_security_middleware()`. The
request-flow order is:

```
AccessLog → GZip → CORS → TrustedHost → Timeout → MaxBodySize
  → ExceptionHandler → SecurityHeaders → RequestId → App
```

### CORS allow_headers

The CORS middleware uses an **explicit allowlist** of headers, not `["*"]`:

```python
allow_headers=["Content-Type", "Authorization", "X-Request-ID"]
```

Wildcard `allow_headers` enables cache poisoning and header injection via
CORS preflight — the explicit list only permits headers the API uses.

### Platform telemetry auto-detection

Auto-detects cloud platform by checking environment signals:

| Platform | Signal | Notes |
|----------|--------|-------|
| GCP (Cloud Run) | `K_SERVICE` | Always triggers |
| GCP (GCE/GKE) | `GCE_METADATA_HOST` | Always triggers |
| GCP (explicit) | `GOOGLE_CLOUD_PROJECT` + `GENKIT_TELEMETRY_GCP=1` | Requires opt-in (GOOGLE_CLOUD_PROJECT alone is too common on dev machines) |
| AWS | `AWS_EXECUTION_ENV` | Always triggers |
| Azure | `CONTAINER_APP_NAME` | Always triggers |
| Generic OTLP | `OTEL_EXPORTER_OTLP_ENDPOINT` | Fallback |

## Threading, Asyncio & Event-Loop Audit Checklist

When modifying any concurrency-related code in this sample (cache, circuit
breaker, rate limiter, middleware), check every item below. These are real
bugs found during code audits.

### Lock types

- **Never use `threading.Lock`/`RLock` in async code** — blocks the event
  loop. All locks in this sample use `asyncio.Lock`.
- **Third-party sync libraries may use threading locks internally.** This
  is why `circuit_breaker.py` and `cache.py` use custom implementations
  instead of wrapping `pybreaker` or `aiocache` — see docstrings for details.

### Time functions

- **Use `time.monotonic()` for intervals/durations**, not `time.time()` or
  `datetime.now()`. Wall-clock time is subject to NTP jumps.
- **Clamp `retry_after`** to `[0, 3600]` to guard against clock anomalies.
- **Call time functions once** and reuse the value when needed in multiple
  expressions.

### Race conditions

- **Cache stampede prevention** — `cache.py` uses per-key `asyncio.Lock`
  coalescing so only one coroutine executes the expensive LLM call per cache
  key. Without this, concurrent misses for the same key all trigger duplicate
  LLM API calls.
- **Half-open probe gating** — `circuit_breaker.py` tracks
  `_half_open_calls` inside the async lock so only `half_open_max_calls`
  probes are allowed in flight. Without this, all concurrent callers that
  arrive during the half-open window would probe simultaneously.
- **Avoid `exists()` + `delete()`** — use a single `delete()` or check-and-delete
  inside one lock acquisition to prevent TOCTOU races.

### Blocking I/O

- **Never call sync network I/O from async code.** All rate limiting,
  caching, and circuit breaking in this sample use in-memory data structures
  (sub-microsecond, safe on the event loop). If switching to Redis/Memcached
  backends, wrap calls in `asyncio.to_thread()`.

### OSS library decisions

| Area | Decision | Why |
|------|----------|-----|
| **Circuit breaker** | Custom (`circuit_breaker.py`) | `pybreaker` is sync-only, uses `threading.RLock`, requires private API access, uses wall-clock time |
| **Cache** | Custom (`cache.py`) | `aiocache` has no LRU, no stampede prevention, weak types, same line count |
| **Rate limiter** | Custom (`rate_limit.py`) | `limits` is sync-only, uses `time.time()`, fixed-window allows boundary bursts |
| **Security headers** | OSS (`secure` library) | Tracks OWASP recommendations, header deprecations (X-XSS-Protection), evolving browser standards |

See the module docstrings in each file for detailed rationale.

## Code Quality

`pyproject.toml` includes full linter and type checker configs — they work
both inside the monorepo and when the sample is copied out as a standalone
project:

| Tool | Purpose |
|------|---------|
| **Ruff** | Linting + formatting (isort, security, async, type annotations) |
| **ty** | Astral's type checker (strict, blocks on errors) |
| **Pyright** | Microsoft's type checker (basic mode) |
| **Pyrefly** | Meta's type checker (strict, warnings-as-errors) |

```bash
just lint                # Run all checks (mirrors workspace bin/lint)
just typecheck           # Type checkers only (ty, pyrefly, pyright)
just fmt                 # Format code with ruff
```

`just lint` includes: ruff check, ruff format, ty, pyrefly, pyright,
shellcheck, addlicense, pysentry-rs, liccheck, and `uv lock --check`.
