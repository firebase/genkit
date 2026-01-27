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

## Testing This Demo

1. **Prerequisites**:
   ```bash
   # Set GCP project
   export GCLOUD_PROJECT=your_project_id

   # Authenticate with GCP
   gcloud auth application-default login
   ```
   Or the demo will prompt for the project interactively.

2. **Firestore Setup**:
   - Enable Firestore in your GCP project
   - Create a Firestore database (if not exists)
   - Enable Vector Search extension (if required)

3. **Run the demo**:
   ```bash
   cd py/samples/firestore-retreiver
   ./run.sh
   ```

4. **Open DevUI** at http://localhost:4000

5. **Test the flows**:
   - [ ] `index_documents` - Index sample documents
   - [ ] `retrieve_documents` - Query for similar documents
   - [ ] Verify retrieved documents match query semantics

6. **Expected behavior**:
   - Documents are embedded and stored in Firestore
   - Vector similarity search returns relevant documents
   - Firebase telemetry captures traces/metrics