# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""HTTP header definitions and functionality for the Genkit framework."""

from __future__ import annotations

import urllib.parse

import structlog

from .handlers import (
    create_lifespan_handler,
)
from .responses import write_not_found_response
from .typing import (
    Application,
    LifespanHandler,
    QueryParams,
    Receive,
    Routes,
    Scope,
    Send,
)

logger = structlog.get_logger(__name__)


def extract_query_params(scope, encoding='utf-8') -> QueryParams:
    """Extract query parameters from ASGI scope.

    Args:
        scope: ASGI connection scope.
        encoding: Character encoding to use for decoding the query string.

    Returns:
        Dictionary mapping parameter names to lists of values.
    """
    query_params = {}
    if 'query_string' in scope and scope['query_string']:
        query_string = scope['query_string'].decode(encoding)
        query_params = urllib.parse.parse_qs(query_string)
    return query_params


def is_query_flag_enabled(query_params: QueryParams, flag: str) -> bool:
    """Check if a query flag is enabled.

    Args:
        query_params: Dictionary containing parsed query parameters.
        flag: Flag name to check for streaming.

    Returns:
        True if the query flag is enabled, False otherwise.
    """
    return query_params.get(flag, ['false'])[0] == 'true'


def create_asgi_app(
    routes: Routes,
    on_lifespan_begin: LifespanHandler | None = None,
    on_lifespan_end: LifespanHandler | None = None,
) -> Application:
    """Create an ASGI application.

    Args:
        routes: List of routes to add to the application.
        on_lifespan_begin: Lifespan handler for startup events.
        on_lifespan_end: Lifespan handler for shutdown events.

    Returns:
        ASGI application.
    """

    async def app(scope: Scope, receive: Receive, send: Send):
        """ASGI application for the Genkit reflection API.

        This handler provides endpoints for inspecting and interacting with
        registered Genkit actions during development.

        Args:
            scope: ASGI connection scope.
            receive: ASGI receive function.
            send: ASGI send function.
        """
        kind = scope['type']
        match kind:
            case 'lifespan':
                lifespan_handler = create_lifespan_handler(
                    on_lifespan_begin, on_lifespan_end
                )
                await lifespan_handler(scope, receive, send)
                return
            case 'http':
                pass
            case _:
                await logger.error(f'Unsupported scope type: {kind}')
                return

        method = scope['method']
        path = scope['path']
        for route in routes:
            if method == route.method and path == route.path:
                await route.handler(scope, receive, send)
                return

        await write_not_found_response(scope, receive, send)

    return app
