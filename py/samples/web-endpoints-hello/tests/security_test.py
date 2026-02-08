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

"""Tests for ASGI security middleware.

Covers SecurityHeadersMiddleware (backed by the ``secure`` library),
MaxBodySizeMiddleware, ExceptionMiddleware, AccessLogMiddleware,
TimeoutMiddleware, and the apply_security_middleware() stack builder.
All tests use a minimal ASGI echo app — no framework dependency.

Run with::

    cd py/samples/web-endpoints-hello
    uv run pytest tests/security_test.py -v
"""

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

import pytest

from src.security import (
    AccessLogMiddleware,
    ExceptionMiddleware,
    MaxBodySizeMiddleware,
    RequestIdMiddleware,
    SecurityHeadersMiddleware,
    TimeoutMiddleware,
    apply_security_middleware,
)

# ASGI callable type aliases.
_ASGIReceive = Callable[[], Awaitable[dict[str, Any]]]
_ASGISend = Callable[[dict[str, Any]], Awaitable[None]]


async def _echo_app(scope: dict[str, Any], receive: _ASGIReceive, send: _ASGISend) -> None:
    """Minimal ASGI app that returns 200 with a JSON body."""
    body = json.dumps({"status": "ok"}).encode()
    await send({
        "type": "http.response.start",
        "status": 200,
        "headers": [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode()),
        ],
    })
    await send({
        "type": "http.response.body",
        "body": body,
    })


def _http_scope(
    *,
    method: str = "GET",
    path: str = "/test",
    scheme: str = "http",
    headers: list[tuple[bytes, bytes]] | None = None,
    client: tuple[str, int] = ("127.0.0.1", 12345),
) -> dict[str, Any]:
    """Build a minimal ASGI HTTP scope dict for testing."""
    return {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "path": path,
        "scheme": scheme,
        "headers": headers or [],
        "client": client,
    }


async def _noop_receive() -> dict[str, Any]:
    """No-op receive callable for ASGI."""
    return {"type": "http.request", "body": b""}


class _ResponseCapture:
    """Captures ASGI send messages for test assertions."""

    def __init__(self) -> None:
        self.messages = []

    async def __call__(self, message: dict[str, Any]) -> None:
        """Record an ASGI send message."""
        self.messages.append(message)

    @property
    def start_message(self) -> dict[str, Any] | None:
        """Return the ``http.response.start`` message, if any."""
        for msg in self.messages:
            if msg["type"] == "http.response.start":
                return msg
        return None

    @property
    def status(self) -> int | None:
        """Return the HTTP status code from the start message."""
        start = self.start_message
        return start["status"] if start else None

    @property
    def headers(self) -> dict[str, str]:
        """Return response headers as a decoded name-value dict."""
        start = self.start_message
        if not start:
            return {}
        return {name.decode(): value.decode() for name, value in start.get("headers", [])}

    @property
    def body(self) -> bytes:
        """Return the response body bytes."""
        for msg in self.messages:
            if msg["type"] == "http.response.body":
                return msg.get("body", b"")
        return b""


@pytest.mark.asyncio
async def test_security_headers_added_to_http_response() -> None:
    """SecurityHeadersMiddleware injects OWASP headers (via secure lib) on HTTP."""
    middleware = SecurityHeadersMiddleware(_echo_app)
    scope = _http_scope()
    capture = _ResponseCapture()

    await middleware(scope, _noop_receive, capture)

    assert capture.status == 200
    headers = capture.headers
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert headers["content-security-policy"] == "default-src none"
    assert headers["permissions-policy"] == "geolocation=(), camera=(), microphone=()"
    assert headers["cross-origin-opener-policy"] == "same-origin"


@pytest.mark.asyncio
async def test_security_headers_no_hsts_over_http() -> None:
    """HSTS is NOT added when the request is over plain HTTP."""
    middleware = SecurityHeadersMiddleware(_echo_app)
    scope = _http_scope(scheme="http")
    capture = _ResponseCapture()

    await middleware(scope, _noop_receive, capture)

    assert "strict-transport-security" not in capture.headers


