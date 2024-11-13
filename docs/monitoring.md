# Monitoring

Firebase Genkit is fully instrumented with
[OpenTelemetry](https://opentelemetry.io/) and provides hooks to export
telemetry data. The [Google Cloud plugin](./plugins/google-cloud.md) and the [Firebase plugin](./plugins/firebase.md) both export telemetry to Cloud's operations suite. Uisng either plugin poweres the [Firebase AI Monitoring dashboard (private preview)](https://forms.gle/Lp5S1NxbZUXsWc457) that has an AI-idiomatic view of telemetry data.