# Google Cloud telemetry and logging plugin

The Google Cloud plugin exports Genkit's telemetry and logging data to
[Google Cloud's operation suite](https://cloud.google.com/products/operations).

Note: Logging is facilitated by the `slog` package
in favor of the [OpenTelemetry](https://opentelemetry.io/) logging APIs. Export
of logs is done via a dedicated Google Cloud exporter.

## Prerequisites

If you want to locally run flows that use this plugin, you need the
[Google Cloud CLI tool](https://cloud.google.com/sdk/docs/install) installed.

## Set up a Google Cloud account

This plugin requires a Google Cloud account ([sign up](https://cloud.google.com/gcp) if you don't already have one) and a Google Cloud project.

Prior to adding the plugin, make sure that the following APIs are enabled for your project:

- [Cloud Logging API](https://console.cloud.google.com/apis/library/logging.googleapis.com)
- [Cloud Trace API](https://console.cloud.google.com/apis/library/cloudtrace.googleapis.com)
- [Cloud Monitoring API](https://console.cloud.google.com/apis/library/monitoring.googleapis.com)

These APIs should be listed in the [API dashboard](https://console.cloud.google.com/apis/dashboard) for your project.

Click [here](https://support.google.com/googleapi/answer/6158841) to learn more about enabling and disabling APIs.

## Configuration

To enable exporting to Google Cloud Tracing, Logging, and Monitoring, import the
`googlecloud` package and run `Init()`. After calling `Init()`, your telemetry
gets automatically exported.

```go
import "github.com/firebase/genkit/go/plugins/googlecloud"
```

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/gcp.go" region_tag="init" adjust_indentation="auto" %}
```

You must specify the Google Cloud project to which you want to export telemetry
data. There are also some optional parameters:

- `ForceExport`: Export telemetry data even when running in a dev environment
  (such as when using `genkit start` or `genkit flow:run`). This is a quick way
  to test your integratiion and send your first events for monitoring in Google
  Cloud.

  If you use this option, you also need to make your Cloud credentials available
  locally:

  ```posix-terminal
  gcloud auth application-default login
  ```

- `MetricInterval`: The interval, in nanoseconds, at which to export telemetry
  information. By default, this is 60 seconds (`60e9` nanoseconds).

- `LogLevel`: The minimum severity level of log entries to export. By default,
  `slog.LevelInfo`.

The plugin requires your Google Cloud project credentials. If you're running
your flows from a Google Cloud environment (Cloud Run, etc), the credentials are
set automatically. Running in other environments requires setting up
[Application Default Credentials](https://cloud.google.com/docs/authentication/provide-credentials-adc).

# Production monitoring via Google Cloud's operations suite

Once a flow is deployed, navigate to [Google Cloud's operations suite](https://console.cloud.google.com/) and select your project.

<img src="../resources/cloud-ops-suite.png" width="750">

## Logs and traces

From the side menu, find 'Logging' and click 'Logs explorer'.

<img src="../resources/cloud-ops-logs-explorer-menu.png" width="750">

You will see all logs that are associated with your deployed flow, including `console.log()`. Any log which has the prefix `[genkit]` is a Genkit-internal log that contains information that may be interesting for debugging purposes. For example, Genkit logs in the format `Config[...]` contain metadata such as the temperature and topK values for specific LLM inferences. Logs in the format `Output[...]` contain LLM responses while `Input[...]` logs contain the prompts. Cloud Logging has robust ACLs that allow fine grained control over sensitive logs.

> Note: Prompts and LLM responses are redacted from trace attributes in Cloud Trace.

For specific log lines, it is possible to navigate to their respective traces by clicking on the extended menu <img src="../resources/cloud-ops-log-menu-icon.png" height="15"> icon and selecting "View in trace details".

 <img src="../resources/cloud-ops-view-trace-details.png" width="750">

This will bring up a trace preview pane providing a quick glance of the details of the trace. To get to the full details, click the "View in Trace" link at the top right of the pane.

 <img src="../resources/cloud-ops-view-in-trace.png" width="750">

The most prominent navigation element in Cloud Trace is the trace scatter plot. It contains all collected traces in a given time span.

 <img src="../resources/cloud-ops-trace-graph.png" width="750">

Clicking on each data point will show its details below the scatter plot.

 <img src="../resources/cloud-ops-trace-view.png" width="750">

The detailed view contains the flow shape, including all steps, and important timing information. Cloud Trace has the ability to interleave all logs associated with a given trace within this view. Select the "Show expanded" option in the "Logs & events" drop down.

 <img src="../resources/cloud-ops-show-expanded.png" width="750">

The resultant view allows detailed examination of logs in the context of the trace, including prompts and LLM responses.

 <img src="../resources/cloud-ops-output-logs.png" width="750">

## Metrics

Viewing all metrics that Genkit exports can be done by selecting "Logging" from the side menu and clicking on "Metrics management".

<img src="../resources/cloud-ops-metrics-mgmt.png" width="750">

The metrics management console contains a tabular view of all collected metrics, including those that pertain to Cloud Run and its surrounding environment. Clicking on the 'Workload' option will reveal a list that includes Genkit-collected metrics. Any metric with the `genkit` prefix constitutes an internal Genkit metric.

<img src="../resources/cloud-ops-metrics-table.png" width="750">

Genkit collects several categories of metrics, including flow-level, action-level, and generate-level metrics. Each metric has several useful dimensions facilitating robust filtering and grouping.

Common dimensions include:

- `flow_name` - the top-level name of the flow.
- `flow_path` - the span and its parent span chain up to the root span.
- `error_code` - in case of an error, the corresponding error code.
- `error_message` - in case of an error, the corresponding error message.
- `model` - the name of the model.
- `temperature` - the inference temperature [value](https://ai.google.dev/docs/concepts#model-parameters).
- `topK` - the inference topK [value](https://ai.google.dev/docs/concepts#model-parameters).
- `topP` - the inference topP [value](https://ai.google.dev/docs/concepts#model-parameters).

### Flow-level metrics

| Name                 | Dimensions                           |
| -------------------- | ------------------------------------ |
| genkit/flow/requests | flow_name, error_code, error_message |
| genkit/flow/latency  | flow_name                            |

### Action-level metrics

| Name                   | Dimensions                           |
| ---------------------- | ------------------------------------ |
| genkit/action/requests | flow_name, error_code, error_message |
| genkit/action/latency  | flow_name                            |

### Generate-level metrics

| Name                                 | Dimensions                                                           |
| ------------------------------------ | -------------------------------------------------------------------- |
| genkit/ai/generate                   | flow_path, model, temperature, topK, topP, error_code, error_message |
| genkit/ai/generate/input_tokens      | flow_path, model, temperature, topK, topP                            |
| genkit/ai/generate/output_tokens     | flow_path, model, temperature, topK, topP                            |
| genkit/ai/generate/input_characters  | flow_path, model, temperature, topK, topP                            |
| genkit/ai/generate/output_characters | flow_path, model, temperature, topK, topP                            |
| genkit/ai/generate/input_images      | flow_path, model, temperature, topK, topP                            |
| genkit/ai/generate/output_images     | flow_path, model, temperature, topK, topP                            |
| genkit/ai/generate/latency           | flow_path, model, temperature, topK, topP, error_code, error_message |

Visualizing metrics can be done through the Metrics Explorer. Using the side menu, select 'Logging' and click 'Metrics explorer'

<img src="../resources/cloud-ops-metrics-explorer.png" width="750">

Select a metrics by clicking on the "Select a metric" dropdown, selecting 'Generic Node', 'Genkit', and a metric.

<img src="../resources/cloud-ops-metrics-generic-node.png" width="750">

The visualization of the metric will depend on its type (counter, histogram, etc). The Metrics Explorer provides robust aggregation and querying facilities to help graph metrics by their various dimensions.

<img src="../resources/cloud-ops-metrics-metric.png" width="750">

## Telemetry Delay

There may be a slight delay before telemetry for a particular execution of a flow is displayed in Cloud's operations suite. In most cases, this delay is under 1 minute.

## Quotas and limits

There are several quotas that are important to keep in mind:

- [Cloud Trace Quotas](http://cloud.google.com/trace/docs/quotas)
  - 128 bytes per attribute key
  - 256 bytes per attribute value
- [Cloud Logging Quotas](http://cloud.google.com/logging/quotas)
  - 256 KB per log entry
- [Cloud Monitoring Quotas](http://cloud.google.com/monitoring/quotas)

## Cost

Cloud Logging, Cloud Trace, and Cloud Monitoring have generous free tiers. Specific pricing can be found at the following links:

- [Cloud Logging Pricing](http://cloud.google.com/stackdriver/pricing#google-cloud-observability-pricing)
- [Cloud Trace Pricing](https://cloud.google.com/trace#pricing)
- [Cloud Monitoring Pricing](https://cloud.google.com/stackdriver/pricing#monitoring-pricing-summary)
