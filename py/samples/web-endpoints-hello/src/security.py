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

"""Security middleware for ASGI applications.

Provides framework-agnostic security hardening that works identically
across FastAPI, Litestar, and Quart:

- **RequestIdMiddleware** — Generates or propagates a unique request
  ID (``X-Request-ID``), binds it to structlog context for correlation.
- **SecurityHeadersMiddleware** — Injects OWASP-recommended HTTP
  response headers (CSP, X-Frame-Options, Cache-Control, etc.) using
  the ``secure`` library.  Suppresses the ``Server`` header to prevent
  version fingerprinting.
- **MaxBodySizeMiddleware** — Rejects requests whose
  ``Content-Length`` exceeds a configurable limit (default 1 MB).
- **ExceptionMiddleware** — Catches unhandled exceptions and returns
  a consistent JSON error (no tracebacks to clients).
- **AccessLogMiddleware** — Logs method, path, status, and duration
  for every HTTP request.
- **TimeoutMiddleware** — Enforces a per-request timeout (default
  120s) to prevent hung workers.
- **apply_security_middleware()** — Wraps an ASGI app with the full
  middleware stack (access log, gzip, CORS, trusted hosts, timeout,
  body limit, exception handler, security headers, request ID).

All middleware classes are pure ASGI — no framework dependency.
"""

from __future__ import annotations

import asyncio
import time
import traceback
import uuid
from typing import Any

import secure as secure_lib
import structlog
import structlog.contextvars
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .util.asgi import (
    ASGIApp,
    Receive,
    Scope,
    Send,
    get_content_length,
    get_header,
    send_json_error,
)

logger = structlog.get_logger(__name__)

_SECURITY_HEADERS_NO_HSTS = secure_lib.Secure(
    csp=secure_lib.ContentSecurityPolicy().default_src("none"),
    coop=secure_lib.CrossOriginOpenerPolicy().same_origin(),
    hsts=None,
    permissions=secure_lib.PermissionsPolicy().geolocation().camera().microphone(),
    referrer=secure_lib.ReferrerPolicy().set("strict-origin-when-cross-origin"),
    xcto=secure_lib.XContentTypeOptions(),
    xfo=secure_lib.XFrameOptions().set("DENY"),
)
"""Production ``secure.Secure`` instance — strict CSP, no HSTS.

HSTS is excluded because it must only be sent over HTTPS. The
middleware adds it conditionally at runtime.

``X-XSS-Protection`` is intentionally omitted: the ``secure`` library
dropped it because the browser XSS auditor it controlled is removed
from all modern browsers and setting it can introduce XSS in
older browsers (OWASP recommendation since 2023).
"""

_SECURITY_HEADERS_DEBUG = secure_lib.Secure(
    csp=secure_lib
    .ContentSecurityPolicy()
    .default_src("'self'")
    .script_src("'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net")
    .style_src("'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net")
    .img_src("'self'", "data:", "https://fastapi.tiangolo.com")
    .connect_src("'self'"),
    coop=secure_lib.CrossOriginOpenerPolicy().same_origin(),
    hsts=None,
    permissions=secure_lib.PermissionsPolicy().geolocation().camera().microphone(),
    referrer=secure_lib.ReferrerPolicy().set("strict-origin-when-cross-origin"),
    xcto=secure_lib.XContentTypeOptions(),
    xfo=secure_lib.XFrameOptions().set("DENY"),
)
"""Debug ``secure.Secure`` instance — relaxed CSP for Swagger UI.

Allows CDN resources from ``cdn.jsdelivr.net`` (Swagger UI JS/CSS),
inline scripts (Swagger UI initializer), and the FastAPI favicon.
All other headers remain the same as production.
"""


class RequestIdMiddleware:
    """ASGI middleware that assigns a unique ID to every HTTP request.

    If the client sends an ``X-Request-ID`` header, it is reused;
    otherwise a new UUID4 is generated. The ID is:

    1. Bound to ``structlog`` context vars for the duration of the
       request, so every log line includes ``request_id``.
    2. Echoed back in the ``X-Request-ID`` response header for
       client-side correlation.
    3. Stored in ``scope["state"]["request_id"]`` for framework access.

    Args:
        app: The ASGI application to wrap.
    """

    def __init__(self, app: ASGIApp) -> None:
        """Wrap *app* with request-ID propagation."""
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Extract or generate a request ID and bind it to the log context."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = get_header(scope, b"x-request-id") or uuid.uuid4().hex

        scope.setdefault("state", {})["request_id"] = request_id

        structlog.contextvars.bind_contextvars(request_id=request_id)

        async def send_with_request_id(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode("latin-1")))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            structlog.contextvars.unbind_contextvars("request_id")

    __slots__ = ("app",)


