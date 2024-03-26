# Observability

The observability framework is based on OpenTelemetry and Genkit uses custom
span processors and exporters to save trace data into Firestore (more options
are being worked on) from where the tooling can use the data for visualization
and evaluation.

To enable tracing for flows and AI primitives all you need to do is enable it in
the config file by setting `enableTracingAndMetrics: true`

```javascript
configureGenkit({
  plugins: // ...
  flowStateStore: 'firebase',
  traceStore: 'firebase',
  enableTracingAndMetrics: true,
  logLevel: 'info',
});
```
