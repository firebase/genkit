# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Testing sample for aioia."""

from __future__ import annotations

import asyncio
import os
from typing import Any

import structlog
from litestar import Controller, Litestar, get, post
from litestar.datastructures import State
from litestar.logging.config import LoggingConfig
from litestar.plugins.structlog import StructlogPlugin
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from aioia.servers import (
    AbstractBaseServer,
    Server,
    ServerConfig,
    ServersManager,
    UvicornAdapter,
    get_health_info,
    get_server_info,
    run_loop,
)
from aioia.servers.middleware import LitestarLoggingMiddleware
from aioia.servers.signals import terminate_all_servers
from aioia.servers.typing import Application, Receive, Scope, Send
from genkit.core.reflection import create_reflection_asgi_app
from genkit.core.registry import Registry

logger = structlog.get_logger(__name__)

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


def is_dev_environment() -> bool:
    """Return whether we're in a development environment.

    Returns:
        True if we're in a development environment, False otherwise.
    """
    return os.environ.get('APP_ENV') == 'dev'


class BaseControllerMixin:
    """Base controller mixin for all litestar controllers."""

    @post('/__quitquitquitz')
    async def quit(self) -> dict[str, Any]:
        """Handle the quit endpoint."""
        await logger.ainfo('Shutting down all servers...')
        terminate_all_servers()
        return {'status': 'ok'}

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


class HelloASGIApp:
    """A simple custom ASGI app."""

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        """A simple custom ASGI app.

        Args:
            scope: ASGI scope
            receive: ASGI receive callback
            send: ASGI send callback
        """
        if scope['type'] != 'http':
            return

        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [
                [b'content-type', b'application/json'],
            ],
        })
        await send({
            'type': 'http.response.body',
            'body': b'{"message": "Pure ASGI application!"}',
        })


class HelloASGIServerLifecycle(AbstractBaseServer):
    """Hello ASGI server implementing the ServerLifecycleProtocol."""

    def create(self, config: ServerConfig) -> Application:
        """Create a Litestar application instance."""
        return HelloASGIApp()


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


class ReflectionApp(Controller, BaseControllerMixin):
    """Controller for the Reflection API endpoints."""

    path = '/'

    @get('/')
    async def root(self) -> dict[str, str]:
        """Handle the root endpoint."""
        msg = 'Hello from Reflection API Server!'
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
            state=State({
                'config': config
            }),  # Set the config in the application state
        )


class ReflectionServerLifecycle(AbstractBaseServer):
    """Reflection server implementing the ServerLifecycleProtocol."""

    def __init__(self, route_handlers: list[type[Controller]]) -> None:
        """Initialize the reflection server.

        Args:
            route_handlers: The handlers to use for routes.
        """
        self.route_handlers = route_handlers

    def create(self, config: ServerConfig) -> Application:
        """Create a Litestar application instance."""

        async def on_app_startup() -> None:
            """Handle application startup."""
            await logger.ainfo('[LIFESPAN] Starting Reflection API server...')
            # Any initialization could go here

        async def on_app_shutdown() -> None:
            """Handle application shutdown."""
            await logger.ainfo(
                '[LIFESPAN] Shutting down Reflection API server...'
            )

        # Create and return the Litestar application
        return Litestar(
            route_handlers=self.route_handlers,
            on_startup=[on_app_startup],
            on_shutdown=[on_app_shutdown],
            logging_config=logging_config,
            middleware=[LitestarLoggingMiddleware],
            plugins=[StructlogPlugin()],
            state=State({
                'config': config
            }),  # Set the config in the application state
        )


async def starlette_reflection_root(request: Request) -> JSONResponse:
    """Handle the root endpoint for Starlette Reflection API."""
    return JSONResponse({
        'greeting': 'Hello from Starlette Reflection API Server!'
    })


async def starlette_server_info(request: Request) -> JSONResponse:
    """Handle the server info endpoint for Starlette Reflection API."""
    config = request.app.state.config
    info = get_server_info(config)
    return JSONResponse(info if isinstance(info, dict) else {'info': info})


async def starlette_health(request: Request) -> JSONResponse:
    """Handle the health check endpoint for Starlette Reflection API."""
    config = request.app.state.config
    return JSONResponse(get_health_info(config))


