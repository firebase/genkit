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

"""Action context definitions and built-in context providers.

This module defines the core types for Genkit's request context system and
provides built-in context providers for common authentication patterns.

Overview:
    Context providers are middleware that read incoming request data (headers,
    body) and produce a context dict that is passed to the Action during
    execution.  They run *before* the Action and can reject requests early
    by raising ``UserFacingError``.

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                      Context Provider Flow                              │
    ├─────────────────────────────────────────────────────────────────────────┤
    │                                                                         │
    │  HTTP Request                                                           │
    │      │                                                                  │
    │      ├──► ContextProvider(request_data)                                 │
    │      │        │                                                         │
    │      │        ├── returns context dict ──► merged into Action context   │
    │      │        └── raises UserFacingError ──► 401/403 response           │
    │      │                                                                  │
    │      └──► Action executes with merged context                          │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘

Built-in Providers:
    - ``api_key()`` — Extract and optionally validate API keys from the
      ``Authorization`` header.

Example:
    Protect deployed flows with an API key via the flows ASGI server::

        from genkit.core.context import api_key
        from genkit.core.flows import create_flows_asgi_app

        app = create_flows_asgi_app(
            registry=ai.registry,
            context_providers=[api_key('my-secret-key')],
        )

    Or use a custom validation policy::

        app = create_flows_asgi_app(
            registry=ai.registry,
            context_providers=[api_key(lambda ctx: validate_key(ctx))],
        )

Note:
    ``api_key()`` protects *incoming* HTTP requests to deployed flows
    (reads the ``Authorization`` header).  It is unrelated to the
    per-request ``config.apiKey`` in ``GenerationCommonConfig``, which
    overrides the *outbound* provider API key for model calls.

See Also:
    - JS SDK parity: ``js/core/src/context.ts``
    - Flow server integration: ``genkit.core.flows``
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from genkit.core.error import UserFacingError

__all__ = [
    'ApiKeyContext',
    'ContextMetadata',
    'ContextProvider',
    'RequestData',
    'api_key',
]


@dataclass
class ContextMetadata:
    """A base class for Context metadata."""

    trace_id: str | None = None


T = TypeVar('T')


@dataclass
class RequestData(Generic[T]):
    """A universal type that request handling extensions.

    For example, Flask can map their request to this type.  This allows
    ContextProviders to build consistent interfaces on any web framework.
    Headers must be lowercase to ensure portability.

    The ``request`` field holds the raw framework-specific request object
    (e.g. Flask's ``request``).  The ``method``, ``headers``, and ``input``
    fields provide a framework-agnostic interface — set them in subclasses
    or pass them directly when constructing from ASGI middleware.
    """

    request: T
    method: str = ''
    headers: dict[str, str] = field(default_factory=dict)
    input: T | None = None
    metadata: ContextMetadata | None = None


class ApiKeyContext:
    """Context returned by the ``api_key()`` context provider.

    Attributes:
        auth: A dict containing the extracted ``api_key`` value (may be
            ``None`` if no ``Authorization`` header was present).
    """

    def __init__(self, api_key_value: str | None) -> None:
        """Initialize an ApiKeyContext.

        Args:
            api_key_value: The API key extracted from the Authorization header.
        """
        self.auth: dict[str, str | None] = {'api_key': api_key_value}

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dict suitable for merging into Action context."""
        return {'auth': self.auth}

    def __eq__(self, other: object) -> bool:
        """Check equality."""
        if isinstance(other, ApiKeyContext):
            return self.auth == other.auth
        return NotImplemented

    def __repr__(self) -> str:
        """Return a developer-friendly representation."""
        return f'ApiKeyContext(auth={self.auth})'


# The policy callable signature: receives an ApiKeyContext, may raise.
ApiKeyPolicy = Callable[[ApiKeyContext], None | Awaitable[None]]

# NOTE: There are currently two incompatible calling conventions for
# context providers in the Python SDK:
#
#   1. Flask plugin (handler.py):  provider(request_data: RequestData) → dict
#      - Matches the JS SDK's ContextProvider<C, T> = (request: RequestData<T>) => C
#      - Single argument: a RequestData instance with method, headers, input
#
#   2. Built-in flow server (flows.py):  provider(context: dict, request_data: dict) → dict
#      - Two arguments: existing context (always {}) + request data as a plain dict
#      - The first arg (context) is always empty — it's app.state.context = {}
#
# The api_key() function below follows convention #2 (the flow server) because
# that's where context_providers=[] is used. The Flask plugin uses a separate
# context_provider= kwarg with convention #1.
#
# TODO(#4351): Align both callers on a single ContextProvider protocol that
# matches the JS SDK: provider(request: RequestData) → dict.  This will
# require updating the flow server's invocation at flows.py:199 to stop
# passing the unused app.state.context argument.
ContextProvider = Callable[[RequestData[T]], dict[str, Any] | Awaitable[dict[str, Any]]]
"""Middleware that reads request data and returns context for the Action.

If the provider raises an error, the request fails and the Action is not
invoked.  Raise ``UserFacingError`` for errors safe to return to clients.

Note:
    This type alias documents the *ideal* (JS-parity) signature.  The
    built-in flow server currently calls providers with two arguments
    ``(context, request_data_dict)`` — see the NOTE comment above.
"""


def api_key(
    value_or_policy: str | ApiKeyPolicy | None = None,
) -> Callable[[Any, dict[str, Any]], Awaitable[dict[str, Any]]]:
    """Create a context provider that extracts and validates API keys.

    The provider reads the ``Authorization`` header from the incoming HTTP
    request and makes it available as ``context['auth']['api_key']``.

    Three usage modes (matching JS SDK ``apiKey()`` parity):

    1. **Pass-through** — ``api_key()``: Extracts the key without validation.
       Useful when downstream code needs access to the key but validation
       is handled elsewhere.

    2. **Exact match** — ``api_key('my-secret')``: Extracts the key and
       validates it matches the expected value.  Raises
       ``UserFacingError('UNAUTHENTICATED')`` if missing, or
       ``UserFacingError('PERMISSION_DENIED')`` if wrong.

    3. **Custom policy** — ``api_key(my_validator)``: Extracts the key and
       calls your validation function with an ``ApiKeyContext``.  Your
       function can inspect ``ctx.auth['api_key']`` and raise any error
       to reject the request.

    Args:
        value_or_policy: One of:
            - ``None`` (default): pass-through, no validation.
            - ``str``: the expected API key value for exact-match validation.
            - ``callable``: a sync or async function that receives an
              ``ApiKeyContext`` and may raise to reject the request.

    Returns:
        A context provider callable compatible with the flows server.

    Example:
        Pass-through (no validation)::

            app = create_flows_asgi_app(
                registry=ai.registry,
                context_providers=[api_key()],
            )

        Exact match::

            app = create_flows_asgi_app(
                registry=ai.registry,
                context_providers=[api_key('my-secret-key')],
            )

        Custom policy::

            def require_premium(ctx: ApiKeyContext) -> None:
                if ctx.auth['api_key'] not in PREMIUM_KEYS:
                    raise UserFacingError('PERMISSION_DENIED', 'Premium required')


            app = create_flows_asgi_app(
                registry=ai.registry,
                context_providers=[api_key(require_premium)],
            )

    See Also:
        - JS SDK: ``apiKey()`` in ``js/core/src/context.ts``
    """

    async def provider(
        _context: Any,  # noqa: ANN401
        request_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Extract API key from request and apply validation policy.

        Args:
            _context: The existing app-level context (unused by this provider).
            request_data: Dict with ``method``, ``headers``, ``input`` keys
                as constructed by the flows server.

        Returns:
            A dict with ``auth.api_key`` to merge into the Action context.

        Raises:
            UserFacingError: If the API key is missing or invalid.
        """
        headers = request_data.get('headers', {})
        key = headers.get('authorization')
        ctx = ApiKeyContext(key)

        if isinstance(value_or_policy, str):
            # Exact-match mode: validate the key.
            if not key:
                raise UserFacingError('UNAUTHENTICATED', 'Unauthenticated')
            if key != value_or_policy:
                raise UserFacingError('PERMISSION_DENIED', 'Permission Denied')
        elif callable(value_or_policy):
            # Custom policy mode: delegate to user function.
            result = value_or_policy(ctx)
            # Support both sync and async policies.
            if result is not None:
                await result

        return ctx.to_dict()

    return provider
