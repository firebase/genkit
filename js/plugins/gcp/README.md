# GCP Plugin - Google Cloud OpenTelemetry Export Plugin

Genkit's tracing and metrics functionality is built on top of [OpenTelemetry](https://opentelemetry.io/) (OT). Genkit seamlessly plugs into existing OT-instrumented applications as well as applications that do not use OT. Logging is facilitated via [Winston](https://github.com/winstonjs/winston) due to the OpenTelemetry [Node.js logging APIs](https://opentelemetry.io/docs/languages/js/getting-started/nodejs/) not being generally available as of Q1 2024.

This plugin exports telemetry and logging data to [Google Cloud Operations Suite](http://cloud/products/operations).

## Adding the plugin

Genkit's configuration supports a `telemetry` block that exposes hooks for instrumentation and logging. Add `gcp()` to the `plugins` array within `genkit.config.ts` and apecify `'gcp'` for both `instrumentation` and `logger` within the `telemetry` block to add this plugin to your project.

```typescript
import { gcp } from '@genkit-ai/plugin-gcp';

export default configureGenkit({
  plugins: [
    ...,
    gcp({...}),
  ],
  ...,
  telemetry: {
    instrumentation: 'gcp',
    logger: 'gcp',
  }
});

```

## Configuring the plugin

There are four available configuration fields:

- `sampler`
- `autoInstrumentation`
- `autoInstrumentationConfig`
- `metricsExportIntervalMillis`

A sample configuration may look similar to:

```typescript
gcp({
  projectId: getProjectId(),
  telemetryConfig: {
    sampler: new AlwaysOnSampler(),
    autoInstrumentation: true,
    autoInstrumentationConfig: {
      '@opentelemetry/instrumentation-fs': { enabled: false },
      '@opentelemetry/instrumentation-dns': { enabled: false },
      '@opentelemetry/instrumentation-net': { enabled: false },
    },
    metricExportIntervalMillis: 5_000,
  },
});
```

### `sampler`

For cases where exporting all traces isn't practical, OpenTelemetry allows trace [sampling](https://opentelemetry.io/docs/languages/java/instrumentation/#sampler).

There are four preconfigured samplers:

- [AlwaysOnSampler](https://github.com/open-telemetry/opentelemetry-java/blob/main/sdk/trace/src/main/java/io/opentelemetry/sdk/trace/samplers/AlwaysOnSampler.java) - samples all traces
- [AlwaysOffSampler](https://github.com/open-telemetry/opentelemetry-java/blob/main/sdk/trace/src/main/java/io/opentelemetry/sdk/trace/samplers/AlwaysOffSampler.java) - samples no traces
- [ParentBased](https://github.com/open-telemetry/opentelemetry-java/blob/main/sdk/trace/src/main/java/io/opentelemetry/sdk/trace/samplers/ParentBasedSampler.java) - samples based on parent span
- [TraceIdRatioBased](https://github.com/open-telemetry/opentelemetry-java/blob/main/sdk/trace/src/main/java/io/opentelemetry/sdk/trace/samplers/TraceIdRatioBasedSampler.java) - samples a configurable percentage of traces

### [`autoInstrumentation`](https://opentelemetry.io/docs/languages/js/automatic/) & [`autoInstrumentationConfig`](https://opentelemetry.io/docs/languages/js/automatic/configuration/)

Enabling automatic instrumentation allows OpenTelemetry to capture telemetry data from [third-party libraries](https://github.com/open-telemetry/opentelemetry-js-contrib/blob/main/metapackages/auto-instrumentations-node/src/utils.ts) without the need to modify code.

### `metricsExportInterval`

This field specifies the metrics export interval in milliseconds. The minimum export interval for GCP Monitoring is 5000ms.
