# Configuration and Plugins

Genkit frameworks has a configuration and plugin system. Every Genkit app starts with configuration where you specify plugins you want to use and configure various subsystems. For example, as you might have seen in one of the earlier examples:

```
configureGenkit({
  plugins: [
    firebase({ projectId: getProjectId() }),
    vertexAI({ projectId: getProjectId(), location: getLocation() || 'us-central1' }),
  ],
  flowStateStore: 'firebase',
  traceStore: 'firebase',
  enableTracingAndMetrics: true,
  logLevel: 'info',
});
```

In `plugins` you specify an array of plugins that will be made available to the framework. Plugins provide such features as: models, retrievers, indexers, flow state stores, trace stores, etc. One plugin can provide more than one thing, and even more than one, for example, model.

`flowStateStore` tell Genkit which plugin to use for persisting flow states. The `firebase` plugin provides a Firestore implementation.

`traceStore` (similar to `flowStateStore`) tell Genkit which plugin to use for persisting traces. The `firebase` plugin provides a Firestore implementation.

`enableTracingAndMetrics` instructs the framework to perform OpenTelemetry instrumentation and enable trace collection.

`logLevel` specifies verbosity level of the framework level logging. Sometimes it's useful when troubleshooting to see more details log messages, set it to `debug`.