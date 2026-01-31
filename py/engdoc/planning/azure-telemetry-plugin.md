# Azure Telemetry Plugin Implementation Plan

**Status:** Ready for Implementation  
**Feasibility:** ✅ HIGH  
**Estimated Effort:** Medium (1-2 weeks)  
**Dependencies:** `azure-monitor-opentelemetry`, `opentelemetry-sdk`

## Overview

The `azure` plugin exports Genkit telemetry to Azure Monitor (Application Insights),
providing distributed tracing, logging, and metrics for Azure-hosted applications.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                  AZURE TELEMETRY PLUGIN ARCHITECTURE                    │
│                                                                         │
│    Key Concepts (ELI5):                                                 │
│    ┌─────────────────────┬────────────────────────────────────────────┐ │
│    │ Azure Monitor       │ Microsoft's observability platform. See    │ │
│    │                     │ traces, logs, metrics in Azure Portal.     │ │
│    ├─────────────────────┼────────────────────────────────────────────┤ │
│    │ Application Insights│ The part of Azure Monitor for apps.        │ │
│    │                     │ Tracks requests, dependencies, exceptions.  │ │
│    ├─────────────────────┼────────────────────────────────────────────┤ │
│    │ Connection String   │ Your key to send data. Found in Azure      │ │
│    │                     │ Portal > App Insights > Connection String. │ │
│    ├─────────────────────┼────────────────────────────────────────────┤ │
│    │ Azure Monitor Distro│ Microsoft's "batteries included" OTEL      │ │
│    │                     │ package. One line to enable everything.    │ │
│    ├─────────────────────┼────────────────────────────────────────────┤ │
│    │ Live Metrics        │ Real-time view of your app's health.       │ │
│    │                     │ See requests as they happen!               │ │
│    └─────────────────────┴────────────────────────────────────────────┘ │
│                                                                         │
│    Data Flow:                                                           │
│    ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐  │
│    │  Genkit App     │────▶│  Azure Monitor  │────▶│  Application    │  │
│    │  (Your Code)    │     │  OTEL Distro    │     │  Insights       │  │
│    └─────────────────┘     └─────────────────┘     └─────────────────┘  │
│           │                        │                       │            │
│           │                        │                       │            │
│           │                        ▼                       ▼            │
│           │               ┌─────────────────────────────────────────┐   │
│           │               │           Azure Portal                  │   │
│           │               │  ┌─────────┐ ┌─────────┐ ┌─────────┐   │   │
│           │               │  │ Traces  │ │  Logs   │ │ Metrics │   │   │
│           │               │  │ (E2E)   │ │ (Query) │ │ (Charts)│   │   │
│           │               │  └─────────┘ └─────────┘ └─────────┘   │   │
│           │               └─────────────────────────────────────────┘   │
│           │                                                             │
│           │    ┌─────────────────┐                                      │
│           └───▶│  structlog      │──── Logs with trace correlation      │
│                │  integration    │                                      │
│                └─────────────────┘                                      │
└─────────────────────────────────────────────────────────────────────────┘
```

## Azure Monitor OpenTelemetry Distro

Microsoft provides an official "batteries included" package that handles everything:

```bash
pip install azure-monitor-opentelemetry
```

**Version:** 1.8.5 (January 2026)  
**Python Support:** 3.9 - 3.14

### What It Includes

- **Azure Monitor exporters** - Send data to Application Insights
- **Auto-instrumentation** - HTTP, database, and framework libraries
- **Trace correlation** - Links traces across services
- **Live Metrics** - Real-time monitoring stream

## Implementation

### Core Plugin Class

```python
"""Azure telemetry plugin for Genkit.

Exports traces, logs, and metrics to Azure Monitor (Application Insights).

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                               │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Azure Monitor       │ Microsoft's observability platform. Like a    │
    │                     │ dashboard showing your app's vital signs.     │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Application Insights│ The part that tracks your app specifically.   │
    │                     │ Requests, errors, dependencies, performance.  │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Connection String   │ Your unique key to send telemetry. Like an    │
    │                     │ address where your data should be delivered.  │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Live Metrics        │ Real-time view of requests as they happen.    │
    │                     │ Like watching a live scoreboard.              │
    └─────────────────────┴────────────────────────────────────────────────┘

Data Flow::

    ┌─────────────────────────────────────────────────────────────────────┐
    │                    HOW AZURE TELEMETRY WORKS                        │
    │                                                                     │
    │    Your Genkit App                                                  │
    │         │                                                           │
    │         │  (1) Initialize AzureTelemetry                            │
    │         ▼                                                           │
    │    ┌─────────────────┐                                              │
    │    │  AzureTelemetry │   Configures OTEL with Azure exporters       │
    │    │  (Manager)      │                                              │
    │    └────────┬────────┘                                              │
    │             │                                                       │
    │             │  (2) Auto-instruments your code                       │
    │             ▼                                                       │
    │    ┌─────────────────┐     ┌─────────────────┐                      │
    │    │  TracerProvider │────▶│  AzureMonitor   │                      │
    │    │  (OTEL)         │     │  Exporter       │                      │
    │    └─────────────────┘     └────────┬────────┘                      │
    │                                     │                               │
    │             ┌───────────────────────┼───────────────────────┐       │
    │             │                       │                       │       │
    │             ▼                       ▼                       ▼       │
    │    ┌─────────────────┐     ┌─────────────────┐     ┌─────────────┐  │
    │    │  Traces         │     │  Logs           │     │  Metrics    │  │
    │    │  (Distributed)  │     │  (Structured)   │     │  (Counters) │  │
    │    └─────────────────┘     └─────────────────┘     └─────────────┘  │
    │             │                       │                       │       │
    │             └───────────────────────┼───────────────────────┘       │
    │                                     │                               │
    │                                     ▼                               │
    │                          ┌─────────────────────┐                    │
    │                          │  Application        │                    │
    │                          │  Insights Portal    │                    │
    │                          └─────────────────────┘                    │
    └─────────────────────────────────────────────────────────────────────┘

Example::

    from genkit.ai import Genkit
    from genkit.plugins.azure import AzureTelemetry
    from genkit.plugins.msfoundry import MSFoundry
    
    # Initialize Azure telemetry
    AzureTelemetry().initialize()
    
    ai = Genkit(
        plugins=[MSFoundry()],
        model='msfoundry/gpt-4o',
    )
"""

