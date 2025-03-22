#!/usr/bin/env python3
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


"""Example demonstrating how to use the Genkit flows API server.

This example shows how to:
1. Create flows using the Genkit registry
2. Start a flows API server to expose the flows as HTTP endpoints
3. Interact with the server using HTTP requests (demonstrated with curl
   commands)

Usage:
    python flows_server_example.py

Then in another terminal:
    # For a non-streaming request:
    curl -X POST http://localhost:3400/testFlow \
         -H "Content-Type: application/json" \
         -d '{"data": "Hello, world!"}'

    # For a streaming request:
    curl -X POST http://localhost:3400/streamy?stream=true \
         -H "Content-Type: application/json" \
         -d '{"data": {"count": 5}}'
"""

import asyncio
import time
from collections.abc import Callable
from typing import Any

import structlog

from genkit import (
    define_flow,
    define_streaming_flow,
    init,
)
from genkit.core.flow_server import start_flows_server

# Set up logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt='%Y-%m-%d %H:%M:%S'),
        structlog.dev.ConsoleRenderer(),
    ]
)
logger = structlog.get_logger()


async def test_flow(ctx: dict[str, Any], input_text: str) -> str:
    """A simple flow that echoes the input with a timestamp.

    Args:
        ctx: The execution context.
        input_text: The input text to echo.

    Returns:
        The input text with a timestamp.
    """
    logger.info('Running test flow', input=input_text)
    return f'{input_text} - processed at {time.time()}'


async def streaming_flow(
    ctx: dict[str, Any],
    count: int,
    callback: Callable[[dict[str, int]], None] | None = None,
) -> str:
    """A simple streaming flow that emits numbered chunks.

    Args:
        ctx: The execution context.
        count: How many chunks to emit.
        callback: Optional callback for streaming chunks.

    Returns:
        A summary of the streaming operation.
    """
    logger.info('Running streaming flow', count=count)
    emitted = 0

    if callback:
        for i in range(count):
            chunk = {'count': i}
            await callback(chunk)
            emitted += 1
            # Simulate some processing time
            await asyncio.sleep(0.5)

    return f'Done streaming {count} chunks, emitted {emitted}'


async def main():
    """Initialize Genkit, register flows, and start the server."""
    # Initialize Genkit
    g = await init()

    # Register flows
    define_flow(g, 'testFlow', test_flow)
    define_streaming_flow(g, 'streamy', streaming_flow)

    # Start the flows server
    logger.info('Starting flows server on http://localhost:3400')
    logger.info('Available flows: testFlow, streamy')
    logger.info('\nExample commands:')
    logger.info(
        '  curl -X POST http://localhost:3400/testFlow \
             -H "Content-Type: application/json" \
             -d \'{"data": "Hello, world!"}\''
    )
    logger.info(
        '  curl -X POST http://localhost:3400/streamy?stream=true \
             -H "Content-Type: application/json" \
             -d \'{"data": {"count": 5}}\''
    )

    # Start the server (this will block until the server exits)
    start_flows_server(
        g.registry,
        host='localhost',
        port=3400,
    )


if __name__ == '__main__':
    asyncio.run(main())
