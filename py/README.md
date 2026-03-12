# Genkit Python SDK

Genkit is a framework for building AI-powered applications. This is the Python implementation with type-safe flows, structured outputs, and integrated observability.

## Installation

Install the Genkit core package and a model provider plugin. For Google AI Gemini models:

```bash
pip install genkit genkit-google-genai-plugin
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add genkit genkit-google-genai-plugin
```

See [PyPI](https://pypi.org/search/?q=genkit) for other plugins (anthropic, ollama, compat-oai, etc.).

## Quick Start

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

## Flows

Define typed, observable AI flows:

```python
from genkit import Genkit
from genkit.plugins.google_genai import GoogleAI

ai = Genkit(
    plugins=[GoogleAI()],
    model="googleai/gemini-2.0-flash",
)

@ai.flow()
async def summarize(text: str) -> str:
    response = await ai.generate(
        prompt=f"Summarize this in one sentence: {text}",
    )
    return response.text
```

Run with the Dev UI: `genkit start -- uv run src/main.py`

## Next Steps

- [Documentation](https://genkit.dev/docs/overview/?lang=python) — Full guides and API reference
- [Samples](samples/README.md) — Example applications
- [Development](GEMINI.md) — Contributing and code quality

## License

Apache 2.0
