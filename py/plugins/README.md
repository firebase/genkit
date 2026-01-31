# Genkit Plugins

This directory contains all official Genkit plugins for Python.

## Plugin Categories

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           GENKIT PLUGIN ECOSYSTEM                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   MODEL PROVIDERS                    TELEMETRY                                  │
│   ───────────────                    ─────────                                  │
│   ┌─────────────────────────┐        ┌─────────────────────────┐               │
│   │ google-genai            │        │ google-cloud            │               │
│   │ • Gemini, Imagen, Veo   │        │ • Cloud Trace           │               │
│   │ • Lyria, TTS            │        │ • Cloud Logging         │               │
│   └─────────────────────────┘        └─────────────────────────┘               │
│   ┌─────────────────────────┐        ┌─────────────────────────┐               │
│   │ anthropic               │        │ aws                     │               │
│   │ • Claude 3.5/4          │        │ • X-Ray                 │               │
│   └─────────────────────────┘        │ • CloudWatch            │               │
│   ┌─────────────────────────┐        └─────────────────────────┘               │
│   │ aws-bedrock             │        ┌─────────────────────────┐               │
│   │ • Claude, Llama, Nova   │        │ firebase                │               │
│   │ • Titan, Mistral        │        │ • Firebase Telemetry    │               │
│   └─────────────────────────┘        └─────────────────────────┘               │
│   ┌─────────────────────────┐                                                  │
│   │ msfoundry               │        INTEGRATIONS                              │
│   │ • GPT-4o, Claude, Llama │        ────────────                              │
│   │ • 11,000+ models        │        ┌─────────────────────────┐               │
│   └─────────────────────────┘        │ flask                   │               │
│   ┌─────────────────────────┐        │ • HTTP endpoints        │               │
│   │ vertex-ai               │        └─────────────────────────┘               │
│   │ • Model Garden          │        ┌─────────────────────────┐               │
│   │ • Vector Search         │        │ mcp                     │               │
│   └─────────────────────────┘        │ • Model Context Protocol│               │
│   ┌─────────────────────────┐        └─────────────────────────┘               │
│   │ ollama                  │                                                  │
│   │ • Local models          │        VECTOR STORES                             │
│   └─────────────────────────┘        ─────────────                             │
│   ┌─────────────────────────┐        ┌─────────────────────────┐               │
│   │ compat-oai              │        │ firebase                │               │
│   │ • OpenAI API compatible │        │ • Firestore vectors     │               │
│   └─────────────────────────┘        └─────────────────────────┘               │
│   ┌─────────────────────────┐        ┌─────────────────────────┐               │
│   │ deepseek                │        │ vertex-ai               │               │
│   │ • DeepSeek V3, R1       │        │ • Vector Search         │               │
│   └─────────────────────────┘        └─────────────────────────┘               │
│   ┌─────────────────────────┐        ┌─────────────────────────┐               │
│   │ xai                     │        │ dev-local-vectorstore   │               │
│   │ • Grok models           │        │ • Local development     │               │
│   └─────────────────────────┘        └─────────────────────────┘               │
│                                                                                 │
│                                      SAFETY & EVALUATION                        │
│                                      ───────────────────                        │
│                                      ┌─────────────────────────┐               │
│                                      │ checks                  │               │
│                                      │ • Content moderation    │               │
│                                      │ • Safety guardrails     │               │
│                                      └─────────────────────────┘               │
│                                      ┌─────────────────────────┐               │
│                                      │ evaluators              │               │
│                                      │ • RAGAS metrics         │               │
│                                      │ • Custom evaluators     │               │
│                                      └─────────────────────────┘               │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## When to Use What