@pytest.mark.asyncio
async def test_security_headers_hsts_over_https() -> None:
    """HSTS IS added when the request arrives over HTTPS."""
    middleware = SecurityHeadersMiddleware(_echo_app, hsts_max_age=86400)
    scope = _http_scope(scheme="https")
    capture = _ResponseCapture()

    await middleware(scope, _noop_receive, capture)

    assert "strict-transport-security" in capture.headers
    assert "max-age=86400" in capture.headers["strict-transport-security"]
    assert "includeSubDomains" in capture.headers["strict-transport-security"]


@pytest.mark.asyncio
async def test_security_headers_hsts_disabled_when_zero() -> None:
    """HSTS is not added when hsts_max_age=0, even over HTTPS."""
    middleware = SecurityHeadersMiddleware(_echo_app, hsts_max_age=0)
    scope = _http_scope(scheme="https")
    capture = _ResponseCapture()

    await middleware(scope, _noop_receive, capture)

    assert "strict-transport-security" not in capture.headers


@pytest.mark.asyncio
async def test_security_headers_passthrough_for_websocket() -> None:
    """Non-HTTP scopes (e.g. websocket) are passed through unmodified."""
    called = False

    async def ws_app(scope: dict[str, Any], receive: _ASGIReceive, send: _ASGISend) -> None:
        nonlocal called
        called = True

    middleware = SecurityHeadersMiddleware(ws_app)
    scope = {"type": "websocket"}

    await middleware(scope, _noop_receive, lambda msg: None)

    assert called


@pytest.mark.asyncio
async def test_security_headers_preserves_existing_headers() -> None:
    """Existing response headers from the app are preserved."""

    async def app_with_custom_header(scope: dict[str, Any], receive: _ASGIReceive, send: _ASGISend) -> None:
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"x-custom", b"hello")],
        })
        await send({"type": "http.response.body", "body": b""})

    middleware = SecurityHeadersMiddleware(app_with_custom_header)
    scope = _http_scope()
    capture = _ResponseCapture()

    await middleware(scope, _noop_receive, capture)

    assert capture.headers["x-custom"] == "hello"
    assert capture.headers["x-content-type-options"] == "nosniff"


@pytest.mark.asyncio
async def test_default_security_headers_count() -> None:
    """SecurityHeadersMiddleware injects the expected number of headers."""
    middleware = SecurityHeadersMiddleware(_echo_app)
    scope = _http_scope()
    capture = _ResponseCapture()

    await middleware(scope, _noop_receive, capture)

    security_header_names = {
        "x-content-type-options",
        "x-frame-options",
        "referrer-policy",
        "content-security-policy",
        "permissions-policy",
        "cross-origin-opener-policy",
    }
    present = security_header_names.intersection(capture.headers.keys())
    assert len(present) == 6


@pytest.mark.asyncio
async def test_max_body_size_allows_small_request() -> None:
    """Requests within the size limit pass through normally."""
    middleware = MaxBodySizeMiddleware(_echo_app, max_bytes=1024)
    scope = _http_scope(headers=[(b"content-length", b"100")])
    capture = _ResponseCapture()

    await middleware(scope, _noop_receive, capture)

    assert capture.status == 200


@pytest.mark.asyncio
async def test_max_body_size_rejects_oversized_request() -> None:
    """Requests exceeding the size limit get 413."""
    middleware = MaxBodySizeMiddleware(_echo_app, max_bytes=100)
    scope = _http_scope(headers=[(b"content-length", b"200")])
    capture = _ResponseCapture()

    await middleware(scope, _noop_receive, capture)

    assert capture.status == 413
    body_data = json.loads(capture.body)
    assert body_data["error"] == "Payload Too Large"
    assert "100" in body_data["detail"]


@pytest.mark.asyncio
async def test_max_body_size_allows_exact_limit() -> None:
    """Request whose Content-Length exactly equals max_bytes passes."""
    middleware = MaxBodySizeMiddleware(_echo_app, max_bytes=500)
    scope = _http_scope(headers=[(b"content-length", b"500")])
    capture = _ResponseCapture()

    await middleware(scope, _noop_receive, capture)

    assert capture.status == 200


