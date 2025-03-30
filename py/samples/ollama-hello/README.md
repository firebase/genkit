# Hello Ollama

## NOTE

Before running the sample make sure to install the model and start ollama
serving.  In case of questions, please refer to `./py/plugins/ollama/README.md`

## Installation

```bash
ollama pull mistral-nemo:latest
ollama pull gemma3:latest
```

## Execute "Hello World" Sample

```bash
genkit start -- uv run src/ollama_hello.py
```
