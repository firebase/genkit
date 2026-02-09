#!/usr/bin/env python3
# pyright: reportUnknownMemberType=false
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

"""Multi-Server Pattern - Run multiple ASGI apps in parallel.

This sample demonstrates how to run multiple HTTP servers concurrently,
each serving different parts of your application:

┌────────────────────────────────────────────┐
│           ServerManager                    │
│  (coordinates lifecycle + shutdown)        │
└────────────────────────────────────────────┘
         │              │
         ▼              ▼
    ┌─────────┐    ┌─────────┐
    │ Public  │    │ Admin   │
    │ :3400   │    │ :3401   │
    └─────────┘    └─────────┘
         │              │
         ▼              ▼
    User APIs      Internal APIs

Use cases:
- Public API (:3400) + Admin API (:3401) on different ports
- HTTP API + gRPC API running side-by-side
- Multiple microservices in one deployment
- Development server + metrics server

All servers start together, stop together, and handle SIGTERM gracefully.
"""

from __future__ import annotations

import asyncio
from typing import override

from litestar import Controller, Litestar, get
from litestar.datastructures import State

from genkit import Genkit
from genkit.core.logging import get_logger
from genkit.web.manager import (
    AbstractBaseServer,
    Server,
    ServerConfig,
    ServerManager,
    UvicornAdapter,
)

logger = get_logger(__name__)


# === PUBLIC API SERVER (Port 3400) ===

class PublicAPIController(Controller):
    """Public-facing API endpoints."""
    
    path: str = '/api'
    
    @get('/hello')
    async def hello(self) -> dict[str, str | int]:
        return {"message": "Hello from Public API", "port": 3400}
    
    @get('/status')
    async def status(self) -> dict[str, str]:
        return {"status": "healthy", "server": "public"}


class PublicServerLifecycle(AbstractBaseServer):
    """Lifecycle manager for the public API server."""
    
    @override
    def create(self, config: ServerConfig) -> Litestar:  # type: ignore[override]
        """Create the public API application."""
        
        async def on_startup() -> None:
            await logger.ainfo(f"✅ Public API started on port {config.port}")
        
        async def on_shutdown() -> None:
            await logger.ainfo("🛑 Public API stopped")
        
        return Litestar(
            route_handlers=[PublicAPIController],
            on_startup=[on_startup],
            on_shutdown=[on_shutdown],
            state=State({'config': config}),
        )


# === ADMIN API SERVER (Port 3401) ===

class AdminAPIController(Controller):
    """Admin/internal API endpoints."""
    
    path: str = '/admin'
    
    @get('/metrics')
    async def metrics(self) -> dict[str, str | int]:
        return {
            "users": 1000,
            "requests_today": 45000,
            "server": "admin",
        }
    
    @get('/config')
    async def config(self) -> dict[str, str]:
        return {
            "environment": "development",
            "version": "1.0.0",
        }


class AdminServerLifecycle(AbstractBaseServer):
    """Lifecycle manager for the admin API server."""
    
    @override
    def create(self, config: ServerConfig) -> Litestar:  # type: ignore[override]
        """Create the admin API application."""
        
        async def on_startup() -> None:
            await logger.ainfo(f"✅ Admin API started on port {config.port}")
        
        async def on_shutdown() -> None:
            await logger.ainfo("🛑 Admin API stopped")
        
        return Litestar(
            route_handlers=[AdminAPIController],
            on_startup=[on_startup],
            on_shutdown=[on_shutdown],
            state=State({'config': config}),
        )


# === MAIN ENTRY POINT ===

async def main() -> None:
    """Run both servers in parallel."""
    
    # Optional: Initialize Genkit if you need flows
    g = Genkit(plugins=[])
    
    @g.flow()
    async def example_flow(name: str) -> str:
        """Example Genkit flow (not exposed in this sample)."""
        return f"Hello {name} from multi-server!"
    
    # Use the flow to avoid "unused" warning
    _ = example_flow
    
    # Define the servers to run
    servers = [
        Server(
            config=ServerConfig(
                name='public-api',
                host='localhost',
                port=3400,
                ports=list(range(3400, 3410)),  # Fallback ports if 3400 is busy
            ),
            lifecycle=PublicServerLifecycle(),
            adapter=UvicornAdapter(),
        ),
        Server(
            config=ServerConfig(
                name='admin-api',
                host='localhost',
                port=3401,
                ports=list(range(3401, 3411)),  # Fallback ports if 3401 is busy
            ),
            lifecycle=AdminServerLifecycle(),
            adapter=UvicornAdapter(),
        ),
    ]
    
    # Start all servers (blocks until SIGTERM/SIGINT)
    manager = ServerManager()
    await logger.ainfo("🚀 Starting multi-server deployment...")
    await manager.run_all(servers)


if __name__ == '__main__':
    asyncio.run(main())
