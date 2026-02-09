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

"""Tests for `FlowCache` in-memory TTL response cache."""

import asyncio
from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel

from src.cache import FlowCache


class FakeInput(BaseModel):
    """Fake Pydantic model used as cache input in tests."""

    text: str = "hello"
    lang: str = "en"


@pytest.fixture
def cache() -> FlowCache:
    """Create a FlowCache with short TTL and small max size."""
    return FlowCache(ttl_seconds=10, max_size=5, enabled=True)


@pytest.fixture
def disabled_cache() -> FlowCache:
    """Create a disabled FlowCache that never caches."""
    return FlowCache(ttl_seconds=10, max_size=5, enabled=False)


class TestFlowCache:
    """Tests for `FlowCache`."""

    @pytest.mark.asyncio
    async def test_cache_hit(self, cache: FlowCache) -> None:
        """Verify cache returns stored value on hit."""
        call = AsyncMock(return_value="result")
        r1 = await cache.get_or_call("f", FakeInput(), call)
        r2 = await cache.get_or_call("f", FakeInput(), call)
        assert r1 == r2 == "result"
        assert call.await_count == 1
        assert cache.hits == 1
        assert cache.misses == 1

    @pytest.mark.asyncio
    async def test_cache_miss_different_input(self, cache: FlowCache) -> None:
        """Verify different inputs produce separate cache entries."""
        call = AsyncMock(side_effect=["a", "b"])
        r1 = await cache.get_or_call("f", FakeInput(text="x"), call)
        r2 = await cache.get_or_call("f", FakeInput(text="y"), call)
        assert r1 == "a"
        assert r2 == "b"
        assert call.await_count == 2

    @pytest.mark.asyncio
    async def test_ttl_expiry(self) -> None:
        """Verify expired entries are evicted and re-fetched."""
        cache = FlowCache(ttl_seconds=1, max_size=10)
        call = AsyncMock(side_effect=["old", "new"])
        await cache.get_or_call("f", FakeInput(), call)
        await asyncio.sleep(1.1)
        r2 = await cache.get_or_call("f", FakeInput(), call)
        assert r2 == "new"
        assert call.await_count == 2

    @pytest.mark.asyncio
    async def test_lru_eviction(self) -> None:
        """Verify LRU eviction keeps cache within max_size."""
        cache = FlowCache(ttl_seconds=60, max_size=3)
        for i in range(5):
            await cache.get_or_call("f", f"input_{i}", AsyncMock(return_value=i))
        assert cache.size == 3

    @pytest.mark.asyncio
    async def test_disabled_cache_always_calls(self, disabled_cache: FlowCache) -> None:
        """Verify disabled cache always invokes the callable."""
        call = AsyncMock(return_value="r")
        await disabled_cache.get_or_call("f", FakeInput(), call)
        await disabled_cache.get_or_call("f", FakeInput(), call)
        assert call.await_count == 2

    @pytest.mark.asyncio
    async def test_invalidate(self, cache: FlowCache) -> None:
        """Verify invalidate removes a cached entry."""
        call = AsyncMock(return_value="r")
        await cache.get_or_call("f", FakeInput(), call)
        removed = await cache.invalidate("f", FakeInput())
        assert removed is True
        assert cache.size == 0

    @pytest.mark.asyncio
    async def test_invalidate_missing(self, cache: FlowCache) -> None:
        """Verify invalidate returns False for missing entries."""
        removed = await cache.invalidate("f", FakeInput())
        assert removed is False

    @pytest.mark.asyncio
    async def test_clear(self, cache: FlowCache) -> None:
        """Verify clear removes all entries and resets stats."""
        for i in range(3):
            await cache.get_or_call("f", f"input_{i}", AsyncMock(return_value=i))
        count = await cache.clear()
        assert count == 3
        assert cache.size == 0
        assert cache.hits == 0

    @pytest.mark.asyncio
    async def test_stats(self, cache: FlowCache) -> None:
        """Verify stats returns correct hit/miss/size counters."""
        call = AsyncMock(return_value="r")
        await cache.get_or_call("f", FakeInput(), call)
        await cache.get_or_call("f", FakeInput(), call)
        stats = cache.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["size"] == 1
        assert stats["hit_rate"] == 0.5

    @pytest.mark.asyncio
    async def test_cached_decorator(self) -> None:
        """Verify the @cached decorator caches repeated calls."""
        cache = FlowCache(ttl_seconds=60, max_size=10)
        call_count = 0

        @cache.cached("my_flow")
        async def my_func(inp: str) -> str:
            nonlocal call_count
            call_count += 1
            return f"result_{inp}"

        r1 = await my_func("hello")
        r2 = await my_func("hello")
        assert r1 == r2 == "result_hello"
        assert call_count == 1

    def test_hit_rate_empty(self, cache: FlowCache) -> None:
        """Verify hit_rate is 0.0 on a fresh cache."""
        assert cache.hit_rate == 0.0
