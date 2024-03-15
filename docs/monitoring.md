# Monitoring

Genkit framework is fully instrumented with OpenTelemetry tracing, metrics and logging. Genkit provides out-of-the-box intergration with Google Cloud Tracing, Logging and Monitoring. To enable exporting your traces, logs and metrics to Google Cloud Tracing, Logging and Monitoring simply add the `gcp` plugin to your configuration.

```js
configureGenkit({
  plugins: [
    firebase({ projectId: getProjectId() }),
    gcp({
      projectId: getProjectId(),
    }),
    // ...
  ],
  traceStore: 'firebase',
  telemetry: {
    instrumentation: 'gcp',
  }
  // ...
});
```

When running in production your telemetry will get automatically exported.

> [!NOTE]  
> When running locally (specifically via the `genkit` CLI) not all instrumentaion is enabled and you may not see your telemetry getting exported during local development.

The `traceStore` is complimentary to your telemetry instrumentation. It allows you to inspect your traces for your flow runs in the Genkit Dev UI. It requires a separeate configuration which provides a trace storage implementation. The `firebase` plugin offers Firestore based implementation. This configuration is optional, but is recommended becuase it allows you to easily inspect and debug issues in production. When using Firestore based trace storage you will want to enable TTL for the trace documents: https://firebase.google.com/docs/firestore/ttl
