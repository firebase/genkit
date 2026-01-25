# Ollama Simple Embed Sample

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
   ollama pull nomic-embed-text
   ollama pull phi4:latest
   ```
4. **Run the sample**:
   ```bash
   genkit start -- uv run src/main.py
   ```
