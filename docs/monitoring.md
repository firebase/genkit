# Monitoring

Firebase Genkit is fully instrumented with
[OpenTelemetry](https://opentelemetry.io/) and provides built-in telemetry support for tracing and metrics.

## Telemetry Configuration

Genkit automatically manages tracing and metrics without requiring explicit configuration. You can enable telemetry exports to Firebase using the respective plugin and helper function. Using the Firebase plugin powers the [Genkit Monitoring dashboard](https://console.firebase.google.com/project/_/genai_monitoring) that has an AI-centric view of telemetry data.

```ts
import { genkit } from 'genkit';
import { enableFirebaseTelemetry } from '@genkit-ai/firebase';

enableFirebaseTelemetry({
  // Configuration options
});

const ai = genkit({
  plugins: [ ... ]
});
```
More details are outlined in the [Firebase plugin docs](./plugins/firebase.md).

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
