# Hello world

## Setup environment
Use `gcloud auth application-default login` to connect to the VertexAI.

```bash
uv venv
source .venv/bin/activate
```

## Run the sample

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

```bash
genkit start -- uv run src/main.py
```
