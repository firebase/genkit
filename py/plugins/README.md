# Genkit Plugins

Official Genkit plugins for Python. Install only what you need.

## Model Providers

| Plugin | Install | Models |
|--------|--------|--------|
| **google-genai** | `genkit-google-genai-plugin` | Gemini, Imagen, Veo, Lyria |
| **anthropic** | `genkit-anthropic-plugin` | Claude |
| **vertex-ai** | `genkit-vertex-ai-plugin` | Model Garden, Vector Search |
| **ollama** | `genkit-ollama-plugin` | Local (Llama, Mistral, etc.) |
| **compat-oai** | `genkit-compat-oai-plugin` | OpenAI, Azure, OpenRouter |
| **deepseek** | `genkit-deepseek-plugin` | DeepSeek V3, R1 |
| **xai** | `genkit-xai-plugin` | Grok |
| **mistral** | `genkit-mistral-plugin` | Mistral, Codestral, Pixtral |
| **huggingface** | `genkit-huggingface-plugin` | 1M+ models via HF Hub |
| **cohere** | `genkit-cohere-plugin` | Command R/R+, Embed, Rerank |

## Telemetry

| Plugin | Install | Backend |
|--------|--------|---------|
| **google-cloud** | `genkit-google-cloud-plugin` | Cloud Trace, Logging |
| **observability** | `genkit-observability-plugin` | Sentry, Honeycomb, Datadog, Grafana, Axiom |
| **firebase** | `genkit-firebase-plugin` | Firebase console |

## Integrations

| Plugin | Install | Purpose |
|--------|--------|---------|
| **fastapi** | `genkit-plugin-fastapi` | Serve flows via FastAPI |
| **flask** | `genkit-flask-plugin` | Serve flows via Flask |
| **mcp** | `genkit-mcp-plugin` | Model Context Protocol |

## Quick Start

```bash
pip install genkit genkit-google-genai-plugin
```

```python
from genkit import Genkit
from genkit.plugins.google_genai import GoogleAI

ai = Genkit(
    plugins=[GoogleAI()],
    model="googleai/gemini-2.0-flash",
)

response = await ai.generate(prompt="Why is Genkit awesome?")
print(response.text)
```

```bash
export GEMINI_API_KEY="your-api-key"
python main.py
```

## Environment Variables

Set the API key for your chosen provider before running:

| Provider | Variable |
|---------|----------|
| Google AI | `GEMINI_API_KEY` |
| Anthropic | `ANTHROPIC_API_KEY` |
| OpenAI | `OPENAI_API_KEY` |
| Vertex AI / GCP | `GOOGLE_CLOUD_PROJECT` + `gcloud auth application-default login` |

See each plugin's README for full configuration options.

## Next Steps

- [Samples](../samples/README.md) — Example applications
- [Contributing](../engdoc/contributing/) — Plugin development
