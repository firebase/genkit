# Ollama Plugin

This Genkit plugin provides a set of tools and utilities for working with Ollama.

## Setup environment

```bash
uv venv
source .venv/bin/activate
```

## Serving Ollama Locally

### Ollama Service Installation

#### MacOS  (brew)

```bash
brew install ollama
```

#### Debian/Ubuntu (apt installer)

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Other installation options may be found [here](https://ollama.com/download)

### Start serving of Ollama locally

```bash
ollama serve
```

Ollama is served at `http://127.0.0.1:11434` by default.

### Installing Required Model

Once ollama service is serving - pull the required model version:

```bash
ollama pull <model-version>:<tag>
```

### Check installed models

Installed models can be reviewed with following command:

```bash
ollama list
```

## Examples

For examples check `./py/samples/ollama/README.md`
