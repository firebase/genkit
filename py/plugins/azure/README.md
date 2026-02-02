# Genkit Azure Plugin

This plugin provides Azure observability integration for Genkit, enabling
telemetry export to Azure Monitor Application Insights.

## Features

- **Azure Application Insights**: Distributed tracing with automatic trace correlation
- **OpenTelemetry Integration**: Uses Azure Monitor OpenTelemetry exporter
- **PII Redaction**: Optional redaction of model inputs/outputs for privacy

## Installation

```bash
pip install genkit-plugin-azure[monitor]
```

## Quick Start

```python
from genkit.plugins.azure import add_azure_telemetry

# Enable telemetry (uses APPLICATIONINSIGHTS_CONNECTION_STRING env var)
add_azure_telemetry()

# Or with explicit connection string
add_azure_telemetry(connection_string="InstrumentationKey=...")
```

## Configuration

### Environment Variables

| Variable | Description |
|----------|-------------|
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Azure Application Insights connection string |

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `connection_string` | str | env var | Application Insights connection string |
| `log_input_and_output` | bool | False | Disable PII redaction |
| `force_dev_export` | bool | True | Export in dev environment |
| `disable_traces` | bool | False | Skip trace export |

## View Traces

After running your Genkit application, view traces in the Azure Portal:

1. Go to your Application Insights resource
2. Navigate to "Transaction search" or "Performance"
3. Filter by operation name to find your Genkit flows

## Trademark Notice

"Microsoft", "Azure", "Application Insights", and related marks are trademarks
of Microsoft Corporation. This is a community plugin and is not officially
supported by Microsoft.
