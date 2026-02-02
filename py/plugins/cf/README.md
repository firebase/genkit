# Genkit Cloudflare Plugin

This plugin provides Cloudflare-compatible observability integration for Genkit,
enabling telemetry export via OpenTelemetry Protocol (OTLP) to any compatible
observability platform.

## Features

- **OTLP Export**: Export traces to any OTLP-compatible endpoint
- **Bearer Token Auth**: Authenticate with Cloudflare API token
- **PII Redaction**: Optional redaction of model inputs/outputs for privacy
- **Platform Flexibility**: Works with Grafana, Honeycomb, Axiom, SigNoz, and more

## Installation

```bash
pip install genkit-plugin-cf
```

## Quick Start

```python
from genkit.plugins.cf import add_cf_telemetry

# Enable telemetry (uses environment variables)
add_cf_telemetry()

# Or with explicit configuration
add_cf_telemetry(
    endpoint='https://your-otlp-endpoint.com/v1/traces',
    api_token='your-api-token'
)
```

## Configuration

### Environment Variables

| Variable | Description |
|----------|-------------|
| `CF_OTLP_ENDPOINT` | OTLP traces endpoint URL |
| `CF_API_TOKEN` | Optional: API token for authentication |

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `endpoint` | str | env var | OTLP traces endpoint |
| `api_token` | str | env var | Bearer token for auth |
| `log_input_and_output` | bool | False | Disable PII redaction |
| `force_dev_export` | bool | True | Export in dev environment |
| `disable_traces` | bool | False | Skip trace export |

## Compatible Platforms

This plugin can export traces to any OTLP-compatible platform:

- **Grafana Cloud**: Use their OTLP endpoint
- **Honeycomb**: Native OTLP support
- **Axiom**: OTLP ingestion available
- **SigNoz**: Open-source OTLP backend
- **Jaeger**: With OTLP collector
- **Cloudflare Workers**: Native OTLP (for Workers at edge)

## Trademark Notice

"Cloudflare" and related marks are trademarks of Cloudflare, Inc. This is a
community plugin and is not officially supported by Cloudflare.
