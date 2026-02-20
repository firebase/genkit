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

"""Circuit breaker for LLM API calls.

Implements the circuit breaker pattern to prevent cascading failures
when the upstream LLM API (Gemini, etc.) is degraded or down. Without
this, a failing API causes:

- **Thread starvation** — Workers block waiting for timeouts.
- **Cascading latency** — Every request waits for the full timeout.
- **Wasted quota** — Retries against a failing API burn rate limits.
- **Poor UX** — Users wait 30s+ before seeing an error.

With a circuit breaker, failures are detected quickly and requests
fail fast with a meaningful 503 response, giving the API time to
recover.

State machine::

    CLOSED ──[failures >= threshold]──► OPEN
      ▲                                   │
      │                              [recovery_timeout]
      │                                   │
      └───[probe succeeds]─── HALF_OPEN ◄─┘
                                   │
                             [probe fails]
                                   │
                                   ▼
                                 OPEN

Why custom instead of ``pybreaker``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We evaluated ``pybreaker`` (the main Python circuit breaker library)
and chose to keep a custom implementation because:

1. **pybreaker is sync-only** — its ``call()`` executes the wrapped
   function synchronously. Wrapping it for async requires accessing
   private internals (``_lock``, ``_state_storage``, ``_handle_error``,
   ``_handle_success``) which are not part of the public API and can
   break across releases.
2. **threading.RLock blocks the event loop** — pybreaker uses a
   ``threading.RLock`` internally. Acquiring it in an async coroutine
   blocks the entire event loop for the duration.
3. **Half-open probe race** — pybreaker's ``before_call()`` in
   ``CircuitOpenState`` synchronously invokes the wrapped function,
   making it impossible to properly ``await`` an async probe.
4. **Wall-clock time** — pybreaker uses ``datetime.now(utc)`` for
   timeout tracking, which is subject to NTP clock jumps. Our
   implementation uses ``time.monotonic()`` which is NTP-immune.
5. **More code, not less** — the async wrapper around pybreaker was
   ~290 lines (the same as this file) while depending on pybreaker's
   private internals, making it strictly worse.

Our implementation is ~120 lines of logic (excluding docs), uses
``asyncio.Lock`` natively, and has zero external dependencies.

Thread-safety and asyncio notes:

- All mutable state is protected by a single ``asyncio.Lock``.
- In half-open state, exactly ``half_open_max_calls`` probes are
  allowed; additional concurrent callers are rejected immediately.
- Counters are only mutated inside the async lock critical section.
- ``time.monotonic()`` is used for all interval measurements,
  making the implementation immune to NTP clock adjustments.

Configuration via environment variables::

    CB_FAILURE_THRESHOLD = 5  # failures before opening (default: 5)
    CB_RECOVERY_TIMEOUT = 30  # seconds before half-open probe (default: 30)
    CB_HALF_OPEN_MAX = 1  # max concurrent probes in half-open (default: 1)
    CB_ENABLED = true  # enable/disable (default: true)

Usage::

    from src.circuit_breaker import CircuitBreaker

    breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=30)

    result = await breaker.call(
        lambda: ai.generate(prompt="Hello"),
    )
"""

from __future__ import annotations

import asyncio
import enum
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")

_MAX_RETRY_AFTER: float = 3600.0
"""Upper bound for ``retry_after`` to guard against monotonic clock anomalies."""


