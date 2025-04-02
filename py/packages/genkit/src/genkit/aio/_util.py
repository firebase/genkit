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

import asyncio
from collections.abc import Callable


def ensure_async(fn: Callable) -> Callable:
    """Ensure the function is async.

    Args:
        fn: The function to ensure is async.

    Returns:
        The async function.
    """
    is_async = asyncio.iscoroutinefunction(fn)
    if is_async:
        return fn

    async def async_wrapper(*args, **kwargs):
        """Wrap the function in an async function.

        Args:
            *args: The arguments to the function.
            **kwargs: The keyword arguments to the function.

        Returns:
            The result of the function.
        """
        return fn(*args, **kwargs)

    return async_wrapper
