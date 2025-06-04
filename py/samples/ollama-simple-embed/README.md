# Ollama Simple Embed Sample

## Prerequisites

- **Ollama** - a local AI model server, which is used to handle embeddings and generate responses.

### Step 1: Install Ollama

1. Go to the [Ollama website](https://ollama.com/download) to download and install Ollama for your operating system.
2. Once installed, start the Ollama server by running:

```bash
ollama serve
```

The server will run at http://localhost:11434 by default.

### Step 2: Pull the Required Models

In this example, we use two models with Ollama:

An embedding model (nomic-embed-text)
A generation model (phi3.5:latest)
Run the following commands in your terminal to pull these models:

```bash
ollama pull nomic-embed-text
ollama pull phi3.5:latest
```

### Step 3: Execute Sample

```bash
genkit start -- uv run src/pokemon_glossary.py
```
