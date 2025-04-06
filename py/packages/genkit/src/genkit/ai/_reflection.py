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

"""Reflection server implementation."""

import structlog

from genkit.ai.server import ServerSpec
from genkit.core.reflection import create_reflection_asgi_app
from genkit.core.registry import Registry
from genkit.web.manager import AbstractBaseServer, Server, ServerConfig, UvicornAdapter, find_free_port_sync
from genkit.web.typing import Application

logger = structlog.get_logger(__name__)


class ReflectionServerLifecycle(AbstractBaseServer):
    """Reflection server lifecycle."""

    def __init__(self, registry: Registry, spec: ServerSpec) -> None:
        """Initialize the reflection server."""
        self._registry = registry
        self._spec = spec

    def create(self, config: ServerConfig) -> Application:
        """Create an ASGI application instance."""

        async def on_app_startup() -> None:
            """Handle application startup."""
            logger.info('Reflection server started', port=self._spec.port)

        async def on_app_shutdown() -> None:
            """Handle application shutdown."""
            logger.info('Reflection server stopped')

        return create_reflection_asgi_app(
            registry=self._registry,
            on_app_startup=on_app_startup,
            on_app_shutdown=on_app_shutdown,
        )


def make_managed_reflection_server(registry: Registry, server_spec: ServerSpec) -> Server:
    """Make a reflection server.

    Args:
        registry: The registry to use for the reflection server.
        server_spec: The server specification to use for the reflection server.

    Returns:
        A reflection server.
    """
    return Server(
        config=ServerConfig(
            name='reflection-api',
            host=server_spec.host,
            port=server_spec.port,
            ports=range(server_spec.port, server_spec.port + 10),
        ),
        lifecycle=ReflectionServerLifecycle(registry, server_spec),
        adapter=UvicornAdapter(),
    )


def make_reflection_server_spec(reflection_server_spec: ServerSpec | None = None) -> ServerSpec:
    """Get the reflection server spec.

    Returns:
        The reflection server spec.
    """
    if reflection_server_spec is not None:
        return reflection_server_spec
    return ServerSpec(scheme='http', host='127.0.0.1', port=find_free_port_sync(3100, 3999))
