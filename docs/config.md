
# Configuration and plugins

Genkit has a configuration and plugin system. Every Genkit app starts with
configuration where you specify the plugins you want to use and configure
various subsystems.

Here is an example you might have seen in some of the examples:

```js
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

In `plugins`, you specify an array of plugins that will be available to the
framework. Plugins provide features such as models, retrievers, indexers, flow
state stores, and trace stores. One plugin can provide more than one feature,
and even more than one instance of that feature.

`flowStateStore` tells Genkit which plugin to use for persisting flow states.
The `firebase` plugin provides a Cloud Firestore implementation.

`traceStore` (similar to `flowStateStore`) tells Genkit which plugin to use for
persisting traces. The `firebase` plugin provides a Cloud Firestore
implementation.

`enableTracingAndMetrics` instructs the framework to perform OpenTelemetry
instrumentation and enable trace collection.

`logLevel` specifies the verbosity of framework-level logging. Sometimes it's
useful when troubleshooting to see more detailed log messages; set it to
`debug`.