class SecurityHeadersMiddleware:
    """ASGI middleware that adds OWASP security headers via ``secure.py``.

    Uses the ``secure`` library to generate header values, ensuring
    alignment with current OWASP recommendations without maintaining
    a manual header list. Also adds ``Strict-Transport-Security``
    conditionally when the request arrived over HTTPS.

    Args:
        app: The ASGI application to wrap.
        hsts_max_age: Max-age for HSTS header in seconds (default: 1 year).
            Set to ``0`` to disable HSTS.
        debug: When ``True``, use a relaxed CSP that allows Swagger UI
            to load CDN resources and inline scripts.
    """

    def __init__(self, app: ASGIApp, *, hsts_max_age: int = 31_536_000, debug: bool = False) -> None:
        """Wrap *app* with OWASP-recommended security response headers."""
        self.app = app
        self.hsts_max_age = hsts_max_age
        headers_obj = _SECURITY_HEADERS_DEBUG if debug else _SECURITY_HEADERS_NO_HSTS
        self._static_headers: list[tuple[bytes, bytes]] = [
            (name.lower().encode(), value.encode()) for name, value in headers_obj.headers.items()
        ]
        # Prevent caching of API responses by intermediaries/browsers.
        self._static_headers.append((b"cache-control", b"no-store"))
        # Suppress server version fingerprinting.
        self._static_headers.append((b"server", b""))

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Intercept HTTP responses and inject security headers."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        is_https = scope.get("scheme") == "https"

        async def send_with_headers(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                # Remove any existing Server header set by the ASGI server
                # to prevent version fingerprinting.
                headers = [(k, v) for k, v in headers if k.lower() != b"server"]
                headers.extend(self._static_headers)
                if is_https and self.hsts_max_age > 0:
                    headers.append((
                        b"strict-transport-security",
                        f"max-age={self.hsts_max_age}; includeSubDomains".encode(),
                    ))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)


class MaxBodySizeMiddleware:
    """ASGI middleware that rejects oversized request bodies.

    Checks the ``Content-Length`` header and returns **413 Payload Too
    Large** if it exceeds ``max_bytes``. Runs before the framework
    parses the body, protecting against memory exhaustion.

    Args:
        app: The ASGI application to wrap.
        max_bytes: Maximum allowed body size in bytes (default: 1 MB).
    """

    def __init__(self, app: ASGIApp, *, max_bytes: int = 1_048_576) -> None:
        """Wrap *app* with a request body size limit of *max_bytes*."""
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Check Content-Length and reject oversized requests."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        content_length = get_content_length(scope)

        if content_length is not None and content_length > self.max_bytes:
            await send_json_error(send, 413, "Payload Too Large", f"Max body size is {self.max_bytes} bytes")
            return

        await self.app(scope, receive, send)


class ExceptionMiddleware:
    """ASGI middleware that catches unhandled exceptions.

    Ensures every error returns a consistent JSON body instead of
    framework-default HTML tracebacks.  The full traceback is logged
    server-side; the client only sees a generic error message.

    Args:
        app: The ASGI application to wrap.
        debug: When ``True``, include the exception type in the
            response detail (never the full traceback).
    """

    def __init__(self, app: ASGIApp, *, debug: bool = False) -> None:
        """Wrap *app* with a catch-all exception handler."""
        self.app = app
        self.debug = debug

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Forward the request and catch any unhandled exception."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        try:
            await self.app(scope, receive, send)
        except Exception:
            logger.error("Unhandled exception", exc_info=True)
            detail = "Internal server error"
            if self.debug:
                # Include the exception class name (never the full
                # traceback) so developers can identify the issue.
                lines = traceback.format_exc().strip().splitlines()
                detail = lines[-1] if lines else detail
            await send_json_error(send, 500, "Internal Server Error", detail)


class AccessLogMiddleware:
    """ASGI middleware that logs every HTTP request with timing.

    Logs method, path, status code, and duration in milliseconds via
    structlog.  Runs as the outermost middleware so the timing includes
    all middleware processing.

    Args:
        app: The ASGI application to wrap.
    """

    def __init__(self, app: ASGIApp) -> None:
        """Wrap *app* with HTTP access logging."""
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Log the request method, path, status, and duration."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.monotonic()
        status_code = 500  # default in case send is never called

        async def send_capturing_status(message: dict[str, Any]) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 500)
            await send(message)

        try:
            await self.app(scope, receive, send_capturing_status)
        finally:
            duration_ms = (time.monotonic() - start) * 1000
            method = scope.get("method", "?")
            path = scope.get("path", "?")
            logger.info(
                "http_request",
                method=method,
                path=path,
                status=status_code,
                duration_ms=round(duration_ms, 1),
            )


class TimeoutMiddleware:
    """ASGI middleware that enforces a per-request timeout.

    If the downstream app does not complete within ``timeout``
    seconds, the request is cancelled and a ``504 Gateway Timeout``
    JSON response is returned.

    Args:
        app: The ASGI application to wrap.
        timeout: Maximum request duration in seconds (default: 120).
    """

    def __init__(self, app: ASGIApp, *, timeout: float = 120.0) -> None:
        """Wrap *app* with a per-request timeout of *timeout* seconds."""
        self.app = app
        self.timeout = timeout

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Run the request with a timeout guard."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        try:
            await asyncio.wait_for(
                self.app(scope, receive, send),
                timeout=self.timeout,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "Request timed out",
                timeout_seconds=self.timeout,
                path=scope.get("path", "?"),
            )
            await send_json_error(
                send,
                504,
                "Gateway Timeout",
                f"Request did not complete within {self.timeout}s",
            )


