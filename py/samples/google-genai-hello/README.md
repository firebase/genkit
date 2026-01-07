# Hello Google GenAI

An example demonstrating running flows using the Google GenAI plugin.

## Setup environment

Obtain an API key from [ai.dev](https://ai.dev).

Export the API key as env variable `GEMINI\_API\_KEY` in your shell
configuration.

```bash
export GEMINI_API_KEY='<Your api key>'
```

## Run the sample

```bash
genkit start -- uv run src/main.py
```

### Testing GCP telemetry

To test Google Cloud Platform telemetry (tracing and metrics), you need a GCP project and valid credentials.

1.  **Enable APIs**: Go to the [Google Cloud Console](https://console.cloud.google.com/) and enable the following APIs for your project:
    -   [Cloud Monitoring API](https://console.cloud.google.com/marketplace/product/google/monitoring.googleapis.com)
    -   [Cloud Trace API](https://console.cloud.google.com/marketplace/product/google/cloudtrace.googleapis.com)

2.  **Authenticate**: Set up Application Default Credentials (ADC).
    ```bash
    gcloud config set project <your-gcp-project-id>
    gcloud auth application-default login
    ```

    Choose the "Select All" option to select all requested permissions before
    proceeding so that the authentication process can complete successfully.
    Otherwise, you may run into a lot of HTTP 503 service unavailable or
    `invalid_grant` errors.
    
3.  **Run with Telemetry**:
    ```bash
    genkit start -- uv run src/main.py --enable-gcp-telemetry
    ```
