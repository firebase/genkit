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

"""Genkit FastAPI lifespan (deprecated)."""

import warnings
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from starlette.types import ASGIApp, Lifespan

from genkit.ai import Genkit


def genkit_lifespan(ai: Genkit) -> Lifespan[ASGIApp]:
    """Create a FastAPI lifespan that registers with Genkit Dev UI.

    .. deprecated::
        ``genkit_lifespan()`` is no longer needed. The Dev UI reflection server
        now starts automatically in a background thread when ``GENKIT_ENV=dev``
        is set, regardless of the web framework used.

        Remove ``lifespan=genkit_lifespan(ai)`` from your ``FastAPI(...)`` call.

    Args:
        ai: The Genkit instance (unused, kept for API compatibility).

    Returns:
        A no-op lifespan context manager.
    """
    warnings.warn(
        'genkit_lifespan() is deprecated and no longer needed. '
        'The Dev UI reflection server starts automatically when GENKIT_ENV=dev is set. '
        'Remove lifespan=genkit_lifespan(ai) from your FastAPI() call.',
        DeprecationWarning,
        stacklevel=2,
    )

    @asynccontextmanager
    async def lifespan(app: Any) -> AsyncGenerator[None, None]:  # noqa: ANN401
        yield

    return lifespan
