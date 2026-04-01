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

"""retry middleware."""

import asyncio
import random
from collections.abc import Awaitable, Callable

from genkit._core._error import GenkitError, StatusName
from genkit._core._model import ModelResponse

from ._base import BaseMiddleware, ModelHookParams
from ._utils import _DEFAULT_RETRY_STATUSES


def retry(
    max_retries: int = 3,
    statuses: list[StatusName] | None = None,
    initial_delay_ms: int = 1000,
    max_delay_ms: int = 60000,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    on_error: Callable[[Exception, int], None] | None = None,
) -> BaseMiddleware:
    """Middleware that retries failed requests with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts (default: 3).
        statuses: List of status codes that trigger retry (default: UNAVAILABLE,
            DEADLINE_EXCEEDED, RESOURCE_EXHAUSTED, ABORTED, INTERNAL).
        initial_delay_ms: Initial delay between retries in milliseconds (default: 1000).
        max_delay_ms: Maximum delay between retries in milliseconds (default: 60000).
        backoff_factor: Multiplier for delay after each retry (default: 2.0).
        jitter: Whether to add random jitter to delays (default: True).
        on_error: Optional callback called on each retry attempt with (error, attempt).

    Returns:
        Middleware that implements retry logic.
    """
    return _RetryMiddleware(
        max_retries=max_retries,
        statuses=statuses or _DEFAULT_RETRY_STATUSES,
        initial_delay_ms=initial_delay_ms,
        max_delay_ms=max_delay_ms,
        backoff_factor=backoff_factor,
        jitter=jitter,
        on_error=on_error,
    )


class _RetryMiddleware(BaseMiddleware):
    def __init__(
        self,
        max_retries: int = 3,
        statuses: list[StatusName] | None = None,
        initial_delay_ms: int = 1000,
        max_delay_ms: int = 60000,
        backoff_factor: float = 2.0,
        jitter: bool = True,
        on_error: Callable[[Exception, int], None] | None = None,
    ) -> None:
        self._max_retries = max_retries
        self._statuses = statuses or _DEFAULT_RETRY_STATUSES
        self._initial_delay_ms = initial_delay_ms
        self._max_delay_ms = max_delay_ms
        self._backoff_factor = backoff_factor
        self._jitter = jitter
        self._on_error = on_error

    async def wrap_model(
        self,
        params: ModelHookParams,
        next_fn: Callable[[ModelHookParams], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        last_error: Exception | None = None
        current_delay_ms: float = float(self._initial_delay_ms)

        for attempt in range(int(self._max_retries) + 1):
            try:
                return await next_fn(params)
            except Exception as e:
                last_error = e

                if attempt < self._max_retries:
                    should_retry = isinstance(e, GenkitError) and e.status in self._statuses

                    if should_retry:
                        if self._on_error:
                            self._on_error(e, attempt + 1)

                        delay = current_delay_ms
                        if self._jitter:
                            delay += random.random() * delay

                        delay = min(delay, float(self._max_delay_ms))
                        await asyncio.sleep(delay / 1000.0)
                        current_delay_ms = min(
                            current_delay_ms * self._backoff_factor,
                            float(self._max_delay_ms),
                        )
                        continue

                raise

        raise last_error or RuntimeError('Retry loop completed without result')
