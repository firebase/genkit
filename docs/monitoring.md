# Monitoring

Genkit is fully instrumented with [OpenTelemetry](https://opentelemetry.io/) and provides hooks to export telemetry data.

## Telemetry Configuration

Genkit's configuration supports a `telemetry` block that exposes instrumentation (trace and metrics) and logging hooks, allowing plugins to provide OpenTelemetry and logging exporters.

```ts
configureGenkit({
  telemetry: {
    instrumentation: ...,
    logger: ...
  }
});
```

Genkit ships with a [Google Cloud plugin](./plugins/google-cloud.md) which exports telemetry to Cloud's operations suite.

## Trace Store

The `traceStore` option is complementary to the telemetry instrumentation. It
lets you inspect your traces for your flow runs in the Genkit Developer UI. It
requires a separate configuration which provides a trace storage implementation.
The `firebase` plugin offers a Firestore-based implementation. This
configuration is optional, but is recommended because it lets you inspect and
debug issues in production. When using Firestore-based trace storage you will
want to enable TTL for the trace documents:
https://firebase.google.com/docs/firestore/ttl

```ts
import { firebase } from '@genkit-ai/plugin-firebase';

configureGenkit({
  plugins: [firebase()],
  traceStore: 'firebase',
});
```
