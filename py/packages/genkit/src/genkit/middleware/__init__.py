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

"""Middleware for Genkit model calls.

This module provides middleware functions that can be used to modify
model requests and responses, add retry logic, implement fallback
behavior, and more.

Example usage:
    from genkit import Genkit
    from genkit.middleware import retry, fallback

    ai = Genkit()

    response = await ai.generate(
        model="gemini-pro",
        prompt="Hello",
        use=[
            retry(max_retries=3),
            fallback(ai, models=["gemini-flash"]),
        ],
    )
"""

from genkit._ai._middleware import (
    CONTEXT_PREFACE,
    DEFAULT_FALLBACK_STATUSES,
    DEFAULT_RETRY_STATUSES,
    augment_with_context,
    download_request_media,
    retry,
    simulate_system_prompt,
    validate_support,
)
from collections.abc import Callable

from genkit._ai._middleware import fallback as _fallback_impl
from genkit._ai._model import ModelMiddleware
from genkit._core._error import GenkitError, StatusName


def fallback(
    ai: object,
    models: list[str],
    statuses: list[StatusName] | None = None,
    on_error: Callable[[GenkitError], None] | None = None,
) -> ModelMiddleware:
    """Middleware that falls back to alternative models on failure."""
    return _fallback_impl(ai.registry, models, statuses, on_error)

__all__ = [
    'CONTEXT_PREFACE',
    'DEFAULT_FALLBACK_STATUSES',
    'DEFAULT_RETRY_STATUSES',
    'augment_with_context',
    'download_request_media',
    'fallback',
    'retry',
    'simulate_system_prompt',
    'validate_support',
]
