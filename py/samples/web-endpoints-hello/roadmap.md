# Roadmap

Planned improvements for the web-endpoints-hello sample. Items are
roughly ordered by priority within each category.

---

## Migrate production modules into Genkit core

The sample currently bundles ~20 production-readiness modules that
every Genkit Python app would need. The long-term goal is to move
the framework-agnostic ones into `genkit` core so that the sample
shrinks to flows + schemas + config only.

### Module dependency graph

```
                        ┌──────────────────────────────────────────────────────────────┐
                        │                     APPLICATION LAYER                        │
                        │                                                              │
                        │   main.py ──────────┬──── config.py (Settings, CLI args)     │
                        │     │               │                                        │
                        │     ├── asgi.py     ├──── sentry_init.py                     │
                        │     │   (app        │                                        │
                        │     │   factory)    ├──── telemetry.py                       │
                        │     │               │                                        │
                        │     ├── server.py   ├──── logging.py                         │
                        │     │   (granian,   │                                        │
                        │     │    uvicorn,   └──── grpc_server.py                     │
                        │     │    hypercorn)       │                                  │
                        │     │                     │                                  │
                        │     └── flows.py ─────────┼── schemas.py (Pydantic models)   │
                        │                           │                                  │
                        └───────────────────────────┼──────────────────────────────────┘
                                                    │
                        ┌───────────────────────────┼──────────────────────────────────┐
                        │            PRODUCTION MIDDLEWARE LAYER                        │
                        │                           │                                  │
                        │   security.py ────────────┤  RequestIdMiddleware             │
                        │     (headers, CORS,       │  SecurityHeadersMiddleware       │
                        │      body-size,           │  MaxBodySizeMiddleware           │
                        │      trusted-host)        │                                  │
                        │                           │                                  │
                        │   rate_limit.py ──────────┤  RateLimitMiddleware (ASGI)      │
                        │     (token bucket)        │  GrpcRateLimitInterceptor        │
                        │                           │                                  │
                        │   cache.py ───────────────┤  FlowCache (TTL + LRU)           │
                        │                           │                                  │
                        │   circuit_breaker.py ─────┤  CircuitBreaker                  │
                        │                           │                                  │
                        │   connection.py ──────────┤  HTTP pool + keep-alive tuning   │
                        │                           │                                  │
                        │   resilience.py ──────────┤  Global cache + breaker singletons│
                        │                           │                                  │
                        └───────────────────────────┼──────────────────────────────────┘
                                                    │
                        ┌───────────────────────────┼──────────────────────────────────┐
                        │               UTILITY LAYER (zero app deps)                  │
                        │                           │                                  │
                        │   util/asgi.py ───────────┤  send_json_error, get_client_ip  │
                        │   util/date.py ───────────┤  utc_now_str, format_utc         │
                        │   util/hash.py ───────────┤  make_cache_key                  │
                        │   util/parse.py ──────────┤  parse_rate, split_comma_list    │
                        │                           │                                  │
                        └──────────────────────────────────────────────────────────────┘
                                                    │
                        ┌───────────────────────────┼──────────────────────────────────┐
                        │                  GENKIT CORE (today)                          │
                        │                                                              │
                        │   genkit.web.manager ─────┤  ServerManager, adapters, ports  │
                        │   genkit.web.typing ──────┤  ASGI type aliases               │
                        │   genkit.core.flows ──────┤  /__health, flow execution       │
                        │   genkit.core.http_client ┤  Per-loop httpx client pool      │
                        │   genkit.core.logging ────┤  structlog typed wrapper         │
                        │   genkit.core.tracing ────┤  OpenTelemetry spans             │
                        │   genkit.core.error ──────┤  GenkitError, status codes       │
                        │                                                              │
                        └──────────────────────────────────────────────────────────────┘
```

### Classification: what stays vs. what moves

The table below classifies every sample module by where it should
live long-term. "Core" means `genkit` package. "Plugin" means a
separate `genkit-plugin-*` package. "Sample" means it stays here.

