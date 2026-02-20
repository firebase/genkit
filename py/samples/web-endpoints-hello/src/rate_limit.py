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

"""Token-bucket rate limiting for ASGI and gRPC servers.

Provides framework-agnostic rate limiting that works identically across
FastAPI, Litestar, Quart, and the gRPC server:

- **RateLimitMiddleware** — Pure ASGI middleware using an in-memory
  token-bucket per client IP. Returns 429 when the bucket is empty.
- **GrpcRateLimitInterceptor** — gRPC server interceptor that applies
  the same token-bucket logic, returning ``RESOURCE_EXHAUSTED``.
- **TokenBucket** — The underlying rate limiter (thread-safe, async-safe).

The token-bucket algorithm is simple: each client gets a bucket of
``capacity`` tokens. One token is consumed per request. Tokens refill
at ``rate`` tokens per second. When the bucket is empty, requests are
rejected until tokens refill.

Why custom instead of the ``limits`` library
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We evaluated the ``limits`` library (used by SlowAPI) and chose to
keep a custom implementation because:

1. **Sync-only API** — ``limits.FixedWindowRateLimiter.hit()`` and
   ``get_window_stats()`` are synchronous. With ``MemoryStorage`` this
   is fast, but if you switch to ``RedisStorage`` or
   ``MemcachedStorage`` these become blocking network I/O calls that
   stall the entire asyncio event loop.
2. **Wall-clock time** — ``limits`` uses ``time.time()`` internally,
   which is subject to NTP clock jumps. Our token bucket uses
   ``time.monotonic()`` which is NTP-immune and monotonically
   increasing.
3. **Fixed-window vs token-bucket** — ``limits`` uses fixed time
   windows, which allows bursts at window boundaries (a client can
   send 2x the limit across two adjacent windows). Token bucket
   provides smooth rate limiting without boundary spikes.
4. **Simpler code** — ``TokenBucket`` is ~25 lines of logic with
   zero dependencies, versus importing and configuring three
   ``limits`` classes (``MemoryStorage``, ``FixedWindowRateLimiter``,
   ``parse``).

Thread-safety and asyncio notes:

- ``TokenBucket.consume()`` is synchronous but sub-microsecond
  (single dict lookup + arithmetic). It does not block the event loop.
- ``retry_after`` values are clamped to ``[0, 3600]`` seconds to guard
  against ``time.monotonic()`` anomalies.

Configuration via environment variables:

- ``RATE_LIMIT_DEFAULT`` — Format: ``<requests>/<period>``
  (e.g. ``60/minute``, ``100/second``, ``1000/hour``). Default: ``60/minute``.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import Any

import grpc
import structlog

from .util.asgi import ASGIApp, Receive, Scope, Send, get_client_ip
from .util.parse import parse_rate

logger = structlog.get_logger(__name__)

_EXEMPT_PATHS: frozenset[str] = frozenset({"/health", "/healthz", "/ready", "/readyz"})
"""Paths exempted from rate limiting (health checks)."""

_MAX_RETRY_AFTER: float = 3600.0
"""Upper bound for ``retry_after`` to guard against clock anomalies."""


class TokenBucket:
    """In-memory token-bucket rate limiter.

    Thread-safe for single-process use (relies on the GIL for dict
    operations). Each key (e.g. client IP) gets an independent bucket.

    Uses ``time.monotonic()`` for interval measurement, which is
    immune to NTP clock adjustments.

    Args:
        capacity: Maximum tokens per bucket.
        refill_period: Seconds to fully refill an empty bucket.
    """

    def __init__(self, capacity: int, refill_period: int) -> None:
        """Initialize the bucket with a token capacity and refill period."""
        self.capacity = capacity
        self.refill_rate = capacity / refill_period
        self._buckets: dict[str, tuple[float, float]] = {}

    def consume(self, key: str) -> tuple[bool, float]:
        """Try to consume one token for ``key``.

        Returns:
            Tuple of (allowed, retry_after_seconds). If ``allowed`` is
            ``False``, ``retry_after_seconds`` indicates when the next
            token will be available. Clamped to ``[0, _MAX_RETRY_AFTER]``.
        """
        now = time.monotonic()
        tokens, last_time = self._buckets.get(key, (float(self.capacity), now))

        elapsed = now - last_time
        tokens = min(float(self.capacity), tokens + elapsed * self.refill_rate)

        if tokens >= 1.0:
            self._buckets[key] = (tokens - 1.0, now)
            return True, 0.0

        retry_after = min((1.0 - tokens) / self.refill_rate, _MAX_RETRY_AFTER)
        self._buckets[key] = (tokens, now)
        return False, retry_after


class RateLimitMiddleware:
    """ASGI middleware that applies token-bucket rate limiting per client IP.

    Returns **429 Too Many Requests** with a ``Retry-After`` header
    when the client's bucket is empty. Health-check endpoints are
    exempt.

    Args:
        app: The ASGI application to wrap.
        rate: Rate string (e.g. ``60/minute``). Default: ``60/minute``.
    """

    def __init__(self, app: ASGIApp, *, rate: str = "60/minute") -> None:
        """Wrap *app* with per-IP rate limiting at the given *rate*."""
        self.app = app
        capacity, period = parse_rate(rate)
        self.bucket = TokenBucket(capacity, period)
        self._rate_str = rate

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Check rate limit for HTTP requests."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in _EXEMPT_PATHS:
            await self.app(scope, receive, send)
            return

        client_ip = get_client_ip(scope)

        allowed, retry_after = self.bucket.consume(client_ip)
        if not allowed:
            await _send_429(send, retry_after)
            return

        await self.app(scope, receive, send)


class GrpcRateLimitInterceptor(grpc.aio.ServerInterceptor):  # ty: ignore[possibly-missing-attribute] — incomplete stubs
    """gRPC server interceptor that applies token-bucket rate limiting.

    Returns ``RESOURCE_EXHAUSTED`` when the client's bucket is empty.

    Args:
        rate: Rate string (e.g. ``60/minute``). Default: ``60/minute``.
    """

    def __init__(self, *, rate: str = "60/minute") -> None:
        """Initialize the interceptor with per-peer rate limiting at *rate*."""
        capacity, period = parse_rate(rate)
        self.bucket = TokenBucket(capacity, period)

    async def intercept_service(
        self,
        continuation: Callable[..., Any],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> Any:  # noqa: ANN401 - return type is dictated by grpc.aio.ServerInterceptor
        """Check rate limit before handling the RPC."""
        peer = getattr(handler_call_details, "invocation_metadata", None)
        method = handler_call_details.method  # ty: ignore[unresolved-attribute] — incomplete stubs
        key = str(peer) if peer else method

        allowed, retry_after = self.bucket.consume(key)
        if not allowed:
            logger.warning(
                "gRPC rate limit exceeded",
                method=method,
                retry_after=f"{retry_after:.1f}s",
            )

            async def _abort(request: Any, context: grpc.aio.ServicerContext) -> None:  # noqa: ANN401 - grpc handler signature  # ty: ignore[possibly-missing-attribute]
                await context.abort(
                    grpc.StatusCode.RESOURCE_EXHAUSTED,
                    f"Rate limit exceeded. Retry after {retry_after:.1f}s.",
                )

            return grpc.unary_unary_rpc_method_handler(
                _abort  # pyrefly: ignore[bad-argument-type] — async handler is correct; stubs expect sync
            )

        return await continuation(handler_call_details)


async def _send_429(send: Send, retry_after: float) -> None:
    """Send a 429 Too Many Requests JSON response.

    Includes ``retry_after`` in both the JSON body (for API consumers)
    and the ``Retry-After`` response header (per HTTP spec).
    """
    retry_seconds = max(1, int(retry_after + 0.5))
    body = json.dumps({
        "error": "Too Many Requests",
        "detail": f"Rate limit exceeded. Retry after {retry_seconds}s.",
        "retry_after": retry_seconds,
    }).encode()
    await send({
        "type": "http.response.start",
        "status": 429,
        "headers": [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode()),
            (b"retry-after", str(retry_seconds).encode()),
        ],
    })
    await send({
        "type": "http.response.body",
        "body": body,
    })