def apply_security_middleware(
    app: ASGIApp,
    *,
    cors_origins: list[str] | None = None,
    cors_methods: list[str] | None = None,
    cors_headers: list[str] | None = None,
    trusted_hosts: list[str] | None = None,
    max_body_size: int = 1_048_576,
    hsts_max_age: int = 31_536_000,
    request_timeout: float = 120.0,
    gzip_min_size: int = 500,
    debug: bool = False,
) -> ASGIApp:
    """Wrap an ASGI app with the full security middleware stack.

    Middleware is applied inside-out (first listed = innermost). The
    final order for an incoming request is::

        AccessLog → GZip → CORS → TrustedHost → Timeout → MaxBodySize
          → ExceptionHandler → SecurityHeaders → RequestId → App

    Secure-by-default behavior:

    - **CORS**: ``None`` / empty → same-origin only in production,
      wildcard in debug mode.
    - **Trusted hosts**: ``None`` / empty → disabled (logs a warning
      in production).
    - **CSP**: strict ``default-src none`` in production, relaxed for
      Swagger UI in debug mode.
    - **CORS headers**: explicit allowlist (``Content-Type``,
      ``Authorization``, ``X-Request-ID``).
    - **Cache-Control**: ``no-store`` on all responses.
    - **Server header**: suppressed (prevents version fingerprinting).
    - **Timeout**: configurable per request (prevents hung workers).
    - **Compression**: gzip for responses above configurable threshold.

    Args:
        app: The ASGI application to wrap.
        cors_origins: Allowed CORS origins. ``None`` or empty list
            applies the secure default (same-origin in production,
            wildcard in debug).
        cors_methods: Allowed CORS methods (default:
            ``["GET", "POST", "OPTIONS"]``).
        cors_headers: Allowed CORS headers (default:
            ``["Content-Type", "Authorization", "X-Request-ID"]``).
        trusted_hosts: If non-empty, only these ``Host`` header values
            are accepted.  ``None`` or empty list disables the check
            (logs a warning in production).
        max_body_size: Max request body in bytes (default: 1 MB).
        hsts_max_age: HSTS max-age in seconds (default: 1 year).
        request_timeout: Max seconds per request (default: 120).
        gzip_min_size: Minimum response size in bytes for gzip
            compression (default: 500).
        debug: When ``True``, relax CORS and CSP for development.
            Must be ``False`` in production.

    Returns:
        The wrapped ASGI application.
    """
    # Secure-by-default CORS: when no origins are configured, allow
    # only same-origin requests in production.  In debug mode, fall
    # back to wildcard so Swagger UI and local dev tools work.
    if not cors_origins:
        cors_origins = ["*"] if debug else []
    if not cors_methods:
        cors_methods = ["GET", "POST", "OPTIONS"]
    if not cors_headers:
        cors_headers = ["Content-Type", "Authorization", "X-Request-ID"]

    # Inside-out: RequestId is closest to the app, AccessLog is outermost.
    wrapped: ASGIApp = RequestIdMiddleware(app)
    wrapped = SecurityHeadersMiddleware(wrapped, hsts_max_age=hsts_max_age, debug=debug)
    wrapped = ExceptionMiddleware(wrapped, debug=debug)
    wrapped = MaxBodySizeMiddleware(wrapped, max_bytes=max_body_size)
    wrapped = TimeoutMiddleware(wrapped, timeout=request_timeout)

    if trusted_hosts:
        wrapped = TrustedHostMiddleware(wrapped, allowed_hosts=trusted_hosts)
    elif not debug:
        logger.warning(
            "No TRUSTED_HOSTS configured — Host-header validation is disabled. "
            "Set TRUSTED_HOSTS to your domain(s) in production to prevent "
            "host-header poisoning attacks.",
        )

    wrapped = CORSMiddleware(
        wrapped,
        allow_origins=cors_origins,
        allow_methods=cors_methods,
        allow_headers=cors_headers,
        allow_credentials=False,
    )

    # GZip compression for responses above the configured threshold.
    wrapped = GZipMiddleware(wrapped, minimum_size=gzip_min_size)

    # Access logging is outermost so timing includes all middleware.
    wrapped = AccessLogMiddleware(wrapped)

    logger.info(
        "Security middleware applied",
        cors_origins=cors_origins or "same-origin only",
        cors_methods=cors_methods,
        cors_headers=cors_headers,
        trusted_hosts=trusted_hosts or "disabled",
        max_body_size=max_body_size,
        request_timeout=request_timeout,
        gzip_min_size=gzip_min_size,
        hsts="enabled" if hsts_max_age > 0 else "disabled",
        debug=debug,
    )

    return wrapped
