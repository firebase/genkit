# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

r"""Genkit endpoints demo — entry point (REST + gRPC).

A reference sample showing how to expose Genkit flows over both REST
(ASGI) and gRPC.  REST endpoints are served via FastAPI, Litestar, or
Quart; the gRPC server runs in parallel on a separate port.

The startup sequence applies security hardening in this order::

    1. parse_args() + make_settings()
    2. setup_sentry()          — if SENTRY_DSN is set (catches init errors)
    3. _create_app(framework)
    4. apply_security_middleware() — wraps the ASGI app:
       AccessLog → GZip → CORS → TrustedHost → Timeout → MaxBodySize
         → ExceptionHandler → SecurityHeaders → RequestId → App
    5. RateLimitMiddleware     — per-client-IP token bucket
    6. setup_otel_instrumentation()
    7. start servers (ASGI + gRPC with interceptors)

CLI Usage::

    python -m src                                   # FastAPI + uvicorn + gRPC
    python -m src --framework litestar              # Litestar + uvicorn + gRPC
    python -m src --framework quart                 # Quart + uvicorn + gRPC
    python -m src --framework fastapi --server granian
    python -m src --env staging                     # load .staging.env
    python -m src --env production --port 9090
    python -m src --no-telemetry                    # disable all telemetry
    python -m src --no-grpc                         # disable the gRPC server
    python -m src --grpc-port 50052                 # custom gRPC port

Module Structure::

    src/
    ├── __init__.py          — Package marker
    ├── __main__.py          — ``python -m src`` entry point
    ├── app_init.py          — Genkit singleton, platform telemetry
    ├── asgi.py              — ASGI app factory for gunicorn (multi-worker)
    ├── cache.py             — In-memory TTL + LRU response cache
    ├── circuit_breaker.py   — Async-safe circuit breaker
    ├── config.py            — Settings, env-file handling, CLI parsing
    ├── connection.py        — Connection pool / keep-alive tuning
    ├── flows.py             — Genkit tools and flows
    ├── frameworks/
    │   ├── __init__.py      — Framework adapter package
    │   ├── fastapi_app.py   — FastAPI app factory + routes
    │   ├── litestar_app.py  — Litestar app factory + routes
    │   └── quart_app.py     — Quart app factory + routes
    ├── generated/           — Protobuf + gRPC stubs (auto-generated)
    ├── grpc_server.py       — gRPC service implementation + interceptors
    ├── log_config.py        — Structured logging (Rich + structlog)
    ├── main.py              — This file — CLI entry point
    ├── rate_limit.py        — Token-bucket rate limiting (ASGI + gRPC)
    ├── resilience.py        — Cache + circuit breaker singletons
    ├── schemas.py           — Pydantic input/output models (with constraints)
    ├── security.py          — Security headers (wraps secure.py) + body size + request ID
    ├── sentry_init.py       — Optional Sentry error tracking
    ├── server.py            — ASGI server helpers (uvicorn / granian / hypercorn)
    ├── telemetry.py         — OpenTelemetry OTLP instrumentation
    └── util/                — Shared utility functions (independently testable)
        ├── __init__.py      — Utility package marker
        ├── asgi.py          — ASGI response helpers, header extraction
        ├── date.py          — Date/time formatting (UTC)
        ├── hash.py          — Deterministic cache key generation
        └── parse.py         — String parsing (rate strings, comma lists)
"""

import asyncio
import os
from collections.abc import Coroutine
from typing import Any

import structlog
import uvloop

from . import resilience
from .app_init import ai
from .cache import FlowCache
from .circuit_breaker import CircuitBreaker
from .config import make_settings, parse_args
from .connection import configure_httpx_defaults
from .grpc_server import serve_grpc
from .log_config import setup_logging
from .rate_limit import RateLimitMiddleware
from .security import apply_security_middleware
from .sentry_init import setup_sentry
from .server import ASGIApp, serve_granian, serve_hypercorn, serve_uvicorn
from .telemetry import setup_otel_instrumentation
from .util.parse import split_comma_list

logger = structlog.get_logger(__name__)


