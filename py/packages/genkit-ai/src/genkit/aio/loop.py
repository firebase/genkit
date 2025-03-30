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

import asyncio
import threading
from collections.abc import Callable, AsyncIterable, Iterable


def create_loop():
    """Creates (or gets current) event loop."""
    try:
        return asyncio.get_event_loop()
    except:
        return asyncio.new_event_loop()


def run_async(loop: asyncio.AbstractEventLoop, fn: Callable):
    """Schedules the callable on the even loop and blocks until it completes."""
    if loop.is_running():
        output = None
        error = None
        lock = threading.Lock()
        lock.acquire()

        async def run_fn():
            nonlocal lock
            nonlocal output
            nonlocal error
            try:
                output = await fn()
                return output
            except Exception as e:
                error = e
            finally:
                lock.release()

        asyncio.run_coroutine_threadsafe(run_fn(), loop=loop)

        def wait_for_done():
            nonlocal lock
            lock.acquire()

        thread = threading.Thread(target=wait_for_done)
        thread.start()
        thread.join()

        if error:
            raise error

        return output
    else:
        return loop.run_until_complete(fn())

def iter_over_async(ait: AsyncIterable, loop: asyncio.AbstractEventLoop) -> Iterable:
    """Iterates over an AsyncIterable as a sync Iterable using the provided event loop."""
    ait = ait.__aiter__()

    async def get_next():
        try:
            obj = await ait.__anext__()
            return False, obj
        except StopAsyncIteration:
            return True, None

    while True:
        done, obj = loop.run_until_complete(get_next())
        if done:
            break
        yield obj