import os
import logging
from typing import Any, MutableMapping, Mapping

import structlog
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

from genkit.core.logging import get_logger


logger = get_logger(__name__)


class AzureTelemetry:
    """Azure Monitor telemetry manager for Genkit applications.
    
    This class provides a centralized way to configure Azure Application Insights
    telemetry, including distributed tracing, structured logging, and metrics.
    
    Args:
        connection_string: Application Insights connection string.
            Falls back to APPLICATIONINSIGHTS_CONNECTION_STRING env var.
        service_name: Name of your service (appears in traces).
        service_version: Version of your service.
        enable_live_metrics: Enable real-time metrics stream.
        log_level: Minimum log level to export.
    
    Example:
        >>> telemetry = AzureTelemetry(service_name="my-genkit-app")
        >>> telemetry.initialize()
    """
    
    def __init__(
        self,
        connection_string: str | None = None,
        service_name: str = "genkit-app",
        service_version: str = "1.0.0",
        enable_live_metrics: bool = True,
        log_level: int = logging.INFO,
    ):
        self.connection_string = (
            connection_string 
            or os.environ.get('APPLICATIONINSIGHTS_CONNECTION_STRING')
        )
        self.service_name = service_name
        self.service_version = service_version
        self.enable_live_metrics = enable_live_metrics
        self.log_level = log_level
        
        if not self.connection_string:
            raise ValueError(
                "Connection string required. Set APPLICATIONINSIGHTS_CONNECTION_STRING "
                "or pass connection_string parameter."
            )
    
    def initialize(self) -> None:
        """Initialize Azure Monitor telemetry.
        
        This method:
        1. Configures the Azure Monitor OpenTelemetry distro
        2. Sets up structured logging with trace correlation
        3. Enables live metrics if configured
        """
        # Configure Azure Monitor (one-liner!)
        configure_azure_monitor(
            connection_string=self.connection_string,
            service_name=self.service_name,
            service_version=self.service_version,
            enable_live_metrics=self.enable_live_metrics,
            logger_name="",  # Capture all loggers
        )
        
        # Configure structlog for trace correlation
        self._configure_logging()
        
        logger.info(
            "Azure telemetry initialized",
            service_name=self.service_name,
            live_metrics=self.enable_live_metrics,
        )
    
    def _configure_logging(self) -> None:
        """Configure structlog to include Azure trace context."""
        processors = list(structlog.get_config().get("processors", []))
        
        # Check if already configured
        if any(
            getattr(p, '__name__', '') == 'inject_azure_trace_context'
            for p in processors
        ):
            return
        
        def inject_azure_trace_context(
            _logger: Any,
            method_name: str,
            event_dict: MutableMapping[str, Any],
        ) -> Mapping[str, Any]:
            """Inject Azure trace context into log events."""
            span = trace.get_current_span()
            if span and span.is_recording():
                ctx = span.get_span_context()
                # Azure uses operation_Id and operation_ParentId
                event_dict['operation_Id'] = format(ctx.trace_id, '032x')
                event_dict['operation_ParentId'] = format(ctx.span_id, '016x')
            return event_dict
        
        new_processors = list(processors)
        new_processors.insert(max(0, len(new_processors) - 1), inject_azure_trace_context)
        structlog.configure(processors=new_processors)