@pytest.mark.asyncio
async def test_max_body_size_no_content_length() -> None:
    """Requests without Content-Length pass through (e.g. chunked)."""
    middleware = MaxBodySizeMiddleware(_echo_app, max_bytes=100)
    scope = _http_scope(headers=[])
    capture = _ResponseCapture()

    await middleware(scope, _noop_receive, capture)

    assert capture.status == 200


@pytest.mark.asyncio
async def test_max_body_size_invalid_content_length() -> None:
    """Non-numeric Content-Length is ignored (request passes through)."""
    middleware = MaxBodySizeMiddleware(_echo_app, max_bytes=100)
    scope = _http_scope(headers=[(b"content-length", b"not-a-number")])
    capture = _ResponseCapture()

    await middleware(scope, _noop_receive, capture)

    assert capture.status == 200


@pytest.mark.asyncio
async def test_max_body_size_passthrough_for_websocket() -> None:
    """Non-HTTP scopes pass through MaxBodySizeMiddleware."""
    called = False

    async def ws_app(scope: dict[str, Any], receive: _ASGIReceive, send: _ASGISend) -> None:
        nonlocal called
        called = True

    middleware = MaxBodySizeMiddleware(ws_app, max_bytes=100)
    scope = {"type": "websocket"}

    await middleware(scope, _noop_receive, lambda msg: None)

    assert called


@pytest.mark.asyncio
async def test_apply_security_middleware_returns_callable() -> None:
    """apply_security_middleware wraps an app and returns a callable."""
    wrapped = apply_security_middleware(_echo_app)
    assert callable(wrapped)


@pytest.mark.asyncio
async def test_apply_security_middleware_adds_cors_headers() -> None:
    """The full middleware stack adds CORS headers to preflight requests."""
    wrapped = apply_security_middleware(
        _echo_app,
        cors_origins=["https://example.com"],
    )
    scope = _http_scope(
        method="OPTIONS",
        headers=[
            (b"origin", b"https://example.com"),
            (b"access-control-request-method", b"POST"),
        ],
    )
    capture = _ResponseCapture()

    await wrapped(scope, _noop_receive, capture)

    assert "access-control-allow-origin" in capture.headers


@pytest.mark.asyncio
async def test_apply_security_middleware_with_trusted_hosts() -> None:
    """Trusted hosts middleware rejects requests with wrong Host header."""
    wrapped = apply_security_middleware(
        _echo_app,
        trusted_hosts=["good.example.com"],
    )
    scope = _http_scope(
        headers=[
            (b"host", b"evil.example.com"),
        ],
    )
    capture = _ResponseCapture()

    await wrapped(scope, _noop_receive, capture)

    assert capture.status == 400


@pytest.mark.asyncio
async def test_apply_security_middleware_body_limit_in_stack() -> None:
    """The full stack rejects oversized bodies."""
    wrapped = apply_security_middleware(
        _echo_app,
        max_body_size=50,
    )
    scope = _http_scope(
        method="POST",
        headers=[
            (b"content-length", b"999"),
            (b"host", b"localhost"),
        ],
    )
    capture = _ResponseCapture()

    await wrapped(scope, _noop_receive, capture)

    assert capture.status == 413


@pytest.mark.asyncio
async def test_apply_security_middleware_security_headers_in_stack() -> None:
    """The full stack injects security headers on normal responses."""
    wrapped = apply_security_middleware(_echo_app)
    scope = _http_scope(headers=[(b"host", b"localhost")])
    capture = _ResponseCapture()

    await wrapped(scope, _noop_receive, capture)

    assert capture.status == 200
    assert capture.headers.get("x-content-type-options") == "nosniff"


@pytest.mark.asyncio
async def test_apply_security_middleware_production_cors_same_origin() -> None:
    """Production default CORS denies cross-origin requests (same-origin only)."""
    wrapped = apply_security_middleware(_echo_app)
    scope = _http_scope(
        method="OPTIONS",
        headers=[
            (b"origin", b"https://anything.example.com"),
            (b"access-control-request-method", b"POST"),
        ],
    )
    capture = _ResponseCapture()

    await wrapped(scope, _noop_receive, capture)

    # Same-origin-only means no Access-Control-Allow-Origin for unknown origins.
    assert capture.headers.get("access-control-allow-origin") != "*"


