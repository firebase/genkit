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

"""Testing sample for multi server."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import structlog
from litestar import Controller, Litestar, get, post
from litestar.datastructures import State
from litestar.logging.config import LoggingConfig
from litestar.middleware.base import AbstractMiddleware
from litestar.plugins.structlog import StructlogPlugin
from litestar.types import Message
from starlette.applications import Starlette

from genkit.core.environment import is_dev_environment
from genkit.core.reflection import create_reflection_asgi_app
from genkit.core.registry import Registry
from genkit.web.manager import (
    AbstractBaseServer,
    Server,
    ServerConfig,
    ServerManager,
    UvicornAdapter,
    get_health_info,
    get_server_info,
    run_loop,
)
from genkit.web.manager.signals import terminate_all_servers
from genkit.web.typing import Application, Receive, Scope, Send

# TODO: Logging middleware > log ALL access requests and fix dups
# TODO: Logging middleware > access requests different color for each server.
# TODO: Logging middleware > show the METHOD and path first and then the structure.
# TODO: Logging middleware > if the response is an error code, highlight in red
# when logging to the console.
# TODO: Logger > default configuration and console output and json output
# TODO: Add opentelemetry integration
# TODO: replace 'requests' with 'aiohttp' or 'httpx' in genkit

logging_config = LoggingConfig(
    loggers={
        'genkit_example': {
            'level': 'DEBUG',
            'handlers': ['console'],
        },
    }
)


logger = structlog.get_logger(__name__)


class LitestarLoggingMiddleware(AbstractMiddleware):
    """Logging middleware for Litestar that logs requests and responses."""

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
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
            formatted_headers = {k.decode('utf-8'): v.decode('utf-8') for k, v in headers.items()}
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
                        {k.decode('utf-8'): v.decode('utf-8') for k, v in resp_headers} if resp_headers else {}
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


class BaseControllerMixin:
    """Base controller mixin for all litestar controllers."""

    @post('/__quitquitquitz')
    async def quit(self) -> dict[str, Any]:
        """Handle the quit endpoint."""
        await logger.ainfo('Shutting down all servers...')
        terminate_all_servers()
        return {'status': 'OK'}

    @get('/__healthz')
    async def health(self, state: State) -> dict[str, Any]:
        """Handle the health check endpoint."""
        config = state.config
        info = get_health_info(config)
        return info

    @get('/__serverz')
    async def server_info(self, state: State) -> dict[str, Any]:
        """Handle the system information check endpoint."""
        config = state.config
        info = get_server_info(config)
        return info if isinstance(info, dict) else {'info': info}


class FlowsEndpoints(Controller, BaseControllerMixin):
    """Controller for the Flows API endpoints."""

    path = '/flow'

    @get('/run')
    async def root(self) -> dict[str, str]:
        """Handle the root endpoint."""
        msg = 'Running flow endpoint!'
        return {'flow': msg}


class GreetingEndpoints(Controller, BaseControllerMixin):
    """Controller for the Greetings API endpoints.

    An example demonstrating multiple controllers bound to the same application
    server.
    """

    path = '/'

    @get('/greet')
    async def root(self) -> dict[str, str]:
        """Handle the root endpoint."""
        msg = 'Hello from greeting endpoints app!'
        return {'greeting': msg}


class FlowsServerLifecycle(AbstractBaseServer):
    """Flows server implementing the ServerLifecycleProtocol."""

    def __init__(self, route_handlers: list[type[Controller]]) -> None:
        """Initialize the flows server.

        Args:
            route_handlers: The controller classes to use for routes.
        """
        self.route_handlers = route_handlers

    def create(self, config: ServerConfig) -> Application:
        """Create a Litestar application instance."""

        async def on_app_startup() -> None:
            """Handle application startup."""
            await logger.ainfo('[LIFESPAN] Starting API server...')
            # Any initialization could go here

        async def on_app_shutdown() -> None:
            """Handle application shutdown."""
            await logger.ainfo('[LIFESPAN] Shutting down API server...')

        # Create and return the Litestar application
        return Litestar(
            route_handlers=self.route_handlers,
            on_startup=[on_app_startup],
            on_shutdown=[on_app_shutdown],
            logging_config=logging_config,
            middleware=[LitestarLoggingMiddleware],
            plugins=[StructlogPlugin()],
            state=State({'config': config}),  # Set the config in the application state
        )


class ReflectionServerStarletteLifecycle(AbstractBaseServer):
    """Reflection server implemented using Starlette."""

    def __init__(self) -> None:
        """Initialize the Starlette reflection server."""
        pass

    def create(self, config: ServerConfig) -> Starlette:
        """Create a Starlette application instance."""

        async def on_app_startup() -> None:
            """Handle application startup."""
            await logger.ainfo('[LIFESPAN] Starting Starlette Reflection API server...')

        async def on_app_shutdown() -> None:
            """Handle application shutdown."""
            await logger.ainfo('[LIFESPAN] Shutting down Starlette Reflection API server...')

        return create_reflection_asgi_app(
            registry=Registry(),
            on_app_startup=on_app_startup,
            on_app_shutdown=on_app_shutdown,
        )


async def add_server_after(mgr: ServerManager, server: Server, delay: float) -> None:
    """Add a server to the servers manager after a delay.

    Args:
        mgr: The servers manager.
        server: The server to add.
        delay: The delay in seconds before adding the server.

    Returns:
        None
    """
    await asyncio.sleep(delay)
    await mgr.queue_server(server)


async def main() -> None:
    """Entry point function."""
    servers = [
        Server(
            config=ServerConfig(
                name='flows',
                host='localhost',
                port=3400,
                ports=range(3400, 3410),
            ),
            lifecycle=FlowsServerLifecycle([FlowsEndpoints, GreetingEndpoints]),
            adapter=UvicornAdapter(),
        ),
    ]

    mgr = ServerManager()
    if is_dev_environment():
        reflection_server = Server(
            config=ServerConfig(
                name='reflection-starlette',
                host='localhost',
                port=3100,
                ports=range(3100, 3110),
            ),
            lifecycle=ReflectionServerStarletteLifecycle(),
            adapter=UvicornAdapter(),
        )
        asyncio.create_task(add_server_after(mgr, reflection_server, 2.0))

    await logger.ainfo('Starting servers...')
    await mgr.run_all(servers)


if __name__ == '__main__':
    run_loop(main())
