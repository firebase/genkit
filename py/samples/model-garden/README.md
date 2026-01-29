# Model Garden

## Setup environment

```bash
uv venv
source .venv/bin/activate
```

## Monitoring and Running

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

TODO

```bash
genkit start -- uv run src/main.py
```

## Testing This Demo

1. **Prerequisites**:
   ```bash
   # Set GCP project
   export GOOGLE_CLOUD_PROJECT=your_project_id

   # Authenticate with GCP
   gcloud auth application-default login
   ```

2. **Enable Model Garden**:
   - Go to Vertex AI Model Garden in GCP Console
   - Enable access to desired models (e.g., Claude)

3. **Run the demo**:
   ```bash
   cd py/samples/model-garden
   ./run.sh
   ```

4. **Open DevUI** at http://localhost:4000

5. **Test the flows**:
   - [ ] `say_hi` - Test generation with Claude models
   - [ ] `say_hi_stream` - Test streaming response
   - [ ] `jokes_flow` - Test with custom temperature settings
   - [ ] `currency_exchange` - Test currency exchange flow (uses tools)
   - [ ] `weather_flow` - Test tool calling
   - [ ] `generate_character` - Test structured output

6. **Expected behavior**:
   - Models respond via Vertex AI infrastructure
   - No direct API keys needed (uses GCP auth)
   - Enterprise features (logging, quotas) available
   - Available models (via Model Garden): `anthropic/claude-3-5-sonnet`, `anthropic/claude-3-haiku`, and other models as enabled in your project
