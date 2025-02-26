# Advanced Configuration {: #advanced-configuration }

This guide focuses on advanced configuration options for deployed features using
the Firebase telemetry plugin. Detailed descriptions of each configuration
option can be found in our
[JS API reference documentation](https://js.api.genkit.dev/interfaces/_genkit-ai_google-cloud.GcpTelemetryConfigOptions.html).

This documentation will describe how to fine-tune which telemetry is collected,
how often, and from what environments.

## Default Configuration {: #default-configuration }

The Firebase telemetry plugin provides default options, out of the box, to get
you up and running quickly. These are the provided defaults:

```typescript
{
  autoInstrumentation: true,
  autoInstrumentationConfig: {
    '@opentelemetry/instrumentation-dns': { enabled: false },
  }
  disableMetrics: false,
  disableTraces: false,
  disableLoggingInputAndOutput: false,
  forceDevExport: false,
  // 5 minutes
  metricExportIntervalMillis: 300_000,
  // 5 minutes
  metricExportTimeoutMillis: 300_000,
  // See https://js.api.genkit.dev/interfaces/_genkit-ai_google-cloud.GcpTelemetryConfigOptions.html#sampler
  sampler: AlwaysOnSampler()
}
```

## Export local telemetry {: #export-local-telemetry }

To export telemetry when running locally set the `forceDevExport` option to
`true`.

```typescript
import { enableFirebaseTelemetry } from '@genkit-ai/firebase';

enableFirebaseTelemetry({forceDevExport: true});
```

During development and testing, you can decrease latency by adjusting the export
interval and timeout.

Note: Shipping to production with a frequent export interval may
increase the cost for exported telemetry.

```typescript
import { enableFirebaseTelemetry } from '@genkit-ai/firebase';

enableFirebaseTelemetry({
  forceDevExport: true,
  metricExportIntervalMillis: 10_000, // 10 seconds
  metricExportTimeoutMillis: 10_000 // 10 seconds
});
```

## Adjust auto instrumentation {: #adjust-auto-instrumentation }

The Firebase telemetry plugin will automatically collect traces and metrics for
popular frameworks using OpenTelemetry [zero-code instrumentation](https://opentelemetry.io/docs/zero-code/js/).

A full list of available instrumentations can be found in the
[auto-instrumentations-node](https://github.com/open-telemetry/opentelemetry-js-contrib/blob/main/metapackages/auto-instrumentations-node/README.md#supported-instrumentations)
documentation.

To selectively disable or enable instrumentations that are eligible for auto
instrumentation, update the `autoInstrumentationConfig` field:

```typescript
import { enableFirebaseTelemetry } from '@genkit-ai/firebase';

enableFirebaseTelemetry({
  autoInstrumentationConfig: {
    '@opentelemetry/instrumentation-fs': { enabled: false },
    '@opentelemetry/instrumentation-dns': { enabled: false },
    '@opentelemetry/instrumentation-net': { enabled: false },
  }
});
```

## Disable telemetry {: #disable-telemetry }

Firebase Genkit Monitoring leverages a combination of logging, tracing, and
metrics to capture a holistic view of your Genkit interactions, however, you can
also disable each of these elements independently if needed.

### Disable input and output logging {: #disable-input-output-logging }

By default, the Firebase telemetry plugin will capture inputs and outputs for
each Genkit feature or step.

To help you control how customer data is stored, you can disable the logging of
input and output by adding the following to your configuration:

```typescript
import { enableFirebaseTelemetry } from '@genkit-ai/firebase';

enableFirebaseTelemetry({
  disableLoggingInputAndOutput: true
});
```

With this option set, input and output attributes will be redacted
in the Firebase Genkit Monitoring trace viewer and will be missing
from Google Cloud logging.

### Disable metrics {: #disable-metrics }

To disable metrics collection, add the following to your configuration:

```typescript
import { enableFirebaseTelemetry } from '@genkit-ai/firebase';

enableFirebaseTelemetry({
  disableMetrics: true
});
```

With this option set, you will no longer see stability metrics in the
Firebase Genkit Monitoring dashboard and will be missing from Google Cloud
Metrics.

### Disable traces {: #disable-traces }

To disable trace collection, add the following to your configuration:

```typescript
import { enableFirebaseTelemetry } from '@genkit-ai/firebase';

enableFirebaseTelemetry({
  disableTraces: true
});
```

With this option set, you will no longer see traces in the Firebase Genkit
Monitoring feature page, have access to the trace viewer, or see traces
present in Google Cloud Tracing.