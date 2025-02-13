# Genkit Monitoring - Troubleshooting

## I can’t see traces and/or metrics in Firebase Genkit Monitoring

1. Ensure that the following APIs are enabled for your underlying GCP project:
    * [Cloud Logging API](https://console.cloud.google.com/apis/library/logging.googleapis.com)
    * [Cloud Trace API](https://console.cloud.google.com/apis/library/cloudtrace.googleapis.com)
    * [Cloud Monitoring API](https://console.cloud.google.com/apis/library/monitoring.googleapis.com)
2. Ensure that the following roles are applied to the service account that is running your code (or service account that has been configured as part of the plugin options) in [Cloud IAM](https://console.cloud.google.com/iam-admin/iam).
    * **Monitoring Metric Writer** (`roles/monitoring.metricWriter`)
    * **Cloud Trace Agent** (`roles/cloudtrace.agent`)
    * **Logs Writer** (`roles/logging.logWriter`)
3. Inspect the application logs for errors writing to Cloud Logging, Cloud Trace, and/or Cloud Monitoring. On GCP infrastructure (e.g. Firebase Functions, Cloud Run, etc), even when telemetry is misconfigured, logs to stdout/stderr are automatically ingested by the Cloud Logging Agent, allowing you to diagnose issues in the in the [Cloud Logging Console](https://console.cloud.google.com/logs). 
4. Debug locally:

    Enable dev export:

    ```typescript
    enableFirebaseTelemetry({
      forceDevExport: true
    });
    ```

    To test with your personal user credentials, authenticate with Google Cloud via the [gcloud CLI](https://cloud.google.com/sdk/docs/install). This can help diagnose enabled/disabled APIs, but will not test the production service account permissions:

    ```
    gcloud auth application-default login
    ```

	Alternatively, impersonating the service account will allow you to test production-like access. You will need to have the `roles/iam.serviceAccountTokenCreator` IAM role applied to your user account in order to impersonate service accounts:

    ```
    gcloud auth application-default login --impersonate-service-account <SERVICE_ACCT_EMAIL>
    ```

	See the [ADC](https://cloud.google.com/docs/authentication/set-up-adc-local-dev-environment) documentation for more information.

### Telemetry upload reliability in Firebase Functions / Cloud Run

When Genkit is hosted in Google Cloud Run (including Firebase Functions), telemetry data upload may be less reliable as the container switches to the "idle" [lifecycle state](https://cloud.google.com/blog/topics/developers-practitioners/lifecycle-container-cloud-run). If higher reliability is important to you, consider changing [CPU allocation](https://cloud.google.com/run/docs/configuring/cpu-allocation) to "always allocated" in the Google Cloud Console. Note that this impacts pricing.