# Security & Hardening

This sample follows a **secure-by-default** philosophy.  Every
configuration default is chosen so that a fresh deployment with zero
configuration is locked down.  Development convenience (Swagger UI,
colored logs, open CORS, gRPC reflection) requires *explicit* opt-in.

!!! tip "Design principle"
    _"If someone forgets to configure this, should the system be open
    or closed?"  Choose closed._

---

## Secure-by-default design

| Principle | How it's enforced |
|-----------|-------------------|
| Locked down on deploy | All defaults are restrictive; dev features require `--debug` or `DEBUG=true` |
| Debug is explicit | A single flag gates Swagger UI, gRPC reflection, relaxed CSP, open CORS |
| Defense in depth | Multiple independent layers — any single bypass still leaves others active |
| Framework-agnostic | All middleware is pure ASGI (no FastAPI/Litestar/Quart dependency) |
| Fail closed | Missing config → deny; not "missing config → allow" |

---

## Debug mode

A single `debug` flag (via `--debug` CLI, `DEBUG=true` env var, or
`Settings.debug`) controls all development-only features:

| Feature | `debug=false` (production default) | `debug=true` (development) |
|---------|------------------------------------|---------------------------|
| Swagger UI (`/docs`, `/redoc`) | Disabled (`docs_url=None`) | Enabled |
| OpenAPI schema (`/openapi.json`) | Disabled (`openapi_url=None`) | Enabled |
| gRPC reflection | Disabled | Enabled (for `grpcui` / `grpcurl`) |
| Content-Security-Policy | `default-src none` (strict) | Allows `cdn.jsdelivr.net`, `fastapi.tiangolo.com`, inline scripts |
| CORS (when unconfigured) | Same-origin only (`[]`) | Wildcard (`["*"]`) |
| Trusted hosts warning | Logs a warning at startup | Suppressed |
| Log format (when unconfigured) | `json` (structured) | `console` (colored) |

Activate debug mode:

```bash
# CLI flag (used by run.sh automatically)
python -m src --debug

# Environment variable
DEBUG=true python -m src

# In .local.env
DEBUG=true
```

!!! danger "Never use `--debug` in production"
    Debug mode disables critical security controls.  The `run.sh` script
    passes `--debug` automatically for local development; production
    deployments (gunicorn, Cloud Run, Kubernetes) should **never** set it.

---

## Middleware stack

Security middleware is applied as pure ASGI wrappers.  The order for an
incoming request:

```
AccessLog → GZip → CORS → TrustedHost → Timeout → MaxBodySize
  → ExceptionHandler → SecurityHeaders → RequestId → App
```

Each layer is independent — disabling one doesn't affect the others.
The response passes through the same layers in reverse.

### Security headers (OWASP)

