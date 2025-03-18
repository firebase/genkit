# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Logging middleware for Litestar that logs requests and responses."""

import time

import structlog
from litestar.middleware.base import AbstractMiddleware
from litestar.types import Message

from ...servers.typing import Receive, Scope, Send

logger = structlog.get_logger(__name__)


class LitestarLoggingMiddleware(AbstractMiddleware):
    """Logging middleware for Litestar that logs requests and responses."""

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        """Process the ASGI request/response cycle with logging."""
        if str(scope['type']) != 'http':
            await self.app(scope, receive, send)
            return

        start_time = time.time()
        path = scope.get('path', '')
        method = scope.get('method', '')

        # Log the request
        request_id = str(id(scope))
        try:
            # Extract request headers
            headers = dict(scope.get('headers', []))
            formatted_headers = {
                k.decode('utf-8'): v.decode('utf-8') for k, v in headers.items()
            }
            await logger.ainfo(
                f'HTTP Request {method} {path}',
                request_id=request_id,
                method=method,
                path=path,
                headers=formatted_headers,
            )
        except Exception as e:
            await logger.aerror(
                'Error logging request',
                error=str(e),
            )

        # Capture the response
        async def wrapped_send(message: Message) -> None:
            if message['type'] == 'http.response.start':
                status_code = message.get('status', 0)
                response_time = time.time() - start_time
                try:
                    # Get response headers
                    resp_headers = message.get('headers', [])
                    formatted_resp_headers = (
                        {
                            k.decode('utf-8'): v.decode('utf-8')
                            for k, v in resp_headers
                        }
                        if resp_headers
                        else {}
                    )
                    await logger.ainfo(
                        f'HTTP Response {method} {path}',
                        request_id=request_id,
                        method=method,
                        path=path,
                        status_code=status_code,
                        response_time_ms=round(response_time * 1000, 2),
                        headers=formatted_resp_headers,
                    )
                except Exception as e:
                    await logger.aerror(
                        'Error logging response',
                        error=str(e),
                    )
            await send(message)

        # Call the next middleware or handler
        await self.app(scope, receive, wrapped_send)
