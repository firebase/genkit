# Authentication and authorization {: #authentication }

The Firebase telemetry plugin requires a Google Cloud or Firebase project ID
and application credentials.

If you don't have a Google Cloud project and account, you can set one up in the
[Firebase Console](https://console.firebase.google.com/) or in the
[Google Cloud Console](https://cloud.google.com). All Firebase project IDs are
Google Cloud project IDs.

## Enable APIs {: #enable-apis }

Prior to adding the plugin, make sure the following APIs are enabled for
your project:

- [Cloud Logging API](https://console.cloud.google.com/apis/library/logging.googleapis.com)
- [Cloud Trace API](https://console.cloud.google.com/apis/library/cloudtrace.googleapis.com)
- [Cloud Monitoring API](https://console.cloud.google.com/apis/library/monitoring.googleapis.com)

These APIs should be listed in the
[API dashboard](https://console.cloud.google.com/apis/dashboard) for your
project.
Click to learn more about how to [enable and disable APIs](https://support.google.com/googleapi/answer/6158841).

## User Authentication {: #user-authentication }

To export telemetry from your local development environment to Firebase Genkit
Monitoring, you will need to authenticate yourself with Google Cloud.

The easiest way to authenticate as yourself is using the gcloud CLI, which will
automatically make your credentials available to the framework through
[Application Default Credentials (ADC)](https://cloud.google.com/docs/authentication/application-default-credentials).

If you don't have the gcloud CLI installed, first follow the [installation instructions](https://cloud.google.com/sdk/docs/install#installation_instructions).

1. Authenticate using the `gcloud` CLI:

   ```posix-terminal
   gcloud auth application-default login
   ```

2. Set your project ID

   ```posix-terminal
   gcloud config set project PROJECT_ID
   ```

## Deploy to Google Cloud {: #deploy-to-cloud }

If deploying your code to a Google Cloud or Firebase environment (Cloud
Functions, Cloud Run, App Hosting, etc), the project ID and credentials will be
discovered automatically with
[Application Default Credentials](https://cloud.google.com/docs/authentication/provide-credentials-adc).

You will need to apply the following roles to the service account that is
running your code (i.e. 'attached service account') using the
[IAM Console](https://console.cloud.google.com/iam-admin/iam):

- `roles/monitoring.metricWriter`
- `roles/cloudtrace.agent`
- `roles/logging.logWriter`

Not sure which service account is the right one? See the
[Find or create your service account](#find-or-create-your-service-account)
section.

## Deploy outside of Google Cloud (with ADC) {: #deploy-to-cloud-with-adc }

If possible, use
[Application Default Credentials](https://cloud.google.com/docs/authentication/provide-credentials-adc)
to make credentials available to the plugin.

Typically this involves generating a service account key and deploying
those credentials to your production environment.

1. Follow the instructions to set up a
   [service account key](https://cloud.google.com/iam/docs/keys-create-delete#creating).

2. Ensure the service account has the following roles:
   - `roles/monitoring.metricWriter`
   - `roles/cloudtrace.agent`
   - `roles/logging.logWriter`

3. Deploy the credential file to production (**do not** check into source code)

4. Set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable as the path to
   the credential file.

    ```posix-terminal
    GOOGLE_APPLICATION_CREDENTIALS = "path/to/your/key/file"
    ```

Not sure which service account is the right one? See the
[Find or create your service account](#find-or-create-your-service-account)
section.

## Deploy outside of Google Cloud (without ADC) {: #deploy-to-cloud-without-adc }

In some serverless environments, you may not be able to deploy a credential
file.

1. Follow the instructions to set up a
[service account key](https://cloud.google.com/iam/docs/keys-create-delete#creating).

2. Ensure the service account has the following roles:
    - `roles/monitoring.metricWriter`
    - `roles/cloudtrace.agent`
    - `roles/logging.logWriter`

3. Download the credential file.

4. Assign the contents of the credential file to the
`GCLOUD_SERVICE_ACCOUNT_CREDS` environment variable as follows:

```posix-terminal
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

Not sure which service account is the right one? See the
[Find or create your service account](#find-or-create-your-service-account)
section.

## Find or create your service account {: #find-or-create-your-service-account }

To find the appropriate service account:

1. Navigate to the [service accounts page](https://console.cloud.google.com/iam-admin/serviceaccounts)
   in the Google Cloud Console
2. Select your project
3. Find the appropriate service account. Common default service accounts are as follows:

- Firebase functions & Cloud Run

    <code><var>PROJECT ID</var>-compute@developer.gserviceaccount.com</code>

- App Engine

    <code><var>PROJECT ID</var>@appspot.gserviceaccount.com</code>

- App Hosting
  
    <code>firebase-app-hosting-compute@<var>PROJECT ID</var>.iam.gserviceaccount.com</code>

If you are deploying outside of the Google ecosystem or don't want to use a
default service account, you can
[create a service account](https://cloud.google.com/iam/docs/service-accounts-create#creating)
in the Google Cloud console.