`SecurityHeadersMiddleware` (in `src/security.py`) uses the
[`secure`](https://secure.readthedocs.io/) library to inject
OWASP-recommended headers on every HTTP response:

| Header | Value | Purpose |
|--------|-------|---------|
| `Content-Security-Policy` | `default-src none` | Block all resource loading (API-only server) |
| `X-Content-Type-Options` | `nosniff` | Prevent MIME-type sniffing |
| `X-Frame-Options` | `DENY` | Block clickjacking via iframes |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Limit referrer leakage |
| `Permissions-Policy` | `geolocation=(), camera=(), microphone=()` | Disable unnecessary browser APIs |
| `Cross-Origin-Opener-Policy` | `same-origin` | Isolate browsing context |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | Force HTTPS (only added over HTTPS) |

!!! note "X-XSS-Protection omitted intentionally"
    The browser XSS auditor it controlled has been removed from all modern
    browsers, and setting it can *introduce* XSS in older browsers (OWASP
    recommendation since 2023).  The `secure` library dropped it for this
    reason.

**Debug mode CSP** allows Swagger UI to function by permitting CDN
resources from `cdn.jsdelivr.net`, the FastAPI favicon, and inline
scripts.

### CORS

Starlette's `CORSMiddleware` is configured from `CORS_ALLOWED_ORIGINS`:

| Scenario | `CORS_ALLOWED_ORIGINS` | Effective behavior |
|----------|----------------------|-------------------|
| Production (default) | `""` (empty) | Same-origin only — all cross-origin requests denied |
| Production (explicit) | `"https://app.example.com"` | Only listed origins allowed |
| Development (debug, unconfigured) | `""` (empty) | Falls back to `*` (wildcard) |

Additional CORS settings (hardcoded for security):

- **Allowed methods**: `GET`, `POST`, `OPTIONS`
- **Allowed headers**: `Content-Type`, `Authorization`, `X-Request-ID`
- **Credentials**: `False` (cookies/auth headers not forwarded)

!!! warning "Why not `allow_headers=["*"]`?"
    Wildcard allowed headers let any custom header through CORS preflight,
    which can be exploited for cache poisoning or header injection.  The
    explicit list only permits headers the API actually uses.

### Request ID / correlation

`RequestIdMiddleware` assigns a unique ID to every HTTP request:

1. If the client sends `X-Request-ID`, it is reused (for end-to-end tracing)
2. Otherwise, a UUID4 is generated
3. The ID is bound to `structlog` context vars — every log line includes `request_id`
4. The ID is echoed in the `X-Request-ID` response header
5. The ID is stored in `scope["state"]["request_id"]` for framework access

### Body size limit

`MaxBodySizeMiddleware` checks `Content-Length` **before** the framework
parses the body, preventing memory exhaustion:

- Default: 1 MB (1,048,576 bytes)
- Override: `MAX_BODY_SIZE=2097152` (2 MB)
- Response: `413 Payload Too Large` with JSON body

The gRPC server applies the same limit via `grpc.max_receive_message_length`.

### Trusted host validation

When `TRUSTED_HOSTS` is set, Starlette's `TrustedHostMiddleware` rejects
requests with spoofed `Host` headers (returns 400).

```bash
TRUSTED_HOSTS=api.example.com,admin.example.com
```

If `TRUSTED_HOSTS` is empty in production (non-debug) mode, a **warning**
is logged at startup:

> No TRUSTED_HOSTS configured — Host-header validation is disabled.
> Set TRUSTED_HOSTS to your domain(s) in production to prevent
> host-header poisoning attacks.

---

## Rate limiting

Token-bucket rate limiting is applied per client IP at both protocol
layers using the same algorithm:

| Protocol | Component | Over-limit response | Headers |
|----------|-----------|-------------------|---------|
| REST | `RateLimitMiddleware` | `429 Too Many Requests` | `Retry-After` |
| gRPC | `GrpcRateLimitInterceptor` | `RESOURCE_EXHAUSTED` | — |

Configuration:

```bash
RATE_LIMIT_DEFAULT=60/minute    # Default
RATE_LIMIT_DEFAULT=100/second   # High-traffic API
RATE_LIMIT_DEFAULT=10/minute    # Restrictive
```

Health endpoints (`/health`, `/healthz`, `/ready`, `/readyz`) are exempt
from rate limiting so orchestration platforms can always probe.

---

## Input validation

All input models in `src/schemas.py` use Pydantic `Field` constraints to
reject malformed input before it reaches any Genkit flow or LLM call:

| Constraint | Example | Purpose |
|-----------|---------|---------|
| `max_length` | Name ≤ 200, text ≤ 10,000, code ≤ 50,000 | Prevent oversized strings |
| `min_length` | text ≥ 1 (no empty strings) | Reject empty inputs |
| `ge` / `le` | 0 ≤ skill ≤ 100 | Numeric range validation |
| `pattern` | `^[a-zA-Z#+]+$` for language | Prevent injection in freeform fields |

Pydantic returns a `422 Unprocessable Entity` with detailed validation
errors for invalid input — no custom error handling needed.

Additional sanitization in `src/flows.py`:

- `text.strip()[:2000]` — normalize and truncate freeform text before
  passing to the LLM

---

## Resilience

### Circuit breaker

`CircuitBreaker` (in `src/circuit_breaker.py`) protects against cascading
failures when the LLM API is degraded.  After consecutive failures, it
fails fast without making API calls, then probes with a single request
before reopening.

| Setting | Env Var | Default | Description |
|---------|---------|---------|-------------|
| Enabled | `CB_ENABLED` | `true` | Enable/disable |
| Failure threshold | `CB_FAILURE_THRESHOLD` | `5` | Consecutive failures to trip |
| Recovery timeout | `CB_RECOVERY_TIMEOUT` | `30.0` | Seconds before half-open probe |

States: **Closed** (normal) → **Open** (fail fast) → **Half-open** (probe).

Uses `time.monotonic()` for NTP-immune timing and `asyncio.Lock` for
thread safety.

### Response cache (stampede protection)

`FlowCache` (in `src/cache.py`) provides in-memory TTL + LRU caching
for idempotent flows with **per-key request coalescing** to prevent cache
stampedes (thundering herd):

| Setting | Env Var | Default | Description |
|---------|---------|---------|-------------|
| Enabled | `CACHE_ENABLED` | `true` | Enable/disable |
| TTL | `CACHE_TTL` | `300` | Time-to-live in seconds |
| Max entries | `CACHE_MAX_SIZE` | `1024` | LRU eviction after this count |

- Uses SHA-256 hashed cache keys (via `src/util/hash.py`)
- Per-key `asyncio.Lock` prevents concurrent identical LLM calls
- Non-idempotent flows (chat, joke) and streaming flows bypass the cache

---

## Connection tuning

| Setting | Env Var | Default | Purpose |
|---------|---------|---------|---------|
| Server keep-alive | `KEEP_ALIVE_TIMEOUT` | `75s` | Above typical 60s LB idle timeout to prevent premature disconnects |
| LLM API timeout | `LLM_TIMEOUT` | `120000ms` | 2-minute hard timeout for LLM calls |
| Connection pool max | `HTTPX_POOL_MAX` | `100` | Max concurrent outbound connections |
| Pool keepalive | `HTTPX_POOL_MAX_KEEPALIVE` | `20` | Max idle connections kept alive |

Configured in `src/connection.py` via `configure_httpx_defaults()`.

---

## Graceful shutdown

SIGTERM is handled with a configurable grace period:

- **Default**: 10 seconds (matches Cloud Run's SIGTERM window)
- **Override**: `SHUTDOWN_GRACE=30` (seconds)
- **gRPC**: `server.stop(grace=shutdown_grace)` drains in-flight RPCs
- **ASGI**: Server-native shutdown (granian/uvicorn/hypercorn)

---

## gRPC security

| Feature | Configuration | Default |
|---------|---------------|---------|
| Max message size | `grpc.max_receive_message_length` | 1 MB (matches REST) |
| Rate limiting | `GrpcRateLimitInterceptor` | `60/minute` per peer |
| Logging | `GrpcLoggingInterceptor` | Logs method, duration, status |
| Reflection | Debug-only | Disabled in production |

!!! warning "gRPC reflection disabled in production"
    Reflection exposes the full API schema (service names, method
    signatures, message types) to unauthenticated clients.  It is only
    enabled when `debug=true`.

---

## Structured logging

| Mode | `LOG_FORMAT` | Output |
|------|-------------|--------|
| Production (default) | `json` | Machine-parseable, no ANSI codes, suitable for log aggregation |
| Development | `console` | Colored, human-friendly with Rich tracebacks |

All log entries include `request_id` from `RequestIdMiddleware` for
request-level correlation.  Set `LOG_FORMAT=console` in your `.local.env`
for development.

---

## Error tracking (Sentry)

Optional integration — only active when `SENTRY_DSN` is set:

```bash
SENTRY_DSN=https://examplePublicKey@o0.ingest.sentry.io/0
SENTRY_TRACES_SAMPLE_RATE=0.1       # 10% of transactions
SENTRY_ENVIRONMENT=production
```

- Auto-detects active framework (FastAPI, Litestar, Quart) + gRPC
- PII stripped by default (`send_default_pii=False`)
- Install: `uv sync --extra sentry` or `pip install "sentry-sdk[fastapi,litestar,quart,grpc]"`

---

## Platform telemetry auto-detection

`src/app_init.py` automatically detects the cloud platform at startup and
enables the matching telemetry plugin (if installed):

| Platform | Detection signal | Plugin (optional dep) |
|----------|-----------------|----------------------|
| GCP — Cloud Run | `K_SERVICE` | `genkit-plugin-google-cloud` (`[gcp]` extra) |
| GCP — GCE/GKE | `GCE_METADATA_HOST` | `genkit-plugin-google-cloud` (`[gcp]` extra) |
| AWS — ECS/App Runner | `AWS_EXECUTION_ENV` | `genkit-plugin-amazon-bedrock` (`[aws]` extra) |
| Azure — Container Apps | `CONTAINER_APP_NAME` | `genkit-plugin-microsoft-foundry` (`[azure]` extra) |
| Generic OTLP | `OTEL_EXPORTER_OTLP_ENDPOINT` | `genkit-plugin-observability` (`[observability]` extra) |

!!! note "GOOGLE_CLOUD_PROJECT alone doesn't trigger GCP telemetry"
    It's commonly set on dev machines for the gcloud CLI.  To force GCP
    telemetry locally, also set `GENKIT_TELEMETRY_GCP=1`.

Disable all telemetry: `GENKIT_TELEMETRY_DISABLED=1` or `--no-telemetry`.

---

## Dependency auditing

```bash
just audit      # pip-audit — checks against PyPA advisory database
just security   # pysentry-rs + pip-audit + liccheck (all checks)
just licenses   # License compliance against allowlist
just lint       # Includes all of the above plus linters and type checkers
```

**License allowlist**: Apache-2.0, MIT, BSD-3-Clause, BSD-2-Clause,
PSF-2.0, ISC, Python-2.0, MPL-2.0.

---

## Container security

The `Containerfile` produces a hardened image using
`gcr.io/distroless/python3-debian13:nonroot`:

| Property | Value |
|----------|-------|
| Shell | None (cannot `exec` into container) |
| Package manager | None (no `apt install` attack vector) |
| User | uid 65534 (`nonroot`) |
| Base size | ~50 MB (vs ~150 MB for `python:3.13-slim`) |
| `setuid` binaries | None |

---

## Health check endpoints

| Endpoint | Purpose | Rate limited |
|----------|---------|-------------|
| `GET /health` | Liveness — process is running | No |
| `GET /ready` | Readiness — app can serve traffic | No |

Both return `{"status": "ok"}` with minimal overhead.

---

## Production hardening checklist

| Item | How | Secure default |
|------|-----|----------------|
| Debug mode | `DEBUG=false` | Off — Swagger, reflection, relaxed CSP disabled |
| TLS termination | Load balancer / reverse proxy | Not included (use Cloud Run, nginx, etc.) |
| Trusted hosts | `TRUSTED_HOSTS=api.example.com` | Disabled (warns at startup) |
| CORS | `CORS_ALLOWED_ORIGINS=https://app.example.com` | Same-origin only |
| Rate limiting | `RATE_LIMIT_DEFAULT=100/minute` | `60/minute` |
| Body size limit | `MAX_BODY_SIZE=524288` | 1 MB |
| Log format | `LOG_FORMAT=json` | JSON (structured) |
| Secrets management | Cloud secrets manager (not `.env`) | `.env` files (dev only) |
| Error tracking | `SENTRY_DSN=...` | Disabled |
| Container image | `Containerfile` with distroless + nonroot | Included |
| Dependency audit | `just security` in CI | Manual |
| License compliance | `just licenses` in CI | Manual |

---

## Security environment variables

| Variable | Description | Secure default |
|----------|-------------|----------------|
| `DEBUG` | Enable dev-only features (Swagger, reflection, relaxed CSP) | `false` |
| `CORS_ALLOWED_ORIGINS` | Comma-separated allowed CORS origins | `""` (same-origin) |
| `TRUSTED_HOSTS` | Comma-separated allowed Host headers | `""` (disabled, warns) |
| `RATE_LIMIT_DEFAULT` | Rate limit in `<count>/<period>` format | `60/minute` |
| `MAX_BODY_SIZE` | Max request body in bytes | `1048576` (1 MB) |
| `LOG_FORMAT` | `json` (production) or `console` (dev) | `json` |
| `SHUTDOWN_GRACE` | Graceful shutdown grace period in seconds | `10.0` |
| `SENTRY_DSN` | Sentry Data Source Name | `""` (disabled) |
| `SENTRY_TRACES_SAMPLE_RATE` | Fraction of transactions to sample | `0.1` |
| `SENTRY_ENVIRONMENT` | Sentry environment tag | (auto from `--env`) |
| `GENKIT_TELEMETRY_DISABLED` | Disable all platform telemetry | `""` (enabled) |
| `GENKIT_TELEMETRY_GCP` | Force GCP telemetry with `GOOGLE_CLOUD_PROJECT` | `""` (disabled) |
