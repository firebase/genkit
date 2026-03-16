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

"""AIO util module for defining and managing AIO utilities."""

import inspect
from collections.abc import Awaitable, Callable
from typing import Any


def ensure_async(fn: Callable[..., Any] | Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
    """Ensure the function is async.

    This function handles three cases:
    1. `fn` is already an async function -> return as-is
    2. `fn` is a sync function that returns a regular value -> wrap in async
    3. `fn` is a sync function (e.g., lambda) that returns a coroutine -> await it

    Args:
        fn: The function to ensure is async.

    Returns:
        The async function.
    """
    is_async = inspect.iscoroutinefunction(fn)
    if is_async:
        return fn

    async def async_wrapper(*args: object, **kwargs: object) -> Any:  # noqa: ANN401
        """Wrap the function in an async function.

        Args:
            *args: The arguments to the function.
            **kwargs: The keyword arguments to the function.

        Returns:
            The result of the function.
        """
        result = fn(*args, **kwargs)
        # Handle case where a sync function (e.g., lambda) returns a coroutine
        if inspect.iscoroutine(result):
            return await result
        return result

    return async_wrapper
