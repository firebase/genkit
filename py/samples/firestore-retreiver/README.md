# Hello world

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

## Create a index to be able to retrieve
```
gcloud firestore indexes composite create \
  --project=<FIREBASE-PROJECT>\
  --collection-group=films \
  --query-scope=COLLECTION \
  --field-config=vector-config='{"dimension":"768","flat": "{}"}',field-path=embedding
```
## Run the sample

TODO

```bash
genkit start -- uv run src/main.py
```