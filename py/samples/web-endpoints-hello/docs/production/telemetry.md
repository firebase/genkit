# Telemetry

The sample includes built-in OpenTelemetry tracing and structured
logging for production observability.

## OpenTelemetry tracing

`src/telemetry.py` configures OTLP trace export so every request
produces a distributed trace:

```
HTTP request → ASGI middleware → Genkit flow → model call
```

### Enabling tracing

```bash
# Local development with Jaeger
just dev  # Auto-starts Jaeger + passes --otel-endpoint

# Manual
python -m src --otel-endpoint http://localhost:4318
```

### Configuration

| Setting | Env var | CLI flag | Default |
|---------|---------|----------|---------|
| Endpoint | `OTEL_EXPORTER_OTLP_ENDPOINT` | `--otel-endpoint` | *(disabled)* |
| Protocol | `OTEL_EXPORTER_OTLP_PROTOCOL` | `--otel-protocol` | `http/protobuf` |
| Service name | `OTEL_SERVICE_NAME` | — | `genkit-endpoints` |

### Supported exporters

| Protocol | Package | Use case |
|----------|---------|----------|
| HTTP/protobuf (default) | `opentelemetry-exporter-otlp-proto-http` | Jaeger, Tempo, GCP |
| gRPC | `opentelemetry-exporter-otlp-proto-grpc` | High-throughput collectors |

### Framework instrumentation

The telemetry module auto-detects the framework and applies the
appropriate instrumentation:

| Framework | Instrumentation |
|-----------|-----------------|
| FastAPI | `opentelemetry-instrumentation-fastapi` |
| Litestar | `opentelemetry-instrumentation-asgi` (generic) |
| Quart | `opentelemetry-instrumentation-asgi` (generic) |

### Cloud platform auto-detection

`src/app_init.py` auto-detects the cloud platform and configures
the appropriate Genkit telemetry plugin:

| Platform | Detection | Plugin |
|----------|-----------|--------|
| Google Cloud | `K_SERVICE` or `GOOGLE_CLOUD_PROJECT` | `google_genai` with Cloud Trace |
| AWS | `AWS_REGION` | OTLP export to X-Ray |
| Azure | `AZURE_FUNCTIONS_ENVIRONMENT` | OTLP export |
| Generic | Fallback | OTLP HTTP export |

### Viewing traces

=== "Jaeger (local)"

    ```bash
    just dev  # Starts Jaeger automatically
    # Open http://localhost:16686
    ```

=== "Google Cloud Trace"

    Deploy to Cloud Run — traces appear automatically in the
    Google Cloud Console under **Trace**.

=== "Custom collector"

    ```bash
    python -m src --otel-endpoint http://your-collector:4318
    ```

## Structured logging

`src/logging.py` provides automatic format detection:

| Environment | Format | Features |
|-------------|--------|----------|
| TTY (dev) | Rich console | Colors, pretty tracebacks |
| Non-TTY (prod) | JSON lines | Machine-parseable, log aggregator friendly |

Force a specific format:

```bash
LOG_FORMAT=json python -m src    # JSON even in terminal
LOG_FORMAT=console python -m src # Rich even in CI
```

### Log context

Every log line includes:

- `request_id` — from `RequestIdMiddleware` (X-Request-ID)
- `timestamp` — ISO 8601 UTC
- `level` — info, warning, error, etc.
- `logger` — module name
- `event` — log message

### Example JSON log

```json
{
  "request_id": "a1b2c3d4e5f6",
  "timestamp": "2026-01-15T10:30:00.000Z",
  "level": "info",
  "logger": "src.flows",
  "event": "Flow completed",
  "flow": "tell_joke",
  "duration_ms": 1234
}
```

## Trace → log correlation

The `request_id` appears in both traces and logs, enabling
correlation across systems. When using Google Cloud:

- Traces appear in Cloud Trace
- Logs appear in Cloud Logging
- Both are linked by `request_id` and trace context
