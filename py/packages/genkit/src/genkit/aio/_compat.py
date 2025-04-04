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

"""AsyncIO compatibility utilities."""

import asyncio
from collections.abc import Awaitable
from typing import TypeVar

_T = TypeVar('_T')


async def async_wait_for(fut: Awaitable[_T], timeout: float | None) -> _T:
    """Cross-version compatibility wrapper for asyncio.wait_for.

    This helps abstract potential differences in timeout/cancellation behavior
    across Python versions.

    Args:
        fut: The awaitable to wait for.
        timeout: The timeout duration in seconds.

    Returns:
        The result of the awaitable.

    Raises:
        asyncio.TimeoutError: If the timeout occurs.
        asyncio.CancelledError: If the operation is cancelled.
    """
    try:
        return await asyncio.wait_for(fut, timeout)
    except asyncio.CancelledError:
        raise
    except asyncio.TimeoutError:
        raise
    except Exception as e:
        raise e
