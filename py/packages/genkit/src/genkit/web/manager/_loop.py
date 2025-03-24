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

"""Utility functions to work with the loop."""

import asyncio
from collections.abc import Coroutine
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


def run_loop(coro: Coroutine[Any, Any, Any], *args: Any, **kwargs: Any) -> Any:
    """Runs a coroutine using uvloop if available.

    Otherwise uses plain `asyncio.run`.

    Args:
        coro: The asynchronous coroutine to run.
        *args: Additional positional arguments to pass to asyncio.run.
        **kwargs: Additional keyword arguments to pass to asyncio.run.
    """
    try:
        import uvloop

        logger.debug('✅ Using uvloop (recommended)')
        return uvloop.run(coro, *args, **kwargs)
    except ImportError as e:
        logger.debug(
            '❓ Using asyncio (install uvloop for better performance)',
            error=e,
        )
        return asyncio.run(coro, *args, **kwargs)