### Model Provider Selection

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    WHICH MODEL PROVIDER SHOULD I USE?                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   "I want the best multimodal AI"                                               │
│       → google-genai (Gemini 2.0)                                               │
│                                                                                 │
│   "I need Claude models"                                                        │
│       → anthropic (direct) OR aws-bedrock OR msfoundry                          │
│                                                                                 │
│   "I'm on AWS and want managed models"                                          │
│       → aws-bedrock (Claude, Llama, Nova, Titan)                                │
│                                                                                 │
│   "I'm on Azure and want managed models"                                        │
│       → msfoundry (GPT-4o, Claude, Llama, 11,000+ models)                       │
│                                                                                 │
│   "I'm on GCP and want third-party models"                                      │
│       → vertex-ai (Model Garden - Claude, Llama, etc.)                          │
│                                                                                 │
│   "I want to run models locally"                                                │
│       → ollama (Llama, Mistral, Phi, etc.)                                      │
│                                                                                 │
│   "I need OpenAI GPT models"                                                    │
│       → compat-oai (direct OpenAI) OR msfoundry (via Azure)                     │
│                                                                                 │
│   "I want to use any OpenAI-compatible API"                                     │
│       → compat-oai (works with OpenRouter, Together, etc.)                      │
│                                                                                 │
│   "I need DeepSeek reasoning models"                                            │
│       → deepseek (V3, R1 reasoning)                                             │
│                                                                                 │
│   "I want Grok models"                                                          │
│       → xai                                                                     │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Telemetry Selection

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        WHICH TELEMETRY PLUGIN SHOULD I USE?                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   NATIVE PLATFORM BACKENDS              THIRD-PARTY BACKENDS                    │
│   ────────────────────────              ────────────────────                    │
│                                                                                 │
│   ┌─────────┐  ┌─────────┐             ┌───────────────────┐                   │
│   │   aws   │  │ google- │             │   observability   │  ← PLANNED        │
│   │         │  │ cloud   │             │   • Sentry        │                   │
│   │ • SigV4 │  │ • ADC   │             │   • Honeycomb     │                   │
│   │ • X-Ray │  │ • Trace │             │   • Datadog       │                   │
│   │ • CW    │  │ • Logs  │             │   • Grafana       │                   │
│   └────┬────┘  └────┬────┘             │   • Axiom         │                   │
│        │            │                   └─────────┬─────────┘                   │
│        ▼            ▼                             │                             │
│   ┌─────────┐  ┌─────────┐                        ▼                             │
│   │ X-Ray   │  │ Cloud   │             ┌───────────────────┐                   │
│   │ Console │  │ Trace   │             │  Any OTLP Backend │                   │
│   └─────────┘  └─────────┘             └───────────────────┘                   │
│                                                                                 │
│   ┌─────────┐                                                                   │
│   │  azure  │  ← PLANNED                                                        │
│   │ • Distro│                                                                   │
│   │ • Live  │   CAN'T BE REPLICATED           CAN BE REPLICATED                │
│   │ • Map   │   WITH GENERIC OTLP             WITH GENERIC OTLP                │
│   └────┬────┘                                                                   │
│        │                                                                        │
│        ▼                                                                        │
│   ┌─────────┐                                                                   │
│   │  App    │                                                                   │
│   │Insights │                                                                   │
│   └─────────┘                                                                   │
│                                                                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   "I'm on AWS and want X-Ray"           → aws plugin                           │
│   "I'm on GCP and want Cloud Trace"     → google-cloud plugin                  │
│   "I'm on Azure and want App Insights"  → azure plugin (PLANNED)               │
│   "I'm using Firebase"                  → firebase plugin (auto telemetry)     │
│                                                                                 │
│   "I want Sentry/Honeycomb/Datadog"     → observability plugin (PLANNED)       │
│   "I'm multi-cloud"                     → observability plugin (PLANNED)       │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Vector Store Selection

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      WHICH VECTOR STORE SHOULD I USE?                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   "I'm just developing/testing locally"                                         │
│       → dev-local-vectorstore                                                   │
│                                                                                 │
│   "I need production vector search on Firebase"                                 │
│       → firebase (Firestore vector search)                                      │
│                                                                                 │
│   "I need enterprise-scale vector search on GCP"                                │
│       → vertex-ai (Vertex AI Vector Search + Firestore/BigQuery)                │
│                                                                                 │
│   "I want to use a third-party vector DB"                                       │
│       → Implement custom retriever (Pinecone, Weaviate, Chroma, etc.)           │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Safety & Evaluation Selection

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                  WHICH SAFETY/EVALUATION PLUGIN SHOULD I USE?                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   "I need content moderation / safety guardrails"                               │
│       → checks (Google Checks AI Safety)                                        │
│         • Real-time content classification                                      │
│         • Block harmful input/output                                            │
│         • 8 policy types (harassment, hate speech, etc.)                        │
│                                                                                 │
│   "I need to evaluate RAG quality"                                              │
│       → evaluators (RAGAS metrics)                                              │
│         • Faithfulness, relevancy, answer accuracy                              │
│         • Custom evaluation metrics                                             │
│                                                                                 │
│   "I need both safety AND quality evaluation"                                   │
│       → Use both: checks for guardrails, evaluators for quality                 │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Plugin List

