# Copyright 2025 Google LLC
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
