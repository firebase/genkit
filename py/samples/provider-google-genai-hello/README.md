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

### Monitoring and Running

For an enhanced development experience, use the provided `run.sh` script to start the sample with automatic reloading:

```bash
./run.sh
```

This script uses `watchmedo` to monitor changes in:
- `src/` (Python logic)
- `../../packages` (Genkit core)
- `../../plugins` (Genkit plugins)
- File patterns: `*.py`, `*.prompt`, `*.json`

Changes will automatically trigger a restart of the sample. You can also pass command-line arguments directly to the script, e.g., `./run.sh --some-flag`.

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

## Testing This Demo

1. **Open DevUI** at http://localhost:4000

2. **Test basic flows**:
   - [ ] `say_hi` - Simple text generation
   - [ ] `say_hi_stream` - Streaming generation (watch text appear)
   - [ ] `say_hi_with_configured_temperature` - Generation with config

3. **Test tools**:
   - [ ] `simple_generate_with_tools_flow` - Tool calling
   - [ ] `simple_generate_with_interrupts` - Tool interrupts

4. **Test structured output**:
   - [ ] `generate_character` - RPG character generation
   - [ ] `generate_character_unconstrained` - Without constraints

5. **Test advanced features**:
   - [ ] `embed_docs` - Document embedding
   - [ ] `describe_image` - Multimodal input (image description)
   - [ ] `thinking_level_pro` / `thinking_level_flash` - Chain of thought
   - [ ] `search_grounding` - Web search grounding
   - [ ] `url_context` - URL context injection
   - [ ] `file_search` - File search (RAG)
   - [ ] `youtube_videos` - Video input processing
   - [ ] `tool_calling` - Basic tool calling chain
   - [ ] `currency_exchange` - Tool calling with mocking
   - [ ] `demo_dynamic_tools` - Dynamic tools and sub-spans

6. **Expected behavior**:
   - All flows should complete without errors
   - Streaming shows incremental output
   - Structured output matches Pydantic schemas
   - Tools are called and responses processed
