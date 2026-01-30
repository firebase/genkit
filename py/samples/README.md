# Genkit Python Samples

This directory contains example applications demonstrating various Genkit features
and integrations. Each sample is self-contained and can be run independently.

## Quick Start

All samples follow a consistent pattern:

```bash
cd sample-name/
./run.sh
# Open http://localhost:4000 in your browser
```

## Sample Categories

### Getting Started

Basic examples to get started with different model providers.

| Sample | Description | Required API Key |
|--------|-------------|------------------|
| [google-genai-hello](./google-genai-hello/) | Basic Gemini usage with flows, tools, and streaming | `GOOGLE_API_KEY` |
| [anthropic-hello](./anthropic-hello/) | Claude models with tools and thinking mode | `ANTHROPIC_API_KEY` |
| [ollama-hello](./ollama-hello/) | Local models via Ollama | None (local) |
| [xai-hello](./xai-hello/) | xAI Grok models | `XAI_API_KEY` |
| [deepseek-hello](./deepseek-hello/) | DeepSeek models | `DEEPSEEK_API_KEY` |
| [compat-oai-hello](./compat-oai-hello/) | OpenAI-compatible endpoints | Varies |

### Google Cloud & Vertex AI

Samples using Google Cloud services and Vertex AI.

| Sample | Description | Required Setup |
|--------|-------------|----------------|
| [google-genai-vertexai-hello](./google-genai-vertexai-hello/) | Vertex AI Gemini models | GCP Project + ADC |
| [google-genai-vertexai-image](./google-genai-vertexai-image/) | Vertex AI Imagen | GCP Project + ADC |
| [model-garden](./model-garden/) | Vertex AI Model Garden (Anthropic, Llama) | GCP Project + ADC |
| [vertex-ai-vector-search-bigquery](./vertex-ai-vector-search-bigquery/) | Vector Search with BigQuery | GCP Project + ADC |
| [vertex-ai-vector-search-firestore](./vertex-ai-vector-search-firestore/) | Vector Search with Firestore | GCP Project + ADC |
| [firestore-retreiver](./firestore-retreiver/) | Firestore document retrieval | GCP Project + ADC |

### RAG (Retrieval-Augmented Generation)

Samples demonstrating RAG patterns with different vector stores.

| Sample | Description | Vector Store |
|--------|-------------|--------------|
| [rag-chroma](./rag-chroma/) | RAG with ChromaDB - cat knowledge base | ChromaDB (in-memory) |
| [rag-pinecone](./rag-pinecone/) | RAG with Pinecone - cat knowledge base | Pinecone (cloud) |
| [dev-local-vectorstore-hello](./dev-local-vectorstore-hello/) | Local file-based vector store | Local files |
| [ollama-simple-embed](./ollama-simple-embed/) | Embeddings with Ollama | Ollama |

### Media Generation

Samples for generating images, audio, and video.

| Sample | Description | Models Used |
|--------|-------------|-------------|
| [media-models-demo](./media-models-demo/) | All media generation (TTS, Image, Video) | TTS, Imagen, Veo, Lyria |
| [google-genai-image](./google-genai-image/) | Image generation with Gemini | Gemini Vision |

### Advanced Features

Samples demonstrating advanced Genkit capabilities.

| Sample | Description | Features |
|--------|-------------|----------|
| [checks-demo](./checks-demo/) | Google Checks AI safety guardrails | Content moderation, policy filtering |
| [menu](./menu/) | Restaurant menu assistant | Multi-case flows, RAG, chat |
| [evaluator-demo](./evaluator-demo/) | Evaluation and testing | Built-in evaluators, custom metrics |
| [prompt_demo](./prompt_demo/) | Dotprompt templates | Prompt files, partials, variants |
| [format-demo](./format-demo/) | Output formatting | JSON, structured output |
| [tool-interrupts](./tool-interrupts/) | Tool interrupt/resume pattern | Human-in-the-loop |
| [short-n-long](./short-n-long/) | Short and long-running operations | Background actions |
| [google-genai-context-caching](./google-genai-context-caching/) | Context caching for efficiency | Cached contexts |
| [google-genai-code-execution](./google-genai-code-execution/) | Code execution sandbox | Code interpreter |

### Web Frameworks

Samples showing framework integrations.

| Sample | Description | Framework |
|--------|-------------|-----------|
| [flask-hello](./flask-hello/) | Flask web app with Genkit | Flask |
| [multi-server](./multi-server/) | Multiple servers architecture | Multi-process |

### Observability

Samples demonstrating tracing and monitoring.

| Sample | Description | Features |
|--------|-------------|----------|
| [realtime-tracing-demo](./realtime-tracing-demo/) | Real-time trace visualization | OpenTelemetry |

## Running Samples

### Prerequisites

1. **Python 3.10+** and **uv** package manager
2. **Genkit CLI**: `npm install -g genkit`
3. **API keys** for the providers you want to use

### Environment Variables

Set the required environment variables for your chosen sample:

```bash
# Google AI (Gemini)
export GOOGLE_API_KEY=your-key

# Anthropic (Claude)
export ANTHROPIC_API_KEY=your-key

# xAI (Grok)
export XAI_API_KEY=your-key

# DeepSeek
export DEEPSEEK_API_KEY=your-key

# OpenAI-compatible
export OPENAI_API_KEY=your-key
export OPENAI_BASE_URL=https://api.example.com/v1

# Google Cloud (ADC)
gcloud auth application-default login
```

### Using run.sh

Each sample includes a `run.sh` script that:
- Installs dependencies via `uv sync`
- Starts the Genkit Dev UI
- Watches for file changes and auto-reloads

```bash
./run.sh          # Start the sample
./run.sh --help   # Show help (if available)
```

### Manual Execution

```bash
cd sample-name/
uv sync
genkit start -- uv run src/main.py
```

## Sample Structure

Each sample follows a standard structure:

```
sample-name/
├── README.md           # Sample documentation
├── pyproject.toml      # Dependencies
├── run.sh              # Run script with hot-reload
├── src/
│   └── main.py         # Main application code
├── data/               # Sample data (if needed)
└── prompts/            # Prompt templates (if needed)
```

## Creating New Samples

When adding a new sample:

1. Create a new directory with a descriptive name
2. Follow the structure above
3. Include a comprehensive `README.md`
4. Add a `run.sh` script with hot-reload support
5. **Update this README.md** with the new sample in the appropriate category
6. Update `py/plugins/README.md` if using a new plugin

## Learn More

- [Genkit Documentation](https://genkit.dev/docs)
- [Python SDK Guide](https://genkit.dev/docs/python)
- [Plugins](../plugins/README.md)

## License

All samples are licensed under Apache 2.0.
