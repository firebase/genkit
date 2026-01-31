# Cloudflare Telemetry Plugin Implementation Plan

**Status:** Research Complete - Limited Native Support  
**Feasibility:** ⚠️ MEDIUM (requires workarounds)  
**Estimated Effort:** Low-Medium (1-2 weeks)  
**Dependencies:** `httpx`, `opentelemetry-sdk`

## Overview

Cloudflare does not have a native tracing backend like AWS X-Ray or GCP Cloud Trace.
However, they support **exporting OpenTelemetry data** to third-party observability platforms
and have recently adopted OpenTelemetry internally for their logging pipeline.

```
┌─────────────────────────────────────────────────────────────────────────┐
│               CLOUDFLARE TELEMETRY OPTIONS ARCHITECTURE                 │
│                                                                         │
│    Key Concepts (ELI5):                                                 │
│    ┌─────────────────────┬────────────────────────────────────────────┐ │
│    │ Logpush             │ Exports logs to external services. Like a  │ │
│    │                     │ pipe sending data to S3, Datadog, etc.     │ │
│    ├─────────────────────┼────────────────────────────────────────────┤ │
│    │ Workers Analytics   │ Built-in metrics for Workers. Basic        │ │
│    │                     │ request counts, CPU time, errors.          │ │
│    ├─────────────────────┼────────────────────────────────────────────┤ │
│    │ AI Gateway OTEL     │ Auto-exports AI request traces! Includes   │ │
│    │                     │ model, tokens, cost, latency.              │ │
│    ├─────────────────────┼────────────────────────────────────────────┤ │
│    │ Workers OTEL Export │ Export traces from Workers to Honeycomb,   │ │
│    │                     │ Grafana, Axiom, Datadog, etc.              │ │
│    └─────────────────────┴────────────────────────────────────────────┘ │
│                                                                         │
│    OPTION A: AI Gateway Integration (Recommended for AI apps)           │
│    ──────────────────────────────────────────────────────────           │
│    ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐  │
│    │  Genkit App     │────▶│  CF AI Gateway  │────▶│  Workers AI     │  │
│    │  (Your Code)    │     │  (Proxy)        │     │  or OpenAI etc  │  │
│    └─────────────────┘     └────────┬────────┘     └─────────────────┘  │
│                                     │                                   │
│                          Auto-export OTEL traces                        │
│                                     │                                   │
│                                     ▼                                   │
│                            ┌─────────────────┐                          │
│                            │  Your OTEL      │                          │
│                            │  Backend        │                          │
│                            │  (Honeycomb,    │                          │
│                            │   Grafana, etc) │                          │
│                            └─────────────────┘                          │
│                                                                         │
│    OPTION B: Direct OTLP Export (For non-Workers apps)                  │
│    ───────────────────────────────────────────────────                  │
│    ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐  │
│    │  Genkit App     │────▶│  OTLP Exporter  │────▶│  Any OTEL       │  │
│    │  (Your Code)    │     │  (Standard)     │     │  Backend        │  │
│    └─────────────────┘     └─────────────────┘     └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

## Cloudflare's OTEL Support

### Supported Third-Party Backends

Cloudflare Workers and AI Gateway support exporting OTEL data to:

| Provider | Traces | Logs | Notes |
|----------|--------|------|-------|
| **Sentry** | ✅ | ✅ | Error tracking + traces |
| **Honeycomb** | ✅ | ✅ | Full OTEL support |
| **Grafana Cloud** | ✅ | ✅ | Tempo + Loki |
| **Axiom** | ✅ | ✅ | Log + trace ingestion |
| **Datadog** | ✅ | ✅ | Full APM integration |

### 1. AI Gateway OpenTelemetry (Best for AI Apps)

Cloudflare AI Gateway automatically exports traces with:

- **Model information** - Which model was called
- **Token usage** - Input/output tokens
- **Cost estimates** - Approximate cost per request
- **Prompts & completions** - Full request/response content
- **Latency metrics** - Time to first token, total time

Configuration via dashboard or API:
```json
{
  "otel": {
    "endpoint": "https://your-sentry-endpoint/v1/traces",
    "headers": {
      "Authorization": "Bearer your-sentry-dsn"
    }
  }
}
```

Or for Honeycomb:
```json
{
  "otel": {
    "endpoint": "https://api.honeycomb.io/v1/traces",
    "headers": {
      "x-honeycomb-team": "your-api-key"
    }
  }
}
```

### 2. Workers OTEL Export

For Workers-deployed apps, traces can be exported to any of the supported backends.
Configure in `wrangler.toml` or via the Cloudflare dashboard.

### 3. Logpush

Exports logs (not traces) to:
- AWS S3
- Google Cloud Storage
- Azure Blob Storage
- Elastic
- Datadog
- Splunk
- Sentry
- And more...

## Implementation Options

### Option A: AI Gateway Proxy Plugin (Recommended)

Route AI requests through Cloudflare AI Gateway to get automatic telemetry.

```python
class CloudflareAIGateway(Plugin):
    """Route AI requests through Cloudflare AI Gateway for telemetry.
    
    Works with ANY model provider (OpenAI, Anthropic, etc.) while adding:
    - Automatic tracing to your OTEL backend
    - Request caching
    - Rate limiting
    - Cost tracking
    """
    
    def __init__(
        self,
        gateway_id: str,  # Your AI Gateway ID
        account_id: str | None = None,
        # The underlying provider (OpenAI, Anthropic, etc.)
        provider: Literal["openai", "anthropic", "workers-ai"] = "openai",
    ):
        self.base_url = f"https://gateway.ai.cloudflare.com/v1/{account_id}/{gateway_id}/{provider}"
