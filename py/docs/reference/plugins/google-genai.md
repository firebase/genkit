# Google Gen AI


## Installation

```bash
pip3 install genkit-plugin-google-genai
```

## Configuration

`genkit-plugin-google-genai` package provides two plugins:

  1. `GoogleAI` - for accessing Google Gemini API models
  2. `VertexAI` - for accessing Gemini API in Vertex AI models


### Google Gemini API

```py
from genkit.plugins.google_genai import GoogleAI

ai = Genkit(
  plugins=[GoogleAI()],
  model='googleai/gemini-2.0-flash', # optional
)
```

You will need to set `GEMINI_API_KEY` environment variable or you can provide the API Key directly:

```py
ai = Genkit(
  plugins=[GoogleAI(api_key='...')]
)
```


### Gemini API in Vertex AI

```py
from genkit.plugins.google_genai import VertexAI

ai = Genkit(
  plugins=[VertexAI()],
  model='vertexai/gemini-2.0-flash', # optional
)
```


you can specify `location` and `project` as well as other configuation options.

```py
ai = Genkit(
  plugins=[VertexAI(
    location='us-east1',
    project='my-project-id',
  )],
)
```


## API Reference

### GeminiConfigSchema

::: genkit.plugins.google_genai.GeminiConfigSchema

### GoogleAI

::: genkit.plugins.google_genai.GoogleAI
    options:
      inherited_members: false

### VertexAI

::: genkit.plugins.google_genai.VertexAI
    options:
      inherited_members: false
