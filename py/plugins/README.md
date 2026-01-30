# Genkit Python Plugins

This directory contains official plugins for the Genkit Python SDK. Plugins extend
Genkit's capabilities with model providers, vector stores, evaluators, and more.

## Plugin Categories

### Model Providers

Plugins that provide access to AI models for text generation, chat, and other tasks.

| Plugin | Package | Description | Models/Features |
|--------|---------|-------------|-----------------|
| [anthropic](./anthropic/) | `genkit-plugin-anthropic` | Anthropic Claude models | Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Haiku |
| [google-genai](./google-genai/) | `genkit-plugin-google-genai` | Google AI models via AI Studio | Gemini 2.0/1.5, Imagen, Veo, Lyria, TTS, Embeddings |
| [vertex-ai](./vertex-ai/) | `genkit-plugin-vertex-ai` | Google Cloud Vertex AI | Model Garden (Anthropic, Llama), Vector Search |
| [ollama](./ollama/) | `genkit-plugin-ollama` | Local models via Ollama | Llama, Mistral, Gemma, any Ollama model |
| [compat-oai](./compat-oai/) | `genkit-plugin-compat-oai` | OpenAI-compatible APIs | Any OpenAI-compatible endpoint |
| [deepseek](./deepseek/) | `genkit-plugin-deepseek` | DeepSeek models | DeepSeek Chat, DeepSeek Coder |
| [xai](./xai/) | `genkit-plugin-xai` | xAI Grok models | Grok-2, Grok-2 Vision |

### Vector Stores

Plugins for storing and retrieving document embeddings for RAG applications.

| Plugin | Package | Description | Features |
|--------|---------|-------------|----------|
| [chroma](./chroma/) | `genkit-plugin-chroma` | ChromaDB vector store | In-memory or persistent, local or remote |
| [pinecone](./pinecone/) | `genkit-plugin-pinecone` | Pinecone managed vector DB | Cloud-hosted, scalable, namespaces |
| [dev-local-vectorstore](./dev-local-vectorstore/) | `genkit-plugin-dev-local-vectorstore` | Local file-based store | Development and testing only |

### Safety & Evaluation

Plugins for content safety, guardrails, and quality evaluation.

| Plugin | Package | Description | Features |
|--------|---------|-------------|----------|
| [checks](./checks/) | `genkit-plugin-checks` | Google Checks AI Safety | Content moderation, policy enforcement |
| [evaluators](./evaluators/) | `genkit-plugin-evaluators` | Built-in evaluators | Faithfulness, relevancy, answer accuracy |

### Integrations

Plugins for external services and protocols.

| Plugin | Package | Description | Features |
|--------|---------|-------------|----------|
| [mcp](./mcp/) | `genkit-plugin-mcp` | Model Context Protocol | MCP client, host, and server |
| [firebase](./firebase/) | `genkit-plugin-firebase` | Firebase integration | Firestore retriever, telemetry |
| [google-cloud](./google-cloud/) | `genkit-plugin-google-cloud` | Google Cloud telemetry | Cloud Trace, Cloud Logging, Metrics |

### Web Frameworks

Plugins for integrating Genkit with web frameworks.

| Plugin | Package | Description | Features |
|--------|---------|-------------|----------|
| [flask](./flask/) | `genkit-plugin-flask` | Flask integration | Expose flows as HTTP endpoints |

## Installation

Install plugins using pip or uv:

```bash
# Install a single plugin
pip install genkit-plugin-google-genai

# Install multiple plugins
pip install genkit-plugin-google-genai genkit-plugin-anthropic genkit-plugin-chroma
```

## Quick Start

```python
from genkit.ai import Genkit
from genkit.plugins.google_genai import GoogleAI
from genkit.plugins.chroma import chroma

# Initialize Genkit with plugins
ai = Genkit(
    plugins=[
        GoogleAI(),
        chroma(collections=[{
            'collection_name': 'my_docs',
            'embedder': 'googleai/text-embedding-004',
        }]),
    ],
    model='googleai/gemini-2.0-flash',
)

# Use models from plugins
response = await ai.generate(prompt='Hello, world!')
```

## Plugin Development

Each plugin follows a standard structure:

```
plugin-name/
├── LICENSE
├── pyproject.toml
├── README.md
├── src/
│   └── genkit/
│       └── plugins/
│           └── plugin_name/
│               ├── __init__.py
│               └── ...
└── tests/
    └── ...
```

### Creating a New Plugin

1. Create the directory structure above
2. Implement the `Plugin` class from `genkit.core.plugin`
3. Register actions (models, retrievers, indexers, etc.) in `initialize()`
4. Add tests and documentation

See existing plugins for examples.

## Cross-Language Parity

These Python plugins maintain API parity with their JavaScript counterparts where
applicable. See the [JS plugins](../../js/plugins/) for reference implementations.

## License

All plugins are licensed under Apache 2.0 unless otherwise noted.
