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

"""Configuration & lifecycle protocol for ServersManager ASGI servers."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from genkit.web.typing import Application

from ._adapters import ASGIServerAdapter, ServerType

DEFAULT_HOST = '127.0.0.1'
DEFAULT_LOG_LEVEL = 'info'
DEFAULT_VERSION = '1.0.0'


@dataclass
class ServerConfig:
    """Configuration for a server instance.

    This class provides the configuration for an ASGI server instance that can
    be managed by a ServersManager.

    Attributes:
        name: A unique identifier for the server.
        host: The host interface to bind to.
        ports: The ports to attempt to listen on.
        port: The port to listen on.
        version: The version of the server.
        log_level: Logging level for the uvicorn server.
        start_time: The time the server started.
    """

    name: str
    ports: Iterable[int]
    port: int | None = None
    host: str = DEFAULT_HOST
    version: str = DEFAULT_VERSION
    log_level: str = DEFAULT_LOG_LEVEL
    start_time: float | None = None

    def __repr__(self) -> str:
        """Return a string representation of the server configuration.

        Returns:
            A string representation including name, port, host, and log_level.
        """
        return (
            f'ServerConfig(name={self.name}, '
            f'version={self.version}, '
            f'port={self.port}, '
            f'ports={self.ports}, '
            f'host={self.host}, '
            f'log_level={self.log_level})'
        )


class ServerLifecycle(Protocol):
    """Protocol for a server lifecycle.

    A server is defined by a ServerConfig and a lifecycle that defines the
    server's behavior. The server defines a factory method to create
    the app, which will handle HTTP requests.

    A server is different from the application in that the application is a
    collection of endpoints and the server binds to a host and port listening
    for incoming connections. The server is responsible for starting and
    stopping the application. The same application can be hosted by multiple
    servers.

    A server has its own lifecycle that includes starting and shutting down
    independent from that of an application. ASGI defines the interface for
    starting and shutting down the application as a lifespan. ServerLifecycle
    defines the interface for starting and shutting down the server.
    """

    def create(self, config: ServerConfig) -> Application:
        """Create the ASGI application.

        Args:
            config: The configuration for the server.
        """
        ...

    async def on_port_check(self, config: ServerConfig, host: str, port: int) -> None:
        """Callback when a port is attempted to be used.

        Args:
            config: The configuration for the server.
            host: The host to check.
            port: The port to check.
        """
        ...

    async def on_port_available(self, config: ServerConfig, host: str, port: int) -> None:
        """Callback when a port is successfully used.

        Args:
            config: The configuration for the server.
            host: The host that was successfully used.
            port: The port that was successfully used.
        """
        ...

    async def on_port_unavailable(self, config: ServerConfig, host: str, port: int) -> None:
        """Callback when a port is not available.

        Args:
            config: The configuration for the server.
            host: The host that was not available.
            port: The port that was not available.
        """
        ...

    async def on_start(self, config: ServerConfig) -> None:
        """Callback when the server starts.

        Args:
            config: The configuration for the server.
        """
        ...

    async def on_shutdown(self, config: ServerConfig) -> None:
        """Callback when the server shuts down.

        Args:
            config: The configuration for the server.
        """
        ...


class Server:
    """Definition of a server with its configuration.

    The Server class encapsulates the configuration needed to run an ASGI
    application server instance. It supports any ASGI-compliant application
    framework, including Starlette, FastAPI, Django, Quart, Litestar, and custom
    ASGI applications.
    """

    def __init__(
        self,
        config: ServerConfig,
        lifecycle: ServerLifecycle,
        adapter: ASGIServerAdapter,
    ) -> None:
        """Initialize the server.

        Args:
            config: The configuration for the server.
            lifecycle: A definition of the server.
            adapter: The ASGI server adapter to use for serving applications.
                If None, a UvicornAdapter is created by default using the
                factory method.  Use this to specify a different server
                implementation.
        """
        self.config = config
        self.lifecycle = lifecycle
        self.adapter = adapter or ASGIServerAdapter.create(ServerType.UVICORN)
