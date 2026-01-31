# Vercel Plugins Implementation Plan

**Status:** Research Complete  
**AI Plugin Feasibility:** ⚠️ LOW-MEDIUM (AI SDK is JS/TS only, but AI Gateway works)  
**Telemetry Plugin Feasibility:** ⚠️ MEDIUM (standard OTEL works, @vercel/otel is Node.js only)  
**Estimated Effort:** Low (if implemented)  
**Dependencies:** `httpx`, `openai` or `anthropic`, `opentelemetry-sdk`

## Overview

**Important Clarification:** Python IS fully supported on Vercel as a runtime platform.
FastAPI, Flask, and other Python frameworks work great as Vercel Functions.

However, Vercel's **AI-specific SDKs** and **@vercel/otel** are JavaScript/TypeScript only.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    VERCEL PYTHON SUPPORT MATRIX                         │
│                                                                         │
│    ┌─────────────────────────────────────────────────────────────────┐  │
│    │                    Vercel + Python                              │  │
│    ├─────────────────────────────────────────────────────────────────┤  │
│    │  Feature           │ Python Support │ Notes                     │  │
│    ├─────────────────────────────────────────────────────────────────┤  │
│    │  Vercel Platform   │ ✅ YES         │ FastAPI, Flask work great │  │
│    │  Vercel Functions  │ ✅ YES         │ Python serverless         │  │
│    │  AI Gateway        │ ✅ YES         │ HTTP API, any language    │  │
│    │  AI SDK            │ ❌ JS/TS only  │ No Python package         │  │
│    │  @vercel/otel      │ ❌ Node.js     │ No Python package         │  │
│    │  Standard OTEL     │ ✅ YES         │ Works from Python apps    │  │
│    └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│    Key Concepts (ELI5):                                                 │
│    ┌─────────────────────┬────────────────────────────────────────────┐ │
│    │ Vercel Functions    │ Run Python (FastAPI/Flask) as serverless. │ │
│    │                     │ Auto-scales, 250MB limit per function.     │ │
│    ├─────────────────────┼────────────────────────────────────────────┤ │
│    │ AI Gateway          │ A proxy that adds caching, rate limiting, │ │
│    │                     │ and routing to AI API calls.              │ │
│    ├─────────────────────┼────────────────────────────────────────────┤ │
│    │ Vercel AI SDK       │ JavaScript library for building AI apps.  │ │
│    │                     │ NOT available for Python (use AI Gateway).│ │
│    ├─────────────────────┼────────────────────────────────────────────┤ │
│    │ @vercel/otel        │ Vercel's OTEL package for Node.js only.   │ │
│    │                     │ Python apps use standard OTEL instead.    │ │
│    ├─────────────────────┼────────────────────────────────────────────┤ │
│    │ OIDC Token          │ Auto-generated auth token on Vercel.      │ │
│    │                     │ Available to Python apps too!             │ │
│    └─────────────────────┴────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘

Reference: https://vercel.com/docs/frameworks/backend/fastapi
```

## Part 1: Vercel AI Gateway Plugin

### What AI Gateway Provides

The AI Gateway is an HTTP proxy that:
- Routes requests to multiple AI providers
- Adds request caching
- Provides rate limiting
- Offers fallback routing
- Works with ANY language via HTTP

### Python Integration

Since AI Gateway uses OpenAI-compatible and Anthropic-compatible APIs, Python apps can
use it by pointing existing SDKs at the gateway URL.

```python
# Using OpenAI SDK with Vercel AI Gateway
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv('AI_GATEWAY_API_KEY'),
    base_url='https://ai-gateway.vercel.sh/v1'
)

