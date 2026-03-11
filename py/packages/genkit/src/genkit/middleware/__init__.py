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

Chain ordering: middleware is applied first-in, outermost. The first
middleware in the list wraps around the rest; calls flow in → out.

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

from genkit._core._middleware._augment_with_context import augment_with_context
from genkit._core._middleware._base import (
    BaseMiddleware,
    GenerateHookParams,
    ModelHookParams,
    ToolHookParams,
)
from genkit._core._middleware._download_request_media import download_request_media
from genkit._core._middleware._fallback import fallback
from genkit._core._middleware._retry import retry
from genkit._core._middleware._simulate_system_prompt import simulate_system_prompt
from genkit._core._middleware._validate_support import validate_support

__all__ = [
    'BaseMiddleware',
    'GenerateHookParams',
    'ModelHookParams',
    'ToolHookParams',
    'augment_with_context',
    'download_request_media',
    'fallback',
    'retry',
    'simulate_system_prompt',
    'validate_support',
]
