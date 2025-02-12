# Authentication and authorization

Firebase Genkit Monitoring requires a Google Cloud project ID and application credentials. 

## User Authentication

When running Genkit locally with the intent to export telemetry to Firebase Genkit Monitoring,
you will be authenticating as yourself. The easiest way to do this is via the gcloud CLI. This
will set up [Application Default Credentials (ADC)](https://cloud.google.com/docs/authentication/application-default-credentials) for your user which will be picked up automatically by the framework.

Follow the gcloud CLI installation instructions [here](https://cloud.google.com/sdk/docs/install#installation_instructions).

1. Authenticate using the `gcloud` CLI:

   ```posix-terminal
   gcloud auth application-default login
   ```

2. Set your project ID

   ```posix-terminal
   gcloud config set project PROJECT_ID
   ```

## Deploy with Application Default Credentials (ADC) on Google Cloud

If deploying your code to a Google Cloud environment (Cloud
Functions, Cloud Run, etc), the project ID and credentials will be discovered
automatically via
[Application Default Credentials](https://cloud.google.com/docs/authentication/provide-credentials-adc).

You will need to apply the following roles to the service account that is
running your code (i.e. 'attached service account') via the
[IAM Console](https://console.cloud.google.com/iam-admin/iam):

- `roles/monitoring.metricWriter`
- `roles/cloudtrace.agent`
- `roles/logging.logWriter`

To find your default service account:

1. Navigate to the [service accounts page](https://console.cloud.google.com/iam-admin/serviceaccounts) in the Google Cloud Console
2. Select your project
3. Your default service account should look like *project-number*-compute@developer.gserviceaccount.com or *project-id*@appspot.gserviceaccount.com if you are using App Engine.

## Deploying outside of Google Cloud with Application Default Credentials (ADC)

If possible, it is still recommended to leverage the
[Application Default Credentials](https://cloud.google.com/docs/authentication/provide-credentials-adc)
process to make credentials available to the plugin.

Typically this involves generating a service account key/pair and deploying
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

    ```
    GOOGLE_APPLICATION_CREDENTIALS = "path/to/your/key/file"
    ```

## Deploying outside of Google Cloud without Application Default Credentials (ADC)

In some serverless environments, you may not be able to deploy a credential
file.

1. Follow the instructions to set up a 
[service account key](https://cloud.google.com/iam/docs/keys-create-delete#creating).

2. Ensure the service account has the following roles:
    - `roles/monitoring.metricWriter`
    - `roles/cloudtrace.agent`
    - `roles/logging.logWriter`

3. Download the credential file.

4. Assign the contents of the credential file to the `GCLOUD_SERVICE_ACCOUNT_CREDS` environment variable as follows:

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
