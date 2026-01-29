# Hello Ollama

## Prerequisites

- **Ollama** - a local AI model server, which is used to handle embeddings and generate responses.

### Quick Start

The simplest way to run this sample is using the included `run.sh` script, which handles installation, server startup, and model pulling automatically:

```bash
./run.sh
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

### Manual Setup

If you prefer to set up manually:

1. **Install Ollama**: Download from [ollama.com](https://ollama.com/download).
2. **Start the server**:
   ```bash
   ollama serve
   ```
3. **Pull models**:
   ```bash
   ollama pull mistral-nemo:latest
   ollama pull gemma3:latest
   ```
4. **Run the sample**:
   ```bash
   genkit start -- uv run src/main.py
   ```

## Testing This Demo

1. **Open DevUI** at http://localhost:4000

2. **Test basic flows**:
   - [ ] `say_hi` - Simple generation with gemma3
   - [ ] `say_hi_stream` - Streaming response
   - [ ] `say_hi_constrained` - Constrained output

3. **Test tools** (requires mistral-nemo):
   - [ ] `calculate_gablorken` - Tool calling demo

4. **Notes**:
   - gemma2:latest does NOT support tool calling
   - Use mistral-nemo for tool-based flows
   - First run may be slow (model loading)

5. **Expected behavior**:
   - Responses generated locally (no API calls)
   - Streaming shows incremental output
   - Tools work with compatible models only
