# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Asyncio helpers."""

from asyncio import FIRST_COMPLETED, Future, Queue, ensure_future, wait
from typing import Any, AsyncIterator


class Channel[T]:
    """
    An asynchronous channel for sending and receiving values.

    This class provides an asynchronous queue-like interface, allowing
    values to be sent and received between different parts of an
    asynchronous program. It also supports closing the channel,
    which will signal to any receivers that no more values will be sent.
    """

    def __init__(self) -> None:
        """
        Initializes a new Channel.

        The channel is initialized with an internal queue to store values,
        a future to signal when the channel is closed, and an optional
        close future.
        """
        self.queue = Queue()
        self.closed = Future()
        return

    def __aiter__(self) -> AsyncIterator[T]:
        """
        Returns the asynchronous iterator for the channel.
        """
        return self

    async def __anext__(self) -> T:
        """
        Retrieves the next value from the channel.

        If the queue is not empty, the value is returned immediately.
        Otherwise, it waits until a value is available or the channel is closed.

        Raises:
            StopAsyncIteration: If the channel is closed and no more values
                                are available.

        Returns:
            Any: The next value from the channel.
        """
        if not self.queue.empty():
            return self.queue.get_nowait()
        pop = ensure_future(self.__pop())
        if not self.__close_future:
            return await pop
        finished, _ = await wait(
            [pop, self.__close_future], return_when=FIRST_COMPLETED
        )
        if pop in finished:
            return pop.result()
        if self.__close_future in finished:
            raise StopAsyncIteration()
        return await pop

    def send(self, value: T):
        """
        Sends a value into the channel.

        The value is added to the internal queue.

        Args:
            value: The value to send.
        """
        return self.queue.put_nowait(value)

    def set_close_future(self, future: Future):
        """
        Sets a future that, when completed, will close the channel.

        Args:
            f (Future): The future to set.
        """
        self.__close_future = ensure_future(future)
        self.__close_future.add_done_callback(
            lambda v: self.closed.set_result(v.result())
        )

    async def __pop(self) -> T:
        """
        Asynchronously retrieves a value from the queue.

        This method waits until a value is available in the queue.

        Raises:
            StopAsyncIteration: If a None value is retrieved,
                                indicating the channel is closed.

        Returns:
            Any: The retrieved value.
        """
        r = await self.queue.get()
        self.queue.task_done()
        if not r:
            raise StopAsyncIteration

        return r
