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

"""Third-party observability sample - Multiple backend support with Genkit.

This sample demonstrates how to export Genkit telemetry to popular third-party
observability platforms using simple presets.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                                   │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Observability       │ Seeing what your app is doing. Like X-ray vision  │
    │                     │ for your code - see timing, errors, everything!   │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Backend Preset      │ Pre-configured settings for a service. Just add   │
    │                     │ your API key - no URLs to remember!               │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Sentry              │ Error tracking that also does tracing. Great for  │
    │                     │ debugging crashes and performance issues.         │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Honeycomb           │ Query your traces like a database. Great for      │
    │                     │ exploring and debugging complex issues.           │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Datadog             │ Full APM suite. Traces, metrics, logs, all in     │
    │                     │ one place with dashboards and alerts.             │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Grafana Cloud       │ Open-source stack. Tempo for traces, Loki for     │
    │                     │ logs, create custom dashboards.                   │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Axiom               │ Fast, SQL-like queries over traces and logs.      │
    │                     │ Great for high-volume data.                       │
    └─────────────────────┴────────────────────────────────────────────────────┘

When to Use What::

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                     PLATFORM SELECTION GUIDE                            │
    │                                                                         │
    │   "I want native AWS/GCP/Azure integration"                             │
    │       → Use aws, google-cloud, or azure plugins instead                 │
    │                                                                         │
    │   "I'm already using Sentry for errors"                                 │
    │       → backend="sentry" (add tracing to your existing setup)           │
    │                                                                         │
    │   "I want to query traces interactively"                                │
    │       → backend="honeycomb" (best query experience)                     │
    │                                                                         │
    │   "I need full APM with dashboards"                                     │
    │       → backend="datadog" (all-in-one platform)                         │
    │                                                                         │
    │   "I want open-source based tooling"                                    │
    │       → backend="grafana" (open-source ecosystem)                       │
    │                                                                         │
    │   "I need to handle high volume efficiently"                            │
    │       → backend="axiom" (fast SQL queries)                              │
    └─────────────────────────────────────────────────────────────────────────┘

Data Flow::

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                  OBSERVABILITY TELEMETRY DATA FLOW                      │
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
    │                 │  (2) Sent via OTLP                                    │
    │                 ▼                                                       │
    │    ┌─────────────────────────────────────────────────────────────────┐  │
    │    │  Your Chosen Backend                                            │  │
    │    │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐        │  │
    │    │  │ Sentry │ │Honeycmb│ │Datadog │ │Grafana │ │ Axiom  │        │  │
    │    │  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘        │  │
    │    └─────────────────────────────────────────────────────────────────┘  │
    └─────────────────────────────────────────────────────────────────────────┘

Testing This Sample:

    1. Set your backend credentials (example: Honeycomb):
       export HONEYCOMB_API_KEY="your-key"

    2. Set your Google AI API key:
       export GOOGLE_GENAI_API_KEY="your-key"

    3. Run the sample:
       ./run.sh

    4. Open the DevUI at http://localhost:4000

    5. Run the "say_hello" flow with a name

    6. View traces in your backend's dashboard
"""

import asyncio

from pydantic import BaseModel, Field

from genkit.ai import Genkit
from genkit.plugins.google_genai import GoogleAI
from genkit.plugins.observability import configure_telemetry
from samples.shared.logging import setup_sample

setup_sample()

# Configure observability telemetry FIRST (before creating Genkit instance)
# Change backend to: "sentry", "datadog", "grafana", "axiom" as needed
configure_telemetry(
    backend='honeycomb',  # Change this to your preferred backend
    service_name='observability-hello',
    service_version='1.0.0',
)

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

    This flow demonstrates third-party observability tracing.
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