def _create_app(framework: str, *, debug: bool = False) -> ASGIApp:
    """Create the ASGI app using the selected framework adapter.

    Args:
        framework: One of ``"fastapi"``, ``"litestar"``, or ``"quart"``.
        debug: When ``True``, enable Swagger UI and other dev-only
            features.  Must be ``False`` in production.

    Returns:
        An ASGI-compatible application instance.
    """
    if framework == "litestar":
        from .frameworks.litestar_app import create_app  # noqa: PLC0415 — conditional on runtime --framework flag
    elif framework == "quart":
        from .frameworks.quart_app import create_app  # noqa: PLC0415 — conditional on runtime --framework flag
    else:
        from .frameworks.fastapi_app import create_app  # noqa: PLC0415 — conditional on runtime --framework flag
    return create_app(ai, debug=debug)


async def _serve_both(
    asgi_coro: Coroutine[Any, Any, None],
    grpc_port: int | None,
    rate_limit: str = "60/minute",
    shutdown_grace: float = 10.0,
    *,
    max_message_size: int = 1_048_576,
    debug: bool = False,
) -> None:
    """Run the ASGI server and (optionally) the gRPC server concurrently.

    Uses ``asyncio.gather`` so both servers share the same event loop
    that ``ai.run_main()`` manages.

    Args:
        asgi_coro: A coroutine that runs the ASGI server.
        grpc_port: If set, start the gRPC server on this port.
            If ``None``, only the ASGI server runs.
        rate_limit: Rate limit string for the gRPC server.
        shutdown_grace: Seconds to wait for in-flight requests during
            graceful shutdown.
        max_message_size: Maximum inbound gRPC message size in bytes.
        debug: When ``True``, enable gRPC reflection.
    """
    if grpc_port is not None:
        await asyncio.gather(
            asgi_coro,
            serve_grpc(
                port=grpc_port,
                rate_limit=rate_limit,
                shutdown_grace=shutdown_grace,
                max_message_size=max_message_size,
                debug=debug,
            ),
        )
    else:
        await asgi_coro


