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

"""Flow Server module for GenKit.

This module provides a high-level server implementation for the GenKit Flows
API.  The `FlowsServer` class offers a convenient way to serve flows over HTTP
with minimal configuration, handling all the details of setting up an ASGI
server and managing its lifecycle.

Features:
- Simple server setup and configuration
- Support for both blocking and non-blocking server operation
- Graceful signal handling for clean shutdowns
- Configurable context providers for request-specific execution contexts
- Built on top of Uvicorn and Starlette for high performance

Example usage:

    ```python
    from genkit.core.flow_server import FlowsServer
    from genkit.core.registry import Registry

    # Create a registry with your flows
    registry = Registry()
    registry.register(my_flow, name='my_flow')

    # Create and start the server
    server = FlowsServer(registry, host='localhost', port=3400)

    # Start server in blocking mode (default)
    server.start()

    # Or start in non-blocking mode to continue execution
    server.start(block=False)
    ```

For lower-level ASGI application control, see
genkit.core.flows.create_flows_asgi_app.
"""

from __future__ import annotations

import asyncio
import signal
from collections.abc import Callable
from typing import Any

import structlog
import uvicorn
from starlette.types import ASGIApp

from genkit.core.flows import create_flows_asgi_app
from genkit.core.registry import Registry

logger = structlog.get_logger(__name__)


class FlowsServer:
    """Server for hosting Genkit flows.

    This server exposes flows registered in a Genkit registry as HTTP endpoints.
    It supports streaming and non-streaming responses, context providers,
    and other configuration options.

    Attributes:
        registry: The Genkit registry containing flows to expose.
        host: The hostname to bind to.
        port: The port to listen on.
        context_providers: Optional callables that enhance request context.
        uvicorn_options: Additional options to pass to uvicorn.
    """

    def __init__(
        self,
        registry: Registry,
        host: str = '127.0.0.1',
        port: int = 3400,
        context_providers: list[Callable] | None = None,
        uvicorn_options: dict[str, Any] | None = None,
    ):
        """Initialize a new FlowsServer.

        Args:
            registry: The Genkit registry containing flows to expose.
            host: The hostname to bind to (default: "127.0.0.1").
            port: The port to listen on (default: 3400).
            context_providers: Optional callables that enhance request context.
            uvicorn_options: Additional options to pass to uvicorn.
        """
        self.registry = registry
        self.host = host
        self.port = port
        self.context_providers = context_providers or []
        self.uvicorn_options = uvicorn_options or {}
        self._server = None
        self._app = None

    async def startup(self):
        """Perform server startup tasks."""
        logger.info('Flows server starting', host=self.host, port=self.port)

        # Initialize app context
        if hasattr(self._app, 'state'):
            self._app.state.context = {}

    async def shutdown(self):
        """Perform server shutdown tasks."""
        logger.info('Flows server shutting down')

    def create_app(self) -> ASGIApp:
        """Create and return the ASGI application for the server.

        Returns:
            The ASGI application.
        """
        self._app = create_flows_asgi_app(
            registry=self.registry,
            context_providers=self.context_providers,
            on_app_startup=self.startup,
            on_app_shutdown=self.shutdown,
        )
        return self._app

    def start(self, block: bool = True):
        """Start the server.

        Args:
            block: If True, block until the server exits. If False,
                  return immediately after starting the server.
        """
        app = self.create_app()

        config = uvicorn.Config(
            app,
            host=self.host,
            port=self.port,
            log_level='info',
            **self.uvicorn_options,
        )
        self._server = uvicorn.Server(config)

        if block:
            # Handle signals for clean shutdown
            loop = asyncio.get_event_loop()
            signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
            for s in signals:
                loop.add_signal_handler(
                    s, lambda s=s: asyncio.create_task(self.handle_signal(s))
                )

            # Run the server
            if self._server:
                self._server.run()
        else:
            # Start the server in a new thread
            import threading

            thread = threading.Thread(
                target=lambda: self._server.run() if self._server else None
            )
            thread.daemon = True
            thread.start()

    async def handle_signal(self, sig):
        """Handle termination signals.

        Args:
            sig: The signal received.
        """
        logger.info(f'Received signal: {sig.name}')
        await self.shutdown()
        if self._server:
            self._server.should_exit = True


def start_flows_server(
    registry: Registry,
    host: str = '127.0.0.1',
    port: int = 3400,
    context_providers: list[Callable] | None = None,
    uvicorn_options: dict[str, Any] | None = None,
    block: bool = True,
) -> FlowsServer:
    """Start a new FlowsServer with the given registry.

    This is a convenience function for creating and starting a FlowsServer.

    Args:
        registry: The Genkit registry containing flows to expose.
        host: The hostname to bind to (default: "127.0.0.1").
        port: The port to listen on (default: 3400).
        context_providers: Optional callables that enhance request context.
        uvicorn_options: Additional options to pass to uvicorn.
        block: If True, block until the server exits. If False,
               return immediately after starting the server.

    Returns:
        The FlowsServer instance.
    """
    server = FlowsServer(
        registry=registry,
        host=host,
        port=port,
        context_providers=context_providers,
        uvicorn_options=uvicorn_options,
    )
    server.start(block=block)
    return server