```

**Pros:**
- Automatic OTEL traces for all AI requests
- Works with any model provider
- Includes cost tracking, caching, rate limiting
- No code changes needed for telemetry

**Cons:**
- Adds network hop (slight latency)
- Only covers AI requests, not all app traces
- Requires AI Gateway setup in CF dashboard

### Option B: Generic OTLP Export (Standard Approach)

Use standard OpenTelemetry exporters to any backend.

```python
class CloudflareTelemetry(Plugin):
    """Export Genkit telemetry to any OTEL-compatible backend.
    
    This is a thin wrapper around standard OTLP export, but with
    preset configurations for popular Cloudflare-compatible backends.
    """
    
    def __init__(
        self,
        backend: Literal["honeycomb", "grafana", "axiom", "datadog", "custom"],
        endpoint: str | None = None,
        api_key: str | None = None,
        headers: dict[str, str] | None = None,
    ):
        ...
```

**Pros:**
- Works for any Python app (not just CF Workers)
- Full control over what's traced
- Standard OTEL approach

**Cons:**
- No Cloudflare-specific features
- Basically same as any OTLP export
- Less "Cloudflare native"

### Option C: Hybrid (Both)

Combine AI Gateway for AI telemetry + standard OTEL for app telemetry.

## Recommended Implementation

Given Cloudflare's limited native tracing, I recommend **Option A (AI Gateway)** as the
primary implementation with a simple helper for configuration.

### Directory Structure

```
py/plugins/cloudflare/
├── pyproject.toml
├── README.md
├── LICENSE
├── src/genkit/plugins/cloudflare/
│   ├── __init__.py              # Plugin entry, ELI5 docs
│   ├── ai_gateway.py            # AI Gateway proxy configuration
│   ├── typing.py                # Configuration schemas
│   └── py.typed
└── tests/
    ├── conftest.py
    └── ai_gateway_test.py
```

### Implementation

```python
# __init__.py
"""Cloudflare plugin for Genkit - AI Gateway integration.

This plugin configures Genkit to route AI requests through Cloudflare's
AI Gateway, which provides automatic OpenTelemetry trace export.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                               │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ AI Gateway          │ A proxy that sits between you and AI models.  │
    │                     │ Adds caching, rate limits, and tracing.        │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Gateway ID          │ Your gateway's unique name. Create in the     │
    │                     │ Cloudflare dashboard under AI > AI Gateway.   │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Automatic OTEL      │ AI Gateway exports traces automatically.       │
    │                     │ Configure destination in CF dashboard.         │
    └─────────────────────┴────────────────────────────────────────────────┘

Example::

    from genkit.ai import Genkit
    from genkit.plugins.cloudflare import configure_ai_gateway
    from genkit.plugins.compat_oai import OpenAI
    
    # Route OpenAI requests through AI Gateway
    ai = Genkit(
        plugins=[
            OpenAI(
                base_url=configure_ai_gateway(
                    account_id="your-account-id",
                    gateway_id="your-gateway-id",
                    provider="openai",
                ),
            ),
        ],
    )
"""

