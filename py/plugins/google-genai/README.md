# Google GenAI Plugin

Gemini and Vertex AI models, embeddings, and media generation for Genkit.

## Installation

```bash
pip install genkit-google-genai-plugin
```

## Configuration

**Google AI (AI Studio):**

```bash
export GEMINI_API_KEY='your-api-key'
```

Get a key at [Google AI Studio](https://aistudio.google.com/).

**Vertex AI:** Use `gcloud auth application-default login` and set `GOOGLE_CLOUD_PROJECT`.

## Quick Start

```python
from genkit import Genkit
from genkit.plugins.google_genai import GoogleAI

ai = Genkit(plugins=[GoogleAI()], model="googleai/gemini-2.0-flash")
response = await ai.generate(prompt="Hello!")
print(response.text)
```

## Samples

- [gemini-code-execution](../../samples/gemini-code-execution/) — Code execution, tools, streaming
- [google-genai-media](../../samples/google-genai-media/) — TTS, Imagen, Veo, Lyria