@pytest.mark.asyncio
async def test_apply_security_middleware_debug_cors_wildcard() -> None:
    """Debug mode CORS allows all origins (wildcard) for dev tools."""
    wrapped = apply_security_middleware(_echo_app, debug=True)
    scope = _http_scope(
        method="OPTIONS",
        headers=[
            (b"origin", b"https://anything.example.com"),
            (b"access-control-request-method", b"POST"),
        ],
    )
    capture = _ResponseCapture()

    await wrapped(scope, _noop_receive, capture)

    assert capture.headers.get("access-control-allow-origin") == "*"


@pytest.mark.asyncio
async def test_apply_security_middleware_no_trusted_hosts() -> None:
    """Without trusted_hosts, all Host headers are accepted."""
    wrapped = apply_security_middleware(
        _echo_app,
        trusted_hosts=None,
    )
    scope = _http_scope(
        headers=[(b"host", b"any-host.example.com")],
    )
    capture = _ResponseCapture()

    await wrapped(scope, _noop_receive, capture)

    assert capture.status == 200


@pytest.mark.asyncio
async def test_exception_middleware_catches_unhandled_error() -> None:
    """ExceptionMiddleware returns 500 JSON on unhandled exceptions."""

    async def crashing_app(scope: dict[str, Any], receive: _ASGIReceive, send: _ASGISend) -> None:
        msg = "boom"
        raise RuntimeError(msg)

    middleware = ExceptionMiddleware(crashing_app)
    scope = _http_scope()
    capture = _ResponseCapture()

    await middleware(scope, _noop_receive, capture)

    assert capture.status == 500
    body_data = json.loads(capture.body)
    assert body_data["error"] == "Internal Server Error"
    assert body_data["detail"] == "Internal server error"


@pytest.mark.asyncio
async def test_exception_middleware_debug_includes_type() -> None:
    """ExceptionMiddleware in debug mode includes exception type in detail."""

    async def crashing_app(scope: dict[str, Any], receive: _ASGIReceive, send: _ASGISend) -> None:
        msg = "kaboom"
        raise ValueError(msg)

    middleware = ExceptionMiddleware(crashing_app, debug=True)
    scope = _http_scope()
    capture = _ResponseCapture()

    await middleware(scope, _noop_receive, capture)

    assert capture.status == 500
    body_data = json.loads(capture.body)
    assert "ValueError" in body_data["detail"]


@pytest.mark.asyncio
async def test_exception_middleware_passthrough_on_success() -> None:
    """ExceptionMiddleware passes through successful responses."""
    middleware = ExceptionMiddleware(_echo_app)
    scope = _http_scope()
    capture = _ResponseCapture()

    await middleware(scope, _noop_receive, capture)

    assert capture.status == 200


@pytest.mark.asyncio
async def test_access_log_middleware_passes_through() -> None:
    """AccessLogMiddleware does not alter the response."""
    middleware = AccessLogMiddleware(_echo_app)
    scope = _http_scope()
    capture = _ResponseCapture()

    await middleware(scope, _noop_receive, capture)

    assert capture.status == 200
    body_data = json.loads(capture.body)
    assert body_data["status"] == "ok"


@pytest.mark.asyncio
async def test_timeout_middleware_passes_fast_request() -> None:
    """TimeoutMiddleware allows requests that complete within the timeout."""
    middleware = TimeoutMiddleware(_echo_app, timeout=5.0)
    scope = _http_scope()
    capture = _ResponseCapture()

    await middleware(scope, _noop_receive, capture)

    assert capture.status == 200


@pytest.mark.asyncio
async def test_timeout_middleware_rejects_slow_request() -> None:
    """TimeoutMiddleware returns 504 for requests exceeding the timeout."""

    async def slow_app(scope: dict[str, Any], receive: _ASGIReceive, send: _ASGISend) -> None:
        await asyncio.sleep(10)

    middleware = TimeoutMiddleware(slow_app, timeout=0.01)
    scope = _http_scope()
    capture = _ResponseCapture()

    await middleware(scope, _noop_receive, capture)

    assert capture.status == 504
    body_data = json.loads(capture.body)
    assert body_data["error"] == "Gateway Timeout"


