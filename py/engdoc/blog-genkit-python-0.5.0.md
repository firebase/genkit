# Genkit Python SDK 0.5.0: A Major Leap Forward

Building intelligent AI-powered applications in Python just got significantly better. Today, we're thrilled to announce the release of **Genkit Python SDK 0.5.0**—our most significant update yet, with **178 commits**, **680+ files changed**, and contributions from **13 developers** across **188 PRs** over the past 8 months.

This release transforms Genkit for Python from an experimental SDK into a production-ready framework with comprehensive plugin coverage, enterprise-grade security, and first-class developer experience.

## What's New in 0.5.0

### Massive Plugin Ecosystem Expansion

We've added **7 new model provider plugins** and **3 telemetry plugins**, giving you access to virtually every major AI provider:

**New Model Providers:**
- **AWS Bedrock**: Access Claude, Titan, Llama, and more through AWS
- **Azure OpenAI (Microsoft Foundry)**: Enterprise Azure OpenAI integration
- **Cloudflare Workers AI**: Edge AI with Cloudflare's global network
- **Mistral AI**: Mistral Large, Small, Codestral, and Pixtral models
- **Hugging Face**: 17+ inference providers through one plugin
- **Anthropic**: Full Claude model support
- **DeepSeek**: DeepSeek models with structured output

**New Telemetry Plugins:**
- **AWS X-Ray**: Production observability with SigV4 signing
- **AIM (Firebase Observability)**: Native Firebase telemetry
- **Google Cloud Telemetry**: Full parity with JS/Go SDKs

### Async-First Architecture

The Python SDK now embraces async-first design throughout. Here's how clean your code can be:

```python
from genkit.ai import Genkit
from genkit.plugins.google_genai import GoogleAI

ai = Genkit(
    plugins=[GoogleAI()],
    model='googleai/gemini-2.5-flash',
)

@ai.flow()
async def analyze_sentiment(text: str) -> str:
    """Analyzes sentiment of the given text."""
    response = await ai.generate(
        prompt=f'Analyze the sentiment of this text: {text}'
    )
    return response.text()
```

### Dynamic Action Provider (DAP)

One of our most requested features: dynamic action creation at runtime. DAP enables factory patterns for creating actions on-the-fly:

```python
@ai.action_provider()
async def model_provider(model_name: str):
    """Dynamically provides model actions based on name."""
    async def generate_action(prompt: str) -> str:
        return await ai.generate(
            model=model_name,
            prompt=prompt
        )
    return generate_action
```

### Enhanced Dotprompt Integration

We've deeply integrated with [Dotprompt](https://github.com/google/dotprompt), our prompt templating engine, bringing:

- **Directory/file prompt loading**: Automatic prompt discovery matching the JS SDK
- **Handlebars partials**: Template reuse with `define_partial`
- **Python 3.14 support**: Full compatibility via our Rust-based Handlebars engine
- **Cycle detection**: Prevents infinite recursion in partial resolution
- **Path traversal hardening**: Security fix for CWE-22 vulnerability

```python
from genkit.dotprompt import Dotprompt

# Load all prompts from a directory
prompts = await Dotprompt.load_directory('./prompts')

# Use partials for reusable components
await Dotprompt.define_partial('header', '# {{title}}\n\n')

# Render with full type safety
result = await prompts['summarize'].render(
    title='Summary',
    content='...'
)
```

### Comprehensive Type Safety

We now run **three type checkers** on every commit:

| Type Checker | Provider | Purpose |
|-------------|----------|---------|
| **ty** | Astral (Ruff) | Fast, strict checking |
| **pyrefly** | Meta | Additional coverage |
| **pyright** | Microsoft | Full type analysis |

This means you get better IDE support, fewer runtime errors, and more confident refactoring.

### Pydantic Output Instances

Generate structured data directly into Pydantic models:

```python
from pydantic import BaseModel, Field

class WeatherReport(BaseModel):
    location: str = Field(description='City name')
    temperature: float = Field(description='Temperature in Celsius')
    conditions: str = Field(description='Weather conditions')

@ai.flow()
async def get_weather(city: str) -> WeatherReport:
    result = await ai.generate(
        prompt=f'Get the current weather for {city}',
        output_schema=WeatherReport,
    )
    # Returns a WeatherReport instance, not dict!
    return result.output
```

## Critical Fixes & Security

This release addresses several important issues:

