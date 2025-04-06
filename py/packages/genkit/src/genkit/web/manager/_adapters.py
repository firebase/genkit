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

"""ASGI server adapters for different server implementations.

This module implements the adapter pattern to provide a clean abstraction over
different ASGI server implementations. Each adapter conforms to a common
interface, allowing the ServersManager to operate independently of the specific
ASGI server being used. The objectives are separation of concerns,
extensibility, maintainbility, and dependency management.

## Key components

| Component         | Description                                        |
|-------------------|----------------------------------------------------|
| ServerType        | Enum defining the supported ASGI server types      |
| ASGIServerAdapter | Abstract base class defining the adapter interface |
| UvicornAdapter    | Concrete adapter for the Uvicorn ASGI server       |
| GranianAdapter    | Concrete adapter for the Granian ASGI server       |

Usage:

    ```python
    # Create a specific adapter directly
    adapter = UvicornAdapter()

    # Or use the factory method with enum
    adapter = ASGIServerAdapter.create(ServerType.UVICORN)

    # Then use the adapter to serve an application
    await adapter.serve(app, host='127.0.0.1', port=8000)
    ```
"""

from __future__ import annotations

import abc
import socket
import sys

import structlog

from genkit.web.typing import Application

logger = structlog.get_logger(__name__)

if sys.version_info < (3, 11):
    from strenum import StrEnum
else:
    from enum import StrEnum


class ServerType(StrEnum):
    """Supported ASGI server types.

    The ServerType enum provides a type-safe way to specify the type of ASGI
    server to use. It is used by the ASGIServerAdapter factory method to
    determine which adapter to use.

    The supported values are:

    - `UVICORN`: For serving applications with Uvicorn
    - `GRANIAN`: For serving applications with Granian
    """

    UVICORN = 'uvicorn'
    GRANIAN = 'granian'


class ASGIServerAdapter(abc.ABC):
    """Abstract base class for ASGI server adapters.

    This class defines the interface that all concrete ASGI server adapters must
    implement. It follows the adapter pattern to provide a consistent interface
    for different server implementations.

    The adapter pattern allows the ServersManager to work with any ASGI server
    implementation without being tightly coupled to their specific APIs. Each
    concrete adapter handles the details of configuring and starting its
    respective server.

    Concrete implementations include:

    | Adapter          | Purpose                               |
    |------------------|---------------------------------------|
    | `UvicornAdapter` | For serving applications with Uvicorn |
    | `GranianAdapter` | For serving applications with Granian |

    New server implementations can be added by creating new adapter classes that
    inherit from this base class.
    """

    @abc.abstractmethod
    async def serve(
        self,
        app: Application,
        host: str,
        port: int,
        log_level: str = 'info',
    ) -> None:
        """Start and run the server.

        Args:
            app: The ASGI application to serve
            host: The host interface to bind to
            port: The port to bind to
            log_level: The logging level to use

        Raises:
            Exception: If the server fails to start or encounters an error
        """
        pass

    @staticmethod
    def create(server_type: ServerType) -> ASGIServerAdapter:
        """Factory method to create the appropriate adapter.

        This static method acts as a factory that instantiates the correct
        adapter based on the specified server type. It encapsulates the creation
        logic and provides a single entry point for obtaining any adapter
        implementation.

        Args:
            server_type: The type of server to create an adapter for,
                         using the ServerType enum

        Returns:
            An adapter instance implementing ASGIServerAdapter

        Raises:
            ValueError: If the server type is not supported
        """
        match server_type:
            case ServerType.UVICORN:
                return UvicornAdapter()
            case ServerType.GRANIAN:
                return GranianAdapter()
            case _:
                raise ValueError(f'Unsupported server type: {server_type}')


class UvicornAdapter(ASGIServerAdapter):
    """Adapter for the Uvicorn ASGI server.

    This adapter implements the ASGIServerAdapter interface for Uvicorn.  It
    handles the specific details of configuring and starting a Uvicorn server,
    including setting up the configuration and ensuring it works with the shared
    event loop.

    The `uvicorn` package is imported lazily in the serve method to avoid
    unnecessary imports when the adapter is not being used.
    """

    async def serve(
        self,
        app: Application,
        host: str,
        port: int,
        log_level: str = 'info',
    ) -> None:
        """Start and run a Uvicorn server.

        Args:
            app: The ASGI application to serve
            host: The host interface to bind to
            port: The port to bind to
            log_level: The logging level to use
        """
        import uvicorn

        # Configure Uvicorn
        config = uvicorn.Config(
            app,
            host=host,
            port=port,
            log_level=log_level,
            # TODO: Disable after we complete logging middleware.
            # log_config=None,
            # access_log=True,
        )

        server = uvicorn.Server(config)

        # Modified server startup to work with shared event loop
        server.config.setup_event_loop = lambda: None

        await logger.ainfo(
            'Starting uvicorn server',
            host=host,
            port=port,
        )

        await server.serve()


class GranianAdapter(ASGIServerAdapter):
    """Adapter for the Granian ASGI server.

    This adapter implements the ASGIServerAdapter interface for Granian.  It
    handles the specific details of configuring and starting a Granian server,
    including mapping log levels from string format to Python logging levels.

    The Granian package is imported lazily in the serve method to avoid
    unnecessary imports when the adapter is not being used. If Granian is not
    available, an ImportError will be raised when the serve method is called.
    """

    async def serve(
        self,
        app: Application,
        host: str,
        port: int,
        log_level: str = 'info',
    ) -> None:
        """Start and run a Granian server.

        Args:
            app: The ASGI application to serve
            host: The host interface to bind to
            port: The port to bind to
            log_level: The logging level to use, mapped to Granian's levels

        Raises:
            ImportError: If Granian is not available
            Exception: If the server fails to start or encounters an error
        """
        import granian

        # Granian accepts the log level as a string
        # Valid values are: 'trace', 'debug', 'info', 'warn', 'error', or 'off'
        valid_levels = ['trace', 'debug', 'info', 'warn', 'error', 'off']
        granian_log_level = log_level.lower() if log_level.lower() in valid_levels else 'info'

        if host == 'localhost':
            ip_address = '127.0.0.1'
        else:
            try:
                ip_address = socket.gethostbyname(host)
            except socket.gaierror:
                ip_address = host

        await logger.ainfo(
            'Starting granian server',
            host=host,
            ip=ip_address,
            port=port,
        )

        try:
            await granian.Granian(
                app,
                address=ip_address,
                port=port,
                workers=1,
                loop='auto',
                log_level=granian_log_level,
            ).serve()
        except Exception as e:
            await logger.aerror(
                'Error starting granian server',
                host=host,
                ip=ip_address,
                port=port,
                error=e,
            )
            raise
