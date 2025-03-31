# Monitoring

Genkit provides two complementary monitoring features: OpenTelemetry
export and trace inspection using the developer UI.

## OpenTelemetry export

Genkit is fully instrumented with [OpenTelemetry](https://opentelemetry.io/) and
provides hooks to export telemetry data.

The [Google Cloud plugin](./plugins/google-cloud.md) exports telemetry to
Cloud's operations suite.

## Trace store

The trace store feature is complementary to the telemetry instrumentation. It
lets you inspect your traces for your flow runs in the Genkit Developer UI.

This feature is enabled whenever you run a Genkit flow in a dev environment
(such as when using `genkit start` or `genkit flow:run`).