- **Race Condition Fix**: Dev server startup race condition resolved (#4225)
- **Thread Safety**: Per-event-loop HTTP client caching prevents event loop binding errors
- **Security Audit**: Full Ruff security rules (S) audit completed
- **SigV4 Signing**: AWS X-Ray OTLP exporter now uses proper AWS signatures

## Developer Experience Improvements

### Hot Reloading

All samples now support hot reloading via [Watchdog](https://github.com/gorakhargosh/watchdog):

```bash
# Start with hot reloading
genkit start -- python main.py
```

### CI Consolidation

Every commit is now release-worthy. Our consolidated CI runs:
- All three type checkers
- Full test suite across Python 3.10-3.14
- Security scanning
- License compliance
- Package builds

### Rich Tracebacks

Better error output with [Rich](https://github.com/Textualize/rich) tracebacks in all samples.

## Available Plugins

### Model Providers

| Plugin | Models | Status |
|--------|--------|--------|
| `genkit-plugin-google-genai` | Gemini 2.5, Imagen, embeddings | ✅ Stable |
| `genkit-plugin-ollama` | Gemma, Llama, Mistral (local) | ✅ Stable |
| `genkit-plugin-anthropic` | Claude 3.5 Sonnet, Opus | ✅ New |
| `genkit-plugin-aws-bedrock` | Claude, Titan, Llama via AWS | ✅ New |
| `genkit-plugin-msfoundry` | Azure OpenAI | ✅ New |
| `genkit-plugin-cf-ai` | Cloudflare Workers AI | ✅ New |
| `genkit-plugin-mistral` | Mistral Large, Codestral | ✅ New |
| `genkit-plugin-huggingface` | 17+ providers | ✅ New |
| `genkit-plugin-deepseek` | DeepSeek models | ✅ New |
| `genkit-plugin-xai` | Grok models | ✅ New |

### Telemetry & Observability

| Plugin | Destination | Status |
|--------|-------------|--------|
| `genkit-plugin-google-cloud` | Cloud Trace/Logging | ✅ Stable |
| `genkit-plugin-aws` | AWS X-Ray | ✅ New |
| `genkit-plugin-aim` | Firebase/AIM | ✅ New |

### Data & Retrieval

| Plugin | Purpose | Status |
|--------|---------|--------|
| `genkit-plugin-firestore` | Vector search with Firestore | ✅ Stable |
| `genkit-plugin-dev-local-vectorstore` | Local vector store for dev | ✅ Stable |

## Get Started

Install Genkit Python SDK 0.5.0:

```bash
pip install genkit==0.5.0
```

Or with specific plugins:

```bash
pip install genkit[google-genai,anthropic,aws-bedrock]==0.5.0
```

### Quick Start Example

```python
import asyncio
from genkit.ai import Genkit
from genkit.plugins.google_genai import GoogleAI

async def main():
    ai = Genkit(
        plugins=[GoogleAI()],
        model='googleai/gemini-2.5-flash',
    )

    @ai.flow()
    async def greeting_flow(name: str) -> str:
        """Generates a personalized greeting."""
        response = await ai.generate(
            prompt=f'Write a creative greeting for {name}'
        )
        return response.text()

    result = await greeting_flow('World')
    print(result)

asyncio.run(main())
```

Run with the Developer UI:

```bash
genkit start -- python main.py
```

## Contributors

This release was made possible by an incredible team effort. Thank you to all **13 contributors** who made this release possible:

| Contributor | Contributions |
|-------------|---------------|
| [@yesudeep](https://github.com/yesudeep) | Core architecture, 7 plugins, type safety, security |
| [@MengqinShen](https://github.com/MengqinShen) | Resources, samples, model configs |
| [@AbeJLazaro](https://github.com/AbeJLazaro) | Model Garden, Ollama, Gemini |
| [@pavelgj](https://github.com/pavelgj) | Reflection API, embedders |
| [@zarinn3pal](https://github.com/zarinn3pal) | Anthropic, DeepSeek, xAI, AIM |
| [@huangjeff5](https://github.com/huangjeff5) | PluginV2, type safety, telemetry |
| [@hendrixmar](https://github.com/hendrixmar) | Evaluators, OpenAI compat, Dotprompt |
| [@ssbushi](https://github.com/ssbushi) | Evaluator plugins |
| [@shrutip90](https://github.com/shrutip90) | ResourcePartSchema |
| [@schlich](https://github.com/schlich) | Type annotations |
| [@ktsmadhav](https://github.com/ktsmadhav) | Windows support |
| [@junhyukhan](https://github.com/junhyukhan) | Documentation |
| [@CorieW](https://github.com/CorieW) | Community contribution |

Special thanks to the [google/dotprompt](https://github.com/google/dotprompt) team for the deep integration work.

## What's Next?

We're committed to continuously evolving Genkit Python. Coming soon:

- **Session/Chat API**: Multi-turn conversation management
- **Reflection API v2**: WebSocket and JSON-RPC 2.0 support
- **More plugins**: Checks, Chroma, Pinecone, Cloud SQL PostgreSQL
- **Feature parity**: Continued alignment with JS/Go SDKs

## Get Involved

Got questions or feedback? Join us on:
- [Discord](https://discord.gg/qXt5zzQKpc)
- [Stack Overflow](https://stackoverflow.com/questions/tagged/genkit)
- [GitHub Issues](https://github.com/firebase/genkit/issues)

Explore the [full documentation](https://python.api.genkit.dev) and start building!

Happy coding, and we look forward to seeing what you create with Genkit Python 0.5.0!

---

*Tags: [Launch](https://firebase.blog/category/launch) | [Genkit](https://firebase.blog/category/genkit) | [AI](https://firebase.blog/category/ai) | [Python](https://firebase.blog/category/python)*
