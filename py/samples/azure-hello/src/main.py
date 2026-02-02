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

"""Azure telemetry sample - Application Insights tracing with Genkit.

This sample demonstrates how to export Genkit telemetry to Azure Application
Insights for distributed tracing, monitoring, and debugging.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                                   │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Application Insights│ Azure's monitoring service. Shows you what your   │
    │                     │ app is doing - like a fitness tracker for code.   │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Connection String   │ Your App Insights "address". Contains the key     │
    │                     │ and endpoint to send traces to.                   │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Traces              │ Records of what happened during a request.        │
    │                     │ Like breadcrumbs showing where your code went.    │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ PII Redaction       │ Model inputs/outputs are hidden by default.       │
    │                     │ Your users' data stays private.                   │
    └─────────────────────┴────────────────────────────────────────────────────┘

Data Flow::

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                    AZURE TELEMETRY DATA FLOW                            │
    │                                                                         │
    │    Your Genkit App                                                      │
    │         │                                                               │
    │         │  (1) You call a flow                                          │
    │         ▼                                                               │
    │    ┌─────────┐     ┌─────────┐                                          │
    │    │say_hello│ ──▶ │ Gemini  │   Each creates a "span" (timing record)  │
    │    │ (flow)  │     │ (model) │                                          │
    │    └─────────┘     └─────────┘                                          │
    │         │               │                                               │
    │         └───────┬───────┘                                               │
    │                 │                                                       │
    │                 │  (2) Spans sent to Azure                              │
    │                 ▼                                                       │
    │    ┌─────────────────────────┐                                          │
    │    │  Azure App Insights     │  View in Azure Portal                    │
    │    │  • Transaction search   │  Debug performance issues                │
    │    │  • Application map      │  See dependencies                        │
    │    └─────────────────────────┘                                          │
    └─────────────────────────────────────────────────────────────────────────┘

Testing This Sample:

    1. Set your Application Insights connection string:
       export APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=..."

    2. Set your Google AI API key:
       export GOOGLE_GENAI_API_KEY="your-key"

    3. Run the sample:
       ./run.sh

    4. Open the DevUI at http://localhost:4000

    5. Run the "say_hello" flow with a name

    6. View traces in Azure Portal → Application Insights → Transaction search
"""

import asyncio

from pydantic import BaseModel, Field
from rich.traceback import install as install_rich_traceback

install_rich_traceback(show_locals=True, width=120, extra_lines=3)

from genkit.ai import Genkit
from genkit.plugins.azure import add_azure_telemetry
from genkit.plugins.google_genai import GoogleAI

# Configure Azure telemetry FIRST (before creating Genkit instance)
# Uses APPLICATIONINSIGHTS_CONNECTION_STRING environment variable
add_azure_telemetry()

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

    This flow demonstrates Azure Application Insights tracing.
    The request/response will be traced and visible in App Insights.

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
