# Google Cloud plugin

The Google Cloud plugin exports Firebase Genkit telemetry and logging data to the [Cloud Observability](https://cloud.google.com/products/operations) suite.

## Installation

```posix-terminal
npm i --save @genkit-ai/google-cloud
```

When running Genkit code locally that includes this plugin, you will also need
the [Google Cloud CLI tool](https://cloud.google.com/sdk/docs/install)
installed.

## Set up a Google Cloud account

This plugin requires a Google Cloud account/project. All Firebase projects
include one by default ([GCP Console](https://console.cloud.google.com)),
or you can sign up at https://cloud.google.com.

Prior to adding the plugin, make sure that the following APIs are enabled for
your GCP project:

- [Cloud Logging API](https://console.cloud.google.com/apis/library/logging.googleapis.com)
- [Cloud Trace API](https://console.cloud.google.com/apis/library/cloudtrace.googleapis.com)
- [Cloud Monitoring API](https://console.cloud.google.com/apis/library/monitoring.googleapis.com)

These APIs should be listed in the
[API dashboard](https://console.cloud.google.com/apis/dashboard) for your
project.

Click [here](https://support.google.com/googleapi/answer/6158841) to learn more
about enabling and disabling APIs.

## Genkit configuration

To enable Cloud Tracing, Logging, and Monitoring (metrics), simply call
`enableGoogleCloudTelemetry()`:

```ts
import { enableGoogleCloudTelemetry } from '@genkit-ai/google-cloud';

enableGoogleCloudTelemetry();
```

When running in production, telemetry will be exported automatically. See the [Advanced configuration guide](./observability/advanced-configuration.md) for configuration options.

Note: All configuration options work for both `enableFirebaseTelemetry` and `enableGoogleCloudTelemetry`.