class CircuitState(enum.Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    """Raised when the circuit breaker is open and rejecting calls.

    Attributes:
        retry_after: Estimated seconds until the circuit may close.
    """

    def __init__(self, retry_after: float, message: str = "") -> None:
        """Initialize with the estimated seconds until the circuit may close."""
        self.retry_after = retry_after
        super().__init__(message or f"Circuit breaker is open. Retry after {retry_after:.1f}s.")


class CircuitBreaker:
    """Async-safe circuit breaker for protecting LLM API calls.

    Tracks consecutive failures and trips the circuit after
    ``failure_threshold`` failures. While open, all calls fail
    immediately with :class:`CircuitOpenError`. After
    ``recovery_timeout`` seconds, one probe call is allowed through
    (half-open state). If it succeeds, the circuit closes; if it
    fails, the circuit re-opens.

    All state is protected by an ``asyncio.Lock`` so the event loop
    is never blocked. ``time.monotonic()`` is used for all interval
    measurement so the circuit is immune to NTP clock adjustments.

    Args:
        failure_threshold: Number of consecutive failures before the
            circuit opens. Default: 5.
        recovery_timeout: Seconds to wait before allowing a probe
            call. Default: 30.
        half_open_max_calls: Maximum concurrent calls allowed in
            half-open state. Default: 1.
        enabled: If ``False``, the breaker is transparent (all calls
            pass through). Default: ``True``.
        name: Friendly name for logging. Default: ``"llm"``.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 1,
        *,
        enabled: bool = True,
        name: str = "llm",
    ) -> None:
        """Initialize the breaker with thresholds, timeouts, and state."""
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.enabled = enabled
        self.name = name

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0.0
        self._half_open_calls = 0
        self._lock = asyncio.Lock()

        self._total_calls = 0
        self._total_failures = 0
        self._total_rejected = 0
        self._total_successes = 0

    @property
    def state(self) -> CircuitState:
        """Current circuit state."""
        return self._state

    def stats(self) -> dict[str, Any]:
        """Return a snapshot of circuit breaker statistics.

        Returns:
            Dict with ``state``, ``failure_count``, counters, and config.
        """
        return {
            "name": self.name,
            "state": self._state.value,
            "enabled": self.enabled,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "total_calls": self._total_calls,
            "total_successes": self._total_successes,
            "total_failures": self._total_failures,
            "total_rejected": self._total_rejected,
        }

    async def call(self, fn: Callable[[], Awaitable[T]]) -> T:
        """Execute ``fn`` through the circuit breaker.

        Args:
            fn: An async callable to protect.

        Returns:
            The result of ``fn()``.

        Raises:
            CircuitOpenError: If the circuit is open and rejecting.
        """
        if not self.enabled:
            return await fn()

        async with self._lock:
            self._total_calls += 1
            self._maybe_transition_to_half_open()
            state = self._state

            if state == CircuitState.OPEN:
                retry_after = self._time_until_half_open()
                self._total_rejected += 1
                logger.warning(
                    "Circuit breaker open — rejecting call",
                    breaker=self.name,
                    retry_after=f"{retry_after:.1f}s",
                    failures=self._failure_count,
                )
                raise CircuitOpenError(retry_after)

            if state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.half_open_max_calls:
                    self._total_rejected += 1
                    raise CircuitOpenError(
                        retry_after=1.0,
                        message="Circuit breaker half-open — probe in progress, rejecting.",
                    )
                self._half_open_calls += 1

        try:
            result = await fn()
        except Exception:
            await self._on_failure()
            raise
        else:
            await self._on_success()
            return result

    async def _on_success(self) -> None:
        """Record a successful call — close the circuit if half-open."""
        async with self._lock:
            self._total_successes += 1
            if self._state == CircuitState.HALF_OPEN:
                logger.info(
                    "Circuit breaker probe succeeded — closing circuit",
                    breaker=self.name,
                )
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._half_open_calls = 0
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0

    async def _on_failure(self) -> None:
        """Record a failed call — open the circuit if threshold met."""
        async with self._lock:
            self._total_failures += 1
            self._failure_count += 1
            self._last_failure_time = time.monotonic()

            if self._state == CircuitState.HALF_OPEN:
                logger.warning(
                    "Circuit breaker probe failed — re-opening circuit",
                    breaker=self.name,
                    failures=self._failure_count,
                )
                self._state = CircuitState.OPEN
                self._half_open_calls = 0
            elif self._state == CircuitState.CLOSED and self._failure_count >= self.failure_threshold:
                logger.error(
                    "Circuit breaker opened — too many failures",
                    breaker=self.name,
                    failures=self._failure_count,
                    threshold=self.failure_threshold,
                    recovery_timeout=self.recovery_timeout,
                )
                self._state = CircuitState.OPEN

    def _maybe_transition_to_half_open(self) -> None:
        """Transition from OPEN to HALF_OPEN if recovery timeout elapsed.

        Must be called while holding ``self._lock``.
        """
        if self._state != CircuitState.OPEN:
            return
        elapsed = time.monotonic() - self._last_failure_time
        if elapsed >= self.recovery_timeout:
            logger.info(
                "Circuit breaker recovery timeout elapsed — entering half-open state",
                breaker=self.name,
                elapsed=f"{elapsed:.1f}s",
            )
            self._state = CircuitState.HALF_OPEN
            self._half_open_calls = 0

    def _time_until_half_open(self) -> float:
        """Seconds remaining until the circuit enters HALF_OPEN.

        Clamped to ``[0, _MAX_RETRY_AFTER]`` to guard against
        anomalous monotonic clock behavior.
        """
        elapsed = time.monotonic() - self._last_failure_time
        return min(max(0.0, self.recovery_timeout - elapsed), _MAX_RETRY_AFTER)

    async def reset(self) -> None:
        """Manually reset the circuit to CLOSED state."""
        async with self._lock:
            previous = self._state
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._half_open_calls = 0
            logger.info(
                "Circuit breaker manually reset",
                breaker=self.name,
                previous_state=previous.value,
            )