def main() -> None:
    """CLI entry point — parse args, configure, and start the servers."""
    args = parse_args()

    settings = make_settings(env=args.env)
    port = args.port or settings.port
    grpc_port: int | None = args.grpc_port or settings.grpc_port
    server_choice = args.server or settings.server
    framework = args.framework or settings.framework

    # Resolve debug flag early — it influences the log format default.
    debug = args.debug if args.debug is not None else settings.debug

    # Apply --log-format CLI override.  setup_logging() was already called
    # at module import time (via app_init.py), but if the user specified
    # a different format on the command line we need to reconfigure.
    # In debug mode, default to "console" (colored) instead of "json".
    log_format = args.log_format or settings.log_format
    if log_format == "json" and debug and not args.log_format:
        log_format = "console"
    if log_format != os.environ.get("LOG_FORMAT", ""):
        os.environ["LOG_FORMAT"] = log_format
        setup_logging()

    if args.no_grpc:
        grpc_port = None

    if args.no_telemetry:
        os.environ["GENKIT_TELEMETRY_DISABLED"] = "1"
        logger.info("Telemetry disabled via --no-telemetry flag")

    if args.env:
        logger.info("Loaded settings for environment", env=args.env)

    if settings.gemini_api_key and "GEMINI_API_KEY" not in os.environ:
        os.environ["GEMINI_API_KEY"] = settings.gemini_api_key

    # Configure outbound connection pool and LLM timeout early.
    os.environ.setdefault("LLM_TIMEOUT", str(settings.llm_timeout))
    configure_httpx_defaults(
        pool_max=settings.httpx_pool_max,
        pool_max_keepalive=settings.httpx_pool_max_keepalive,
    )

    # Initialize the response cache and circuit breaker as module-level
    # singletons so flows.py can import them.
    resilience.flow_cache = FlowCache(
        ttl_seconds=settings.cache_ttl,
        max_size=settings.cache_max_size,
        enabled=settings.cache_enabled,
    )
    resilience.llm_breaker = CircuitBreaker(
        failure_threshold=settings.cb_failure_threshold,
        recovery_timeout=settings.cb_recovery_timeout,
        enabled=settings.cb_enabled,
        name="llm",
    )
    logger.info(
        "Resilience initialized",
        cache_enabled=settings.cache_enabled,
        cache_ttl=settings.cache_ttl,
        cache_max_size=settings.cache_max_size,
        circuit_breaker_enabled=settings.cb_enabled,
        cb_failure_threshold=settings.cb_failure_threshold,
        cb_recovery_timeout=settings.cb_recovery_timeout,
    )

    # Initialize Sentry early (before app creation) so init errors are captured.
    sentry_env = settings.sentry_environment or (args.env or "")
    if settings.sentry_dsn:
        setup_sentry(
            dsn=settings.sentry_dsn,
            framework=framework,
            environment=sentry_env,
            traces_sample_rate=settings.sentry_traces_sample_rate,
        )

    # Create the framework-specific ASGI app.
    app = _create_app(framework, debug=debug)

    # Resolve CLI overrides for middleware settings.
    max_body_size = args.max_body_size if args.max_body_size is not None else settings.max_body_size
    request_timeout = args.request_timeout if args.request_timeout is not None else settings.request_timeout
    rate_limit = args.rate_limit or settings.rate_limit_default

    # Apply security middleware stack (CORS, trusted hosts, body limit, headers).
    # Secure defaults are enforced inside apply_security_middleware():
    #   - CORS: empty list = same-origin only (debug mode falls back to "*")
    #   - Trusted hosts: empty list = disabled (warns in production)
    cors_origins = split_comma_list(settings.cors_allowed_origins)
    cors_methods = split_comma_list(settings.cors_allowed_methods)
    cors_headers = split_comma_list(settings.cors_allowed_headers)
    trusted_hosts = split_comma_list(settings.trusted_hosts)
    app = apply_security_middleware(
        app,
        cors_origins=cors_origins or None,
        cors_methods=cors_methods or None,
        cors_headers=cors_headers or None,
        trusted_hosts=trusted_hosts or None,
        max_body_size=max_body_size,
        hsts_max_age=settings.hsts_max_age,
        request_timeout=request_timeout,
        gzip_min_size=settings.gzip_min_size,
        debug=debug,
    )

    # Apply rate limiting.
    app = RateLimitMiddleware(app, rate=rate_limit)

    logger.info(
        "Created ASGI app",
        framework=framework,
        server=server_choice,
        rest_port=port,
        grpc_port=grpc_port or "disabled",
        rate_limit=rate_limit,
        max_body_size=max_body_size,
        request_timeout=request_timeout,
        debug=debug,
    )

    # Set up OpenTelemetry with OTLP export if an endpoint is configured.
    otel_endpoint = args.otel_endpoint or settings.otel_exporter_otlp_endpoint
    if otel_endpoint and not args.no_telemetry:
        otel_protocol = args.otel_protocol or settings.otel_exporter_otlp_protocol
        otel_service_name = args.otel_service_name or settings.otel_service_name
        setup_otel_instrumentation(app, otel_endpoint, otel_protocol, otel_service_name)

    shutdown_grace = settings.shutdown_grace
    keep_alive = settings.keep_alive_timeout

    if server_choice == "granian":
        ai.run_main(
            _serve_both(
                serve_granian(app, port, settings.log_level, keep_alive),
                grpc_port,
                rate_limit,
                shutdown_grace,
                max_message_size=max_body_size,
                debug=debug,
            )
        )
    elif server_choice == "hypercorn":
        ai.run_main(
            _serve_both(
                serve_hypercorn(app, port, settings.log_level, keep_alive),
                grpc_port,
                rate_limit,
                shutdown_grace,
                max_message_size=max_body_size,
                debug=debug,
            )
        )
    else:
        uvloop.install()
        ai.run_main(
            _serve_both(
                serve_uvicorn(app, port, settings.log_level, keep_alive),
                grpc_port,
                rate_limit,
                shutdown_grace,
                max_message_size=max_body_size,
                debug=debug,
            )
        )


if __name__ == "__main__":
    main()
