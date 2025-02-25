# Get started with Genkit Monitoring {: #get-started }

This quickstart guide describes how to set up Firebase Genkit Monitoring for
your deployed Genkit features, so that you can collect and view real-time
telemetry data. With Firebase Genkit Monitoring, you get visibility into how
your Genkit features are performing in production.

Key capabilities of Firebase Genkit Monitoring include:

* Viewing quantitative metrics like Genkit feature latency, errors, and
  token usage.
* Inspecting traces to see your Genkit's feature steps, inputs, and outputs,
  to help with debugging and quality improvement.
* Exporting production traces to run evals within Genkit.

Setting up Genkit Monitoring requires completing tasks in both your codebase
and on the Google Cloud Console.

## Before you begin {: #before-you-begin }

1. If you haven't already, create a Firebase project.

   In the [Firebase console](https://console.firebase.google.com), click
   **Add a project**, then follow the on-screen instructions. You can
   create a new project or add Firebase services to an already-existing
   Google Cloud project.

2. Ensure your project is on the
   [Blaze pricing plan](https://firebase.google.com/pricing).

   Genkit Monitoring relies on telemetry data written to Google Cloud
   Logging, Metrics, and Trace, which are paid services. View the
   [Google Cloud Observability pricing](https://cloud.google.com/stackdriver/pricing)
   page for pricing details and to learn about free-of-charge tier limits.

3. Write a Genkit feature by following the
   [Get Started Guide](https://firebase.google.com/docs/genkit/get-started), and
   prepare your code for deployment by using one of the following guides:

   1. [Deploy flows using Cloud Functions for Firebase](../firebase)
   2. [Deploy flows using Cloud Run](../cloud-run)
   3. [Deploy flows to any Node.js platform](../deploy-node)

## Step 1. Add the Firebase plugin {: #add-plugin }

Install the `@genkit-ai/firebase` plugin in your project:

```posix-terminal
npm i –save @genkit-ai/firebase
```

Import `enableFirebaseTelemetry` into your Genkit configuration file (the
file where `genkit(...)` is initalized), and call it:

```typescript
import { enableFirebaseTelemetry } from '@genkit-ai/firebase';

enableFirebaseTelemetry();
```

## Step 2. Enable the required APIs {: #enable-apis }

Make sure that the following APIs are enabled for your Google Cloud project:

* [Cloud Logging API](https://console.cloud.google.com/apis/library/logging.googleapis.com)
* [Cloud Trace API](https://console.cloud.google.com/apis/library/cloudtrace.googleapis.com)
* [Cloud Monitoring API](https://console.cloud.google.com/apis/library/monitoring.googleapis.com)

These APIs should be listed in the
[API dashboard](https://console.cloud.google.com/apis/dashboard) for your
project.

## Step 3. Set up permissions {: #set-up-permissions }

The Firebase plugin needs to use a _service account_ to authenticate with
Google Cloud Logging, Metrics, and Trace services.

Grant the following roles to whichever service account is configured to run
your code within the
[Google Cloud IAM Console](https://console.cloud.google.com/iam-admin/iam).
For Cloud Functions for Firebase and Cloud Run, that's typically the default
compute service account.

* **Monitoring Metric Writer** (`roles/monitoring.metricWriter`)
* **Cloud Trace Agent** (`roles/cloudtrace.agent`)
* **Logs Writer** (`roles/logging.logWriter`)

## Step 4. (Optional) Test your configuration locally {: #test-locally }

Before deploying, you can run your Genkit code locally to confirm that
telemetry data is being collected, and is viewable in the Genkit Monitoring
dashboard.

1. In your Genkit code, set `forceDevExport` to `true` to send telemetry from
   your local environment.

2. Use your service account to authenticate and test your configuration.

   Tip: In order to impersonate the service account, you will need to have
   the `roles/iam.serviceAccountTokenCreator`
   [IAM role](https://console.cloud.google.com/iam-admin/iam) applied to your
   user account.

   With the
   [Google Cloud CLI tool](https://cloud.google.com/sdk/docs/install?authuser=0),
   authenticate using the service account:

    ```posix-terminal
    gcloud auth application-default login --impersonate-service-account SERVICE_ACCT_EMAIL
    ```

3. Run and invoke your Genkit feature, and then view metrics on the
   [Genkit Monitoring dashboard](https://console.firebase.google.com/project/_/genai_monitoring).
   Allow for up to 5 minutes to collect the first metric. You can reduce this
   delay by setting `metricExportIntervalMillis` in the telemetry configuration.

4. If metrics are not appearing in the Genkit Monitoring dashboard, view the
   [Troubleshooting](/docs/genkit/observability/troubleshooting) guide for steps
   to debug.

## Step 5. Re-build and deploy code {: #build-and-deploy }

Re-build, deploy, and invoke your Genkit feature to start collecting data.
After Genkit Monitoring receives your metrics, you can view them by
visiting the
[Genkit Monitoring dashboard](https://console.firebase.google.com/project/_/genai_monitoring)

Note: It may take up to 5 minutes to collect the first metric (based on the
default `metricExportIntervalMillis` setting in the telemetry configuration).

<!--
## Next Steps:

View [advanced configuration](/docs/genkit/advanced) options for the Firebase
telemetry plugin.
-->