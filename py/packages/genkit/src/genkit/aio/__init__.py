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

"""Asynchronous utilities for the Genkit framework.

This module provides async utilities used internally by Genkit for handling
concurrent operations, streaming responses, and async/sync interoperability.

Overview:
    Genkit is async-first, leveraging Python's asyncio for concurrent operations.
    This module provides utilities that simplify async patterns used throughout
    the framework, particularly for streaming model responses.

Key Components:
    ┌─────────────────────────────────────────────────────────────────────────┐
    │ Component         │ Description                                         │
    ├───────────────────┼─────────────────────────────────────────────────────┤
    │ Channel           │ AsyncIterator for streaming chunks with a final     │
    │                   │ value (used for streaming model responses)          │
    │ ensure_async()    │ Wrap sync/async functions to ensure async callable  │
    └───────────────────┴─────────────────────────────────────────────────────┘

Example:
    Using Channel for streaming:

    ```python
    from genkit.aio import Channel

    # Create a channel for streaming chunks with a final result
    channel: Channel[str, int] = Channel()


    async def producer():
        for chunk in ['Hello', ' ', 'World']:
            channel.send(chunk)
        channel.close(final_value=len('Hello World'))


    # Consume chunks
    async for chunk in channel:
        print(chunk, end='')

    # Get final value
    result = await channel.result()
    ```

    Using ensure_async:

    ```python
    from genkit.aio import ensure_async


    def sync_fn(x: int) -> int:
        return x * 2


    async_fn = ensure_async(sync_fn)
    result = await async_fn(5)  # Returns 10
    ```

See Also:
    - asyncio documentation: https://docs.python.org/3/library/asyncio.html
"""

from ._util import ensure_async
from .channel import Channel

__all__ = [
    'Channel',
    'ensure_async',
]