@pytest.mark.asyncio
async def test_security_headers_include_cache_control() -> None:
    """SecurityHeadersMiddleware injects Cache-Control: no-store."""
    middleware = SecurityHeadersMiddleware(_echo_app)
    scope = _http_scope()
    capture = _ResponseCapture()

    await middleware(scope, _noop_receive, capture)

    assert capture.headers.get("cache-control") == "no-store"


@pytest.mark.asyncio
async def test_security_headers_suppress_server_header() -> None:
    """SecurityHeadersMiddleware removes upstream Server headers."""

    async def app_with_server(scope: dict[str, Any], receive: _ASGIReceive, send: _ASGISend) -> None:
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"server", b"Uvicorn/0.30"), (b"content-type", b"text/plain")],
        })
        await send({"type": "http.response.body", "body": b"ok"})

    middleware = SecurityHeadersMiddleware(app_with_server)
    scope = _http_scope()
    capture = _ResponseCapture()

    await middleware(scope, _noop_receive, capture)

    # The upstream "Uvicorn/0.30" should be stripped; our empty server header remains.
    assert not capture.headers.get("server")


@pytest.mark.asyncio
async def test_request_id_middleware_generates_id() -> None:
    """RequestIdMiddleware generates a UUID when no header is sent."""
    middleware = RequestIdMiddleware(_echo_app)
    scope = _http_scope()
    capture = _ResponseCapture()

    await middleware(scope, _noop_receive, capture)

    assert capture.status == 200
    assert capture.headers.get("x-request-id")


@pytest.mark.asyncio
async def test_request_id_middleware_propagates_header() -> None:
    """RequestIdMiddleware reuses X-Request-ID from the client."""
    middleware = RequestIdMiddleware(_echo_app)
    scope = _http_scope(headers=[(b"x-request-id", b"abc-123")])
    capture = _ResponseCapture()

    await middleware(scope, _noop_receive, capture)

    assert capture.headers.get("x-request-id") == "abc-123"


@pytest.mark.asyncio
async def test_request_id_middleware_passthrough_for_websocket() -> None:
    """RequestIdMiddleware passes through non-HTTP scopes."""
    called = False

    async def ws_app(scope: dict[str, Any], receive: _ASGIReceive, send: _ASGISend) -> None:
        nonlocal called
        called = True

    middleware = RequestIdMiddleware(ws_app)
    scope = {"type": "websocket"}

    await middleware(scope, _noop_receive, lambda msg: None)

    assert called


@pytest.mark.asyncio
async def test_exception_middleware_passthrough_for_websocket() -> None:
    """ExceptionMiddleware passes through non-HTTP scopes."""
    called = False

    async def ws_app(scope: dict[str, Any], receive: _ASGIReceive, send: _ASGISend) -> None:
        nonlocal called
        called = True

    middleware = ExceptionMiddleware(ws_app)
    scope = {"type": "websocket"}

    await middleware(scope, _noop_receive, lambda msg: None)

    assert called


@pytest.mark.asyncio
async def test_access_log_middleware_passthrough_for_websocket() -> None:
    """AccessLogMiddleware passes through non-HTTP scopes."""
    called = False

    async def ws_app(scope: dict[str, Any], receive: _ASGIReceive, send: _ASGISend) -> None:
        nonlocal called
        called = True

    middleware = AccessLogMiddleware(ws_app)
    scope = {"type": "websocket"}

    await middleware(scope, _noop_receive, lambda msg: None)

    assert called


@pytest.mark.asyncio
async def test_timeout_middleware_passthrough_for_websocket() -> None:
    """TimeoutMiddleware passes through non-HTTP scopes."""
    called = False

    async def ws_app(scope: dict[str, Any], receive: _ASGIReceive, send: _ASGISend) -> None:
        nonlocal called
        called = True

    middleware = TimeoutMiddleware(ws_app)
    scope = {"type": "websocket"}

    await middleware(scope, _noop_receive, lambda msg: None)

    assert called


@pytest.mark.asyncio
async def test_security_headers_debug_mode_relaxed_csp() -> None:
    """Debug mode uses a relaxed CSP allowing CDN resources."""
    middleware = SecurityHeadersMiddleware(_echo_app, debug=True)
    scope = _http_scope()
    capture = _ResponseCapture()

    await middleware(scope, _noop_receive, capture)

    csp = capture.headers.get("content-security-policy", "")
    assert "'self'" in csp
    assert "cdn.jsdelivr.net" in csp


