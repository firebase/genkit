# Telemetry Collection {: #telemetry-collection }

The Firebase telemetry plugin exports a combination of metrics, traces, and
logs to Google Cloud Observability. This document details which metrics, trace
attributes, and logs will be collected and what you can expect in terms of
latency, quotas, and cost.

## Telemetry delay {: #telemetry-delay }

There may be a slight delay before telemetry from a given invocation is
available in Firebase. This is dependent on your export interval (5 minutes
by default).

## Quotas and limits {: #quotas-and-limits }

There are several quotas that are important to keep in mind:

- [Cloud Trace Quotas](http://cloud.google.com/trace/docs/quotas)
- [Cloud Logging Quotas](http://cloud.google.com/logging/quotas)
- [Cloud Monitoring Quotas](http://cloud.google.com/monitoring/quotas)

## Cost {: #cost }

Cloud Logging, Cloud Trace, and Cloud Monitoring have generous free-of-charge
tiers. Specific pricing can be found at the following links:

- [Cloud Logging Pricing](http://cloud.google.com/stackdriver/pricing#google-cloud-observability-pricing)
- [Cloud Trace Pricing](https://cloud.google.com/trace#pricing)
- [Cloud Monitoring Pricing](https://cloud.google.com/stackdriver/pricing#monitoring-pricing-summary)

## Metrics {: #metrics }

The Firebase telemetry plugin collects a number of different metrics to support
the various Genkit action types detailed in the following sections.

### Feature metrics {: #feature-metrics }

Features are the top-level entry-point to your Genkit code. In most cases, this
will be a flow. Otherwise, this will be the top-most span in a trace.

| Name                    | Type      | Description             |
| ----------------------- | --------- | ----------------------- |
| genkit/feature/requests | Counter   | Number of requests      |
| genkit/feature/latency  | Histogram | Execution latency in ms |

Each feature metric contains the following dimensions:

| Name          | Description                                                                      |
| ------------- | -------------------------------------------------------------------------------- |
| name          | The name of the feature. In most cases, this is the top-level Genkit flow        |
| status        | 'success' or 'failure' depending on whether or not the feature request succeeded |
| error         | Only set when `status=failure`. Contains the error type that caused the failure  |
| source        | The Genkit source language. Eg. 'ts'                                             |
| sourceVersion | The Genkit framework version                                                     |

### Action metrics {: #action-metrics }

Actions represent a generic step of execution within Genkit. Each of these steps
will have the following metrics tracked:

| Name                    | Type      | Description                                   |
| ----------------------- | --------- | --------------------------------------------- |
| genkit/action/requests  | Counter   | Number of times this action has been executed |
| genkit/action/latency   | Histogram | Execution latency in ms                       |

Each action metric contains the following dimensions:

| Name          | Description                                                                                          |
| ------------- | ---------------------------------------------------------------------------------------------------- |
| name          | The name of the action                                                                               |
| featureName   | The name of the parent feature being executed                                                        |
| path          | The path of execution from the feature root to this action. eg. '/myFeature/parentAction/thisAction' |
| status        | 'success' or 'failure' depending on whether or not the action succeeded                              |
| error         | Only set when `status=failure`. Contains the error type that caused the failure                      |
| source        | The Genkit source language. Eg. 'ts'                                                                 |
| sourceVersion | The Genkit framework version                                                                         |

### Generate metrics {: #generate-metrics }

These are special action metrics relating to actions that interact with a model.
In addition to requests and latency, input and output are also tracked, with
model specific dimensions that make debugging and configuration tuning easier.

| Name                                 | Type      | Description                                |
| ------------------------------------ | --------- | ------------------------------------------ |
| genkit/ai/generate/requests          | Counter   | Number of times this model has been called |
| genkit/ai/generate/latency           | Histogram | Execution latency in ms                    |
| genkit/ai/generate/input/tokens      | Counter   | Input tokens                               |
| genkit/ai/generate/output/tokens     | Counter   | Output tokens                              |
| genkit/ai/generate/input/characters  | Counter   | Input characters                           |
| genkit/ai/generate/output/characters | Counter   | Output characters                          |
| genkit/ai/generate/input/images      | Counter   | Input images                               |
| genkit/ai/generate/output/images     | Counter   | Output images                              |
| genkit/ai/generate/input/audio       | Counter   | Input audio files                          |
| genkit/ai/generate/output/audio      | Counter   | Output audio files                         |

Each generate metric contains the following dimensions:

| Name            | Description                                                                                          |
| --------------- | ---------------------------------------------------------------------------------------------------- |
| modelName       | The name of the model                                                                                |
| featureName     | The name of the parent feature being executed                                                        |
| path            | The path of execution from the feature root to this action. eg. '/myFeature/parentAction/thisAction' |
| latencyMs       | The response time taken by the model                                                                 |
| status          | 'success' or 'failure' depending on whether or not the feature request succeeded                     |
| error           | Only set when `status=failure`. Contains the error type that caused the failure                      |
| source          | The Genkit source language. Eg. 'ts'                                                                 |
| sourceVersion   | The Genkit framework version                                                                         |

## Traces {: #traces }

All Genkit actions are automatically instrumented to provide detailed traces for
your AI features. Locally, traces are visible in the Developer UI. For deployed
apps enable Firebase Genkit Monitoring to get the same level of visibility.

The following sections describe what trace attributes you can expect based on
the Genkit action type for a particular span in the trace.

### Root Spans {: #root-spans }

Root spans have special attributes to help disambiguate the state attributes for
the whole trace versus an individual span.

| Attribute name          | Description                                                                                                                       |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| genkit/feature          | The name of the parent feature being executed                                                                                     |
| genkit/isRoot           | Marked true if this span is the root span                                                                                         |
| genkit/rootState        | The state of the overall execution as `success` or `error`. This does not indicate that this step failed in particular.           |

### Flow {: #flow }

| Attribute name          | Description                                                                                                                       |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| genkit/input            | The input to the flow. This will always be `<redacted>` because of trace attribute size limits.                                   |
| genkit/metadata/subtype | The type of Genkit action. For flows it will be `flow`.                                                                           |
| genkit/name             | The name of this Genkit action. In this case the name of the flow                                                                 |
| genkit/output           | The output generated in the flow. This will always be `<redacted>` because of trace attribute size limits.                        |
| genkit/path             | The fully qualified execution path that lead to this step in the trace, including type information.                               |
| genkit/state            | The state of this span's execution as `success` or `error`.                                                                       |
| genkit/type             | The type of Genkit primitive that corresponds to this span. For flows, this will be `action`.                                     |

### Util {: #util }

| Attribute name          | Description                                                                                                                       |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| genkit/input            | The input to the util. This will always be `<redacted>` because of trace attribute size limits.                                   |
| genkit/name             | The name of this Genkit action. In this case the name of the flow                                                                 |
| genkit/output           | The output generated in the util. This will always be `<redacted>` because of trace attribute size limits.                        |
| genkit/path             | The fully qualified execution path that lead to this step in the trace, including type information.                               |
| genkit/state            | The state of this span's execution as `success` or `error`.                                                                       |
| genkit/type             | The type of Genkit primitive that corresponds to this span. For flows, this will be `util`.                                       |

### Model {: #model }

| Attribute name          | Description                                                                                                                       |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| genkit/input            | The input to the model. This will always be `<redacted>` because of trace attribute size limits.                                  |
| genkit/metadata/subtype | The type of Genkit action. For models it will be `model`.                                                                         |
| genkit/model            | The name of the model.                                                                                                            |
| genkit/name             | The name of this Genkit action. In this case the name of the model.                                                               |
| genkit/output           | The output generated by the model. This will always be `<redacted>` because of trace attribute size limits.                       |
| genkit/path             | The fully qualified execution path that lead to this step in the trace, including type information.                               |
| genkit/state            | The state of this span's execution as `success` or `error`.                                                                       |
| genkit/type             | The type of Genkit primitive that corresponds to this span. For flows, this will be `action`.                                     |

### Tool {: #tool }

| Attribute name          | Description                                                                                                                       |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| genkit/input            | The input to the model. This will always be `<redacted>` because of trace attribute size limits.                                  |
| genkit/metadata/subtype | The type of Genkit action. For tools it will be `tool`.                                                                           |
| genkit/name             | The name of this Genkit action. In this case the name of the model.                                                               |
| genkit/output           | The output generated by the model. This will always be `<redacted>` because of trace attribute size limits.                       |
| genkit/path             | The fully qualified execution path that lead to this step in the trace, including type information.                               |
| genkit/state            | The state of this span's execution as `success` or `error`.                                                                       |
| genkit/type             | The type of Genkit primitive that corresponds to this span. For flows, this will be `action`.                                     |

## Logs {: #logs }

For deployed apps with Firebase Genkit Monitoring, logs are used to capture
input, output, and configuration metadata that provides rich detail about
each step in your AI feature.

All logs will include the following shared metadata fields:

| Field name        | Description                                                                                                                       |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| insertId          | Unique id for the log entry                                                                                                       |
| jsonPayload       | Container for variable information that is unique to each log type                                                                |
| labels            | `{module: genkit}`                                                                                                                |
| logName           | `projects/weather-gen-test-next/logs/genkit_log`                                                                                  |
| receivedTimestamp | Time the log was received by Cloud                                                                                                |
| resource          | Information about the source of the log including deployment information region, and projectId                                    |
| severity          | The log level written. See Cloud's [LogSeverity](https://cloud.google.com/logging/docs/reference/v2/rest/v2/LogEntry#logseverity) |
| spanId            | Identifier for the span that created this log                                                                                     |
| timestamp         | Time that the client logged a message                                                                                             |
| trace             | Identifier for the trace of the format `projects/<project-id>/traces/<trace-id>`                                                  |
| traceSampled      | Boolean representing whether the trace was sampled. Logs are not sampled.                                                         |

Each log type will have a different json payload described in each section.

### Input {: #input }

JSON payload:

| Field name        | Description                                                                                                                       |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| message           | `[genkit] Input[<path>, <featureName>]` including `(message X of N)` for multi-part messages                                       |
| metadata          | Additional context including the input message sent to the action                                                                 |

Metadata:

| Field name        | Description                                                                                                                                                     |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| content           | The input message content sent to this Genkit action                                                                                                            |
| featureName       | The name of the Genkit flow, action, tool, util, or helper.                                                                                                     |
| messageIndex *    | Index indicating the order of messages for inputs that contain multiple messages. For single messages, this will always be 0.                                   |
| model *           | Model name.                                                                                                                                                     |
| path              | The execution path that generated this log of the format `step1 > step2 > step3`                                                                                 |
| partIndex *       | Index indicating the order of parts within a message for multi-part messages. This is typical when combining text and images in a single input.                 |
| qualifiedPath     | The execution path that generated this log, including type information of the format: `/{flow1,t:flow}/{generate,t:util}/{modelProvider/model,t:action,s:model` |
| totalMessages *   | The total number of messages for this input. For single messages, this will always be 1.                                                                        |
| totalParts *      | Total number of parts for this message. For single-part messages, this will always be 1.                                                                        |

(*) Starred items are only present on Input logs for model interactions.

### Output {: #output }

JSON payload:

| Field name        | Description                                                                                                                       |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| message           | `[genkit] Output[<path>, <featureName>]` including `(message X of N)` for multi-part messages                                      |
| metadata          | Additional context including the input message sent to the action                                                                 |

Metadata:

| Field name                     | Description                                                                                                                                                     |
| ------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| candidateIndex * (deprecated)  | Index indicating the order of candidates for outputs that contain multiple candidates. For logs with single candidates, this will always be 0.                  |
| content                        | The output message generated by the Genkit action                                                                                                               |
| featureName                    | The name of the Genkit flow, action, tool, util, or helper.                                                                                                     |
| messageIndex *                 | Index indicating the order of messages for inputs that contain multiple messages. For single messages, this will always be 0.                                   |
| model *                        | Model name.                                                                                                                                                     |
| path                           | The execution path that generated this log of the format `step1 > step2 > step3                                                                                 |
| partIndex *                    | Index indicating the order of parts within a message for multi-part messages. This is typical when combining text and images in a single output.                |
| qualifiedPath                  | The execution path that generated this log, including type information of the format: `/{flow1,t:flow}/{generate,t:util}/{modelProvider/model,t:action,s:model` |
| totalCandidates * (deprecated) | Total number of candidates generated as output. For single-candidate messages, this will always be 1.                                                           |
| totalParts *                   | Total number of parts for this message. For single-part messages, this will always be 1.                                                                        |

(*) Starred items are only present on Output logs for model interactions.

### Config {: #config }

JSON payload:

| Field name        | Description                                                                                                                       |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| message           | `[genkit] Config[<path>, <featureName>]`                                                                                           |
| metadata          | Additional context including the input message sent to the action                                                                 |

Metadata:

| Field name        | Description                                                                                                                                                     |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| featureName       | The name of the Genkit flow, action, tool, util, or helper.                                                                                                     |
| model             | Model name.                                                                                                                                                     |
| path              | The execution path that generated this log of the format `step1 > step2 > step3                                                                                 |
| qualifiedPath     | The execution path that generated this log, including type information of the format: `/{flow1,t:flow}/{generate,t:util}/{modelProvider/model,t:action,s:model` |
| source            | The Genkit library language used. This will always be set to 'ts' as it is the only supported language.                                                         |
| sourceVersion     | The Genkit library version.                                                                                                                                     |
| temperature       | Model temperature used.                                                                                                                                         |

### Paths {: #paths }

JSON payload:

| Field name        | Description                                                                                                                       |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| message           | `[genkit] Paths[<path>, <featureName>]`                                                                                            |
| metadata          | Additional context including the input message sent to the action                                                                 |

Metadata:

| Field name        | Description                                                                                                                                                     |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| flowName          | The name of the Genkit flow, action, tool, util, or helper.                                                                                                                |
| paths             | An array containing all execution paths for the collected spans.                                                                                                |