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

"""Tests for token-bucket rate limiting (ASGI middleware and gRPC interceptor).

Covers parse_rate(), TokenBucket, RateLimitMiddleware, and
GrpcRateLimitInterceptor. All tests use minimal ASGI/gRPC stubs —
no framework or live gRPC server required.

Run with::

    cd py/samples/web-endpoints-hello
    uv run pytest tests/rate_limit_test.py -v
"""

import json
import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.rate_limit import (
    GrpcRateLimitInterceptor,
    RateLimitMiddleware,
    TokenBucket,
)
from src.util.asgi import Receive, Scope, Send


def test_token_bucket_allows_initial_requests() -> None:
    """A fresh bucket allows requests up to capacity."""
    bucket = TokenBucket(capacity=3, refill_period=60)

    allowed1, _ = bucket.consume("client-a")
    allowed2, _ = bucket.consume("client-a")
    allowed3, _ = bucket.consume("client-a")

    assert allowed1
    assert allowed2
    assert allowed3


def test_token_bucket_rejects_after_capacity() -> None:
    """After consuming all tokens, the next request is rejected."""
    bucket = TokenBucket(capacity=2, refill_period=60)

    bucket.consume("client-a")
    bucket.consume("client-a")
    allowed, retry_after = bucket.consume("client-a")

    assert not allowed
    assert retry_after > 0


def test_token_bucket_independent_keys() -> None:
    """Different keys have independent buckets."""
    bucket = TokenBucket(capacity=1, refill_period=60)

    bucket.consume("client-a")
    allowed_b, _ = bucket.consume("client-b")

    assert allowed_b


def test_token_bucket_refills_over_time() -> None:
    """Tokens refill after time passes."""
    bucket = TokenBucket(capacity=1, refill_period=1)

    bucket.consume("client-a")
    allowed_before_refill, _ = bucket.consume("client-a")
    assert not allowed_before_refill

    # Simulate time passing by patching monotonic.
    original_monotonic = time.monotonic
    with patch("src.rate_limit.time") as mock_time:
        mock_time.monotonic.return_value = original_monotonic() + 2.0
        allowed_after_refill, _ = bucket.consume("client-a")

    assert allowed_after_refill


def test_token_bucket_retry_after_value() -> None:
    """retry_after indicates when the next token will be available."""
    bucket = TokenBucket(capacity=1, refill_period=10)

    bucket.consume("client-a")
    _, retry_after = bucket.consume("client-a")

    # With 1 token per 10 seconds, retry should be around 10 seconds.
    assert retry_after > 0
    assert retry_after <= 10.0


def test_token_bucket_zero_retry_when_allowed() -> None:
    """Allowed requests always return 0 retry_after."""
    bucket = TokenBucket(capacity=10, refill_period=60)

    _, retry_after = bucket.consume("client-a")

    assert retry_after == 0.0


async def _echo_app(scope: Scope, receive: Receive, send: Send) -> None:
    """Minimal ASGI app that returns 200."""
    body = b'{"status":"ok"}'
    await send({
        "type": "http.response.start",
        "status": 200,
        "headers": [(b"content-type", b"application/json")],
    })
    await send({"type": "http.response.body", "body": body})


def _http_scope(*, path: str = "/test", client: tuple[str, int] = ("127.0.0.1", 12345)) -> dict[str, Any]:
    """Build a minimal ASGI HTTP scope for testing."""
    return {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "path": path,
        "scheme": "http",
        "headers": [],
        "client": client,
    }


async def _noop_receive() -> dict[str, Any]:
    """Return a minimal ASGI HTTP request body."""
    return {"type": "http.request", "body": b""}


class _ResponseCapture:
    """Captures ASGI send messages."""

    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []

    async def __call__(self, message: dict[str, Any]) -> None:
        self.messages.append(message)

    @property
    def status(self) -> int | None:
        for msg in self.messages:
            if msg["type"] == "http.response.start":
                return msg["status"]
        return None

    @property
    def headers(self) -> dict[str, str]:
        for msg in self.messages:
            if msg["type"] == "http.response.start":
                return {name.decode(): value.decode() for name, value in msg.get("headers", [])}
        return {}

    @property
    def body(self) -> bytes:
        for msg in self.messages:
            if msg["type"] == "http.response.body":
                return msg.get("body", b"")
        return b""


@pytest.mark.asyncio
async def test_rate_limit_middleware_allows_within_limit() -> None:
    """Requests within the rate limit pass through."""
    middleware = RateLimitMiddleware(_echo_app, rate="10/second")
    scope = _http_scope()
    capture = _ResponseCapture()

    await middleware(scope, _noop_receive, capture)

    assert capture.status == 200


