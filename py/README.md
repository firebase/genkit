# Genkit Python SDK

Genkit is a framework for building AI-powered applications with type-safe flows, structured outputs, and integrated observability. This is the Python implementation that maintains feature parity with the JavaScript/TypeScript SDK.

## Directory Structure

```
py/
├── packages/genkit/          # Core Genkit framework package
├── plugins/                  # Official plugins
│   ├── amazon-bedrock/       # Amazon Bedrock models + X-Ray telemetry (community)
│   ├── anthropic/            # Claude models
│   ├── azure/                # Azure AI telemetry (community)
│   ├── cloudflare-workers-ai/        # Cloudflare Workers AI + OTLP telemetry (community)
│   ├── checks/               # Safety guardrails
│   ├── compat-oai/           # OpenAI-compatible APIs
│   ├── deepseek/             # DeepSeek models
│   ├── dev-local-vectorstore/# Local development vector store
│   ├── evaluators/           # RAGAS and custom evaluators
│   ├── firebase/             # Firebase integration + telemetry
│   ├── flask/                # Flask HTTP endpoints
│   ├── google-cloud/         # GCP telemetry (Cloud Trace, Logging)
│   ├── google-genai/         # Gemini, Imagen, Veo, Lyria, TTS
│   ├── huggingface/          # HuggingFace Inference API
│   ├── mcp/                  # Model Context Protocol
│   ├── mistral/              # Mistral models
│   ├── microsoft-foundry/            # Azure AI Foundry (11,000+ models) (community)
│   ├── observability/        # 3rd party telemetry (Sentry, Datadog, etc.)
│   ├── ollama/               # Local Ollama models
│   ├── vertex-ai/            # Model Garden + Vector Search
│   └── xai/                  # Grok models
├── samples/                  # Sample applications
└── testapps/                 # Test applications
```

## Setup Instructions

1. Install `uv` from https://docs.astral.sh/uv/getting-started/installation/

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Install required tools using `uv`

```bash
uv tool install httpie
uv tool install mypy
uv tool install ruff
```

3. If you are using VSCode, install the `Ruff` extension from the marketplace to add linter support.

## Quick Start

```python
from genkit import Genkit
from genkit.plugins.google_genai import GoogleGenAI, gemini_2_0_flash

ai = Genkit(
    plugins=[GoogleGenAI()],
    model=gemini_2_0_flash,
)

response = await ai.generate(prompt="Tell me a joke")
print(response.text)
```

## Plugin Categories

| Category | Plugins | Purpose |
|----------|---------|---------|
| **Model Providers** | google-genai, anthropic, amazon-bedrock, ollama, compat-oai, deepseek, xai, mistral, huggingface, microsoft-foundry, cloudflare-workers-ai | AI model access |
| **Telemetry** | google-cloud, amazon-bedrock, azure, firebase, cloudflare-workers-ai, observability | Distributed tracing & logging |
| **Vector Stores** | firebase, vertex-ai, dev-local-vectorstore | Embeddings storage & retrieval |
| **Safety** | checks, evaluators | Guardrails & evaluation |
| **Integrations** | flask, mcp | HTTP endpoints, tool protocols |

## Community Plugins

Some plugins are community-maintained and supported on a best-effort basis:

- **amazon-bedrock** - Amazon Bedrock models + AWS X-Ray telemetry
- **azure** - Azure Monitor / Application Insights telemetry
- **cloudflare-workers-ai** - Cloudflare Workers AI models + OTLP telemetry
- **microsoft-foundry** - Azure AI Foundry (11,000+ models)
- **observability** - Third-party backends (Sentry, Honeycomb, Datadog, etc.)

## Running Tests

Run all unit tests:

```bash
uv run pytest .
```

Run tests for a specific plugin:

```bash
uv run pytest plugins/amazon-bedrock/
```

## Running Samples

See the [samples/README.md](samples/README.md) for instructions on running individual samples.

Quick start:

```bash
cd samples/provider-google-genai-hello
./run.sh
```

## Development

See [GEMINI.md](GEMINI.md) for detailed development guidelines, including:
- Code quality and linting requirements
- Type checking configuration
- Testing conventions
- Documentation standards

## License

Apache 2.0
