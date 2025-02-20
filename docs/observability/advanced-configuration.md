# Advanced Configuration

This guide focuses on advanced configuration options for deployed features using
the Firebase telemetry plugin. Detailed descriptions of each configuration
option can be found in our
[JS API reference documentation](https://js.api.genkit.dev/interfaces/_genkit-ai_google-cloud.GcpTelemetryConfigOptions.html).

This documentation will describe how to fine-tune which telemetry is collected,
how often, and from what environments.

## Default Configuration

Firebase Genkit Monitoring provides default options, out of the box, to get you
up and running quickly.

* [autoInstrumentation](https://opentelemetry.io/docs/zero-code/js/): `true`
* [autoInstrumentationConfig](https://github.com/open-telemetry/opentelemetry-js-contrib/blob/main/metapackages/auto-instrumentations-node/README.md#supported-instrumentations):

```typescript
{
  '@opentelemetry/instrumentation-dns': { enabled: false },
},
```

* credentials: pulled from chosen [authentication strategy](./authentication.md)
* disableMetrics: `false`
* disableTraces: `false`
* disableLoggingInputAndOutput: `false`
* forceDevExport: `false`
* metricExportIntervalMillis: 5 minutes
* metricExportTimeoutMillis: 5 minutes
* projectId: pulled from [authentication strategy](./authentication.md)
* sampler: [AlwaysOnSampler](https://js.api.genkit.dev/interfaces/_genkit-ai_google-cloud.GcpTelemetryConfigOptions.html#sampler)

## Export local telemetry

To export telemetry when running locally set the `forceDevExport` option to `true`.

```typescript
import { enableFirebaseTelemetry } from '@genkit-ai/firebase';

enableFirebaseTelemetry({forceDevExport: true});
```

During development and testing, you can decrease latency by adjusting the export
interval and/or timeout.

Note: you should not ship to production with these reduced values.

```typescript
import { enableFirebaseTelemetry } from '@genkit-ai/firebase';

enableFirebaseTelemetry({
  forceDevExport: true,
  metricExportIntervalMillis: 10_000, // 10 seconds
  metricExportTimeoutMillis: 10_000 // 10 seconds
});
```

## Adjust auto instrumentation

The Firebase telemetry plugin will automatically collect traces and metrics for
popular frameworks, via by OpenTelemetry [zero-code instrumentation](https://opentelemetry.io/docs/zero-code/js/).

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

## Disable telemetry

Firebase Genkit Monitoring leverages a combination of logging, tracing, and
metrics to capture a holistic view of your Genkit interactions, however, you can
also disable each of these elements independently if needed.

### Disable input and output logging

By default, the Firebase telemetry plugin will capture inputs and outputs for
each Genkit feature and/or step.

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

### Disable metrics

To disable metrics collection, add the following to your configuration:

```typescript
import { enableFirebaseTelemetry } from '@genkit-ai/firebase';

enableFirebaseTelemetry({
  disableMetrics: true
});
```

With this option set, you will no longer see stability metrics in the
Firebase Genkit Monitoring dashboard and will be missing from Google Cloud Metrics.

### Disable traces

To disable trace collection, add the following to your configuration:

```typescript
import { enableFirebaseTelemetry } from '@genkit-ai/firebase';

enableFirebaseTelemetry({
  disableTraces: true
});
```

With this option set, you will no longer see traces in the Firebase Genkit Monitoring
feature page, have access to the trace viewer, or see traces present in Google
Cloud Tracing.