### Model Providers

| Plugin | Models | Best For |
|--------|--------|----------|
| **google-genai** | Gemini, Imagen, Veo, Lyria | Multimodal AI, Google ecosystem |
| **anthropic** | Claude 3.5, Claude 4 | Direct Claude access |
| **aws-bedrock** | Claude, Llama, Nova, Titan | AWS managed models |
| **msfoundry** | GPT-4o, Claude, Llama, 11,000+ | Azure AI, enterprise |
| **vertex-ai** | Model Garden (Claude, Llama) | GCP third-party models |
| **ollama** | Llama, Mistral, Phi, etc. | Local/private deployment |
| **compat-oai** | Any OpenAI-compatible | OpenAI, OpenRouter, etc. |
| **deepseek** | DeepSeek V3, R1 | Reasoning, cost-effective |
| **xai** | Grok | X/Twitter integration |

### Telemetry

| Plugin | Backend | Features |
|--------|---------|----------|
| **google-cloud** | Cloud Trace, Logging | GCP native, log correlation |
| **aws** | X-Ray, CloudWatch | AWS native, SigV4 auth |
| **firebase** | Firebase console | Auto-telemetry for Firebase apps |

### Integrations

| Plugin | Purpose |
|--------|---------|
| **flask** | Serve flows via Flask HTTP endpoints |
| **mcp** | Model Context Protocol for tool integration |

### Safety & Evaluation

| Plugin | Purpose | Features |
|--------|---------|----------|
| **checks** | Content moderation & safety | Google Checks AI guardrails, 8 policy types |
| **evaluators** | Quality evaluation | RAGAS metrics, custom evaluators |

### Vector Stores

| Plugin | Backend | Scale |
|--------|---------|-------|
| **dev-local-vectorstore** | Local JSON | Development only |
| **firebase** | Firestore | Production, serverless |
| **vertex-ai** | Vertex AI Vector Search | Enterprise scale |

## Installation

Each plugin is a separate package. Install only what you need:

```bash
# Model providers
pip install genkit-google-genai-plugin
pip install genkit-anthropic-plugin
pip install genkit-aws-bedrock-plugin
pip install genkit-msfoundry-plugin

# Telemetry
pip install genkit-google-cloud-plugin
pip install genkit-aws-plugin

# Safety & Evaluation
pip install genkit-checks-plugin
pip install genkit-evaluators-plugin

# Integrations
pip install genkit-flask-plugin
pip install genkit-mcp-plugin
```

## Quick Start

```python
from genkit.ai import Genkit
from genkit.plugins.google_genai import GoogleAI

# Initialize with your chosen plugin
ai = Genkit(
    plugins=[GoogleAI()],
    model="googleai/gemini-2.0-flash",
)

@ai.flow()
async def hello(name: str) -> str:
    response = await ai.generate(prompt=f"Say hello to {name}")
    return response.text
```

## Further Reading

- [Plugin Planning & Roadmap](../engdoc/planning/)
- [Feature Matrix](../engdoc/planning/FEATURE_MATRIX.md)
- [Contributing Guide](../engdoc/contributing/)