| Module | Current | Target | Rationale |
|--------|---------|--------|-----------|
| `security.py` | Sample | **Core** | Every ASGI Genkit app needs request-ID, security headers, body-size limits. Generic, framework-agnostic. |
| `rate_limit.py` | Sample | **Core** | Rate limiting is table-stakes for any public API. The ASGI middleware + gRPC interceptor pair is reusable. |
| `cache.py` | Sample | **Core** | Flow-level response caching is Genkit-specific (keyed on flow name + input). Belongs next to `ai.flow()`. |
| `circuit_breaker.py` | Sample | **Core** | LLM APIs fail; every Genkit app needs a breaker. Wrapping `ai.generate()` calls is Genkit-specific. |
| `connection.py` | Sample | **Core** | HTTP pool tuning and `HttpOptions` for the Google GenAI SDK should be framework defaults, not boilerplate. |
| `logging.py` | Sample | **Core** | Production (JSON) vs. dev (Rich) logging is a universal need. Core already has a structlog wrapper but lacks the prod/dev auto-switch. |
| `telemetry.py` | Sample | **Plugin** | Platform-specific OTEL setup belongs in `genkit-plugin-google-cloud`, `genkit-plugin-aws`, etc. The generic OTLP export could be in core. |
| `sentry_init.py` | Sample | **Plugin** | Error-tracker integration is optional. Ship as `genkit-plugin-sentry`. |
| `server.py` | Sample | **Core** | Server helpers for granian/uvicorn/hypercorn duplicate what `genkit.web.manager` partially provides. Merge. |
| `config.py` | Sample | Sample | App-specific settings (API keys, feature flags) stay in the app. Core could provide a base `GenkitSettings` class. |
| `flows.py` | Sample | Sample | Application-specific LLM flows are always user code. |
| `schemas.py` | Sample | Sample | Application-specific Pydantic schemas are always user code. |
| `grpc_server.py` | Sample | **Core** | gRPC flow serving is generic: map `ai.flow()` to unary/streaming RPCs. Core should provide `serve_grpc()`. |
| `asgi.py` | Sample | Sample | App factory wiring is app-specific, but becomes trivial once middleware and server are in core. |
| `main.py` | Sample | Sample | CLI entry point is app-specific. |
| `resilience.py` | Sample | **Core** | If cache + breaker move to core, the wiring singletons go with them. |
| `util/asgi.py` | Sample | **Core** | Pure ASGI helpers (error responses, header extraction) are generic. Merge into `genkit.web`. |
| `util/date.py` | Sample | Sample | Trivial; not Genkit-specific. |
| `util/hash.py` | Sample | **Core** | Deterministic cache-key generation is tied to `FlowCache`. Moves with it. |
| `util/parse.py` | Sample | **Core** | `parse_rate` is tied to rate-limiter config. Moves with it. |

### What the sample looks like after migration

Once the above modules move to core/plugins, the sample reduces to:

```
src/
  __init__.py
  __main__.py
  main.py            <-- ~30 lines: parse args, ai.serve()
  config.py           <-- app-specific settings
  flows.py            <-- LLM flows (user code)
  schemas.py          <-- Pydantic models (user code)
  frameworks/         <-- 3 one-file adapters (FastAPI, Litestar, Quart)
```

Everything else comes from `genkit` core or plugins:

```python
from genkit.web.security import apply_security_middleware
from genkit.web.rate_limit import RateLimitMiddleware
from genkit.cache import FlowCache
from genkit.resilience import CircuitBreaker
```

### Existing open-source libraries (avoid duplicating)

Before building into core, evaluate whether wrapping an existing
library is better than reimplementing. The table below maps each
module to established OSS alternatives.