response = client.chat.completions.create(
    model='anthropic/claude-sonnet-4.5',  # Can use any provider!
    messages=[{'role': 'user', 'content': 'Hello!'}]
)
```

### Implementation Option: Simple Helper

Rather than a full plugin, provide a helper function:

```python
# py/plugins/vercel/__init__.py
"""Vercel AI Gateway integration for Genkit.

Vercel's AI Gateway is a proxy that works with any AI provider, adding
caching, rate limiting, and fallback routing.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                               │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ AI Gateway          │ A middleman between you and AI providers.     │
    │                     │ Adds caching and rate limiting automatically. │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Universal Provider  │ Use any model (OpenAI, Anthropic, etc.)       │
    │                     │ through one consistent API.                   │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ API Key             │ Your AI_GATEWAY_API_KEY for authentication.   │
    │                     │ Get it from Vercel dashboard.                 │
    └─────────────────────┴────────────────────────────────────────────────┘

Example::

    from genkit.ai import Genkit
    from genkit.plugins.vercel import vercel_gateway_url
    from genkit.plugins.compat_oai import OpenAI
    
    # Route OpenAI requests through Vercel AI Gateway
    ai = Genkit(
        plugins=[
            OpenAI(
                base_url=vercel_gateway_url(),
                api_key=os.environ['AI_GATEWAY_API_KEY'],
            ),
        ],
    )
"""

import os

AI_GATEWAY_BASE_URL = "https://ai-gateway.vercel.sh/v1"


def vercel_gateway_url() -> str:
    """Get the Vercel AI Gateway base URL.
    
    Returns:
        The AI Gateway URL to use with OpenAI-compatible SDKs.
    
    Example:
        >>> from genkit.plugins.compat_oai import OpenAI
        >>> OpenAI(base_url=vercel_gateway_url())
    """
    return AI_GATEWAY_BASE_URL


def get_vercel_auth() -> str | None:
    """Get the appropriate auth token for Vercel.
    
    On Vercel deployments, uses OIDC token. Otherwise, uses API key.
    
    Returns:
        Auth token string or None if not configured.
    """
    # On Vercel, OIDC token is auto-generated
    if oidc := os.environ.get('VERCEL_OIDC_TOKEN'):
        return oidc
    # For local development, use API key
    return os.environ.get('AI_GATEWAY_API_KEY')
```

### Feasibility Assessment

**Feasibility: ⚠️ LOW-MEDIUM**

**Reasons:**
1. AI Gateway works fine with Python via existing SDKs
2. No Vercel-specific AI functionality beyond the gateway
3. Implementation would be trivial (just URL helper)
4. Users can already do this without a plugin

**Recommendation:**
- Document how to use AI Gateway with existing plugins (`compat-oai`, `anthropic`)
- Don't create a separate plugin unless there's strong user demand
- Could add as a simple utility function in documentation

---

## Part 2: Vercel Telemetry Plugin

### Current State

Vercel's `@vercel/otel` package is **Node.js only**, but Python apps on Vercel CAN use
standard OpenTelemetry to export traces to any OTEL-compatible backend.

```typescript
// @vercel/otel - JavaScript/TypeScript only
import { registerOTel } from '@vercel/otel';

export function register() {
  registerOTel({ serviceName: 'your-project-name' });
}
```

### What @vercel/otel Provides (Node.js only)

- Auto-configuration for Vercel's OTEL collector
- Node.js and Edge runtime support
- W3C Trace Context propagation
- Fetch API instrumentation

### Python Options on Vercel

Python apps deployed on Vercel (FastAPI, Flask, etc.) can use standard OTEL:

```python
# Standard OTLP export from Python on Vercel
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

# Works from Vercel Python Functions!
provider = TracerProvider()
provider.add_span_processor(
    BatchSpanProcessor(
        OTLPSpanExporter(
            endpoint="https://api.honeycomb.io/v1/traces",  # Or any OTEL backend
            headers={"x-honeycomb-team": os.environ["HONEYCOMB_API_KEY"]},
        )
    )
)
trace.set_tracer_provider(provider)
```

### Potential Vercel Telemetry Plugin

A simple plugin could provide preset configs for common backends:

```python
class VercelTelemetry:
    """Telemetry for Python apps on Vercel.
    
    Since @vercel/otel is Node.js only, this provides standard OTEL
    configuration with presets for popular backends.
    """
    
    def __init__(
        self,
        backend: Literal["honeycomb", "datadog", "grafana", "axiom"],
        service_name: str = "genkit-vercel-app",
        api_key: str | None = None,
    ):
        ...
