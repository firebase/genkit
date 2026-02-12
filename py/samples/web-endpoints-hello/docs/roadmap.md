# Roadmap

Planned improvements for the web-endpoints-hello sample.

!!! note
    The full roadmap with implementation details and dependency
    graphs lives in [`roadmap.md`](https://github.com/firebase/genkit/blob/main/py/samples/web-endpoints-hello/roadmap.md)
    in the repository root.

## Core migration

The long-term goal is to move production-readiness modules into
`genkit` core so the sample shrinks to flows + schemas + config only.

| Module | Target | Status |
|--------|--------|--------|
| `security.py` | Core (`genkit.web.security`) | Planned |
| `rate_limit.py` | Core (`genkit.web.rate_limit`) | Planned |
| `cache.py` | Core (`genkit.cache`) | Planned |
| `circuit_breaker.py` | Core (`genkit.resilience`) | Planned |
| `connection.py` | Core (`genkit.core.http_client`) | Planned |
| `logging.py` | Core (`genkit.core.logging`) | Planned |
| `grpc_server.py` | Core (`genkit.web.grpc`) | Planned |
| `server.py` | Core (`genkit.web.manager`) | Planned |
| `telemetry.py` | Plugin (`genkit-plugin-*`) | Planned |
| `sentry_init.py` | Plugin (`genkit-plugin-sentry`) | Planned |

## Security hardening

All core security hardening is **complete** (92% branch coverage).
The sample follows a secure-by-default philosophy. See
[Security & Hardening](production/security.md) for full details.

### Completed

- [x] OWASP security headers (CSP, X-Frame-Options, COOP, etc.)
- [x] Content-Security-Policy (strict production / relaxed debug)
- [x] CORS same-origin default with explicit header allowlist
- [x] Trusted host validation (warns if unconfigured)
- [x] Per-client-IP rate limiting (REST + gRPC)
- [x] Request body size limits (REST + gRPC)
- [x] Per-request timeout middleware (504 on expiry)
- [x] Global exception handler (no tracebacks to clients)
- [x] Secret masking in structured logs
- [x] Request ID / correlation (`X-Request-ID`)
- [x] Server header suppression
- [x] Cache-Control: no-store on API responses
- [x] HSTS (conditional on HTTPS, configurable max-age)
- [x] GZip response compression (configurable min size)
- [x] HTTP access logging (method, path, status, duration)
- [x] Circuit breaker for LLM calls (async-safe)
- [x] Response cache with stampede protection
- [x] gRPC interceptors (logging + rate limiting)
- [x] gRPC reflection gated behind debug flag
- [x] Swagger UI / OpenAPI gated behind debug flag
- [x] Readiness probe with dependency checks
- [x] Sentry error tracking (optional)
- [x] Platform telemetry auto-detection (GCP, AWS, Azure, OTLP)
- [x] Distroless container
- [x] Dependency auditing (vulnerabilities, licenses, headers)
- [x] All security settings configurable via env vars + CLI

### Pending

| # | Feature | Priority | Complexity |
|---|---------|----------|------------|
| 1 | Redis-backed rate limiting (`RATE_LIMIT_REDIS_URL`) | Medium | Medium |
| 2 | mTLS for gRPC (service-to-service auth) | Medium | Medium |
| 3 | API key authentication middleware | Medium | Low-Medium |
| 4 | Google Checks integration (AI Safety, Code Compliance, App Compliance) | Low | High |
| 5 | TensorFlow-based content filtering | Low | High |

## Planned features

### Performance

- [ ] Redis-backed response cache (`CACHE_REDIS_URL`)
- [ ] Adaptive circuit breaker (sliding-window failure rate)
- [ ] Response streaming cache

### gRPC

- [ ] Streaming TellJoke RPC (match REST SSE)
- [ ] gRPC-Web proxy (Envoy)

### Observability

- [ ] Prometheus `/metrics` endpoint
- [ ] Structured audit logging (SIEM-ready)

### Testing

- [ ] Locust load testing (`locustfile.py`)
- [ ] Proto-based contract tests

### Deployment

- [ ] Kubernetes manifests (`k8s/`)
- [ ] Terraform / Pulumi infrastructure-as-code

### Build systems

- [ ] Bazel support (`BUILD.bazel`)
