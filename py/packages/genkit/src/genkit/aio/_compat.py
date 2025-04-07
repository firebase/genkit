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

"""Compatibility layer for asyncio.

This module provides a compatibility layer for asyncio.

The asyncio.wait_for function was changed in Python 3.11 to raise a TimeoutError
instead of an asyncio.TimeoutError. This module provides a compatibility layer
for this change among others.

See: https://docs.python.org/3/library/asyncio-task.html#asyncio.wait_for
"""

import asyncio
import sys
from typing import TypeVar

T = TypeVar('T')


async def wait_for_310(fut: asyncio.Future[T], timeout: float | None = None) -> T:
    """Wait for a future to complete.

    This is a compatibility layer for asyncio.wait_for that raises a TimeoutError
    instead of an asyncio.TimeoutError.

    This is necessary because the behavior of asyncio.wait_for changed in Python
    3.11.

    See: https://docs.python.org/3/library/asyncio-task.html#asyncio.wait_for

    Args:
        fut: The future to wait for.
        timeout: The timeout in seconds.

    Returns:
        The result of the future.
    """
    try:
        return await asyncio.wait_for(fut, timeout)
    except asyncio.TimeoutError as e:
        raise TimeoutError() from e


if sys.version_info < (3, 11):
    wait_for = wait_for_310
else:
    wait_for = asyncio.wait_for
