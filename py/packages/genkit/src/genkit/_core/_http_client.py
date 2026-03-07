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

"""Shared HTTP client utilities for Genkit plugins."""

import asyncio
import threading
import weakref
from collections.abc import MutableMapping
from typing import Any

import httpx

from genkit._core._logger import get_logger

logger = get_logger(__name__)

# event_loop -> (cache_key -> client)
_loop_clients: MutableMapping[asyncio.AbstractEventLoop, dict[str, httpx.AsyncClient]] = weakref.WeakKeyDictionary()
_cache_lock = threading.Lock()


def get_cached_client(
    cache_key: str,
    headers: dict[str, str] | None = None,
    timeout: httpx.Timeout | float | None = None,
    **httpx_kwargs: Any,
) -> httpx.AsyncClient:
    """Get or create a cached httpx.AsyncClient for the current event loop."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError as e:
        raise RuntimeError('get_cached_client() must be called from an async context') from e

    with _cache_lock:
        loop_cache = _loop_clients.setdefault(loop, {})

        if cache_key in loop_cache:
            client = loop_cache[cache_key]
            if not client.is_closed:
                return client
            del loop_cache[cache_key]

        if timeout is None:
            timeout = httpx.Timeout(60.0, connect=10.0)
        elif isinstance(timeout, (int, float)):
            timeout = httpx.Timeout(float(timeout))

        client = httpx.AsyncClient(headers=headers or {}, timeout=timeout, **httpx_kwargs)
        loop_cache[cache_key] = client
        return client


async def close_cached_clients(cache_key: str | None = None) -> None:
    """Close and remove cached clients for the current event loop."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return

    clients_to_close: dict[str, httpx.AsyncClient] = {}

    with _cache_lock:
        if loop not in _loop_clients:
            return

        loop_cache = _loop_clients[loop]

        if cache_key is not None:
            if cache_key in loop_cache:
                clients_to_close[cache_key] = loop_cache.pop(cache_key)
        else:
            clients_to_close.update(loop_cache)
            loop_cache.clear()

    for key, client in clients_to_close.items():
        try:
            await client.aclose()
        except Exception as e:
            logger.warning('Failed to close cached client', cache_key=key, error=e)


def clear_client_cache() -> None:
    """Clear all cached clients (for testing). Does NOT close clients."""
    with _cache_lock:
        _loop_clients.clear()
