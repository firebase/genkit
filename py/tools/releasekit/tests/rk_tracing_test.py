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

"""Tests for releasekit.tracing — OpenTelemetry tracing.

Exercises the tracer factory, span decorator, and coroutine detection.
Without a configured TracerProvider, OTel’s default no-op provider is
used, so spans are silently discarded.
"""

from __future__ import annotations

import asyncio

from releasekit.tracing import (
    _is_coroutine_function,
    get_tracer,
    span,
)

# get_tracer


class TestGetTracer:
    """Tests for get_tracer()."""

    def test_returns_tracer(self) -> None:
        """Returns a tracer (no-op when OTel is absent)."""
        tracer = get_tracer('test_module')
        assert tracer is not None

    def test_caches_tracer(self) -> None:
        """Same name returns the same tracer instance."""
        t1 = get_tracer('cached_module')
        t2 = get_tracer('cached_module')
        assert t1 is t2

    def test_different_names_different_tracers(self) -> None:
        """Different names may return different tracers."""
        t1 = get_tracer('module_a_unique')
        t2 = get_tracer('module_b_unique')
        # They could be the same no-op instance, but the cache keys differ.
        assert get_tracer('module_a_unique') is t1
        assert get_tracer('module_b_unique') is t2

    def test_default_name(self) -> None:
        """Default tracer name works."""
        tracer = get_tracer()
        assert tracer is not None


# span decorator


class TestSpanDecorator:
    """Tests for the @span decorator."""

    def test_sync_function(self) -> None:
        """Decorated sync function works normally."""

        @span('test_sync')
        def add(a: int, b: int) -> int:
            """Add."""
            return a + b

        assert add(2, 3) == 5

    def test_async_function(self) -> None:
        """Decorated async function works normally."""

        @span('test_async')
        async def add(a: int, b: int) -> int:
            """Add."""
            return a + b

        result = asyncio.run(add(2, 3))
        assert result == 5

    def test_sync_with_attributes(self) -> None:
        """Decorated sync function with attributes works."""

        @span('test_attrs', attributes={'algo': 'bfs'})
        def compute() -> str:
            """Compute."""
            return 'done'

        assert compute() == 'done'

    def test_async_with_attributes(self) -> None:
        """Decorated async function with attributes works."""

        @span('test_attrs_async', attributes={'algo': 'bfs'})
        async def compute() -> str:
            """Compute."""
            return 'done'

        assert asyncio.run(compute()) == 'done'

    def test_preserves_function_name(self) -> None:
        """Decorator preserves the original function name."""

        @span('named_span')
        def my_function() -> None:
            """My function."""
            pass

        # When OTel is not available, the function is returned as-is.
        # When OTel IS available, functools.wraps preserves __name__.
        assert my_function.__name__ == 'my_function'

    def test_sync_exception_propagates(self) -> None:
        """Exceptions in sync functions propagate through the decorator."""

        @span('failing_sync')
        def fail() -> None:
            """Fail."""
            raise ValueError('sync boom')

        try:
            fail()
            raise AssertionError('Should have raised')
        except ValueError as e:
            assert str(e) == 'sync boom'

    def test_async_exception_propagates(self) -> None:
        """Exceptions in async functions propagate through the decorator."""

        @span('failing_async')
        async def fail() -> None:
            """Fail."""
            raise ValueError('async boom')

        try:
            asyncio.run(fail())
            raise AssertionError('Should have raised')
        except ValueError as e:
            assert str(e) == 'async boom'


# _is_coroutine_function


class TestIsCoroutineFunction:
    """Tests for _is_coroutine_function helper."""

    def test_sync_function(self) -> None:
        """Sync function returns False."""

        def sync_fn() -> None:
            """Sync fn."""
            pass

        assert _is_coroutine_function(sync_fn) is False

    def test_async_function(self) -> None:
        """Async function returns True."""

        async def async_fn() -> None:
            """Async fn."""
            pass

        assert _is_coroutine_function(async_fn) is True

    def test_lambda(self) -> None:
        """Lambda returns False."""
        assert _is_coroutine_function(lambda: None) is False
