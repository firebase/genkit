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

"""Tests for HTTP client caching."""

import asyncio

import httpx
import pytest

from genkit._core._http_client import (
    _loop_clients,
    clear_client_cache,
    close_cached_clients,
    get_cached_client,
)


@pytest.fixture(autouse=True)
def clear_cache() -> None:
    clear_client_cache()


@pytest.mark.asyncio
async def test_returns_httpx_async_client() -> None:
    client = get_cached_client(cache_key='test')
    assert isinstance(client, httpx.AsyncClient)


@pytest.mark.asyncio
async def test_client_cached_per_event_loop() -> None:
    client1 = get_cached_client(cache_key='test')
    client2 = get_cached_client(cache_key='test')
    assert client1 is client2


@pytest.mark.asyncio
async def test_different_cache_keys_get_different_clients() -> None:
    client1 = get_cached_client(cache_key='plugin-a')
    client2 = get_cached_client(cache_key='plugin-b')
    assert client1 is not client2


@pytest.mark.asyncio
async def test_client_has_correct_headers() -> None:
    headers = {'Authorization': 'Bearer test-token', 'X-Custom': 'value'}
    client = get_cached_client(cache_key='test', headers=headers)
    assert client.headers.get('Authorization') == 'Bearer test-token'
    assert client.headers.get('X-Custom') == 'value'


@pytest.mark.asyncio
async def test_client_has_correct_timeout_float() -> None:
    client = get_cached_client(cache_key='test', timeout=30.0)
    assert client.timeout.read == 30.0
    assert client.timeout.connect == 30.0


@pytest.mark.asyncio
async def test_client_has_correct_timeout_object() -> None:
    timeout = httpx.Timeout(60.0, connect=10.0)
    client = get_cached_client(cache_key='test', timeout=timeout)
    assert client.timeout.read == 60.0
    assert client.timeout.connect == 10.0


@pytest.mark.asyncio
async def test_default_timeout_applied() -> None:
    client = get_cached_client(cache_key='test')
    assert client.timeout.read == 60.0
    assert client.timeout.connect == 10.0


@pytest.mark.asyncio
async def test_closed_client_gets_replaced() -> None:
    client1 = get_cached_client(cache_key='test')
    await client1.aclose()
    assert client1.is_closed

    client2 = get_cached_client(cache_key='test')
    assert client2 is not client1
    assert not client2.is_closed


@pytest.mark.asyncio
async def test_client_stored_in_cache() -> None:
    clear_client_cache()
    _ = get_cached_client(cache_key='test')
    loop = asyncio.get_running_loop()
    assert loop in _loop_clients
    assert 'test' in _loop_clients[loop]


def test_raises_without_running_event_loop() -> None:
    with pytest.raises(RuntimeError, match='must be called from an async context'):
        get_cached_client(cache_key='test')


@pytest.mark.asyncio
async def test_close_specific_client() -> None:
    _ = get_cached_client(cache_key='to-close')
    _ = get_cached_client(cache_key='keep')

    await close_cached_clients('to-close')

    loop = asyncio.get_running_loop()
    assert 'to-close' not in _loop_clients[loop]
    assert 'keep' in _loop_clients[loop]


@pytest.mark.asyncio
async def test_close_all_clients_in_loop() -> None:
    _ = get_cached_client(cache_key='client-a')
    _ = get_cached_client(cache_key='client-b')

    await close_cached_clients()

    loop = asyncio.get_running_loop()
    assert loop not in _loop_clients or len(_loop_clients[loop]) == 0


@pytest.mark.asyncio
async def test_close_nonexistent_key_is_noop() -> None:
    _ = get_cached_client(cache_key='exists')
    await close_cached_clients('does-not-exist')


@pytest.mark.asyncio
async def test_close_when_no_clients_is_noop() -> None:
    await close_cached_clients()


@pytest.mark.asyncio
async def test_clear_removes_all_cached_clients() -> None:
    _ = get_cached_client(cache_key='client-a')
    _ = get_cached_client(cache_key='client-b')
    clear_client_cache()
    assert len(_loop_clients) == 0


def test_clear_when_empty_is_noop() -> None:
    clear_client_cache()
    clear_client_cache()


@pytest.mark.asyncio
async def test_cache_uses_current_event_loop_as_key() -> None:
    _ = get_cached_client(cache_key='test')
    loop = asyncio.get_running_loop()
    assert loop in _loop_clients


@pytest.mark.asyncio
async def test_multiple_cache_keys_same_loop() -> None:
    client_a = get_cached_client(cache_key='plugin-a')
    client_b = get_cached_client(cache_key='plugin-b')
    client_c = get_cached_client(cache_key='plugin-c')

    loop = asyncio.get_running_loop()
    assert len(_loop_clients[loop]) == 3
    assert _loop_clients[loop]['plugin-a'] is client_a
    assert _loop_clients[loop]['plugin-b'] is client_b
    assert _loop_clients[loop]['plugin-c'] is client_c
