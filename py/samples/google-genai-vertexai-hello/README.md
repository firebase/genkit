# Hello Google GenAI - Vertex AI

An example demonstrating the use of the Google GenAI plugin to use
Vertex AI.

## Setup environment

1. Install [GCP CLI](https://cloud.google.com/sdk/docs/install).
2. Put your GCP project and location in the code to run VertexAI there.

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

3. Run the sample.

```bash
uv venv
source .venv/bin/activate
```

## Run the sample

TODO

```bash
genkit start -- uv run src/main.py
```
