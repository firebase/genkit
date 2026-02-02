# Genkit Mistral AI Plugin

This Genkit plugin provides integration with Mistral AI's models, including
Mistral Large, Mistral Small, Codestral, and Pixtral vision models.

## Installation

```bash
pip install genkit-plugin-mistral
```

Or with uv:

```bash
uv add genkit-plugin-mistral
```

## Setup

Set your Mistral API key:

```bash
export MISTRAL_API_KEY=your-api-key
```

Get your API key from: https://console.mistral.ai/api-keys/

## Usage

```python
from genkit import Genkit
from genkit.plugins.mistral import Mistral

ai = Genkit(plugins=[Mistral()], model='mistral/mistral-large-latest')

response = await ai.generate(prompt='Hello, Mistral!')
print(response.text)
```

## Supported Models

| Model | Description |
|-------|-------------|
| `mistral/mistral-large-latest` | Most capable model for complex tasks |
| `mistral/mistral-small-latest` | Fast and efficient for everyday use |
| `mistral/codestral-latest` | Specialized for code generation |
| `mistral/pixtral-large-latest` | Vision-language model |
| `mistral/ministral-8b-latest` | Compact model for edge deployment |
| `mistral/ministral-3b-latest` | Smallest model for resource-constrained environments |

## Features

- **Text Generation**: Standard chat completions
- **Streaming**: Real-time token streaming
- **Vision**: Image understanding with Pixtral models
- **Code Generation**: Specialized coding with Codestral
- **Function Calling**: Tool use support

## Configuration

```python
from genkit.plugins.mistral import Mistral

# With explicit API key
ai = Genkit(plugins=[Mistral(api_key='your-key')])
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `MISTRAL_API_KEY` | Your Mistral AI API key | Yes |

## Links

- [Mistral AI Documentation](https://docs.mistral.ai/)
- [Mistral API Reference](https://docs.mistral.ai/api/)
- [Mistral Console](https://console.mistral.ai/)
- [Genkit Documentation](https://genkit.dev/)