```

### Feasibility Assessment

**Feasibility: ⚠️ MEDIUM**

**Reasons:**
1. Python DOES work on Vercel (FastAPI, Flask are first-class)
2. Standard OTEL works from Python Vercel Functions
3. No Vercel-specific OTEL package, but standard approach works
4. Could provide convenience presets for common backends

**Recommendation:**
- **Consider a simple helper** for common OTEL backends
- Not Vercel-specific, but useful for Vercel Python users
- Lower priority than `azure` and `cloudflare-ai`

---

## Summary: Should We Build Vercel Plugins?

### Vercel AI Plugin

| Aspect | Assessment |
|--------|------------|
| **Need** | Low - existing plugins work fine with AI Gateway |
| **Effort** | Very low - just URL helper |
| **Value** | Convenience for Vercel users |
| **Recommendation** | **Low priority** - document AI Gateway usage |

### Vercel Telemetry Plugin

| Aspect | Assessment |
|--------|------------|
| **Need** | Medium - Python on Vercel is growing |
| **Effort** | Low - standard OTEL with presets |
| **Value** | Convenience for common backends |
| **Recommendation** | **Consider** if user demand exists |

---

## Alternative: Documentation Only

Instead of plugins, provide documentation showing how to:

### Using AI Gateway with Genkit

```markdown
# Using Vercel AI Gateway with Genkit

Vercel AI Gateway can be used with Genkit's `compat-oai` plugin by setting
the base URL:

```python
from genkit.ai import Genkit
from genkit.plugins.compat_oai import OpenAI
import os

ai = Genkit(
    plugins=[
        OpenAI(
            base_url="https://ai-gateway.vercel.sh/v1",
            api_key=os.environ['AI_GATEWAY_API_KEY'],
        ),
    ],
    model="openai/gpt-4o",  # or "anthropic/claude-sonnet-4.5"
)
```

### Telemetry for Python on Vercel

For Python serverless functions on Vercel, use standard OpenTelemetry
with your preferred backend (Honeycomb, Datadog, etc.):

```python
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
# ... standard OTLP setup
```
```

---

## Comparison with Other Platforms

| Platform | AI Plugin | Telemetry Plugin | Python Runtime |
|----------|-----------|------------------|----------------|
| **AWS** | ✅ aws-bedrock | ✅ aws | ✅ Full |
| **GCP** | ✅ google-genai | ✅ google-cloud | ✅ Full |
| **Azure** | ✅ msfoundry | ✅ azure (planned) | ✅ Full |
| **Cloudflare** | ✅ cloudflare-ai (planned) | ⚠️ AI Gateway only | ✅ Workers |
| **Vercel** | ⚠️ AI Gateway helper | ⚠️ Standard OTEL | ✅ Functions |

---

## Final Recommendation

**Low priority, but feasible if user demand exists.** Python works great on Vercel!

### Recommended Approach

1. **Document AI Gateway usage** with existing `compat-oai` and `anthropic` plugins
2. **Document standard OTEL** for telemetry from Python Vercel Functions
3. **Consider a simple `vercel` plugin** if users request it, containing:
   - `vercel_gateway_url()` helper for AI Gateway
   - `VercelTelemetry` class with presets for Honeycomb, Datadog, etc.

### Priority

| Plugin | Priority | Reason |
|--------|----------|--------|
| `azure` | High | Official OTEL distro, pairs with msfoundry |
| `cloudflare-ai` | High | Growing edge AI market |
| `vercel` | Low | Works without plugin, add if demanded |

### If We Build It

A minimal `vercel` plugin would look like:

```python
# py/plugins/vercel/src/genkit/plugins/vercel/__init__.py
"""Vercel integration helpers for Genkit.

Provides utilities for Python apps deployed on Vercel Functions.
"""

def vercel_gateway_url() -> str:
    """Get Vercel AI Gateway URL."""
    return "https://ai-gateway.vercel.sh/v1"

class VercelTelemetry:
    """Standard OTEL with presets for common backends."""
    ...
```

## References

- [Vercel AI Gateway - Python](https://vercel.com/docs/ai-gateway/python)
- [Vercel AI SDK](https://sdk.vercel.ai/docs) (JS/TS only)
- [@vercel/otel](https://www.npmjs.com/package/@vercel/otel) (Node.js only)
- [Python AI SDK (Community)](https://github.com/python-ai-sdk/sdk) (unofficial)
