# Genkit Cohere AI Plugin

The Cohere AI plugin for [Genkit](https://github.com/firebase/genkit)
provides integration with [Cohere's](https://cohere.com/) AI models,
including:

- **Chat models** — Command A, Command A Vision, Command A Reasoning,
  Command R+, Command R, and more for text generation, tool calling,
  and structured output via the V2 API.
- **Embedding models** — Embed v4.0, Embed English/Multilingual v3.0
  for semantic search, RAG, and clustering.

## Installation

```bash
pip install genkit-plugin-cohere
```

## Quick Start

```python
from genkit.ai import Genkit
from genkit.plugins.cohere import Cohere, cohere_name

ai = Genkit(
    plugins=[Cohere()],
    model=cohere_name('command-a-03-2025'),
)

response = await ai.generate(prompt='Hello, Cohere!')
print(response.text)
```

## Configuration

Set your Cohere API key via the `COHERE_API_KEY` environment variable
(or `CO_API_KEY`), or pass it directly:

```python
ai = Genkit(plugins=[Cohere(api_key='your-api-key')])
```

Get an API key from: https://dashboard.cohere.com/api-keys

## Supported Models

### Chat Models

| Model                         | Tool Calling | Structured Output | Media | Streaming |
|-------------------------------|:------------:|:-----------------:|:-----:|:---------:|
| `command-a-03-2025`           | ✅           | ✅                | ❌    | ✅        |
| `command-a-reasoning-08-2025` | ✅           | ✅                | ❌    | ✅        |
| `command-a-translate-08-2025` | ✅           | ✅                | ❌    | ✅        |
| `command-a-vision-07-2025`    | ❌           | ✅                | ✅    | ✅        |
| `command-r7b-12-2024`         | ✅           | ✅                | ❌    | ✅        |
| `command-r-plus-08-2024`      | ✅           | ✅                | ❌    | ✅        |
| `command-r-plus-04-2024`      | ✅           | ✅                | ❌    | ✅        |
| `command-r-plus`              | ✅           | ✅                | ❌    | ✅        |
| `command-r-08-2024`           | ✅           | ✅                | ❌    | ✅        |
| `command-r-03-2024`           | ✅           | ✅                | ❌    | ✅        |
| `command-r`                   | ✅           | ✅                | ❌    | ✅        |

> **Note:** `command` and `command-light` were removed by Cohere on
> September 15, 2025 and are not supported.

### Embedding Models

| Model                           | Dimensions | Languages    |
|---------------------------------|-----------:|--------------|
| `embed-v4.0`                    | 1024       | Multilingual |
| `embed-english-v3.0`            | 1024       | English      |
| `embed-english-light-v3.0`      | 384        | English      |
| `embed-multilingual-v3.0`       | 1024       | 100+         |
| `embed-multilingual-light-v3.0` | 384        | 100+         |

## Features

### Tool Calling

```python
@ai.tool()
async def get_weather(location: str) -> str:
    \"\"\"Get weather for a location.\"\"\"
    return f'Sunny and 72°F in {location}'

response = await ai.generate(
    model=cohere_name('command-a-03-2025'),
    prompt='What is the weather in San Francisco?',
    tools=[get_weather],
)
```

### Structured Output

```python
from pydantic import BaseModel
from genkit.ai import Output

class Character(BaseModel):
    name: str
    backstory: str

response = await ai.generate(
    prompt='Create an RPG character',
    output=Output(schema=Character),
)
character = response.output  # typed as Character
```

### Embeddings

```python
from genkit.blocks.document import Document

doc = Document.from_text('Hello world')
embeddings = await ai.embed(
    embedder=cohere_name('embed-v4.0'),
    content=doc,
)
```

## License

Apache-2.0
