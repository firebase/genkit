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

"""Built-in middleware registration.

Definitions live in ._base (which avoids importing Registry) so the plugin module can
load them without import cycles; this module registers built-ins and helpers.
"""

from __future__ import annotations

from typing import Any

from genkit._core._error import StatusName
from genkit._core._registry import Registry

from ._base import (
    BaseMiddleware,
    GenerateMiddleware,
    MiddlewareFnOptions,
    generate_middleware,
)
from ._download_request_media import download_request_media
from ._fallback import _fallback_for_registry
from ._retry import retry
from ._simulate_system_prompt import simulate_system_prompt
from ._validate_support import validate_support

__all__ = [
    'GenerateMiddleware',
    'MiddlewareFnOptions',
    'builtin_generate_middleware_definitions',
    'generate_middleware',
    'register_builtin_generate_middleware',
]


def _cfg_get(cfg: dict[str, Any] | None, camel: str, snake: str, default: Any = None) -> Any:
    """Read Dev UI / JSON camelCase or Python snake_case config keys."""
    if not cfg:
        return default
    if camel in cfg:
        return cfg[camel]
    if snake in cfg:
        return cfg[snake]
    return default


def _factory_retry(opts: MiddlewareFnOptions) -> BaseMiddleware:
    c = opts.config or {}
    statuses_raw = _cfg_get(c, 'statuses', 'statuses')
    statuses: list[StatusName] | None = None
    if isinstance(statuses_raw, list):
        statuses = [str(s) for s in statuses_raw]
    return retry(
        max_retries=int(_cfg_get(c, 'maxRetries', 'max_retries', 3)),
        statuses=statuses,
        initial_delay_ms=int(_cfg_get(c, 'initialDelayMs', 'initial_delay_ms', 1000)),
        max_delay_ms=int(_cfg_get(c, 'maxDelayMs', 'max_delay_ms', 60000)),
        backoff_factor=float(_cfg_get(c, 'backoffFactor', 'backoff_factor', 2.0)),
        jitter=bool(_cfg_get(c, 'jitter', 'jitter', True)),
        on_error=None,
    )


def _factory_fallback(opts: MiddlewareFnOptions) -> BaseMiddleware:
    c = opts.config or {}
    models = _cfg_get(c, 'models', 'models')
    if not models or not isinstance(models, list):
        raise ValueError('fallback middleware requires config "models": list of model name strings.')
    statuses_raw = _cfg_get(c, 'statuses', 'statuses')
    statuses: list[StatusName] | None = None
    if isinstance(statuses_raw, list):
        statuses = [str(s) for s in statuses_raw]
    return _fallback_for_registry(opts.registry, models=models, statuses=statuses, on_error=None)


def _factory_simulate_system_prompt(opts: MiddlewareFnOptions) -> BaseMiddleware:
    c = opts.config or {}
    return simulate_system_prompt(
        preface=str(_cfg_get(c, 'preface', 'preface', 'SYSTEM INSTRUCTIONS:\n')),
        acknowledgement=str(_cfg_get(c, 'acknowledgement', 'acknowledgement', 'Understood.')),
    )


def _factory_download_request_media(opts: MiddlewareFnOptions) -> BaseMiddleware:
    c = opts.config or {}
    mb = _cfg_get(c, 'maxBytes', 'max_bytes')
    return download_request_media(
        max_bytes=int(mb) if mb is not None else None,
        filter_fn=None,
    )


def _factory_validate_support(opts: MiddlewareFnOptions) -> BaseMiddleware:
    c = opts.config or {}
    name = _cfg_get(c, 'name', 'name')
    if not name:
        raise ValueError('validate_support middleware requires config "name".')
    supports_raw = _cfg_get(c, 'supports', 'supports')
    supports_parsed = None
    if isinstance(supports_raw, dict):
        from genkit._core._typing import Supports

        supports_parsed = Supports.model_validate(supports_raw)
    return validate_support(str(name), supports=supports_parsed)


_RETRY_SCHEMA: dict[str, Any] = {
    'type': 'object',
    'properties': {
        'maxRetries': {'type': 'integer', 'default': 3},
        'initialDelayMs': {'type': 'integer', 'default': 1000},
        'maxDelayMs': {'type': 'integer', 'default': 60000},
        'backoffFactor': {'type': 'number', 'default': 2.0},
        'jitter': {'type': 'boolean', 'default': True},
        'statuses': {'type': 'array', 'items': {'type': 'string'}},
    },
}

_FALLBACK_SCHEMA: dict[str, Any] = {
    'type': 'object',
    'properties': {
        'models': {'type': 'array', 'items': {'type': 'string'}},
        'statuses': {'type': 'array', 'items': {'type': 'string'}},
    },
    'required': ['models'],
}

_SIMULATE_SCHEMA: dict[str, Any] = {
    'type': 'object',
    'properties': {
        'preface': {'type': 'string'},
        'acknowledgement': {'type': 'string'},
    },
}

_DOWNLOAD_SCHEMA: dict[str, Any] = {
    'type': 'object',
    'properties': {
        'maxBytes': {'type': 'integer'},
    },
}

_VALIDATE_SCHEMA: dict[str, Any] = {
    'type': 'object',
    'properties': {
        'name': {'type': 'string'},
        'supports': {'type': 'object'},
    },
    'required': ['name'],
}


def builtin_generate_middleware_definitions() -> list[GenerateMiddleware]:
    """Built-in middleware definitions (registry and developer UI)."""
    return [
        generate_middleware(
            {
                'name': 'retry',
                'description': 'Middleware that retries failed requests with exponential backoff.',
                'config_schema': _RETRY_SCHEMA,
            },
            _factory_retry,
        ),
        generate_middleware(
            {
                'name': 'fallback',
                'description': 'Middleware that falls back to alternative models on failure.',
                'config_schema': _FALLBACK_SCHEMA,
            },
            _factory_fallback,
        ),
        generate_middleware(
            {
                'name': 'simulate_system_prompt',
                'description': 'Middleware that simulates system prompt for models without native support.',
                'config_schema': _SIMULATE_SCHEMA,
            },
            _factory_simulate_system_prompt,
        ),
        generate_middleware(
            {
                'name': 'download_request_media',
                'description': 'Middleware that downloads HTTP media URLs and converts to base64 data URIs.',
                'config_schema': _DOWNLOAD_SCHEMA,
            },
            _factory_download_request_media,
        ),
        generate_middleware(
            {
                'name': 'validate_support',
                'description': 'Middleware that validates request against model capabilities.',
                'config_schema': _VALIDATE_SCHEMA,
            },
            _factory_validate_support,
        ),
    ]


def register_builtin_generate_middleware(registry: Registry) -> None:
    """Register built-in middleware definitions on the given registry."""
    for gm in builtin_generate_middleware_definitions():
        registry.register_value('middleware', gm.name, gm)
