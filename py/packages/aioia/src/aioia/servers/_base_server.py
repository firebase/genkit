# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Base server implementing the ServerLifecycleProtocol."""

import abc

import structlog

from ._server import ServerConfig
from .typing import Application

logger = structlog.get_logger(__name__)


class AbstractBaseServer(abc.ABC):
    """Abstract base server implementing the ServerLifecycleProtocol."""

    @abc.abstractmethod
    def create(self, config: ServerConfig) -> Application:
        """Create a ASGI application instance.

        This factory method can be used to create an instance of
        an application that exposes HTTP endpoints to be handled
        by the server.

        Args:
            config: The server configuration object.

        Returns:
            An ASGI application.
        """
        ...

    async def on_port_check(
        self, config: ServerConfig, host: str, port: int
    ) -> None:
        """Callback when a port is attempted to be used.

        Args:
            config: The server configuration object.
            host: The host to check.
            port: The port to check.

        Returns:
            None
        """
        await logger.ainfo('Checking port', config=config, host=host, port=port)

    async def on_port_available(
        self, config: ServerConfig, host: str, port: int
    ) -> None:
        """Callback when a port is successfully used.

        Args:
            config: The server configuration object.
            host: The host that was successfully used.
            port: The port that was successfully used.

        Returns:
            None
        """
        await logger.ainfo(
            'Port available', config=config, host=host, port=port
        )

    async def on_port_unavailable(
        self, config: ServerConfig, host: str, port: int
    ) -> None:
        """Callback when a port is not available.

        Args:
            config: The server configuration object.
            host: The host that was not available.
            port: The port that was not available.

        Returns:
            None
        """
        await logger.ainfo(
            'Port unavailable', config=config, host=host, port=port
        )

    async def on_start(self, config: ServerConfig) -> None:
        """Callback when the server starts.

        Args:
            config: The server configuration object.

        Returns:
            None
        """
        await logger.ainfo('Server started', config=config)

    async def on_shutdown(self, config: ServerConfig) -> None:
        """Callback when the server shuts down.

        Args:
            config: The server configuration object.

        Returns:
            None
        """
        await logger.ainfo('Server shutdown', config=config)
