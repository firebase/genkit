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

## Testing This Demo

1. **Prerequisites**:
   ```bash
   # Set GCP project (for Vertex AI embeddings)
   export GCLOUD_PROJECT=your_project_id

   # Authenticate with GCP
   gcloud auth application-default login
   ```
   Or the demo will prompt for the project interactively.

2. **Run the demo**:
   ```bash
   cd py/samples/dev-local-vectorstore-hello
   ./run.sh
   ```

3. **Open DevUI** at http://localhost:4000

4. **Test the flows**:
   - [ ] `index_documents` - Index sample film documents
   - [ ] `retreive_documents` - Query for similar films
   - [ ] Try different query terms

5. **Expected behavior**:
   - Documents are embedded using Vertex AI
   - Vector store persists locally (in-memory for dev)
   - Retrieval returns semantically similar documents
   - No external vector database required
   - Sample documents include film descriptions with genres and plots
