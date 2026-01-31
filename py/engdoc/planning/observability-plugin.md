# Observability Plugin Implementation Plan

**Status:** Ready for Implementation  
**Feasibility:** ✅ HIGH  
**Estimated Effort:** 1 week  
**Dependencies:** `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-http`

## Overview

The `observability` plugin provides a unified way to export Genkit telemetry to any
OTLP-compatible backend (Sentry, Honeycomb, Datadog, Grafana, Axiom, etc.) with
simple presets for popular services.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      OBSERVABILITY PLUGIN ARCHITECTURE                          │
│                                                                                 │
│    Key Concepts (ELI5):                                                         │
│    ┌─────────────────────┬────────────────────────────────────────────────────┐ │
│    │ OTLP                │ OpenTelemetry Protocol. The universal language     │ │
│    │                     │ for sending traces. Sentry, Honeycomb, all speak it.│ │
│    ├─────────────────────┼────────────────────────────────────────────────────┤ │
│    │ Backend Preset      │ Pre-configured settings for a service. Just add    │ │
│    │                     │ your API key and you're done!                      │ │
│    ├─────────────────────┼────────────────────────────────────────────────────┤ │
│    │ Sentry              │ Error tracking + tracing. Great for debugging      │ │
│    │                     │ crashes and performance issues.                    │ │
│    ├─────────────────────┼────────────────────────────────────────────────────┤ │
│    │ Honeycomb           │ Observability platform built for debugging.        │ │
│    │                     │ Query your traces like a database.                 │ │
│    ├─────────────────────┼────────────────────────────────────────────────────┤ │
│    │ Datadog             │ Full-stack monitoring. Traces, metrics, logs,      │ │
│    │                     │ all in one place.                                  │ │
│    └─────────────────────┴────────────────────────────────────────────────────┘ │
│                                                                                 │
│    Data Flow:                                                                   │
│    ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐         │
│    │  Genkit App     │────▶│  OTLP Exporter  │────▶│  Your Backend   │         │
│    │  (Your Code)    │     │  (HTTP/gRPC)    │     │  (Sentry, etc.) │         │
│    └─────────────────┘     └─────────────────┘     └─────────────────┘         │
│                                                                                 │
│    Supported Backends:                                                          │
│    ┌────────────┬────────────┬────────────┬────────────┬────────────┐          │
│    │  Sentry    │ Honeycomb  │  Datadog   │  Grafana   │   Axiom    │          │
│    │  ✅        │  ✅        │  ✅        │  ✅        │  ✅        │          │
│    └────────────┴────────────┴────────────┴────────────┴────────────┘          │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## When to Use This Plugin

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     WHEN TO USE WHAT                                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   "I'm on AWS and want X-Ray"           → aws plugin (SigV4, X-Ray format)     │
│   "I'm on GCP and want Cloud Trace"     → google-cloud plugin (ADC)            │
│   "I'm on Azure and want App Insights"  → azure plugin (Live Metrics, Map)     │
│                                                                                 │
│   "I'm on AWS but want Honeycomb"       → observability plugin ← THIS ONE      │
│   "I'm on GCP but want Sentry"          → observability plugin ← THIS ONE      │
│   "I'm multi-cloud, want Datadog"       → observability plugin ← THIS ONE      │
│   "I don't care, just give me traces"   → observability plugin ← THIS ONE      │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Why Not Just Use Platform Plugins?

Platform plugins (aws, google-cloud, azure) provide:
- Platform-specific authentication (SigV4, ADC)
- Native backend features (Live Metrics, X-Ray Service Map)
- Platform log correlation (CloudWatch, Cloud Logging)

**These CAN'T be replicated with generic OTLP.**

The observability plugin is for users who:
- Don't want platform-native tools
- Need the same backend across multiple clouds
- Prefer third-party tools like Sentry or Honeycomb
- Want simple setup without platform-specific auth

## Supported Backends

| Backend | Endpoint | Auth | Features |
|---------|----------|------|----------|
| **Sentry** | `https://{org}.ingest.sentry.io/api/{project}/envelope/` | DSN | Error tracking, performance |
| **Honeycomb** | `https://api.honeycomb.io/v1/traces` | API Key | Query-based debugging |
| **Datadog** | `https://trace.agent.datadoghq.com/v0.4/traces` | API Key | Full-stack APM |
| **Grafana Cloud** | `https://{stack}.grafana.net/otlp` | API Key | Tempo traces |
| **Axiom** | `https://api.axiom.co/v1/traces` | API Token | Log + trace ingestion |
| **Custom** | Any OTLP endpoint | Headers | Bring your own |

## API Design

