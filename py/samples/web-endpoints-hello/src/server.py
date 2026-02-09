# Copyright 2026 Google LLC
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

"""ASGI server helpers — granian, uvicorn, and hypercorn.

All three servers accept any ASGI application (FastAPI, Litestar, Quart, etc.)
and serve it on the configured port with production-tuned defaults.

Two servers run concurrently at startup:

1. An ASGI server (granian, uvicorn, or hypercorn) serves the app on ``$PORT``.
2. ``ai.run_main()`` starts the Genkit reflection server on ``:4000`` (dev only).

For multi-worker production deployments, use ``gunicorn`` with
``UvicornWorker`` (see ``gunicorn.conf.py`` and ``src/asgi.py``).
The embedded servers here are single-process — each function runs
the server as an ``asyncio`` task inside ``ai.run_main()``.

Keep-alive tuning:

    Server keep-alive must exceed the load balancer idle timeout
    (typically 60s for Cloud Run, ALB, Azure Front Door). We default
    to 75s. If the server closes a connection before the LB does,
    clients see sporadic 502 errors.
"""

from collections.abc import Callable
from typing import Any

import uvicorn

from .connection import KEEP_ALIVE_TIMEOUT

# ASGI application type — frameworks return callables matching the ASGI spec.
# Using Callable[..., Any] since FastAPI, Litestar, and Quart all satisfy this.
ASGIApp = Callable[..., Any]


async def serve_uvicorn(
    app: ASGIApp,
    port: int,
    log_level: str,
    timeout_keep_alive: int = KEEP_ALIVE_TIMEOUT,
) -> None:
    """Start the ASGI app via uvicorn.

    Args:
        app: Any ASGI-compatible application.
        port: TCP port to bind.
        log_level: Logging level (e.g. ``"info"``, ``"debug"``).
        timeout_keep_alive: Keep-alive timeout in seconds (default: 75).
    """
    config = uvicorn.Config(
        app,
        host="0.0.0.0",  # noqa: S104 - bind to all interfaces for container/dev use
        port=port,
        log_level=log_level,
        timeout_keep_alive=timeout_keep_alive,
    )
    server = uvicorn.Server(config)
    await server.serve()


async def serve_granian(
    app: ASGIApp,
    port: int,
    log_level: str,
    timeout_keep_alive: int = KEEP_ALIVE_TIMEOUT,
) -> None:
    """Start the ASGI app via granian's embedded async server.

    Granian is a Rust-powered ASGI server that provides high throughput
    with its own optimized event loop. The embed API runs the server
    as an asyncio task, compatible with ``ai.run_main()``.

    Args:
        app: Any ASGI-compatible application.
        port: TCP port to bind.
        log_level: Logging level (unused by granian embed, kept for API
            symmetry).
        timeout_keep_alive: Kept for API symmetry with other server
            functions. Granian 2.x manages keep-alive internally via
            ``HTTP1Settings``; an explicit timeout knob is not exposed.
    """
    try:
        from granian.constants import Interfaces  # noqa: PLC0415 — granian is one of three ASGI server choices
        from granian.http import HTTP1Settings  # noqa: PLC0415 — granian is one of three ASGI server choices
        from granian.server.embed import Server  # noqa: PLC0415 — granian is one of three ASGI server choices
    except ImportError as err:
        raise SystemExit(
            "granian is not installed. Install it with:\n"
            "  pip install granian\n"
            'Or add "granian>=1.0.0" to your pyproject.toml dependencies.'
        ) from err

    server = Server(
        app,
        address="0.0.0.0",  # noqa: S104 — bind to all interfaces for container/dev use
        port=port,
        interface=Interfaces.ASGI,
        http1_settings=HTTP1Settings(keep_alive=True),
    )
    await server.serve()


async def serve_hypercorn(
    app: ASGIApp,
    port: int,
    log_level: str,
    timeout_keep_alive: int = KEEP_ALIVE_TIMEOUT,
) -> None:
    """Start the ASGI app via Hypercorn.

    Hypercorn supports HTTP/2 and is written by the same author as Quart,
    making it the natural pairing for Quart apps. It uses anyio under the
    hood, supporting both asyncio and trio event loops.

    Args:
        app: Any ASGI-compatible application.
        port: TCP port to bind.
        log_level: Logging level (e.g. ``"info"``, ``"debug"``).
        timeout_keep_alive: Keep-alive timeout in seconds (default: 75).
    """
    try:
        from hypercorn.asyncio import serve  # noqa: PLC0415 — hypercorn is one of three ASGI server choices
        from hypercorn.config import Config  # noqa: PLC0415 — hypercorn is one of three ASGI server choices
    except ImportError as err:
        raise SystemExit(
            "hypercorn is not installed. Install it with:\n"
            "  pip install hypercorn\n"
            'Or add "hypercorn>=0.17.0" to your pyproject.toml dependencies.'
        ) from err

    config = Config()
    config.bind = [f"0.0.0.0:{port}"]
    config.loglevel = log_level.upper()
    config.keep_alive_timeout = timeout_keep_alive
    await serve(app, config)
