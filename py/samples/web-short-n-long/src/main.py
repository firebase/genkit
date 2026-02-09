#!/usr/bin/env python3
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
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

"""Genkit Deployment Modes - Run flows as CLI scripts OR web servers.

This sample demonstrates the two fundamental ways to deploy Genkit flows:

1. **Short-lived mode** (CLI/batch): Run a flow once and exit
   - Use for: CLI tools, cron jobs, batch processing, Lambda functions
   - Example: python src/main.py

2. **Long-running mode** (HTTP server): Start a server that handles requests forever
   - Use for: REST APIs, Cloud Run, Kubernetes, always-on services  
   - Example: python src/main.py --server

The same @ai.flow() functions work in both modes - the only difference
is the execution wrapper.
"""

import argparse
import os

import uvicorn
from pydantic import BaseModel, Field

from genkit import Genkit
from genkit.core.flows import create_flows_asgi_app
from genkit.core.logging import get_logger
from genkit.plugins.google_genai import GoogleAI  # type: ignore[import-untyped]

logger = get_logger(__name__)

# Initialize Genkit
if 'GEMINI_API_KEY' not in os.environ:
    os.environ['GEMINI_API_KEY'] = input('Please enter your GEMINI_API_KEY: ')

ai = Genkit(
    plugins=[GoogleAI()],
    model='googleai/gemini-3-flash-preview',
)


# Define input schema
class GreetingInput(BaseModel):
    """Input for greeting flows."""
    name: str = Field(default='World', description='Name to greet')


# Define your Genkit flows
@ai.flow()  # type: ignore[misc]
async def greet(input: GreetingInput) -> str:
    """Generate a friendly greeting.
    
    This flow works identically in both modes:
    - Short mode: Called directly, returns result
    - Server mode: Exposed as POST //flow/greet
    """
    resp = await ai.generate(prompt=f"Say a friendly hello to {input.name}")
    return resp.text


# MODE 1: Short-lived execution (run once and exit)
async def run_once():
    """Execute a flow once and exit.
    
    Use cases:
    - CLI tools: python main.py --name Alice
    - Cron jobs: Run daily at midnight
    - Batch processing: Process a file and exit
    - Serverless: AWS Lambda, Cloud Functions (one invocation)
    """
    await logger.ainfo("Running in short-lived mode...")
    result = await greet(GreetingInput(name="World"))
    await logger.ainfo(f"Result: {result}")
    await logger.ainfo("Exiting.")


# MODE 2: Long-running HTTP server
async def run_server(port: int = 3400) -> None:
    """Start HTTP server that runs forever.
    
    Use cases:
    - REST APIs: Public-facing service
    - Cloud Run / App Engine: Container stays running
    - Kubernetes: Long-running pod
    - Development: Keep server up, test with curl
    
    All @ai.flow() functions are automatically exposed as HTTP endpoints:
    - POST //flow/greet with body: {"data": {"name": "Alice"}}
    """
    await logger.ainfo(f"Starting server on port {port}...")
    
    async def on_startup() -> None:
        logger.info("[LIFESPAN] Server started")
    
    async def on_shutdown() -> None:
        logger.info("[LIFESPAN] Server stopped")
    
    app = create_flows_asgi_app(
        registry=ai.registry,
        on_app_startup=on_startup,
        on_app_shutdown=on_shutdown,
    )
    
    config = uvicorn.Config(app, host='localhost', port=port, log_level='info')
    server = uvicorn.Server(config)
    await server.serve()


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Genkit deployment modes demo')
    parser.add_argument('--server', action='store_true', 
                       help='Run as HTTP server (default: run once and exit)')
    parser.add_argument('--port', type=int, default=3400,
                       help='Server port (only used with --server)')
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    
    # Select execution mode based on --server flag
    if args.server:
        ai.run_main(run_server(args.port))
    else:
        ai.run_main(run_once())