```python
"""Observability plugin for Genkit - Third-party telemetry backends.

This plugin provides simple presets for popular observability platforms,
all using standard OpenTelemetry Protocol (OTLP) export.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                                   │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ OTLP                │ The universal language for traces. Like USB but   │
    │                     │ for observability data.                           │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Backend             │ Where your traces go. Sentry, Honeycomb, etc.     │
    │                     │ Pick one, add your API key, done!                 │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Preset              │ Pre-configured settings for a backend. Knows      │
    │                     │ the right URLs, headers, and formats.             │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Span                │ A single operation's timing. Like a stopwatch     │
    │                     │ for one function call.                            │
    └─────────────────────┴────────────────────────────────────────────────────┘

Data Flow::

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                  HOW OBSERVABILITY EXPORT WORKS                         │
    │                                                                         │
    │    Your Genkit App                                                      │
    │         │                                                               │
    │         │  (1) Flows, models, tools create spans                        │
    │         ▼                                                               │
    │    ┌─────────────────┐                                                  │
    │    │  TracerProvider │   Collects all spans from your app               │
    │    │  (OpenTelemetry)│                                                  │
    │    └────────┬────────┘                                                  │
    │             │                                                           │
    │             │  (2) Batch and export via OTLP                            │
    │             ▼                                                           │
    │    ┌─────────────────┐                                                  │
    │    │  OTLP Exporter  │   Sends to your chosen backend                   │
    │    │  (HTTP POST)    │                                                  │
    │    └────────┬────────┘                                                  │
    │             │                                                           │
    │             │  (3) View in your dashboard                               │
    │             ▼                                                           │
    │    ┌─────────────────┐                                                  │
    │    │  Sentry /       │   Query, alert, debug your traces                │
    │    │  Honeycomb /    │                                                  │
    │    │  Datadog / etc  │                                                  │
    │    └─────────────────┘                                                  │
    └─────────────────────────────────────────────────────────────────────────┘

Example::

    from genkit.plugins.observability import configure_telemetry
    
    # Sentry
    configure_telemetry(backend="sentry", sentry_dsn="https://...")
    
    # Honeycomb
    configure_telemetry(backend="honeycomb", honeycomb_api_key="...")
    
    # Datadog
    configure_telemetry(backend="datadog", datadog_api_key="...")
    
    # Custom OTLP endpoint
    configure_telemetry(
        backend="custom",
        endpoint="https://my-collector/v1/traces",
        headers={"Authorization": "Bearer ..."},
    )
"""

from enum import Enum
from typing import Literal


class Backend(str, Enum):
    """Supported observability backends."""
    
    SENTRY = "sentry"
    HONEYCOMB = "honeycomb"
    DATADOG = "datadog"
    GRAFANA = "grafana"
    AXIOM = "axiom"
    CUSTOM = "custom"


def configure_telemetry(
    backend: Backend | Literal["sentry", "honeycomb", "datadog", "grafana", "axiom", "custom"],
    *,
    # Common options
    service_name: str = "genkit-app",
    service_version: str = "1.0.0",
    environment: str | None = None,
    
    # Sentry
    sentry_dsn: str | None = None,
    
    # Honeycomb
    honeycomb_api_key: str | None = None,
    honeycomb_dataset: str | None = None,
    
    # Datadog
    datadog_api_key: str | None = None,
    datadog_site: str = "datadoghq.com",
    
    # Grafana Cloud
    grafana_endpoint: str | None = None,
    grafana_api_key: str | None = None,
    
    # Axiom
    axiom_api_token: str | None = None,
    axiom_dataset: str | None = None,
    
    # Custom OTLP
    endpoint: str | None = None,
    headers: dict[str, str] | None = None,
) -> None:
    """Configure telemetry export to a third-party backend.
    
    Args:
        backend: Which backend to use (sentry, honeycomb, datadog, etc.)
        service_name: Name of your service (appears in traces)
        service_version: Version of your service
        environment: Environment name (production, staging, etc.)
        
        # Backend-specific (provide based on chosen backend):
        sentry_dsn: Sentry DSN (for backend="sentry")
        honeycomb_api_key: Honeycomb API key (for backend="honeycomb")
        datadog_api_key: Datadog API key (for backend="datadog")
        grafana_endpoint: Grafana Cloud OTLP endpoint (for backend="grafana")
        axiom_api_token: Axiom API token (for backend="axiom")
        
        # Custom OTLP:
        endpoint: Custom OTLP endpoint URL (for backend="custom")
        headers: Custom headers for authentication (for backend="custom")
    
    Example:
        >>> # Sentry
        >>> configure_telemetry(backend="sentry", sentry_dsn="https://...")
        >>> 
        >>> # Honeycomb  
        >>> configure_telemetry(backend="honeycomb", honeycomb_api_key="...")
    """
    ...
```

## Directory Structure

```
py/plugins/observability/
├── pyproject.toml
├── README.md
├── LICENSE
├── src/genkit/plugins/observability/
│   ├── __init__.py              # Main API, configure_telemetry()
│   ├── backends/
│   │   ├── __init__.py
│   │   ├── base.py              # Base backend configuration
│   │   ├── sentry.py            # Sentry preset
│   │   ├── honeycomb.py         # Honeycomb preset
│   │   ├── datadog.py           # Datadog preset
│   │   ├── grafana.py           # Grafana Cloud preset
│   │   ├── axiom.py             # Axiom preset
│   │   └── custom.py            # Custom OTLP
│   ├── typing.py                # Configuration schemas
│   └── py.typed
└── tests/
    ├── conftest.py
    ├── sentry_test.py
    ├── honeycomb_test.py
    └── integration_test.py
```

