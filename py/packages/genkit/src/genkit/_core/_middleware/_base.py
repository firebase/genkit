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

"""Middleware protocol, hook params, default implementation, and registration types.

Two roles (they are not superclass/subclass):

- **Runtime:** BaseMiddleware (and the Middleware protocol) — objects that implement
  the wrap_* hooks. Factories produce these; they are not passed directly in ``use=``.
- **Definition:** GenerateMiddleware — a named bundle in the registry (metadata plus a
  factory callable). It does not extend BaseMiddleware; calling it with options returns
  the BaseMiddleware instance for that request. Register via ``middleware_plugin`` or
  ``Plugin.generate_middleware``; reference by name in ``use=`` as ``MiddlewareRef``.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol

from genkit._core._model import (
    GenerateActionOptions,
    GenerateHookParams,
    ModelHookParams,
    ModelRequest,
    ModelResponse,
    ModelResponseChunk,
    ToolHookParams,
)
from genkit._core._middleware._runtime import MiddlewareRuntime
from genkit._core._typing import Part, ToolRequestPart


class Middleware(Protocol):
    """Middleware with hooks for the generate loop, model call, and tool execution.

    Subclass BaseMiddleware to implement only the hooks you need.
    """

    def wrap_generate(
        self,
        params: GenerateHookParams,
        next_fn: Callable[[GenerateHookParams], Awaitable[ModelResponse]],
    ) -> Awaitable[ModelResponse]:
        """Wrap each iteration of the tool loop (model call + optional tool resolution)."""
        ...

    def wrap_model(
        self,
        params: ModelHookParams,
        next_fn: Callable[[ModelHookParams], Awaitable[ModelResponse]],
    ) -> Awaitable[ModelResponse]:
        """Wrap each model API call."""
        ...

    def wrap_tool(
        self,
        params: ToolHookParams,
        next_fn: Callable[[ToolHookParams], Awaitable[tuple[Part | None, Part | None]]],
    ) -> Awaitable[tuple[Part | None, Part | None]]:
        """Wrap each tool execution."""
        ...


class BaseMiddleware(MiddlewareRuntime):
    """Default hook implementation at runtime (pass-through; override what you need).

    Instances receive wrap_generate, wrap_model, and wrap_tool. That is different from
    GenerateMiddleware, which is only the registry definition plus a factory that
    produces a BaseMiddleware.

    To expose middleware to ``use=``, build a ``GenerateMiddleware`` with generate_middleware
    (meta dict + factory, or ``name`` / ``description`` / schema class attributes +
    ``generate_middleware(MySubclass)``), register it via ``middleware_plugin`` or a ``Plugin``,
    then pass ``MiddlewareRef(name=...)``. The class form calls ``MySubclass()`` with no arguments;
    use the dict form for a custom factory.
    """

    # Class-level metadata for generate_middleware(MyClass); not instance fields.
    name = ''
    description = None
    middleware_config_schema = None
    middleware_metadata = None

    def wrap_generate(
        self,
        params: GenerateHookParams,
        next_fn: Callable[[GenerateHookParams], Awaitable[ModelResponse]],
    ) -> Awaitable[ModelResponse]:
        return next_fn(params)

    def wrap_model(
        self,
        params: ModelHookParams,
        next_fn: Callable[[ModelHookParams], Awaitable[ModelResponse]],
    ) -> Awaitable[ModelResponse]:
        return next_fn(params)

    def wrap_tool(
        self,
        params: ToolHookParams,
        next_fn: Callable[[ToolHookParams], Awaitable[tuple[Part | None, Part | None]]],
    ) -> Awaitable[tuple[Part | None, Part | None]]:
        return next_fn(params)


@dataclass
class MiddlewareFnOptions:
    """Arguments passed when invoking a GenerateMiddleware callable (definition with options).

    registry is typed loosely (Any) so this module does not import Registry (avoids
    import cycles with plugins).
    """

    registry: Any
    config: dict[str, Any] | None = None
    plugin_config: Any = None
    genkit: Any = None


class GenerateMiddleware:
    """Named definition for the registry, not a hook class.

    Holds name, optional Dev UI metadata, and a factory that builds the real middleware.
    It does not subclass BaseMiddleware; only the value returned when the definition is
    called with options runs in the pipeline. Stored under the middleware kind and
    resolved when generate runs with use entries that reference by name.
    """

    def __init__(
        self,
        *,
        name: str,
        factory: Callable[[MiddlewareFnOptions], BaseMiddleware],
        description: str | None = None,
        config_schema: dict[str, Any] | None = None,
        metadata: dict[str, object] | None = None,
    ) -> None:
        if '/' in name:
            raise ValueError(
                'GenerateMiddleware name must not contain "/". '
                'Use a single segment (for example "myorg_logging_mw") so it stays distinct '
                'from model/action keys, which use "/".'
            )
        self.name = name
        self._factory = factory
        self.description = description
        self.config_schema = config_schema
        self.metadata = metadata

    def __call__(self, options: MiddlewareFnOptions) -> BaseMiddleware:
        """Return the BaseMiddleware instance for this request."""
        return self._factory(options)

    def with_name(self, name: str) -> GenerateMiddleware:
        """Return a copy with the same factory and metadata but a different registry name."""
        return GenerateMiddleware(
            name=name,
            factory=self._factory,
            description=self.description,
            config_schema=self.config_schema,
            metadata=self.metadata,
        )

    def to_json(self) -> dict[str, Any]:
        """Serialize for the developer UI and reflection (camelCase keys where applicable)."""
        out: dict[str, Any] = {'name': self.name}
        if self.description:
            out['description'] = self.description
        if self.config_schema is not None:
            out['configSchema'] = self.config_schema
        if self.metadata:
            out['metadata'] = self.metadata
        return out


def _generate_middleware_from_class(middleware_cls: type[BaseMiddleware]) -> GenerateMiddleware:
    """Build a definition from BaseMiddleware class metadata."""
    if not isinstance(middleware_cls, type) or not issubclass(middleware_cls, BaseMiddleware):
        raise TypeError(
            'generate_middleware(cls) expects a BaseMiddleware subclass; '
            f'got {middleware_cls!r}'
        )
    reg_name = middleware_cls.name
    if not reg_name:
        raise ValueError(
            f'{middleware_cls.__qualname__}.name must be set to a non-empty '
            'flat string (no "/") for class-based generate_middleware(MyClass).'
        )

    def _factory(_opts: MiddlewareFnOptions) -> BaseMiddleware:
        return middleware_cls()

    return GenerateMiddleware(
        name=reg_name,
        factory=_factory,
        description=middleware_cls.description,
        config_schema=middleware_cls.middleware_config_schema,
        metadata=middleware_cls.middleware_metadata,
    )


def generate_middleware(
    meta_or_cls: dict[str, Any] | type[BaseMiddleware],
    factory: Callable[[MiddlewareFnOptions], BaseMiddleware] | None = None,
) -> GenerateMiddleware:
    """Create a GenerateMiddleware definition.

    Form 1 — meta dict plus factory (full control, including custom constructors). Example:

        generate_middleware(
            {
                'name': 'my_middleware',
                'description': '...',
                'config_schema': {...},
            },
            lambda opts: MyMiddleware(),
        )

    Form 2 — middleware class only — set ``name``, ``description``, ``middleware_config_schema``,
    and ``middleware_metadata`` on your BaseMiddleware subclass. Then:

        generate_middleware(MyMiddleware)

    The class form instantiates with MyMiddleware() when the definition is invoked.

    Args:
        meta_or_cls: Either a meta dict (must include name) or a BaseMiddleware subclass
            with ``name`` set.
        factory: Required with the dict form. Omitted with the class form.

    Returns:
        A definition suitable for registry.register_value.
    """
    if isinstance(meta_or_cls, dict):
        if factory is None:
            raise TypeError('generate_middleware(meta_dict, factory) requires a factory callable')
        meta = meta_or_cls
        return GenerateMiddleware(
            name=meta['name'],
            factory=factory,
            description=meta.get('description'),
            config_schema=meta.get('config_schema'),
            metadata=meta.get('metadata'),
        )
    if factory is not None:
        raise TypeError('generate_middleware(MyMiddlewareClass): remove the factory argument')
    return _generate_middleware_from_class(meta_or_cls)
