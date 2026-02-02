# Genkit CF AI Plugin (Cloudflare Workers AI)

This plugin provides access to [Cloudflare Workers AI](https://developers.cloudflare.com/workers-ai/) models for the Genkit framework. Cloudflare Workers AI runs AI models at the edge, close to users, providing low-latency inference with global availability.

## Installation

```bash
pip install genkit-plugin-cf-ai
```

## Setup

1. Get your Cloudflare Account ID and API Token from the [Cloudflare Dashboard](https://dash.cloudflare.com/).
2. Set environment variables:

```bash
export CLOUDFLARE_ACCOUNT_ID=your_account_id
export CLOUDFLARE_API_TOKEN=your_api_token
```

## Usage

### Basic Text Generation

```python
from genkit import Genkit
from genkit.plugins.cf_ai import CfAI, cf_model

ai = Genkit(
    plugins=[CfAI()],
    model=cf_model('@cf/meta/llama-3.1-8b-instruct'),
)

@ai.flow()
async def say_hello(name: str) -> str:
    response = await ai.generate(prompt=f'Say hello to {name}!')
    return response.text
```

### Streaming

```python
@ai.flow()
async def stream_story() -> str:
    chunks = []
    async for chunk in ai.generate_stream(prompt='Write a short story.'):
        print(chunk.text, end='', flush=True)
        chunks.append(chunk.text)
    return ''.join(chunks)
```

### Embeddings

```python
from genkit.plugins.cf_ai import bge_base_en

@ai.flow()
async def get_embeddings(text: str) -> list[float]:
    response = await ai.embed(content=text, embedder=bge_base_en)
    return response.embeddings[0].embedding
```

## Supported Models

### Text Generation (Chat)

| Model ID | Description |
|----------|-------------|
| `@cf/meta/llama-3.3-70b-instruct-fp8-fast` | Meta Llama 3.3 70B |
| `@cf/meta/llama-3.1-8b-instruct` | Meta Llama 3.1 8B |
| `@cf/meta/llama-3.1-8b-instruct-fast` | Meta Llama 3.1 8B (Fast) |
| `@cf/meta/llama-4-scout-17b-16e-instruct` | Meta Llama 4 Scout 17B (Multimodal) |
| `@cf/mistral/mistral-7b-instruct-v0.2` | Mistral 7B |
| `@cf/qwen/qwen1.5-14b-chat-awq` | Qwen 1.5 14B |

### Embeddings

| Model ID | Dimensions |
|----------|------------|
| `@cf/baai/bge-base-en-v1.5` | 768 |
| `@cf/baai/bge-large-en-v1.5` | 1024 |
| `@cf/baai/bge-small-en-v1.5` | 384 |

## Features

- **Text generation** with streaming support (SSE)
- **Tool/function calling** for agentic workflows
- **Text embeddings** for semantic search and RAG
- **Multimodal inputs** (with Llama 4 Scout)
- **Edge inference** - low latency globally

## Testing

Run the sample application:

```bash
cd py/samples/cf-ai-hello
./run.sh
```

Then open the Genkit Dev UI at http://localhost:4000 to test the flows.

## Documentation

- [Cloudflare Workers AI](https://developers.cloudflare.com/workers-ai/)
- [Models Catalog](https://developers.cloudflare.com/workers-ai/models/)
- [REST API](https://developers.cloudflare.com/workers-ai/get-started/rest-api/)
