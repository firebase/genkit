# Copyright 2025 Google LLC
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

"""Tests for aio utility functions."""

import pytest

from genkit.aio._util import ensure_async


@pytest.mark.asyncio
async def test_ensure_async_with_sync_function() -> None:
    """Test that sync functions are wrapped correctly."""

    def sync_fn(x: int) -> int:
        return x * 2

    async_fn = ensure_async(sync_fn)
    result = await async_fn(5)
    assert result == 10


@pytest.mark.asyncio
async def test_ensure_async_with_async_function() -> None:
    """Test that async functions are returned as-is."""

    async def async_fn(x: int) -> int:
        return x * 2

    wrapped = ensure_async(async_fn)
    assert wrapped is async_fn  # Should be the same function
    result = await wrapped(5)
    assert result == 10


@pytest.mark.asyncio
async def test_ensure_async_with_lambda_returning_coroutine() -> None:
    """Test that lambdas returning coroutines are handled correctly.

    This is the key fix: when a sync function (lambda) returns a coroutine,
    ensure_async should await it.
    """

    async def async_operation(x: int) -> int:
        return x * 2

    # Lambda that returns a coroutine (common pattern with ai.run())
    lambda_fn = lambda: async_operation(5)  # noqa: E731

    async_fn = ensure_async(lambda_fn)
    result = await async_fn()
    assert result == 10


@pytest.mark.asyncio
async def test_ensure_async_with_lambda_returning_value() -> None:
    """Test that lambdas returning regular values work correctly."""
    lambda_fn = lambda x: x * 2  # noqa: E731

    async_fn = ensure_async(lambda_fn)
    result = await async_fn(5)
    assert result == 10


@pytest.mark.asyncio
async def test_ensure_async_with_nested_coroutine_pattern() -> None:
    """Test the nested pattern used in ai.run() with recursive async functions."""

    async def recursive_fn(depth: int) -> str:
        if depth <= 0:
            return 'done'
        # Simulate what ai.run() does with a lambda
        wrapped = ensure_async(lambda: recursive_fn(depth - 1))
        return f'level-{depth}:' + await wrapped()

    result = await recursive_fn(3)
    assert result == 'level-3:level-2:level-1:done'
