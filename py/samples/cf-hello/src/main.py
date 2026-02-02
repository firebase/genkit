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

"""Cloudflare/OTLP telemetry sample - Generic OTLP export with Genkit.

This sample demonstrates how to export Genkit telemetry via OpenTelemetry
Protocol (OTLP) to any compatible backend. The "cf" plugin is named after
Cloudflare but works with any OTLP receiver.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                                   │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ OTLP                │ OpenTelemetry Protocol. A standard way to send    │
    │                     │ traces. Like USB for observability data.          │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Endpoint            │ Where your traces go. Any OTLP receiver works:    │
    │                     │ Grafana, Honeycomb, Axiom, custom, etc.           │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Bearer Token        │ Your API key for authentication. Sent in the      │
    │                     │ Authorization header with "Bearer" prefix.        │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ PII Redaction       │ Model inputs/outputs are hidden by default.       │
    │                     │ Your users' data stays private.                   │
    └─────────────────────┴────────────────────────────────────────────────────┘

Compatible Backends::

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                  WORKS WITH ANY OTLP RECEIVER                           │
    │                                                                         │
    │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐        │
    │  │ Grafana    │  │ Honeycomb  │  │ Axiom      │  │ SigNoz     │        │
    │  │ Cloud Tempo│  │            │  │            │  │            │        │
    │  └────────────┘  └────────────┘  └────────────┘  └────────────┘        │
    │                                                                         │
    │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐        │
    │  │ Jaeger     │  │ Zipkin     │  │ LightStep  │  │ Custom     │        │
    │  │            │  │            │  │            │  │ Collector  │        │
    │  └────────────┘  └────────────┘  └────────────┘  └────────────┘        │
    └─────────────────────────────────────────────────────────────────────────┘

Data Flow::

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                       OTLP TELEMETRY DATA FLOW                          │
    │                                                                         │
    │    Your Genkit App                                                      │
    │         │                                                               │
    │         │  (1) You call a flow                                          │
    │         ▼                                                               │
    │    ┌─────────┐     ┌─────────┐                                          │
    │    │say_hello│ ──▶ │ Gemini  │   Each creates a "span"                  │
    │    │ (flow)  │     │ (model) │                                          │
    │    └─────────┘     └─────────┘                                          │
    │         │               │                                               │
    │         └───────┬───────┘                                               │
    │                 │                                                       │
    │                 │  (2) Sent via OTLP/HTTP                               │
    │                 ▼                                                       │
    │    ┌─────────────────────────┐                                          │
    │    │  Your OTLP Backend      │  Grafana, Honeycomb, Axiom, etc.         │
    │    │  • View traces          │                                          │
    │    │  • Debug issues         │                                          │
    │    │  • Set alerts           │                                          │
    │    └─────────────────────────┘                                          │
    └─────────────────────────────────────────────────────────────────────────┘

Testing This Sample:

    1. Set your OTLP endpoint:
       export CF_OTLP_ENDPOINT="https://your-otlp-endpoint/v1/traces"

    2. Set your API token (if required):
       export CF_API_TOKEN="your-api-token"

    3. Set your Google AI API key:
       export GOOGLE_GENAI_API_KEY="your-key"

    4. Run the sample:
       ./run.sh

    5. Open the DevUI at http://localhost:4000

    6. Run the "say_hello" flow with a name

    7. View traces in your OTLP backend's dashboard
"""

import asyncio

from pydantic import BaseModel, Field
from rich.traceback import install as install_rich_traceback

install_rich_traceback(show_locals=True, width=120, extra_lines=3)

from genkit.ai import Genkit
from genkit.plugins.cf import add_cf_telemetry
from genkit.plugins.google_genai import GoogleAI

# Configure OTLP telemetry FIRST (before creating Genkit instance)
# Uses CF_OTLP_ENDPOINT and CF_API_TOKEN environment variables
add_cf_telemetry()

# Initialize Genkit with Google AI
ai = Genkit(
    plugins=[GoogleAI()],
    model='googleai/gemini-2.0-flash',
)


class HelloInput(BaseModel):
    """Input for the say_hello flow."""

    name: str = Field(default='World', description='Name to greet')


@ai.flow()
async def say_hello(input: HelloInput) -> str:
    """Say hello to someone.

    This flow demonstrates OTLP tracing.
    The request/response will be traced and visible in your backend.

    Args:
        input: Contains the name to greet.

    Returns:
        A personalized greeting from the AI model.
    """
    response = await ai.generate(prompt=f'Say a friendly hello to {input.name}!')
    return response.text


async def main() -> None:
    """Run the sample and keep the server alive."""
    await asyncio.Event().wait()


if __name__ == '__main__':
    ai.run_main(main())
