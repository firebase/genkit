# Hello Google GenAI

An example demonstrating running flows using the Google GenAI plugin.

## Setup environment

### How to Get Your Gemini API Key

To use the Google GenAI plugin, you need a Gemini API key.

1.  **Visit AI Studio**: Go to [Google AI Studio](https://aistudio.google.com/).
2.  **Create API Key**: Click on "Get API key" and create a key in a new or existing Google Cloud project.

For more details, check out the [official documentation](https://ai.google.dev/gemini-api/docs/api-key).

Export the API key as env variable `GEMINI_API_KEY` in your shell configuration.

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
