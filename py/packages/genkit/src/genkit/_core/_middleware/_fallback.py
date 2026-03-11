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

"""fallback middleware."""

from collections.abc import Awaitable, Callable

from genkit._core._error import GenkitError, StatusName
from genkit._core._model import ModelResponse
from genkit._core._registry import HasRegistry, Registry

from ._base import BaseMiddleware, ModelHookParams
from ._utils import _DEFAULT_FALLBACK_STATUSES


def fallback(
    ai: HasRegistry,
    models: list[str],
    statuses: list[StatusName] | None = None,
    on_error: Callable[[GenkitError], None] | None = None,
) -> BaseMiddleware:
    """Middleware that falls back to alternative models on failure.

    Args:
        ai: Object with a registry (e.g. Genkit instance) for resolving fallback models.
        models: Ordered list of fallback model names to try.
        statuses: List of status codes that trigger fallback (default: UNAVAILABLE,
            DEADLINE_EXCEEDED, RESOURCE_EXHAUSTED, ABORTED, INTERNAL, NOT_FOUND,
            UNIMPLEMENTED).
        on_error: Optional callback called when fallback is triggered.

    Returns:
        Middleware that implements fallback logic.
    """
    return _fallback_for_registry(ai.registry, models, statuses, on_error)


def _fallback_for_registry(
    registry: Registry,
    models: list[str],
    statuses: list[StatusName] | None = None,
    on_error: Callable[[GenkitError], None] | None = None,
) -> BaseMiddleware:
    """Internal: fallback middleware that takes a Registry (for testing)."""
    return _FallbackMiddleware(
        registry=registry,
        models=models,
        statuses=statuses or _DEFAULT_FALLBACK_STATUSES,
        on_error=on_error,
    )


class _FallbackMiddleware(BaseMiddleware):
    def __init__(
        self,
        registry: Registry,
        models: list[str],
        statuses: list[StatusName],
        on_error: Callable[[GenkitError], None] | None = None,
    ) -> None:
        self._registry = registry
        self._models = models
        self._statuses = statuses
        self._on_error = on_error

    async def wrap_model(
        self,
        params: ModelHookParams,
        next_fn: Callable[[ModelHookParams], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        try:
            return await next_fn(params)
        except Exception as e:
            if isinstance(e, GenkitError) and e.status in self._statuses:
                if self._on_error:
                    self._on_error(e)

                last_error: Exception = e
                for model_name in self._models:
                    try:
                        model = await self._registry.resolve_model(model_name)
                        if model is None:
                            raise GenkitError(
                                status='NOT_FOUND',
                                message=f"Fallback model '{model_name}' not found.",
                            )
                        result = await model.run(
                            input=params.request,
                            context=params.context,
                            on_chunk=params.on_chunk,
                        )
                        return result.response
                    except Exception as e2:
                        last_error = e2
                        if isinstance(e2, GenkitError) and e2.status in self._statuses:
                            if self._on_error:
                                self._on_error(e2)
                            continue
                        raise
                raise last_error from None
            raise
