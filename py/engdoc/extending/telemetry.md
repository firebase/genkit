# Telemetry: Tracing, Metrics, and Logs

This document describes the OpenTelemetry implementation in Genkit, detailing
the spans, metrics, logs, and other telemetry components that are tracked across
the JavaScript/TypeScript implementation, which is the basis for the Python
implementation.

## Tracing Architecture

Genkit's tracing system is built on OpenTelemetry and consists of these key
components:

| System                          | Notes                                                                                      |
|---------------------------------|--------------------------------------------------------------------------------------------|
| **Core Tracing System**         | Defined in `/js/core/src/tracing.ts` that provides the foundational tracing infrastructure |
| **Google Cloud Implementation** | Most telemetry reporting is implemented in the Google Cloud plugin                         |
| **Span Processors**             | Multiple span processors support different export targets, including a "telemetry server"  |
| **Environment-aware Behavior**  | Different behavior in development vs. production environments                              |
| **Log Integration**             | Structured logging with correlation to trace context                                       |
| **Context Propagation**         | Async local storage ensures trace context is maintained across async boundaries            |

## OpenTelemetry Spans

| Span Type                | Description                      | Attributes                                                                                                                             | Context                                        |
|--------------------------|----------------------------------|----------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------|
| **Root Span**            | Main entry point for a feature   | `genkit:name`, `genkit:path`, `genkit:isRoot=true`, `genkit:state`                                                                     | Created in `newTrace()` for top-level features |
| **Action Span**          | Individual actions within a flow | `genkit:name`, `genkit:path`, `genkit:state`, `genkit:input`, `genkit:output`                                                          | Generated for each action execution            |
| **Tool Span**            | Model tool calls                 | `genkit:name`, `genkit:path`, `genkit:input`, `genkit:output`, `genkit:metadata:subtype=tool`, `genkit:sessionId`, `genkit:threadName` | Tracked when tools are called                  |
| **Generate Span**        | AI model generation requests     | `genkit:name`, `genkit:path`, `genkit:modelName`, `genkit:temperature`, `genkit:topK`, `genkit:topP`                                   | Generated when models are called               |
| **User Feedback Span**   | User feedback events             | `genkit:metadata:subtype=userFeedback`, `genkit:metadata:feedbackValue`, `genkit:metadata:textFeedback`                                | Records user feedback                          |
| **User Acceptance Span** | User acceptance events           | `genkit:metadata:subtype=userAcceptance`, `genkit:metadata:acceptanceValue`                                                            | Tracks user acceptance of suggestions          |

## OpenTelemetry Metrics

### Action Metrics

| Metric                   | Type      | Description                           | Dimensions                                                                      |
|--------------------------|-----------|---------------------------------------|---------------------------------------------------------------------------------|
| `genkit/action/requests` | Counter   | Counts calls to Genkit actions        | `name`, `featureName`, `path`, `status`, `errorName`, `source`, `sourceVersion` |
| `genkit/action/latency`  | Histogram | Latencies when calling Genkit actions | `name`, `featureName`, `path`, `status`, `errorName`, `source`, `sourceVersion` |

### Feature Metrics

| Metric                    | Type      | Description                            | Dimensions                                               |
|---------------------------|-----------|----------------------------------------|----------------------------------------------------------|
| `genkit/feature/requests` | Counter   | Counts calls to Genkit features        | `name`, `status`, `errorName`, `source`, `sourceVersion` |
| `genkit/feature/latency`  | Histogram | Latencies when calling Genkit features | `name`, `status`, `errorName`, `source`, `sourceVersion` |

### AI Model Metrics

| Metric                                 | Type      | Description                                        | Dimensions                                                                                             |
|----------------------------------------|-----------|----------------------------------------------------|--------------------------------------------------------------------------------------------------------|
| `genkit/ai/generate/requests`          | Counter   | Counts calls to Genkit generate actions            | `modelName`, `featureName`, `path`, `temperature`, `topK`, `topP`, `status`, `source`, `sourceVersion` |
| `genkit/ai/generate/latency`           | Histogram | Latencies when interacting with a Genkit model     | `modelName`, `featureName`, `path`, `temperature`, `topK`, `topP`, `status`, `source`, `sourceVersion` |
| `genkit/ai/generate/input/characters`  | Counter   | Counts input characters to any Genkit model        | `modelName`, `featureName`, `path`                                                                     |
| `genkit/ai/generate/input/tokens`      | Counter   | Counts input tokens to a Genkit model              | `modelName`, `featureName`, `path`                                                                     |
| `genkit/ai/generate/input/images`      | Counter   | Counts input images to a Genkit model              | `modelName`, `featureName`, `path`                                                                     |
| `genkit/ai/generate/input/videos`      | Counter   | Counts input videos to a Genkit model              | `modelName`, `featureName`, `path`                                                                     |
| `genkit/ai/generate/input/audio`       | Counter   | Counts input audio files to a Genkit model         | `modelName`, `featureName`, `path`                                                                     |
| `genkit/ai/generate/output/characters` | Counter   | Counts output characters from a Genkit model       | `modelName`, `featureName`, `path`                                                                     |
| `genkit/ai/generate/output/tokens`     | Counter   | Counts output tokens from a Genkit model           | `modelName`, `featureName`, `path`                                                                     |
| `genkit/ai/generate/tool_call/count`   | Counter   | Counts tool calls within a Genkit model invocation | `modelName`, `featureName`, `path`, `toolName`                                                         |
| `genkit/ai/generate/tool_call/latency` | Histogram | Tracks latency for each tool call                  | `modelName`, `featureName`, `path`, `toolName`                                                         |

