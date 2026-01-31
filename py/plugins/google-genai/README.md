# Google GenAI Plugin

This Genkit plugin provides a unified interface for Google AI (Gemini) and Vertex AI models, embedding, and other services.

## Setup environment

```bash
uv venv
source .venv/bin/activate
pip install genkit-plugins-google-genai
```

## Configuration

### Google AI (AI Studio)

To use Google AI models, obtain an API key from [Google AI Studio](https://aistudio.google.com/) and set it in your environment:

```bash
export GEMINI_API_KEY='<your-api-key>'
```

### Vertex AI (Google Cloud)

To use Vertex AI models, ensure you have a Google Cloud project and Application Default Credentials (ADC) set up:

```bash
gcloud auth application-default login
```

## Features

### Dynamic Models

The plugin automatically discovers available models from the API upon initialization. You can use any model name supported by the API (e.g., `googleai/gemini-2.0-flash-exp`, `vertexai/gemini-1.5-pro`).

### Dynamic Configuration

New or experimental parameters can be passed flexibly using `model_validate` to bypass strict schema checks:

```python
from genkit.plugins.google_genai import GeminiConfigSchema

config = GeminiConfigSchema.model_validate({
    'temperature': 1.0,
    'response_modalities': ['TEXT', 'IMAGE'],
})
```

## Examples

For comprehensive usage examples, see [`py/samples/google-genai-hello/README.md`](../../samples/google-genai-hello/README.md).
