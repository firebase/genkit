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

"""Genkit FastAPI lifespan for Dev UI integration."""

import asyncio
import os
import socket
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from starlette.types import ASGIApp, Lifespan

import uvicorn
from genkit.ai import Genkit
from genkit.ai._runtime import RuntimeManager
from genkit.ai._server import ServerSpec
from genkit.core.reflection import create_reflection_asgi_app


def _find_free_port(start: int = 3100, end: int = 3999) -> int:
    """Find a free port in the given range."""
    for port in range(start, end):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    raise RuntimeError(f'No free port found in range {start}-{end}')


def genkit_lifespan(ai: Genkit) -> Lifespan[ASGIApp]:
    """Create a FastAPI lifespan that registers with Genkit Dev UI.

    When GENKIT_ENV=dev is set, this lifespan starts a reflection server
    and registers the app with the Genkit Developer UI.

    Example:
        ```python
        from fastapi import FastAPI
        from genkit import Genkit
        from genkit.plugins.fastapi import genkit_lifespan

        ai = Genkit(...)
        app = FastAPI(lifespan=genkit_lifespan(ai))
        ```

    Args:
        ai: The Genkit instance to register.

    Returns:
        A lifespan context manager for FastAPI.
    """

    @asynccontextmanager
    async def lifespan(app: Any) -> AsyncGenerator[None, None]:
        reflection_server = None
        runtime_manager = None

        # Only start reflection server in dev mode
        if os.environ.get('GENKIT_ENV') == 'dev':
            port = _find_free_port()
            server_spec = ServerSpec(scheme='http', host='127.0.0.1', port=port)

            # Create and start reflection server
            reflection_app = create_reflection_asgi_app(registry=ai.registry)
            config = uvicorn.Config(
                reflection_app,  # pyrefly: ignore[bad-argument-type]
                host='127.0.0.1',
                port=port,
                log_level='warning',
            )
            reflection_server = uvicorn.Server(config)

            # Register runtime with Dev UI
            runtime_manager = RuntimeManager(server_spec)
            await runtime_manager.__aenter__()

            # Start reflection server in background
            asyncio.create_task(reflection_server.serve())

        yield

        # Cleanup
        if reflection_server:
            reflection_server.should_exit = True
        if runtime_manager:
            await runtime_manager.__aexit__(None, None, None)

    return lifespan