### User Engagement Metrics

| Metric                         | Type    | Description                          | Dimensions                                            |
|--------------------------------|---------|--------------------------------------|-------------------------------------------------------|
| `genkit/engagement/feedback`   | Counter | Counts user feedback events          | `name`, `value`, `hasText`, `source`, `sourceVersion` |
| `genkit/engagement/acceptance` | Counter | Tracks unique user acceptance events | `name`, `value`, `source`, `sourceVersion`            |

## How Tracing Works

### Initialization
   * When Genkit initializes, the `enableTelemetry()` function is called
   * This sets up the OpenTelemetry NodeSDK with configured exporters
   * In development mode, a `SimpleSpanProcessor` is used; in production, a `BatchSpanProcessor`

### Span Creation
   * Spans are created using the `runInNewSpan()` and `newTrace()` functions
   * Each span receives metadata attributes via the `metadataToAttributes()` function
   * Context propagation is handled using async local storage

### Path Tracking
   * Spans form a hierarchy with paths tracking parent-child relationships
   * Path names are constructed in the `buildPath()` function
   * A `SpanMetadata` object is maintained for each span

### Error Handling
   * Spans capture errors with `SpanStatusCode.ERROR`
   * Exception events are recorded in spans
   * Error information is captured in metrics

### Export Process
   * The Google Cloud plugin provides exporters for Cloud Trace and Cloud Monitoring
   * Spans are processed into metrics using telemetry implementations
   * Different telemetry implementations for different types of spans (action, feature, generate, etc.)
   * Metrics are batched and periodically exported to GCP

### Cleanup
   * When the application shuts down, the `cleanUpTracing()` function is called
   * This flushes any pending metrics and shuts down the OpenTelemetry SDK

## OpenTelemetry Logs

Genkit integrates OpenTelemetry with structured logging through the following components:

| Log Component         | Description                                   | Implementation                              |
|-----------------------|-----------------------------------------------|---------------------------------------------|
| **Structured Logger** | Pino/Winston integration with OpenTelemetry   | Automatic context enrichment with trace IDs |
| **Log Correlation**   | Automatically adds trace and span IDs to logs | Enables correlation between logs and traces |
| **Log Exporting**     | Exports logs to Google Cloud Logging          | Maintains trace context in logs             |
| **Log Levels**        | Debug, Info, Warn, Error                      | Controls verbosity of exported logs         |

## Resource Attributes

Resource attributes provide information about the execution environment and are attached to all telemetry signals:

| Resource Attribute       | Description             | Example Value     |
|--------------------------|-------------------------|-------------------|
| `service.name`           | Name of the service     | `"genkit"`        |
| `service.version`        | Service version         | `"v0.2.0"`        |
| `deployment.environment` | Environment (dev, prod) | `"production"`    |
| `gcp.project.id`         | Google Cloud project ID | `"my-project-id"` |
| `gcp.region`             | Google Cloud region     | `"us-central1"`   |
| `telemetry.sdk.name`     | SDK name                | `"opentelemetry"` |
| `telemetry.sdk.language` | SDK language            | `"nodejs"`        |
| `telemetry.sdk.version`  | SDK version             | `"1.0.0"`         |

## Sampling Configuration

Genkit implements the following sampling strategies:

| Sampling Type     | Description                                        | Environment |
|-------------------|----------------------------------------------------|-------------|
| **AlwaysOn**      | Samples 100% of traces                             | Development |
| **Probabilistic** | Samples a percentage of traces                     | Production  |
| **Head-based**    | Sampling decision made at the beginning of a trace | Default     |

Sampling configuration can be adjusted through the Google Cloud plugin configuration.

## Context Propagation

Genkit uses several mechanisms for context propagation:

1. **Async Local Storage**: Node.js AsyncLocalStorage for propagating context across async boundaries
2. **W3C Trace Context**: Standard format for trace context propagation
3. **Baggage**: For carrying additional key-value pairs across service boundaries

## OpenTelemetry Exporters

Genkit supports the following exporters:

| Exporter                      | Description                                   | Signal Types |
|-------------------------------|-----------------------------------------------|--------------|
| **Cloud Trace Exporter**      | Exports spans to Google Cloud Trace           | Traces       |
| **Cloud Monitoring Exporter** | Exports metrics to Google Cloud Monitoring    | Metrics      |
| **Cloud Logging Exporter**    | Exports logs to Google Cloud Logging          | Logs         |
| **Telemetry Server Exporter** | Exports telemetry to local development server | Traces       |

## Correlation Between Signals

Genkit correlates telemetry signals using:

1. **Trace ID**: Links spans, logs, and metrics from the same trace
2. **Span ID**: Identifies the specific operation within a trace
3. **Resource**: Common resource attributes attached to all signals
4. **Session ID**: Tracks user sessions across multiple traces

This correlation enables end-to-end visibility into application behavior and performance.

## Implementation Differences

Different language implementations (Go, JavaScript/TypeScript, Python) may have
slightly different metric names or collection strategies, but they all follow
the same general principles for tracing and telemetry.
