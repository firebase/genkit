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

"""Azure Plugin for Genkit.

This plugin provides Azure observability integration for Genkit,
enabling telemetry export to Azure Monitor Application Insights.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                                   │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Application Insights│ Azure's detective for your app. Collects traces,  │
    │                     │ errors, and performance data so you can debug.    │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Telemetry           │ Data about what your app is doing. Like a         │
    │                     │ fitness tracker but for your code.                │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Trace               │ The full story of one request. Shows every step   │
    │                     │ from start to finish (flow → model → response).   │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Span                │ One step in a trace. "Called Gemini model" or     │
    │                     │ "Ran my_flow" - each is a span with timing info.  │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Connection String   │ Your Application Insights "address". Like a       │
    │                     │ mailing address - tells Azure where to send data. │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ PII Redaction       │ Hiding sensitive data in traces. We don't send    │
    │                     │ your actual prompts/responses by default.         │
    └─────────────────────┴────────────────────────────────────────────────────┘

Data Flow::

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                    HOW YOUR CODE GETS TRACED                           │
    │                                                                         │
    │    Your Genkit App                                                      │
    │         │                                                               │
    │         │  (1) You call a flow, model, or tool                          │
    │         ▼                                                               │
    │    ┌─────────┐     ┌─────────┐     ┌─────────┐                          │
    │    │ Flow    │ ──▶ │ Model   │ ──▶ │ Tool    │   Each creates a "span"  │
    │    │ (span)  │     │ (span)  │     │ (span)  │   (a timing record)      │
    │    └─────────┘     └─────────┘     └─────────┘                          │
    │         │               │               │                               │
    │         └───────────────┼───────────────┘                               │
    │                         │                                               │
    │                         │  (2) Spans adjusted (PII redacted, errors)    │
    │                         ▼                                               │
    │              ┌─────────────────────┐                                    │
    │              │ AdjustingExporter   │                                    │
    │              │ (optional redaction)│                                    │
    │              └──────────┬──────────┘                                    │
    │                         │                                               │
    │                         │  (3) Sent to Azure via OTLP                   │
    │                         ▼                                               │
    │              ┌─────────────────────┐                                    │
    │              │ Azure Monitor       │                                    │
    │              │ OTLP Exporter       │                                    │
    │              └──────────┬──────────┘                                    │
    │                         │                                               │
    │    ════════════════════════════════════════════════════                 │
    │                         │                                               │
    │                         ▼                                               │
    │              ┌─────────────────────┐                                    │
    │              │   Azure Portal      │   View traces in Application      │
    │              │   Application       │   Insights. Debug latency,        │
    │              │   Insights          │   errors, and dependencies.       │
    │              └─────────────────────┘                                    │
    └─────────────────────────────────────────────────────────────────────────┘

Architecture Overview::

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                         AZURE TELEMETRY PLUGIN                          │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  __init__.py - Plugin Entry Point                                       │
    │  ├── add_azure_telemetry() - Main configuration function                │
    │  └── package_name() - Plugin identification                             │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  telemetry/tracing.py - Distributed Tracing                             │
    │  ├── Azure Monitor OTLP exporter configuration                          │
    │  ├── Application Insights connection string handling                    │
    │  └── PII redaction via AdjustingTraceExporter                           │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐      │
    │  │ Genkit App   │───►│ OpenTelemetry│───►│ Azure Application    │      │
    │  │ (actions,    │    │ SDK + Azure  │    │ Insights             │      │
    │  │  flows)      │    │ Exporter     │    │                      │      │
    │  └──────────────┘    └──────────────┘    └──────────────────────┘      │
    └─────────────────────────────────────────────────────────────────────────┘

Example:
    ```python
    from genkit.plugins.azure import add_azure_telemetry

    # Enable telemetry export to Azure Application Insights
    add_azure_telemetry()

    # With explicit connection string
    add_azure_telemetry(connection_string='InstrumentationKey=...')

    # Traces are now exported to:
    # - Azure Portal > Application Insights > Transaction Search
    ```

Trademark Notice:
    "Microsoft", "Azure", "Application Insights", and related marks are
    trademarks of Microsoft Corporation. This is a community plugin and
    is not officially supported by Microsoft.

See Also:
    - Application Insights: https://docs.microsoft.com/azure/azure-monitor/app/app-insights-overview
    - Azure Monitor: https://docs.microsoft.com/azure/azure-monitor/
    - Genkit documentation: https://genkit.dev/
"""

from .telemetry import add_azure_telemetry


def package_name() -> str:
    """Get the package name for the Azure plugin.

    Returns:
        The fully qualified package name as a string.
    """
    return 'genkit.plugins.azure'


__all__ = ['add_azure_telemetry', 'package_name']
