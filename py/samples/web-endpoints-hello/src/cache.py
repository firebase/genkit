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

"""In-memory TTL response cache for idempotent Genkit flows.

Provides a lightweight async-safe cache that avoids redundant LLM
calls for identical inputs within a configurable time window. This is
critical for production deployments because:

- LLM API calls are **expensive** (~$0.001-0.01 per call).
- Identical prompts produce similar (but not identical) responses.
- Bursty traffic often repeats the same requests.

Design decisions:

- **In-memory** — No external dependency (Redis, Memcached). Suitable
  for single-process deployments (Cloud Run, Lambda). For multi-instance
  deployments, layer a Redis cache in front (see ROADMAP.md).
- **TTL-based** — Entries expire after ``ttl_seconds`` to bound
  staleness. Default 300s (5 min) balances freshness with cost savings.
- **LRU eviction** — ``max_size`` caps memory usage. Least-recently-used
  entries are evicted first when the cache is full.
- **Hash-based keys** — Input models are serialized to JSON and hashed
  with SHA-256 for compact, collision-resistant cache keys.
- **Async-safe** — Uses ``asyncio.Lock`` for safe concurrent access
  (but not multi-process safe; each worker has its own cache).

Why custom instead of ``aiocache``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We evaluated ``aiocache`` and chose to keep a custom implementation
because:

1. **No LRU eviction** — ``aiocache.SimpleMemoryCache`` only supports
   TTL expiration. It does not enforce ``max_size`` or evict
   least-recently-used entries, so memory can grow unbounded.
2. **No stampede prevention** — ``aiocache`` has no built-in request
   coalescing. Without per-key locks, concurrent cache misses for the
   same key trigger duplicate expensive LLM calls (thundering herd).
3. **Weak type hints** — ``aiocache.get()`` returns ``Any``, defeating
   pyright strict mode and requiring ``type: ignore`` annotations.
4. **Same line count** — The ``aiocache`` wrapper was ~270 lines (the
   same as this file) once we added per-key locks, stampede prevention,
   Genkit-specific cache keys, and the ``cached`` decorator. The
   ``aiocache`` dependency added weight with zero net benefit.
5. **``time.monotonic()``** — Our implementation uses monotonic time
   for TTL, which is NTP-immune. ``aiocache`` uses wall-clock time.

Our implementation is ~100 lines of logic (excluding docs), uses
``OrderedDict`` for O(1) LRU, and has zero external dependencies.

Thread-safety and asyncio notes:

- A **global** ``asyncio.Lock`` protects all ``OrderedDict`` mutations
  (get, set, move_to_end, popitem). It is held only for sub-microsecond
  dict operations, never across ``await`` boundaries.
- **Per-key** ``asyncio.Lock`` coalescing ensures that at most one
  coroutine executes the expensive LLM call for a given cache key.
  Other coroutines waiting on the same key block (non-busily) until
  the first one populates the cache, then return the cached result.
  This prevents cache stampedes (thundering-herd problem).
- Hit/miss counters are only mutated inside lock critical sections.

Configuration via environment variables::

    CACHE_TTL = 300  # seconds (default: 300 = 5 minutes)
    CACHE_MAX_SIZE = 1024  # max entries (default: 1024)
    CACHE_ENABLED = true  # enable/disable (default: true)

Usage::

    from src.cache import FlowCache

    cache = FlowCache(ttl_seconds=300, max_size=1024)

    # Cache a flow call
    result = await cache.get_or_call(
        "translate_text",
        input_model,
        lambda: translate_text(input_model),
    )


    # Use as decorator
    @cache.cached("translate_text")
    async def cached_translate(input: TranslateInput) -> TranslationResult:
        return await translate_text(input)
"""

from __future__ import annotations

import asyncio
import dataclasses
import functools
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

import structlog
from pydantic import BaseModel

from .util.hash import make_cache_key

logger = structlog.get_logger(__name__)

T = TypeVar("T")


@dataclasses.dataclass(slots=True)
class _CacheEntry:
    """A single cached value with creation time for TTL checking.

    Attributes:
        value: The cached result.
        created_at: Monotonic timestamp when the entry was stored.
    """

    value: Any
    created_at: float


