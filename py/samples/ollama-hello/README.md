# Hello Ollama

## Prerequisites

- **Ollama** - a local AI model server, which is used to handle embeddings and generate responses.

### Quick Start

The simplest way to run this sample is using the included `run.sh` script, which handles installation, server startup, and model pulling automatically:

```bash
./run.sh
```

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
