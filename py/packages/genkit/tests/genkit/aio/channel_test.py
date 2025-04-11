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

"""Tests for genkit.aio.Channel."""

from __future__ import annotations

import asyncio

import pytest

from genkit.aio import Channel


@pytest.mark.asyncio
async def test_channel_send_and_receive():
    """Tests sending a value and receiving it from the channel."""
    channel = Channel()
    channel.send('hello')
    received = await channel.__anext__()
    assert received == 'hello'


@pytest.mark.asyncio
async def test_channel_empty():
    """Tests that __anext__ waits for a value when the channel is empty."""
    close_future = asyncio.Future()
    channel = Channel()
    channel.set_close_future(close_future)

    async def async_send():
        channel.send('world')

    send_task = asyncio.create_task(async_send())
    receive_task = asyncio.create_task(channel.__anext__())
    assert not receive_task.done()
    await send_task
    received = await receive_task
    assert received == 'world'


@pytest.mark.asyncio
async def test_channel_close():
    """Tests that the channel closes correctly."""
    channel = Channel()
    close_future = asyncio.Future()
    channel.set_close_future(close_future)
    close_future.set_result(None)
    with pytest.raises(StopAsyncIteration):
        await channel.__anext__()


@pytest.mark.asyncio
async def test_channel_multiple_send_receive():
    """Tests sending and receiving multiple values."""
    channel = Channel()
    values = ['one', 'two', 'three']
    for value in values:
        channel.send(value)
    received_values = [await channel.__anext__() for _ in range(len(values))]
    assert received_values == values


@pytest.mark.asyncio
async def test_channel_aiter_anext():
    """Tests the asynchronous iterator functionality."""
    close_future = asyncio.Future()
    channel = Channel()
    channel.set_close_future(close_future)
    values = ['a', 'b', 'c']
    for value in values:
        channel.send(value)
    close_future.set_result('done')
    received_values = []
    async for item in channel:
        received_values.append(item)
    assert received_values == values
    assert (await channel.closed) == 'done'


@pytest.mark.asyncio
async def test_channel_invalid_timeout():
    """Tests that an invalid timeout value raises ValueError."""
    with pytest.raises(ValueError):
        Channel(timeout=-0.1)


@pytest.mark.asyncio
async def test_channel_timeout():
    """Tests that the channel raises TimeoutError when timeout is reached."""
    channel = Channel(timeout=0.1)
    with pytest.raises(TimeoutError):
        await channel.__anext__()


@pytest.mark.asyncio
async def test_channel_no_timeout():
    """Tests that the channel doesn't timeout when timeout=None."""
    channel = Channel(timeout=None)
    anext_task = asyncio.create_task(channel.__anext__())
    await asyncio.sleep(0.1)
    assert not anext_task.done()
    channel.send('value')
    result = await anext_task
    assert result == 'value'


@pytest.mark.asyncio
async def test_channel_timeout_with_close_future():
    """Tests timeout with an active close_future."""
    channel = Channel(timeout=0.1)
    close_future = asyncio.Future()
    channel.set_close_future(close_future)
    with pytest.raises(TimeoutError):
        await channel.__anext__()
    close_future.set_result(None)
    with pytest.raises(StopAsyncIteration):
        await channel.__anext__()


@pytest.mark.asyncio
async def test_channel_invalid_timeout_negative():
    """Tests that negative timeout values raise ValueError."""
    with pytest.raises(ValueError) as excinfo:
        Channel(timeout=-1.0)
    assert 'Timeout must be non-negative' in str(excinfo.value)


@pytest.mark.asyncio
async def test_channel_timeout_race_condition():
    """Tests the behavior when a value arrives just as the timeout occurs."""
    channel = Channel(timeout=0.2)

    async def delayed_send():
        await asyncio.sleep(0.15)
        channel.send('just in time')

    send_task = asyncio.create_task(delayed_send())
    result = await channel.__anext__()
    assert result == 'just in time'
    await send_task