```

### Directory Structure

```
py/plugins/azure/
├── pyproject.toml
├── README.md
├── LICENSE
├── src/genkit/plugins/azure/
│   ├── __init__.py              # Plugin entry, ELI5 docs, exports
│   ├── telemetry/
│   │   ├── __init__.py
│   │   └── tracing.py           # AzureTelemetry class
│   ├── typing.py                # Configuration schemas
│   └── py.typed
└── tests/
    ├── conftest.py
    └── azure_telemetry_test.py
```

### pyproject.toml

```toml
[project]
name = "genkit-azure-plugin"
version = "0.1.0"
description = "Azure Monitor telemetry plugin for Genkit"
requires-python = ">=3.10"
dependencies = [
    "genkit",
    "azure-monitor-opentelemetry>=1.8.0",
    "structlog>=24.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
]
```

## Configuration Options

### Connection String

Get from Azure Portal:
1. Go to your Application Insights resource
2. Click "Overview" or "Properties"
3. Copy the "Connection String"

Format:
```
InstrumentationKey=xxx;IngestionEndpoint=https://xxx.in.applicationinsights.azure.com/;LiveEndpoint=https://xxx.livediagnostics.monitor.azure.com/;ApplicationId=xxx
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Yes | App Insights connection string |
| `AZURE_SDK_TRACING_IMPLEMENTATION` | No | Set to "opentelemetry" for SDK tracing |

## Features

### 1. Distributed Tracing

Automatic tracing for:
- HTTP requests (incoming and outgoing)
- Database calls (via auto-instrumentation)
- Genkit flows, models, and tools
- Cross-service correlation

### 2. Structured Logging

Logs automatically include:
- `operation_Id` - Links logs to traces
- `operation_ParentId` - Parent span context
- Custom properties from structlog

### 3. Live Metrics

Real-time stream showing:
- Request rate
- Failure rate
- Response time
- Server health

### 4. Application Map

Visual diagram of:
- Service dependencies
- Call flows
- Performance bottlenecks

## Sample Application

```python
# py/samples/azure-hello/src/main.py
"""Azure telemetry hello sample - Monitor Genkit with Application Insights.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                               │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Application Insights│ Microsoft's app monitoring. See traces, logs, │
    │                     │ and metrics in Azure Portal.                   │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Connection String   │ Your key to send data. Find it in Azure       │
    │                     │ Portal > App Insights > Properties.           │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Live Metrics        │ Real-time view of requests as they happen.    │
    │                     │ Great for debugging production issues!         │
    └─────────────────────┴────────────────────────────────────────────────┘
"""

from genkit.ai import Genkit
from genkit.plugins.azure import AzureTelemetry
from genkit.plugins.msfoundry import MSFoundry

# Initialize Azure telemetry FIRST
AzureTelemetry(
    service_name="azure-hello-sample",
    enable_live_metrics=True,
).initialize()

ai = Genkit(
    plugins=[MSFoundry()],
    model='msfoundry/gpt-4o',
)

@ai.flow()
async def say_hi(name: str) -> str:
    """Say hello - traced in Application Insights."""
    response = await ai.generate(prompt=f"Say hi to {name}!")
    return response.text
```

## Comparison with AWS/GCP Telemetry

| Feature | AWS (`aws`) | GCP (`google-cloud`) | Azure (`azure`) |
|---------|-------------|---------------------|-----------------|
| Native Backend | X-Ray | Cloud Trace | Application Insights |
| OTEL Distro | Manual setup | Manual setup | ✅ Official distro |
| One-liner Setup | ❌ | ❌ | ✅ `configure_azure_monitor()` |
| Live Metrics | ❌ | ❌ | ✅ Built-in |
| Application Map | ❌ | ❌ | ✅ Built-in |
| Log Correlation | ✅ | ✅ | ✅ |
| Auto-instrumentation | Manual | Manual | ✅ Automatic |

## Implementation Phases

### Phase 1: Core Telemetry (3-4 days)

1. Plugin skeleton with `AzureTelemetry` class
2. Integration with `azure-monitor-opentelemetry`
3. Structlog trace correlation
4. Basic tests

### Phase 2: Sample & Docs (2-3 days)

1. `azure-hello` sample application
2. README with setup instructions
3. Integration with `msfoundry` plugin

### Phase 3: Advanced Features (Optional)

1. Custom metrics support
2. Exception tracking
3. Availability tests integration

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Connection string exposure | High | Document secure storage practices |
| High telemetry volume | Medium | Configure sampling |
| SDK version conflicts | Low | Pin compatible versions |

## References

- [Azure Monitor OpenTelemetry Distro](https://learn.microsoft.com/en-us/python/api/overview/azure/monitor-opentelemetry-readme)
- [Configure Azure Monitor OpenTelemetry](https://learn.microsoft.com/en-us/azure/azure-monitor/app/opentelemetry-configuration)
- [Application Insights Overview](https://learn.microsoft.com/en-us/azure/azure-monitor/app/app-insights-overview)
- [PyPI Package](https://pypi.org/project/azure-monitor-opentelemetry/)