## Implementation

### Core Configuration

```python
# src/genkit/plugins/observability/__init__.py

import os
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION

from .backends import get_backend_config


def configure_telemetry(
    backend: str,
    *,
    service_name: str = "genkit-app",
    service_version: str = "1.0.0",
    **kwargs: Any,
) -> None:
    """Configure telemetry export to a third-party backend."""
    
    # Get backend-specific configuration
    config = get_backend_config(backend, **kwargs)
    
    # Create resource with service info
    resource = Resource.create({
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version,
    })
    
    # Create OTLP exporter with backend config
    exporter = OTLPSpanExporter(
        endpoint=config.endpoint,
        headers=config.headers,
    )
    
    # Configure tracer provider
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
```

### Backend Presets

```python
# src/genkit/plugins/observability/backends/sentry.py

from dataclasses import dataclass


@dataclass
class SentryConfig:
    """Sentry OTLP configuration."""
    
    endpoint: str
    headers: dict[str, str]


def get_sentry_config(dsn: str) -> SentryConfig:
    """Create Sentry configuration from DSN.
    
    DSN format: https://{key}@{org}.ingest.sentry.io/{project}
    """
    # Parse DSN and construct OTLP endpoint
    # Sentry accepts OTLP at: https://{org}.ingest.sentry.io/api/{project}/envelope/
    
    return SentryConfig(
        endpoint=f"https://sentry.io/api/0/envelope/",
        headers={
            "X-Sentry-Auth": f"Sentry sentry_key={dsn}",
        },
    )
```

## pyproject.toml

```toml
[project]
name = "genkit-observability-plugin"
version = "0.1.0"
description = "Third-party observability backends for Genkit"
requires-python = ">=3.10"
dependencies = [
    "genkit",
    "opentelemetry-sdk>=1.20.0",
    "opentelemetry-exporter-otlp-proto-http>=1.20.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
]
```

## Sample Application

```python
# py/samples/observability-hello/src/main.py
"""Observability hello sample - Third-party telemetry with Genkit.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                                   │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Observability       │ Seeing what your app is doing. Like X-ray          │
    │                     │ vision for your code!                              │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Traces              │ The journey of a request through your app.         │
    │                     │ Shows timing, errors, everything.                  │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Backend             │ Where traces are stored and visualized.            │
    │                     │ Sentry, Honeycomb, Datadog, etc.                   │
    └─────────────────────┴────────────────────────────────────────────────────┘
"""

import os
from genkit.ai import Genkit
from genkit.plugins.observability import configure_telemetry
from genkit.plugins.google_genai import GoogleAI

# Configure telemetry FIRST (before any Genkit operations)
configure_telemetry(
    backend="honeycomb",  # or "sentry", "datadog", etc.
    honeycomb_api_key=os.environ["HONEYCOMB_API_KEY"],
    service_name="observability-hello",
)

ai = Genkit(
    plugins=[GoogleAI()],
    model="googleai/gemini-2.0-flash",
)

@ai.flow()
async def say_hi(name: str) -> str:
    """Say hello - traced to your observability backend."""
    response = await ai.generate(prompt=f"Say hi to {name}!")
    return response.text
```

## Environment Variables

| Variable | Backend | Description |
|----------|---------|-------------|
| `SENTRY_DSN` | Sentry | Your Sentry DSN |
| `HONEYCOMB_API_KEY` | Honeycomb | Honeycomb API key |
| `DD_API_KEY` | Datadog | Datadog API key |
| `GRAFANA_OTLP_ENDPOINT` | Grafana | Grafana Cloud OTLP endpoint |
| `AXIOM_TOKEN` | Axiom | Axiom API token |

## Feasibility Score

| Factor | Score | Notes |
|--------|-------|-------|
| **API Documentation** | 9/10 | Standard OTLP, well-documented |
| **Python Support** | 10/10 | Official opentelemetry-python |
| **Setup Simplicity** | 9/10 | One function call with preset |
| **Feature Coverage** | 8/10 | Traces + basic metrics |
| **Community Demand** | 9/10 | Common request |
| **Maintenance Burden** | 9/10 | Stable OTLP protocol |
| **Strategic Value** | 8/10 | Platform-agnostic option |
| **TOTAL** | **89/100** | ✅ **BUILD** |

## References

- [OpenTelemetry Python](https://opentelemetry.io/docs/languages/python/)
- [Sentry OTLP](https://docs.sentry.io/platforms/python/tracing/)
- [Honeycomb OpenTelemetry](https://docs.honeycomb.io/send-data/opentelemetry/)
- [Datadog OTLP](https://docs.datadoghq.com/tracing/trace_collection/open_standards/otlp_ingest_in_the_agent/)
- [Grafana Cloud OTLP](https://grafana.com/docs/grafana-cloud/send-data/otlp/)
- [Axiom OpenTelemetry](https://axiom.co/docs/send-data/opentelemetry)