| Module | OSS library | PyPI | Notes |
|--------|-------------|------|-------|
| **Rate limiting** | [SlowAPI](https://slowapi.readthedocs.io/) | `slowapi` | FastAPI/Starlette decorator-based. Uses `limits` under the hood with Redis/memcached backends. Well-maintained. |
| | [asgi-ratelimit](https://github.com/abersheeran/asgi-ratelimit) | `asgi-ratelimit` | Pure ASGI middleware with regex rules and Redis backend. More generic than SlowAPI. Last updated 2022. |
| | [limits](https://limits.readthedocs.io/) | `limits` | Backend-agnostic rate limit strategies (fixed-window, sliding-window, token-bucket). SlowAPI uses this internally. |
| **Circuit breaker** | [PyBreaker](https://github.com/danielfm/pybreaker) | `pybreaker` | Mature (v1.4, 2025). Configurable thresholds, listeners, Redis-backed state. Thread-safe. |
| | [Tenacity](https://tenacity.readthedocs.io/) | `tenacity` | Retry library with exponential backoff, jitter, custom predicates. Complements (not replaces) a breaker. |
| | [resilient-circuit](https://resilient-circuit.readthedocs.io/) | `resilient-circuit` | Newer (2025). Composable breaker + retry policies. PostgreSQL-backed distributed state. |
| **Caching** | [aiocache](https://github.com/aio-libs/aiocache) | `aiocache` | aio-libs maintained. Memory, Redis, Memcached backends. TTL support. Serializers. |
| | [cashews](https://github.com/krukas/cashews) | `cashews` | Decorator-based async cache. TTL strings ("2h5m"), Redis + disk backends. Active (2025). |
| **Security headers** | [secure.py](https://secure.readthedocs.io/) | `secure` | Lightweight, multi-framework. HSTS, CSP, X-Frame, Referrer-Policy, Permissions-Policy. |
| | [Secweb](https://github.com/tmotagam/Secweb) | `Secweb` | 16 OWASP-aligned security middlewares for Starlette/FastAPI. Active (Jan 2026). No external deps. |
| **Request ID** | [asgi-correlation-id](https://github.com/snok/asgi-correlation-id) | `asgi-correlation-id` | Reads/generates X-Request-ID, injects into structlog context. 630+ stars, production-stable. |
| **Error tracking** | [sentry-sdk](https://docs.sentry.io/platforms/python/) | `sentry-sdk` | Official SDK with built-in ASGI, FastAPI, gRPC integrations. Auto-discovers frameworks. |
| **Logging** | [structlog](https://www.structlog.org/) | `structlog` | Already used. Provides JSON renderer, dev console, context vars. Core should ship a pre-configured setup. |
| **HTTP resilience** | [httpx](https://www.python-httpx.org/) | `httpx` | Already used by Google GenAI SDK. Built-in connection pooling, timeouts, retries. |

### Recommended approach per module

| Module | Recommendation | Status |
|--------|---------------|--------|
| `rate_limit.py` | Wrap **`limits`** (strategy layer) in a Genkit-specific ASGI middleware + gRPC interceptor. Supports in-memory + Redis out of the box. Drop custom `TokenBucket`. | **Done** — Migrated to `limits.FixedWindowRateLimiter` with `MemoryStorage`. Custom `TokenBucket` removed. |
| `circuit_breaker.py` | Wrap **`pybreaker`**. It already supports listeners (for metrics), Redis state (for multi-instance), and configurable thresholds. Add a `genkit.resilience.circuit_breaker()` helper that returns a configured `CircuitBreaker`. | **Done** — Wrapped `pybreaker.CircuitBreaker` with async-aware adapter (pybreaker's `call()` is sync-only; `CircuitOpenState.before_call()` invokes it internally). Manual state check + `_handle_error`/`_handle_success` delegation. |
| `cache.py` | Wrap **`aiocache`** or **`cashews`**. Provide a `FlowCache` adapter that handles Genkit-specific cache-key generation (flow name + Pydantic input hashing) on top of the pluggable backend. | **Done** — Wrapped `aiocache.SimpleMemoryCache` in `FlowCache` adapter. TTL managed by aiocache; LRU eviction deferred to Redis eviction policies for production (in-memory relies on TTL). |
| `security.py` | Wrap **`secure.py`** for security headers (tiny, no deps). Keep custom `MaxBodySizeMiddleware` and `RequestIdMiddleware` (or adopt **`asgi-correlation-id`** for the latter). Bundle as `genkit.web.security`. | **Done** — Security headers generated by `secure.Secure()` with OWASP-aligned defaults. `MaxBodySizeMiddleware` and `RequestIdMiddleware` kept (small, tightly integrated with structlog). |
| `sentry_init.py` | Thin wrapper around **`sentry-sdk`** auto-discovery. Ship as `genkit-plugin-sentry` with a `setup_sentry(dsn=..., genkit_instance=ai)` one-liner. | Pending — already using `sentry-sdk` directly; plugin extraction is a Genkit-core concern. |
| `logging.py` | Extend `genkit.core.logging` with a `setup_logging(env="auto")` that auto-detects TTY vs production and configures **`structlog`** with JSON or Rich accordingly. | Pending — Genkit-core enhancement. |
| `connection.py` | Merge into core's `genkit.core.http_client`. Add `HttpOptions` defaults and `HTTPX_*` env-var tuning as part of `Genkit.__init__()`. | Pending — Genkit-core enhancement. |
| `server.py` | Merge into `genkit.web.manager`. Add Hypercorn adapter alongside existing Uvicorn + Granian adapters. | Pending — Genkit-core enhancement. |
| `grpc_server.py` | Add `genkit.web.grpc` module. Auto-generate servicer from registered flows. Provide `ai.serve_grpc(port=50051)` alongside existing `ai.serve()`. | Pending — Genkit-core enhancement. |

---

## Build systems

- [ ] **Bazel support** — Add `BUILD.bazel` files for hermetic,
  reproducible builds. Useful for monorepo integration and CI caching.
  Includes `py_binary`, `py_library`, `py_test` targets for the Python
  code, and `proto_library` / `grpc_py_library` for protobuf codegen.
  Would replace `scripts/generate_proto.sh` with a Bazel rule.

- [ ] **Makefile** — Evaluate whether a `Makefile` is needed alongside
  `justfile`. Current assessment: **not needed**. The `justfile` already
  covers all workflows (dev, test, build, deploy, lint, audit, security).
  A Makefile would duplicate functionality. Reconsider only if consumers
  strongly prefer Make over just.

## gRPC

- [ ] **Streaming TellJoke RPC** — The REST side has `/tell-joke/stream`
  (SSE) but the gRPC service only exposes `TellJoke` as a unary RPC.
  Add a `TellJokeStream` server-streaming RPC to the proto definition
  and implement it in `grpc_server.py`.

- [ ] **gRPC-Web proxy** — Add an Envoy or grpc-web proxy configuration
  so browser clients can call gRPC endpoints directly.

## Security

### Completed

All core security hardening is implemented and tested (92% branch
coverage). The sample follows a **secure-by-default** philosophy —
production settings are restrictive out of the box; debug mode relaxes
them for local development.

| Feature | Module | Notes |
|---------|--------|-------|
| OWASP security headers | `security.py` | Via `secure.py` library; CSP, X-Frame-Options, Referrer-Policy, Permissions-Policy, COOP |
| Content-Security-Policy | `security.py` | Strict `default-src none` in production; relaxed for Swagger UI in debug mode |
| CORS (same-origin default) | `security.py` | Empty allowlist = same-origin; wildcard only in debug mode |
| CORS explicit header allowlist | `security.py` | `Content-Type`, `Authorization`, `X-Request-ID` (no wildcard) |
| Trusted host validation | `security.py` | Warns in production if `TRUSTED_HOSTS` is not set |
| Per-client-IP rate limiting | `rate_limit.py` | REST (ASGI middleware) + gRPC (interceptor); health endpoints exempt |
| Request body size limit | `security.py` | REST (`MaxBodySizeMiddleware`) + gRPC (`grpc.max_receive_message_length`) |
| Per-request timeout | `security.py` | `TimeoutMiddleware` returns 504 on expiry; configurable via settings/CLI |
| Global exception handler | `security.py` | `ExceptionMiddleware` returns JSON 500; no tracebacks to clients |
| Secret masking in logs | `log_config.py` | `structlog` processor redacts API keys, tokens, passwords, DSNs |
| Request ID / correlation | `security.py` | `RequestIdMiddleware` generates or propagates `X-Request-ID`; bound to structlog context |
| Server header suppression | `security.py` | Removes upstream `Server` header to prevent version fingerprinting |
| Cache-Control: no-store | `security.py` | Prevents intermediaries/browsers from caching API responses |
| HSTS (conditional on HTTPS) | `security.py` | Configurable `max-age`; only sent over HTTPS |
| GZip response compression | `security.py` | Via Starlette `GZipMiddleware`; configurable minimum size |
| HTTP access logging | `security.py` | `AccessLogMiddleware` logs method, path, status, duration |
| Circuit breaker for LLM calls | `circuit_breaker.py` | Async-safe; wraps `pybreaker` with stampede protection |
| Response cache (stampede-safe) | `cache.py` | TTL + LRU via `aiocache`; single-flight dedup prevents thundering herd |
| gRPC logging interceptor | `grpc_server.py` | Logs method, duration, status for every RPC |
| gRPC rate limiting interceptor | `rate_limit.py` | Token-bucket per client; returns `RESOURCE_EXHAUSTED` |
| gRPC reflection gated | `grpc_server.py` | Only enabled in debug mode |
| Swagger UI / OpenAPI gated | framework adapters | Only enabled in debug mode |
| Readiness probe with checks | framework adapters | `/ready` verifies `GEMINI_API_KEY`; returns 503 if missing |
| Sentry error tracking | `sentry_init.py` | Optional; activated via `SENTRY_DSN` env var |
| Platform telemetry auto-detection | `app_init.py` | GCP, AWS, Azure, generic OTLP |
| Distroless container | `Dockerfile` | Minimal attack surface; no shell, no package manager |
| Dependency auditing | `justfile` | `pysentry-rs` (vulnerabilities), `liccheck` (licenses), `addlicense` (headers) |
| Configurable settings + CLI | `config.py` | All security parameters (timeouts, body size, rate limit, CORS, HSTS, gzip) configurable via env vars and CLI flags |

### Pending

| # | Feature | Priority | Complexity | Description |
|---|---------|----------|------------|-------------|
| 1 | **Redis-backed rate limiting** | Medium | Medium | Current in-memory token bucket is per-process. Add optional Redis backend via `RATE_LIMIT_REDIS_URL` for multi-instance deployments. The `limits` library already supports this. |
| 2 | **mTLS for gRPC** | Medium | Medium | Mutual TLS on the gRPC server for service-to-service authentication in zero-trust environments. |
| 3 | **API key authentication** | Medium | Low-Medium | Optional API key middleware for REST + gRPC interceptor, configurable via `API_KEY` env var. |
| 4 | **Google Checks integration** | Low | High | Middleware integrating with [Google Checks](https://checks.google.com/) for AI Safety (input/output policy enforcement), Code Compliance (CI/CD privacy monitoring), and App Compliance (regulatory tracking). Implement as optional REST middleware + gRPC interceptor gated on Checks policy evaluation. |
| 5 | **TensorFlow-based content filtering** | Low | High | Optional input/output filtering using TensorFlow models for content safety: [Jigsaw Perspective API](https://perspectiveapi.com/) (cloud toxicity scoring), TF Lite text classifier (offline), or custom `SavedModel`. ASGI middleware + gRPC interceptor with configurable `CONTENT_FILTER_THRESHOLD` (default: `0.8`). Install via optional `[safety]` extra. |

## Performance

- [ ] **Redis-backed response cache** — The current flow cache is
  in-memory (per-process). Add an optional Redis backend via
  `CACHE_REDIS_URL` for shared caching across multi-instance
  deployments. If wrapping `aiocache` or `cashews`, this comes for free.

- [ ] **Adaptive circuit breaker** — The current circuit breaker uses
  a fixed failure threshold. Add sliding-window failure rate tracking
  and adaptive thresholds based on error percentage rather than
  absolute count. `pybreaker` supports listeners for custom metrics.

- [ ] **Response streaming cache** — Cache streamed responses by
  collecting chunks and storing the assembled result for subsequent
  identical requests.

## Observability

- [ ] **Prometheus metrics endpoint** — Expose `/metrics` with request
  count, latency histograms, and rate-limit rejection counts.

- [ ] **Structured audit logging** — Log all request metadata (client IP,
  method, path, status, duration) in a machine-parseable format suitable
  for SIEM ingestion.

## Testing

- [ ] **Load testing with Locust** — Add a `locustfile.py` for
  performance benchmarking of REST and gRPC endpoints.

- [ ] **Contract tests** — Add proto-based contract tests that verify the
  gRPC service matches the `.proto` definition at test time.

## Deployment

- [ ] **Kubernetes manifests** — Add `k8s/` directory with Deployment,
  Service, HPA, and NetworkPolicy manifests.

- [ ] **Terraform / Pulumi** — Infrastructure-as-code for Cloud Run, App
  Runner, or Container Apps deployment.

- [x] **GitHub Actions CI** — `.github/workflows/` with lint, test,
  build, and deploy pipelines (6 cloud platforms + CI).
