# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

import asyncio

import pytest
from genkit.core.aio import Channel


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
