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

"""Server implementation."""

import structlog

from genkit.ai import Genkit
from genkit.core.flows import create_flows_asgi_app
from genkit.web.manager import (
    AbstractBaseServer,
    Server,
    ServerConfig,
    ServerManager,
    UvicornAdapter,
)
from genkit.web.typing import Application

logger = structlog.get_logger(__name__)


class FlowsServerLifecycle(AbstractBaseServer):
    """Flows server implementing the ServerLifecycleProtocol."""

    def __init__(self, ai: Genkit) -> None:
        """Initialize the flows server."""
        self.ai = ai

    def create(self, config: ServerConfig) -> Application:
        """Create a flows application instance."""

        async def on_app_startup() -> None:
            """Handle application startup."""
            await logger.ainfo('[LIFESPAN] Starting flows server...')
            # Any initialization could go here

        async def on_app_shutdown() -> None:
            """Handle application shutdown."""
            await logger.ainfo('[LIFESPAN] Shutting down flows server...')

        return create_flows_asgi_app(
            registry=self.ai.registry,
            context_providers=[],
            on_app_startup=on_app_startup,
            on_app_shutdown=on_app_shutdown,
        )


async def server_main(ai: Genkit) -> None:
    """Entry point function for the server application."""
    servers = [
        Server(
            config=ServerConfig(
                name='flows',
                host='localhost',
                port=3400,
                ports=range(3400, 3410),
            ),
            lifecycle=FlowsServerLifecycle(ai),
            adapter=UvicornAdapter(),
        ),
    ]

    mgr = ServerManager()

    await logger.ainfo('Starting servers...')
    await mgr.run_all(servers)
