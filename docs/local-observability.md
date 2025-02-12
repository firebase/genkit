# Observability

Genkit provides a robust set of built-in observability features, including tracing and metrics collection powered by [OpenTelemetry](https://opentelemetry.io/). For local observability (e.g. during the development phase), the Genkit Developer UI provides detailed trace viewing and debugging capabilities. For production observability, we provide Genkit Monitoring in the Firebase console via the Firebase plugin. Alternatively, you can export your OpenTelemetry data to the observability tooling of your choice.

## Tracing & Metrics

Genkit automatically collects traces and metrics without requiring explicit configuration, allowing you to observe and debug your Genkit code's behavior in the Developer UI. These traces are stored locally, enabling you to analyze your Genkit flows step-by-step with detailed input/output logging and statistics. In production, traces and metrics can be exported to Firebase Genkit Monitoring for further analysis.

## Logging

Genkit also provides a centralized logging system that can be configured using the logging module. One advantage of using the Genkit provided logger is that logs will automatically be exported to Genkit Monitoring when the Firebase Telemetry plugin is enabled.

```typescript
import { logger } from 'genkit/logging';

// Set the desired log level
logger.setLogLevel('debug');
```

## Production Observability

The [Genkit Monitoring](https://console.firebase.google.com/project/_/genai_monitoring) dashboard helps you to understand the overall health of your Genkit features, as well as debug stability and content issues that may point to problems with your LLM prompts and/or Genkit Flows. See the [Getting Started](./observability/getting-started.md) guide for more details.