@pytest.mark.asyncio
async def test_rate_limit_middleware_blocks_over_limit() -> None:
    """Requests exceeding the rate limit get 429."""
    middleware = RateLimitMiddleware(_echo_app, rate="2/minute")

    # Exhaust the bucket.
    for _ in range(2):
        capture = _ResponseCapture()
        await middleware(_http_scope(), _noop_receive, capture)
        assert capture.status == 200

    # Third request should be blocked.
    capture = _ResponseCapture()
    await middleware(_http_scope(), _noop_receive, capture)

    assert capture.status == 429
    body_data = json.loads(capture.body)
    assert body_data["error"] == "Too Many Requests"
    assert "retry_after" in body_data
    assert "retry-after" in capture.headers


@pytest.mark.asyncio
async def test_rate_limit_middleware_exempts_health_paths() -> None:
    """Health-check paths are exempt from rate limiting."""
    middleware = RateLimitMiddleware(_echo_app, rate="1/minute")

    # Exhaust the bucket on a non-health path.
    capture = _ResponseCapture()
    await middleware(_http_scope(path="/api/data"), _noop_receive, capture)
    assert capture.status == 200

    # Health paths should still pass even though the bucket is empty.
    for path in ["/health", "/healthz", "/ready", "/readyz"]:
        capture = _ResponseCapture()
        await middleware(_http_scope(path=path), _noop_receive, capture)
        assert capture.status == 200, f"{path} should be exempt"


@pytest.mark.asyncio
async def test_rate_limit_middleware_per_client_ip() -> None:
    """Different client IPs have separate rate limits."""
    middleware = RateLimitMiddleware(_echo_app, rate="1/minute")

    # Client A exhausts its bucket.
    capture = _ResponseCapture()
    await middleware(_http_scope(client=("10.0.0.1", 1)), _noop_receive, capture)
    assert capture.status == 200

    # Client B still has tokens.
    capture = _ResponseCapture()
    await middleware(_http_scope(client=("10.0.0.2", 2)), _noop_receive, capture)
    assert capture.status == 200


@pytest.mark.asyncio
async def test_rate_limit_middleware_passthrough_non_http() -> None:
    """Non-HTTP scopes (websocket etc.) pass through without rate limiting."""
    called = False

    async def ws_app(scope: Scope, receive: Receive, send: Send) -> None:
        nonlocal called
        called = True

    middleware = RateLimitMiddleware(ws_app, rate="1/minute")
    scope: dict[str, str] = {"type": "websocket"}

    await middleware(scope, _noop_receive, lambda msg: None)

    assert called


@pytest.mark.asyncio
async def test_rate_limit_429_response_format() -> None:
    """The 429 response is valid JSON with required fields."""
    middleware = RateLimitMiddleware(_echo_app, rate="1/minute")

    # First request succeeds.
    capture = _ResponseCapture()
    await middleware(_http_scope(), _noop_receive, capture)

    # Second request triggers 429.
    capture = _ResponseCapture()
    await middleware(_http_scope(), _noop_receive, capture)

    assert capture.status == 429
    body_data = json.loads(capture.body)
    assert "error" in body_data
    assert "detail" in body_data
    assert "retry_after" in body_data
    assert isinstance(body_data["retry_after"], int)
    assert body_data["retry_after"] >= 1


@pytest.mark.asyncio
async def test_grpc_rate_limit_interceptor_allows_within_limit() -> None:
    """GRPC interceptor allows calls within the rate limit."""
    interceptor = GrpcRateLimitInterceptor(rate="10/second")

    mock_handler = MagicMock()
    mock_continuation = AsyncMock(return_value=mock_handler)
    mock_details = MagicMock()
    mock_details.method = "/genkit.sample.v1.GenkitService/TellJoke"
    mock_details.invocation_metadata = None

    result = await interceptor.intercept_service(mock_continuation, mock_details)

    assert result is mock_handler
    mock_continuation.assert_awaited_once_with(mock_details)


@pytest.mark.asyncio
async def test_grpc_rate_limit_interceptor_blocks_over_limit() -> None:
    """GRPC interceptor returns an error handler when rate limit exceeded."""
    interceptor = GrpcRateLimitInterceptor(rate="1/minute")

    mock_handler = MagicMock()
    mock_continuation = AsyncMock(return_value=mock_handler)
    mock_details = MagicMock()
    mock_details.method = "/genkit.sample.v1.GenkitService/TellJoke"
    mock_details.invocation_metadata = None

    # First call succeeds.
    await interceptor.intercept_service(mock_continuation, mock_details)

    # Second call should return an abort handler.
    result = await interceptor.intercept_service(mock_continuation, mock_details)

    # The result should be a gRPC method handler (not the original handler).
    assert result is not mock_handler
    # continuation should only have been called once (the first time).
    assert mock_continuation.await_count == 1