class FlowCache:
    """In-memory TTL + LRU cache for Genkit flow responses.

    Thread-safe for single-process async use. Each worker process in a
    multi-worker deployment maintains its own independent cache.

    Uses per-key request coalescing to prevent cache stampedes: if
    multiple coroutines request the same key concurrently, only the
    first executes the expensive call; the rest wait and return the
    cached result.

    Args:
        ttl_seconds: Time-to-live in seconds. Entries older than this
            are treated as expired. Default: 300 (5 minutes).
        max_size: Maximum number of entries. When full, the
            least-recently-used entry is evicted. Default: 1024.
        enabled: If ``False``, all cache operations are no-ops.
            Default: ``True``.
    """

    def __init__(
        self,
        ttl_seconds: int = 300,
        max_size: int = 1024,
        *,
        enabled: bool = True,
    ) -> None:
        """Initialize the cache with TTL, max size, and enabled flag."""
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self.enabled = enabled
        self._store: OrderedDict[str, _CacheEntry] = OrderedDict()
        self._lock = asyncio.Lock()
        self._key_locks: dict[str, asyncio.Lock] = {}
        self._hits = 0
        self._misses = 0

    @property
    def hits(self) -> int:
        """Total cache hits since creation."""
        return self._hits

    @property
    def misses(self) -> int:
        """Total cache misses since creation."""
        return self._misses

    @property
    def size(self) -> int:
        """Current number of entries in the cache."""
        return len(self._store)

    @property
    def hit_rate(self) -> float:
        """Cache hit rate as a float between 0.0 and 1.0."""
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    def stats(self) -> dict[str, Any]:
        """Return a snapshot of cache statistics.

        Returns:
            Dict with ``hits``, ``misses``, ``hit_rate``, ``size``,
            ``max_size``, ``ttl_seconds``, and ``enabled``.
        """
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self.hit_rate, 4),
            "size": self.size,
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds,
            "enabled": self.enabled,
        }

    def _get_key_lock(self, key: str) -> asyncio.Lock:
        """Return (or create) a per-key asyncio.Lock for request coalescing.

        This prevents multiple coroutines from concurrently executing
        the same expensive LLM call when the cache is cold or expired
        (cache stampede / thundering-herd problem).
        """
        if key not in self._key_locks:
            self._key_locks[key] = asyncio.Lock()
        return self._key_locks[key]

    async def get_or_call(
        self,
        flow_name: str,
        input_data: BaseModel | dict | str,
        call: Callable[[], Awaitable[T]],
    ) -> T:
        """Return a cached result or execute ``call()`` and cache it.

        Uses per-key request coalescing: if multiple coroutines
        request the same key concurrently, only the first executes
        ``call()``; the rest wait and return the cached result.

        Args:
            flow_name: Logical name for the flow (used in the cache key).
            input_data: The flow's input (Pydantic model, dict, or string).
            call: An async callable that produces the result on cache miss.

        Returns:
            The (possibly cached) result of the flow call.
        """
        if not self.enabled:
            return await call()

        key = make_cache_key(flow_name, input_data)

        # Per-key lock prevents cache stampedes: only the first
        # coroutine for a given key executes call(); others wait.
        async with self._get_key_lock(key):
            now = time.monotonic()

            # Check cache under the global store lock (sub-microsecond).
            async with self._lock:
                entry = self._store.get(key)
                if entry is not None and (now - entry.created_at) < self.ttl_seconds:
                    self._store.move_to_end(key)
                    self._hits += 1
                    logger.debug("Cache hit", flow=flow_name, key=key[:24])
                    return entry.value

            self._misses += 1
            result = await call()

            # Store result under the global store lock.
            async with self._lock:
                self._store[key] = _CacheEntry(value=result, created_at=now)
                self._store.move_to_end(key)
                while len(self._store) > self.max_size:
                    evicted_key, _ = self._store.popitem(last=False)
                    logger.debug("Cache eviction (LRU)", evicted_key=evicted_key[:24])

            return result

    async def invalidate(self, flow_name: str, input_data: BaseModel | dict | str) -> bool:
        """Remove a specific entry from the cache.

        Args:
            flow_name: Flow name used when the entry was cached.
            input_data: The input used when the entry was cached.

        Returns:
            ``True`` if the entry was found and removed.
        """
        key = make_cache_key(flow_name, input_data)
        async with self._lock:
            if key in self._store:
                del self._store[key]
                return True
        return False

    async def clear(self) -> int:
        """Remove all entries from the cache.

        Returns:
            The number of entries that were removed.
        """
        async with self._lock:
            count = len(self._store)
            self._store.clear()
            self._key_locks.clear()
            self._hits = 0
            self._misses = 0
        logger.info("Cache cleared", evicted=count)
        return count

    def cached(self, flow_name: str) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
        """Decorator that caches the result of an async function.

        The first positional argument is used as the cache key input.

        Args:
            flow_name: Logical name for the cached flow.

        Returns:
            A decorator that wraps async functions with caching.

        Usage::

            cache = FlowCache()


            @cache.cached("translate_text")
            async def translate(input: TranslateInput) -> TranslationResult:
                return await translate_text(input)
        """

        def decorator(fn: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
            @functools.wraps(fn)
            async def wrapper(*args: Any, **kwargs: Any) -> T:  # noqa: ANN401 — generic decorator must forward arbitrary args
                input_data = args[0] if args else kwargs.get("input", "")
                return await self.get_or_call(flow_name, input_data, lambda: fn(*args, **kwargs))

            # Expose the cache instance for introspection/testing.
            wrapper.cache = self  # type: ignore[attr-defined] — dynamic attribute on wrapper; safe at runtime
            return wrapper

        return decorator
