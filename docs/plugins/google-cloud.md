# Google Cloud plugin

The Google Cloud plugin exports Firebase Genkit's telemetry and logging data to
[Google Cloud's operations suite](https://cloud.google.com/products/operations) which powers the [Firebase AI Monitoring dashboard (private preview)](https://forms.gle/Lp5S1NxbZUXsWc457).

> Note: Logging is facilitated by [Winston](https://github.com/winstonjs/winston) in favor of the [OpenTelemetry](https://opentelemetry.io/) logging APIs. Export of logs is done via a dedicated Winston Google Cloud exporter.

## Installation

```posix-terminal
npm i --save @genkit-ai/google-cloud
```

If you want to locally run flows that use this plugin, you also need the
[Google Cloud CLI tool](https://cloud.google.com/sdk/docs/install) installed.

## Set up a Google Cloud account

This plugin requires a Google Cloud account ([sign up](https://cloud.google.com/gcp) if you don't already have one) and a Google Cloud project.

Prior to adding the plugin, make sure that the following APIs are enabled for your project:

- [Cloud Logging API](https://console.cloud.google.com/apis/library/logging.googleapis.com)
- [Cloud Trace API](https://console.cloud.google.com/apis/library/cloudtrace.googleapis.com)
- [Cloud Monitoring API](https://console.cloud.google.com/apis/library/monitoring.googleapis.com)

These APIs should be listed in the [API dashboard](https://console.cloud.google.com/apis/dashboard) for your project.

Click [here](https://support.google.com/googleapi/answer/6158841) to learn more about enabling and disabling APIs.

## Genkit configuration

To enable exporting to Google Cloud Tracing, Logging, and Monitoring, simply call `enableGoogleCloudTelemetry()`:

```ts
import { enableGoogleCloudTelemetry } from '@genkit-ai/google-cloud';

enableGoogleCloudTelemetry();
```

When running in production, your telemetry gets automatically exported.

### Authentication

The plugin requires the Google Cloud project ID and your Google Cloud project credentials. If you're running your flow from a Google Cloud environment (Cloud Functions, Cloud Run, etc), the project ID and credentials are set automatically. 

#### Application Default Credentials

Running in other environments requires setting the `GCLOUD_PROJECT` environment variable to your Google Cloud project and authenticating using the `gcloud` tool:

```posix-terminal
gcloud auth application-default login
```

For more information, see the [Application Default Credentials](https://cloud.google.com/docs/authentication/provide-credentials-adc) docs.

#### Service Account Credentials

If you are using a service account and running outside of a Google Cloud environment, you can set your credentials as an environment variable. Follow instructions here to [set up your Google Cloud Service Account Key](https://cloud.google.com/iam/docs/keys-create-delete#creating).

Once you have downloaded the key file, you can specify the credentials in two ways; a file location using the `GOOGLE_APPLICATION_CREDENTIALS` environment variable or directly copy the contents of the json file to the environment variable `GCLOUD_SERVICE_ACCOUNT_CREDS`.

File path:

```
GOOGLE_APPLICATION_CREDENTIALS = "path/to/your/key/file"
```

Direct copy:

```
GCLOUD_SERVICE_ACCOUNT_CREDS='{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "your-private-key-id",
  "private_key": "your-private-key",
  "client_email": "your-client-email",
  "client_id": "your-client-id",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://accounts.google.com/o/oauth2/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "your-cert-url"
}'
```

## Plugin configuration

The `enableGoogleCloudTelemetry()` function takes an optional configuration object which configures the [OpenTelemetry NodeSDK](https://open-telemetry.github.io/opentelemetry-js/classes/_opentelemetry_sdk_node.NodeSDK.html) instance.

```ts
import { AlwaysOnSampler } from '@opentelemetry/sdk-trace-base';

enableGoogleCloudTelemetry({
  forceDevExport: false, // Set this to true to export telemetry for local runs
  sampler: new AlwaysOnSampler(),
  autoInstrumentation: true,
  autoInstrumentationConfig: {
    '@opentelemetry/instrumentation-fs': { enabled: false },
    '@opentelemetry/instrumentation-dns': { enabled: false },
    '@opentelemetry/instrumentation-net': { enabled: false },
  },
  metricExportIntervalMillis: 5_000,
});
```
The configuration objects allows fine grained control over various aspects of the telemetry export outlined below.

#### credentials
Allows specifying credentials directly using [JWTInput](http://cloud/nodejs/docs/reference/google-auth-library/latest/google-auth-library/jwtinput) from the google-auth library.

#### sampler

For cases where exporting all traces isn't practical, OpenTelemetry allows trace [sampling](https://opentelemetry.io/docs/languages/java/instrumentation/#sampler).

There are four preconfigured samplers:

- [AlwaysOnSampler](https://github.com/open-telemetry/opentelemetry-java/blob/main/sdk/trace/src/main/java/io/opentelemetry/sdk/trace/samplers/AlwaysOnSampler.java) - samples all traces
- [AlwaysOffSampler](https://github.com/open-telemetry/opentelemetry-java/blob/main/sdk/trace/src/main/java/io/opentelemetry/sdk/trace/samplers/AlwaysOffSampler.java) - samples no traces
- [ParentBased](https://github.com/open-telemetry/opentelemetry-java/blob/main/sdk/trace/src/main/java/io/opentelemetry/sdk/trace/samplers/ParentBasedSampler.java) - samples based on parent span
- [TraceIdRatioBased](https://github.com/open-telemetry/opentelemetry-java/blob/main/sdk/trace/src/main/java/io/opentelemetry/sdk/trace/samplers/TraceIdRatioBasedSampler.java) - samples a configurable percentage of traces

#### autoInstrumentation & autoInstrumentationConfig

Enabling [automatic instrumentation](https://opentelemetry.io/docs/languages/js/automatic/) allows OpenTelemetry to capture telemetry data from [third-party libraries](https://github.com/open-telemetry/opentelemetry-js-contrib/blob/main/metapackages/auto-instrumentations-node/src/utils.ts) without the need to modify code.

#### metricExportIntervalMillis

This field specifies the metrics export interval in milliseconds.

> Note: The minimum export interval for Google Cloud Monitoring is 5000ms.

#### metricExportTimeoutMillis

This field specifies the timeout for the metrics export in milliseconds.

#### disableMetrics

Provides an override that disables metrics export while still exporting traces and logs.

#### disableTraces

Provides an override that disables exporting traces while still exprting metrics and logs.

#### disableLoggingIO

Provides an override that disables collecting input and output logs.

#### forceDevExport

This option will force Genkit to export telemetry and log data when running in the `dev` environment (e.g. locally).

> Note: When running locally, internal telemetry buffers may not fully flush prior to the process exiting, resulting in an incomplete telemetry export.

## Test your integration

When configuring the plugin, use `forceDevExport: true` to enable telemetry export for local runs. Navigate to the Google Cloud Logs, Metrics, or Trace Explorer to view telemetry. Alternatively, navigate to the [Firebase AI Monitoring dashboard (private preview)](https://forms.gle/Lp5S1NxbZUXsWc457) for an AI-idiomatic view of telemetry.
