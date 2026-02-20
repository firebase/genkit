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

"""ASGI application factory for gunicorn / external process managers.

This module provides a ``create_app()`` factory that returns a fully
configured ASGI application with all middleware applied. It is designed
for use with gunicorn + UvicornWorker, which manages worker processes
externally while still speaking ASGI::

    gunicorn -c gunicorn.conf.py 'src.asgi:create_app()'

The factory approach (vs. a module-level ``app`` variable) ensures
each worker process creates its own application instance after fork,
avoiding shared-state issues with the event loop and connections.

For local development, use ``python -m src`` (or ``run.sh``) which
includes the gRPC server and Genkit DevUI. Gunicorn mode only serves
REST endpoints — run the gRPC server separately if needed::

    # Terminal 1: REST via gunicorn (multi-worker)
    gunicorn -c gunicorn.conf.py 'src.asgi:create_app()'

    # Terminal 2: gRPC server (single-process)
    python -c "import asyncio; from src.grpc_server import serve_grpc; asyncio.run(serve_grpc())"
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

import structlog

from .config import make_settings
from .connection import configure_httpx_defaults
from .rate_limit import RateLimitMiddleware
from .security import apply_security_middleware
from .sentry_init import setup_sentry
from .util.parse import split_comma_list

logger = structlog.get_logger(__name__)


def create_app() -> Callable[..., Any]:
    """Create a production-ready ASGI application with all middleware.

    Reads configuration from environment variables and ``.env`` files.
    Applies the full security middleware stack, rate limiting, and
    optional Sentry integration.

    Returns:
        A fully configured ASGI application suitable for gunicorn or
        any ASGI server.
    """
    env = os.environ.get("APP_ENV", None)
    settings = make_settings(env=env)
    framework = os.environ.get("FRAMEWORK", settings.framework)

    configure_httpx_defaults(
        pool_max=settings.httpx_pool_max,
        pool_max_keepalive=settings.httpx_pool_max_keepalive,
    )

    if settings.sentry_dsn:
        setup_sentry(
            dsn=settings.sentry_dsn,
            framework=framework,
            environment=settings.sentry_environment or env or "",
            traces_sample_rate=settings.sentry_traces_sample_rate,
        )

    if framework == "litestar":
        from .frameworks.litestar_app import (  # noqa: PLC0415 — conditional on ASGI_FRAMEWORK env var
            create_app as _create,
        )
    elif framework == "quart":
        from .frameworks.quart_app import (  # noqa: PLC0415 — conditional on ASGI_FRAMEWORK env var
            create_app as _create,
        )
    else:
        from .frameworks.fastapi_app import (  # noqa: PLC0415 — conditional on ASGI_FRAMEWORK env var
            create_app as _create,
        )

    from .app_init import ai  # noqa: PLC0415 — deferred to avoid import-time side effects in gunicorn master

    debug = settings.debug
    app: Any = _create(ai, debug=debug)

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
        max_body_size=settings.max_body_size,
        hsts_max_age=settings.hsts_max_age,
        request_timeout=settings.request_timeout,
        gzip_min_size=settings.gzip_min_size,
        debug=debug,
    )

    app = RateLimitMiddleware(app, rate=settings.rate_limit_default)

    # Resilience singletons — must be initialised per-worker so that
    # flows.py picks up cache and circuit breaker instances.
    from . import resilience  # noqa: PLC0415 — deferred to gunicorn worker initialization
    from .cache import FlowCache  # noqa: PLC0415 — deferred to gunicorn worker initialization
    from .circuit_breaker import CircuitBreaker  # noqa: PLC0415 — deferred to gunicorn worker initialization

    resilience.flow_cache = FlowCache(
        ttl_seconds=settings.cache_ttl,
        max_size=settings.cache_max_size,
        enabled=settings.cache_enabled,
    )
    resilience.llm_breaker = CircuitBreaker(
        failure_threshold=settings.cb_failure_threshold,
        recovery_timeout=settings.cb_recovery_timeout,
        enabled=settings.cb_enabled,
    )

    logger.info(
        "ASGI app factory created app",
        framework=framework,
        rate_limit=settings.rate_limit_default,
        cache_enabled=settings.cache_enabled,
        circuit_breaker_enabled=settings.cb_enabled,
    )

    return app