@pytest.mark.asyncio
async def test_apply_security_middleware_custom_cors_methods() -> None:
    """Custom CORS methods are respected in the middleware stack."""
    wrapped = apply_security_middleware(
        _echo_app,
        cors_origins=["https://example.com"],
        cors_methods=["GET", "PUT"],
        cors_headers=["Content-Type"],
    )
    assert callable(wrapped)


@pytest.mark.asyncio
async def test_apply_security_middleware_custom_timeout_and_gzip() -> None:
    """Custom timeout and gzip settings are accepted."""
    wrapped = apply_security_middleware(
        _echo_app,
        request_timeout=30.0,
        gzip_min_size=1000,
    )
    assert callable(wrapped)


# ──────────────────────────────────────────────────────────────────
# debug=False invariant tests
#
# These tests enforce the invariant that debug=False (production)
# ALWAYS results in more restrictive security than debug=True.
# If a new feature uses the debug flag, add a paired test here.
# See GEMINI.md "debug=False security invariants" for the checklist.
# ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_invariant_csp_strict_when_debug_false() -> None:
    """Production CSP must be ``default-src none`` — no CDN, no inline."""
    prod = SecurityHeadersMiddleware(_echo_app, debug=False)
    scope = _http_scope()
    capture = _ResponseCapture()

    await prod(scope, _noop_receive, capture)

    csp = capture.headers["content-security-policy"]
    assert csp == "default-src none", f"debug=False CSP is not strict: {csp!r}"


@pytest.mark.asyncio
async def test_invariant_csp_relaxed_when_debug_true() -> None:
    """Debug CSP must allow Swagger CDN — the paired complement of the strict test."""
    dev = SecurityHeadersMiddleware(_echo_app, debug=True)
    scope = _http_scope()
    capture = _ResponseCapture()

    await dev(scope, _noop_receive, capture)

    csp = capture.headers["content-security-policy"]
    assert csp != "default-src none", "debug=True CSP should be relaxed"
    assert "cdn.jsdelivr.net" in csp, "debug=True CSP should allow Swagger CDN"


@pytest.mark.asyncio
async def test_invariant_csp_production_stricter_than_debug() -> None:
    """Production CSP must be strictly shorter (more restrictive) than debug."""
    prod_mid = SecurityHeadersMiddleware(_echo_app, debug=False)
    debug_mid = SecurityHeadersMiddleware(_echo_app, debug=True)

    prod_capture = _ResponseCapture()
    debug_capture = _ResponseCapture()
    scope = _http_scope()

    await prod_mid(scope, _noop_receive, prod_capture)
    await debug_mid(scope, _noop_receive, debug_capture)

    prod_csp = prod_capture.headers["content-security-policy"]
    debug_csp = debug_capture.headers["content-security-policy"]

    assert len(prod_csp) < len(debug_csp), (
        f"Production CSP ({len(prod_csp)} chars) must be shorter than debug CSP ({len(debug_csp)} chars)"
    )


@pytest.mark.asyncio
async def test_invariant_exception_no_leak_when_debug_false() -> None:
    """Production exception handler must not expose exception type to clients."""

    async def crashing_app(scope: dict[str, Any], receive: _ASGIReceive, send: _ASGISend) -> None:
        msg = "secret internal error"
        raise ValueError(msg)

    middleware = ExceptionMiddleware(crashing_app, debug=False)
    scope = _http_scope()
    capture = _ResponseCapture()

    await middleware(scope, _noop_receive, capture)

    assert capture.status == 500
    body = json.loads(capture.body)
    assert body["detail"] == "Internal server error", "debug=False must return generic error detail"
    assert "ValueError" not in body["detail"], "debug=False must not expose exception type"
    assert "secret internal error" not in body["detail"], "debug=False must not expose exception message"