def configure_ai_gateway(
    account_id: str | None = None,
    gateway_id: str | None = None,
    provider: str = "openai",
) -> str:
    """Get the AI Gateway base URL for a provider.
    
    Args:
        account_id: Cloudflare account ID (or CLOUDFLARE_ACCOUNT_ID env var)
        gateway_id: AI Gateway ID (or CLOUDFLARE_GATEWAY_ID env var)
        provider: Provider name ("openai", "anthropic", "workers-ai", etc.)
    
    Returns:
        Base URL to use with the provider's SDK/plugin
    """
    account_id = account_id or os.environ.get('CLOUDFLARE_ACCOUNT_ID')
    gateway_id = gateway_id or os.environ.get('CLOUDFLARE_GATEWAY_ID')
    
    if not account_id or not gateway_id:
        raise ValueError(
            "CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_GATEWAY_ID required"
        )
    
    return f"https://gateway.ai.cloudflare.com/v1/{account_id}/{gateway_id}/{provider}"
```

## Alternative: Don't Create a Separate Plugin

Given the limited scope, this functionality could also be:

1. **Documented in cloudflare-ai plugin** - Show how to use AI Gateway with Workers AI
2. **Added as a utility function** - Simple helper in `genkit.plugins.cloudflare_ai`
3. **Left to user configuration** - Just document how to set `base_url`

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `CLOUDFLARE_ACCOUNT_ID` | Yes | Your Cloudflare account ID |
| `CLOUDFLARE_GATEWAY_ID` | Yes (for AI Gateway) | Your AI Gateway ID |

## Comparison with Other Telemetry Plugins

| Feature | AWS (`aws`) | GCP (`google-cloud`) | Cloudflare |
|---------|-------------|---------------------|------------|
| Native Tracing Backend | ✅ X-Ray | ✅ Cloud Trace | ❌ None (use 3rd party) |
| Third-Party Export | ✅ | ✅ | ✅ Sentry, Honeycomb, etc. |
| OTLP Export | ✅ | ✅ | ✅ (Workers + AI Gateway) |
| Log Correlation | ✅ | ✅ | ✅ Logpush to many backends |
| Metrics | ✅ CloudWatch | ✅ Cloud Monitoring | ⚠️ Workers Analytics |
| Auto-instrumentation | ✅ | ✅ | ✅ AI Gateway auto-traces |
| Python SDK | ✅ Official | ✅ Official | ❌ REST API only |

## Feasibility Assessment

**Feasibility: ⚠️ MEDIUM-HIGH**

**Reasons:**
1. No native Cloudflare tracing backend, BUT excellent third-party support
2. AI Gateway auto-exports traces to Sentry, Honeycomb, Datadog, etc.
3. Workers OTEL export supports all major observability platforms
4. Implementation would provide presets for common backends

**Recommendation:**
- **Consider implementing** a `cloudflare` telemetry plugin that:
  - Provides presets for Sentry, Honeycomb, Datadog, Grafana, Axiom
  - Helps configure AI Gateway OTEL export
  - Documents the integration patterns
- Could be combined with `cloudflare-ai` plugin or kept separate

## References

- [AI Gateway OTEL Integration](https://developers.cloudflare.com/ai-gateway/observability/otel-integration/)
- [Workers OTEL Export](https://developers.cloudflare.com/workers/observability/exporting-opentelemetry-data/)
- [Logpush Documentation](https://developers.cloudflare.com/logs/logpush/)
- [Workers Analytics](https://developers.cloudflare.com/workers/observability/)
