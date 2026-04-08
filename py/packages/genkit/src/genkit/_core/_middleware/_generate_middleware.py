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

"""Middleware definition helpers and registry hooks.

Stock middleware definitions (retry, fallback, …) are registered in a follow-up change;
this module exposes ``generate_middleware`` and empty built-in registration for ``Genkit``.
"""

from __future__ import annotations

from genkit._core._registry import Registry

from ._base import (
    GenerateMiddleware,
    MiddlewareFnOptions,
    generate_middleware,
)

__all__ = [
    'GenerateMiddleware',
    'MiddlewareFnOptions',
    'builtin_generate_middleware_definitions',
    'generate_middleware',
    'register_builtin_generate_middleware',
]


def builtin_generate_middleware_definitions() -> list[GenerateMiddleware]:
    """Stock middleware definitions; empty until built-in middleware PR lands."""
    return []


def register_builtin_generate_middleware(registry: Registry) -> None:
    """Register built-in middleware definitions on the given registry."""
    for gm in builtin_generate_middleware_definitions():
        registry.register_value('middleware', gm.name, gm)
