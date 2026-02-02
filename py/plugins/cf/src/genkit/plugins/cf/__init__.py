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

"""Cloudflare Plugin for Genkit.

This plugin provides Cloudflare-compatible observability integration for Genkit,
enabling telemetry export via OpenTelemetry Protocol (OTLP) to any compatible
observability platform including Cloudflare's native OTLP endpoints.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                                   │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ OTLP                │ OpenTelemetry Protocol - a universal language for  │
    │                     │ sending traces. Like a common shipping label.      │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Telemetry           │ Data about what your app is doing. Like a         │
    │                     │ fitness tracker but for your code.                │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Trace               │ The full story of one request. Shows every step   │
    │                     │ from start to finish (flow → model → response).   │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Span                │ One step in a trace. "Called AI model" or         │
    │                     │ "Ran my_flow" - each is a span with timing info.  │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Endpoint            │ Where your traces go. Like a mailing address      │
    │                     │ for your telemetry data.                          │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ API Token           │ Your key to authenticate with the endpoint.       │
    │                     │ Like an ID badge to get into the building.        │
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
    │                         │  (3) Sent via OTLP/HTTP                       │
    │                         ▼                                               │
    │              ┌─────────────────────┐                                    │
    │              │ OTLP Span Exporter  │                                    │
    │              │ (+ Bearer auth)     │                                    │
    │              └──────────┬──────────┘                                    │
    │                         │                                               │
    │    ════════════════════════════════════════════════════                 │
    │                         │                                               │
    │                         ▼                                               │
    │              ┌─────────────────────┐                                    │
    │              │  Your OTLP Backend  │   Grafana, Honeycomb, Axiom,       │
    │              │  (any compatible)   │   SigNoz, Jaeger, etc.             │
    │              └─────────────────────┘                                    │
    └─────────────────────────────────────────────────────────────────────────┘

Architecture Overview::

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                         CLOUDFLARE TELEMETRY PLUGIN                     │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  __init__.py - Plugin Entry Point                                       │
    │  ├── add_cf_telemetry() - Main configuration function                   │
    │  └── package_name() - Plugin identification                             │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  telemetry/tracing.py - Distributed Tracing                             │
    │  ├── OTLP/HTTP exporter configuration                                   │
    │  ├── Bearer token authentication                                        │
    │  └── PII redaction via AdjustingTraceExporter                           │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐      │
    │  │ Genkit App   │───►│ OpenTelemetry│───►│ OTLP Backend         │      │
    │  │ (actions,    │    │ SDK + OTLP   │    │ (Grafana, Honeycomb, │      │
    │  │  flows)      │    │ Exporter     │    │  Axiom, SigNoz, etc.)│      │
    │  └──────────────┘    └──────────────┘    └──────────────────────┘      │
    └─────────────────────────────────────────────────────────────────────────┘

Example:
    ```python
    from genkit.plugins.cf import add_cf_telemetry

    # Enable telemetry export to any OTLP-compatible endpoint
    add_cf_telemetry()

    # With explicit endpoint and authentication
    add_cf_telemetry(endpoint='https://otel.example.com/v1/traces', api_token='your-api-token')

    # Traces are now exported to your configured backend
    ```

Trademark Notice:
    "Cloudflare" and related marks are trademarks of Cloudflare, Inc.
    This is a community plugin and is not officially supported by Cloudflare.

See Also:
    - Cloudflare Workers Observability: https://developers.cloudflare.com/workers/observability/
    - OpenTelemetry: https://opentelemetry.io/
    - Genkit documentation: https://genkit.dev/
"""

from .telemetry import add_cf_telemetry


def package_name() -> str:
    """Get the package name for the Cloudflare plugin.

    Returns:
        The fully qualified package name as a string.
    """
    return 'genkit.plugins.cf'


__all__ = ['add_cf_telemetry', 'package_name']
