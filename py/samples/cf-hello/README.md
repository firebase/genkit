# Cloudflare/OTLP Telemetry Hello Sample

This sample demonstrates Cloudflare-compatible OTLP telemetry export with Genkit.

The `cf` plugin exports traces via OpenTelemetry Protocol (OTLP) to any compatible
backend - not just Cloudflare's endpoints. Use it with Grafana, Honeycomb, Axiom, 
or any OTLP receiver.

## Prerequisites

1. An OTLP-compatible endpoint (Grafana Cloud, Honeycomb, Axiom, etc.)
2. API token for authentication (if required)

## Setup

### 1. Configure your OTLP endpoint

```bash
# For Grafana Cloud
export CF_OTLP_ENDPOINT="https://otlp-gateway-prod-us-central-0.grafana.net/otlp/v1/traces"
export CF_API_TOKEN="your-grafana-api-key"

# For Honeycomb (via OTLP)
export CF_OTLP_ENDPOINT="https://api.honeycomb.io/v1/traces"
export CF_API_TOKEN="your-honeycomb-api-key"

# For Axiom
export CF_OTLP_ENDPOINT="https://api.axiom.co/v1/traces"
export CF_API_TOKEN="your-axiom-token"
```

### 2. Set your Google AI API key

```bash
export GOOGLE_GENAI_API_KEY="your-google-ai-key"
```

## Running the Sample

```bash
# From the sample directory
./run.sh
```

## Testing with the DevUI

1. Open http://localhost:4000 in your browser
2. Navigate to the "say_hello" flow
3. Enter a name and run the flow
4. View traces in your OTLP backend's dashboard

## What This Sample Demonstrates

- Generic OTLP export via the cf plugin
- Bearer token authentication
- PII redaction for model inputs/outputs
- Works with any OTLP-compatible backend
