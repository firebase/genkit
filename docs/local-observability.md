# Observe local metrics

Genkit provides a robust set of built-in observability features, including
tracing and metrics collection powered by
[OpenTelemetry](https://opentelemetry.io/). For local observability, such as
during the development phase, the Genkit Developer UI provides detailed trace
viewing and debugging capabilities. For production observability, we provide
Genkit Monitoring in the Firebase console via the Firebase plugin.
Alternatively, you can export your OpenTelemetry data to the observability
tooling of your choice.

## Tracing & Metrics {:#tracing-and-metrics}

Genkit automatically collects traces and metrics without requiring explicit configuration, allowing you to observe and debug your Genkit code's behavior
in the Developer UI. Genkit stores these traces, enabling you to analyze
your Genkit flows step-by-step with detailed input/output logging and
statistics. In production, Genkit can export traces and metrics to Firebase
Genkit Monitoring for further analysis.

## Log and export events {:#log-and-export}

Genkit provides a centralized logging system that you can configure using
the logging module. One advantage of using the Genkit-provided logger is that
it automatically exports logs to Genkit Monitoring when the Firebase
Telemetry plugin is enabled.

```typescript
import { logger } from 'genkit/logging';

// Set the desired log level
logger.setLogLevel('debug');
```

## Production Observability {:#production-observability}

The
[Genkit Monitoring](https://console.firebase.google.com/project/_/genai_monitoring)
dashboard helps you understand the overall health of your Genkit features. It
is also useful for debugging stability and content issues that may
indicate problems with your LLM prompts and/or Genkit Flows. See the
[Getting Started](/docs/genkit/observability/getting-started) guide for
more details.