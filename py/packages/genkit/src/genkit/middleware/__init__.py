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

This module provides middleware that can be used to modify model requests and
responses, add retry logic, implement fallback behavior, and more.

Chain ordering: middleware is applied first-in, outermost. The first middleware
in the list wraps around the rest; calls flow in → out.

Example usage:
    from genkit import Genkit, MiddlewareRef
    from genkit.middleware import BaseMiddleware

    class MyMw(BaseMiddleware):
        ...

    ai = Genkit()

    response = await ai.generate(
        model="gemini-pro",
        prompt="Hello",
        use=[
            MyMw(),
            MiddlewareRef(name="retry", config={"max_retries": 3}),
        ],
    )
"""

from genkit._core._middleware._augment_with_context import augment_with_context
from genkit._core._middleware._base import (
    BaseMiddleware,
    GenerateMiddleware,
    MiddlewareFnOptions,
    generate_middleware,
)
from genkit._core._model import GenerateHookParams, ModelHookParams, ToolHookParams
from genkit._core._middleware._download_request_media import (
    download_request_media,
)
from genkit._core._middleware._fallback import fallback
from genkit._core._middleware._retry import retry
from genkit._core._middleware._simulate_system_prompt import (
    simulate_system_prompt,
)
from genkit._core._middleware._validate_support import validate_support
from genkit._core._middleware._runtime import MiddlewareRuntime
from genkit._core._plugin import middleware_plugin

__all__ = [
    'BaseMiddleware',
    'GenerateHookParams',
    'GenerateMiddleware',
    'MiddlewareFnOptions',
    'MiddlewareRuntime',
    'ModelHookParams',
    'ToolHookParams',
    'augment_with_context',
    'download_request_media',
    'fallback',
    'generate_middleware',
    'middleware_plugin',
    'retry',
    'simulate_system_prompt',
    'validate_support',
]