async def starlette_quit(request: Request) -> JSONResponse:
    """Handle the quit endpoint for Starlette Reflection API."""
    await logger.ainfo('Triggering shutdown')
    terminate_all_servers()
    return JSONResponse({'message': 'Shutting down...'})


class StarletteReflectionServerLifecycle(AbstractBaseServer):
    """Reflection server implemented using Starlette."""

    def __init__(self) -> None:
        """Initialize the Starlette reflection server."""
        pass

    def create(self, config: ServerConfig) -> Starlette:
        """Create a Starlette application instance."""

        async def on_app_startup() -> None:
            """Handle application startup."""
            await logger.ainfo(
                '[LIFESPAN] Starting Starlette Reflection API server...'
            )

        async def on_app_shutdown() -> None:
            """Handle application shutdown."""
            await logger.ainfo(
                '[LIFESPAN] Shutting down Starlette Reflection API server...'
            )

        # Create routes
        routes = [
            Route('/', starlette_reflection_root),
            Route('/__serverz', starlette_server_info),
            Route('/__healthz', starlette_health),
            Route('/__quit', starlette_quit),
        ]

        # Create and return the Starlette application
        app = Starlette(
            routes=routes,
            on_startup=[on_app_startup],
            on_shutdown=[on_app_shutdown],
        )

        # Store the config in app state
        app.state.config = config

        return app


async def append_starlette_reflection_server(
    mgr: ServersManager, delay: float
) -> None:
    """Append a Starlette reflection server to the servers manager.

    Args:
        mgr: The servers manager.
        delay: The delay in seconds before adding the server.

    Returns:
        None
    """
    await asyncio.sleep(delay)
    await mgr.queue_server(
        Server(
            config=ServerConfig(
                name='reflection-starlette',
                host='localhost',
                port=3200,
                ports=[3200],
            ),
            lifecycle=StarletteReflectionServerLifecycle(),
            adapter=UvicornAdapter(),
        )
    )


class NativeReflectionServerLifecycle(AbstractBaseServer):
    """Reflection server implemented using plain native ASGI."""

    def __init__(self) -> None:
        """Initialize the Starlette reflection server."""
        pass

    def create(self, config: ServerConfig) -> Starlette:
        """Create a Starlette application instance."""

        async def on_app_startup() -> None:
            """Handle application startup."""
            await logger.ainfo(
                '[LIFESPAN] Starting Starlette Reflection API server...'
            )

        async def on_app_shutdown() -> None:
            """Handle application shutdown."""
            await logger.ainfo(
                '[LIFESPAN] Shutting down Starlette Reflection API server...'
            )

        return create_reflection_asgi_app(
            registry=Registry(),
            on_app_startup=lambda c, r, s: on_app_startup(),
            on_app_shutdown=lambda c, r, s: on_app_shutdown(),
        )


async def append_native_reflection_server(
    mgr: ServersManager, delay: float
) -> None:
    """Append a Starlette reflection server to the servers manager.

    Args:
        mgr: The servers manager.
        delay: The delay in seconds before adding the server.

    Returns:
        None
    """
    await asyncio.sleep(delay)
    await mgr.queue_server(
        Server(
            config=ServerConfig(
                name='reflection-asgi',
                host='localhost',
                port=3800,
                ports=[3800],
            ),
            lifecycle=NativeReflectionServerLifecycle(),
            adapter=UvicornAdapter(),
        )
    )


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
        Server(
            config=ServerConfig(
                name='hello',
                host='localhost',
                port=3300,
                ports=[3300],
            ),
            lifecycle=HelloASGIServerLifecycle(),
            adapter=UvicornAdapter(),
        ),
    ]
    if is_dev_environment():
        servers.append(
            Server(
                config=ServerConfig(
                    name='reflection',
                    host='localhost',
                    port=3100,
                    ports=[3100],
                ),
                lifecycle=ReflectionServerLifecycle([ReflectionApp]),
                adapter=UvicornAdapter(),
            )
        )

    await logger.ainfo('Starting servers...')
    mgr = ServersManager()
    asyncio.create_task(append_starlette_reflection_server(mgr, 5))
    asyncio.create_task(append_native_reflection_server(mgr, 2))
    await mgr.run_all(servers)


if __name__ == '__main__':
    run_loop(main())
