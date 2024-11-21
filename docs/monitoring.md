# Monitoring

Firebase Genkit is fully instrumented with
[OpenTelemetry](https://opentelemetry.io/) and provides built-in telemetry support for tracing and metrics.

## Telemetry Configuration

Genkit automatically manages tracing and metrics without requiring explicit configuration. You can enable telemetry exports for Firebase or Google Cloud using their respective plugins and helper functions. Using either plugin poweres the [Firebase AI Monitoring dashboard (private preview)](https://forms.gle/Lp5S1NxbZUXsWc457) that has an AI-idiomatic view of telemetry data.

### For Firebase:

```ts
import { genkit } from 'genkit';
import { enableFirebaseTelemetry } from '@genkit-ai/firebase';

enableFirebaseTelemetry({
  // Firebase-specific configuration options
});

const ai = genkit({
  plugins: [ ... ]
});
```
More details are outlined in the [Firebase plugin docs](./plugins/firebase.md).

### For Google Cloud:

```ts
import { genkit } from 'genkit';
import { enableGoogleCloudTelemetry } from '@genkit-ai/google-cloud';

enableGoogleCloudTelemetry({
  // Google Cloud-specific configuration options
});

const ai = genkit({
  plugins: [ ... ]
});
```
More details are outlined in the [Google Cloud plugin docs](./plugins/google-cloud.md).

## Logging
Genkit provides a centralized logging system that can be configured using the logging module. Logs will be exported Google Cloud operations suite if telemetry export is enabled.

```ts
import { logger } from 'genkit/logging';

// Set the desired log level
logger.setLogLevel('debug');
```

## Trace Storage and Developer UI
Traces are automatically captured and can be viewed in the Genkit Developer UI. To start the UI:

```posix-terminal
npx genkit start -- <command to run your code>
```

When using Firebase, trace data is automatically stored in Firestore. It's recommended to enable [TTL (Time To Live)](https://firebase.google.com/docs/firestore/ttl) for trace documents to manage storage costs and data retention.