@pytest.mark.asyncio
async def test_invariant_exception_shows_type_when_debug_true() -> None:
    """Debug exception handler includes exception type for developer convenience."""

    async def crashing_app(scope: dict[str, Any], receive: _ASGIReceive, send: _ASGISend) -> None:
        msg = "kaboom"
        raise ValueError(msg)

    middleware = ExceptionMiddleware(crashing_app, debug=True)
    scope = _http_scope()
    capture = _ResponseCapture()

    await middleware(scope, _noop_receive, capture)

    assert capture.status == 500
    body = json.loads(capture.body)
    assert "ValueError" in body["detail"], "debug=True should expose exception type"


@pytest.mark.asyncio
async def test_invariant_cors_same_origin_when_debug_false() -> None:
    """Production CORS with no explicit origins must enforce same-origin."""
    wrapped = apply_security_middleware(_echo_app, debug=False)
    scope = _http_scope(
        method="OPTIONS",
        headers=[
            (b"origin", b"https://evil.example.com"),
            (b"access-control-request-method", b"POST"),
        ],
    )
    capture = _ResponseCapture()

    await wrapped(scope, _noop_receive, capture)

    acao = capture.headers.get("access-control-allow-origin", "")
    assert acao != "*", "debug=False CORS must not allow wildcard origins"
    assert acao != "https://evil.example.com", "debug=False CORS must reject unknown origins"


@pytest.mark.asyncio
async def test_invariant_cors_wildcard_when_debug_true() -> None:
    """Debug CORS with no explicit origins must fall back to wildcard."""
    wrapped = apply_security_middleware(_echo_app, debug=True)
    scope = _http_scope(
        method="OPTIONS",
        headers=[
            (b"origin", b"https://evil.example.com"),
            (b"access-control-request-method", b"POST"),
        ],
    )
    capture = _ResponseCapture()

    await wrapped(scope, _noop_receive, capture)

    assert capture.headers.get("access-control-allow-origin") == "*", "debug=True CORS should fall back to wildcard"


@pytest.mark.asyncio
async def test_invariant_security_headers_always_present_debug_false() -> None:
    """Production mode must always include all OWASP security headers."""
    middleware = SecurityHeadersMiddleware(_echo_app, debug=False)
    scope = _http_scope()
    capture = _ResponseCapture()

    await middleware(scope, _noop_receive, capture)

    h = capture.headers
    assert h.get("x-content-type-options") == "nosniff"
    assert h.get("x-frame-options") == "DENY"
    assert h.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert h.get("permissions-policy") == "geolocation=(), camera=(), microphone=()"
    assert h.get("cross-origin-opener-policy") == "same-origin"
    assert h.get("cache-control") == "no-store"
    assert not h.get("server"), "Server header must be suppressed"


@pytest.mark.asyncio
async def test_invariant_security_headers_always_present_debug_true() -> None:
    """Debug mode must still include all OWASP headers (except relaxed CSP)."""
    middleware = SecurityHeadersMiddleware(_echo_app, debug=True)
    scope = _http_scope()
    capture = _ResponseCapture()

    await middleware(scope, _noop_receive, capture)

    h = capture.headers
    assert h.get("x-content-type-options") == "nosniff"
    assert h.get("x-frame-options") == "DENY"
    assert h.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert h.get("permissions-policy") == "geolocation=(), camera=(), microphone=()"
    assert h.get("cross-origin-opener-policy") == "same-origin"
    assert h.get("cache-control") == "no-store"
    assert not h.get("server"), "Server header must be suppressed even in debug"


@pytest.mark.asyncio
async def test_invariant_trusted_hosts_warning_fires_in_production(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Production mode logs a warning when TRUSTED_HOSTS is empty."""
    with caplog.at_level(logging.WARNING):
        apply_security_middleware(_echo_app, trusted_hosts=None, debug=False)

    assert any("TRUSTED_HOSTS" in record.message for record in caplog.records), (
        "debug=False should warn about missing TRUSTED_HOSTS"
    )


@pytest.mark.asyncio
async def test_invariant_trusted_hosts_no_warning_in_debug(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Debug mode suppresses the trusted hosts warning."""
    with caplog.at_level(logging.WARNING):
        apply_security_middleware(_echo_app, trusted_hosts=None, debug=True)

    assert not any("TRUSTED_HOSTS" in record.message for record in caplog.records), (
        "debug=True should suppress the TRUSTED_HOSTS warning"
    )
