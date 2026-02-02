# Genkit DeepSeek Plugin

This Genkit plugin provides integration with DeepSeek's AI models, including
their powerful reasoning model (R1) and general-purpose chat model (V3).

## Installation

```bash
pip install genkit-plugin-deepseek
```

Or with uv:

```bash
uv add genkit-plugin-deepseek
```

## Setup

Set your DeepSeek API key:

```bash
export DEEPSEEK_API_KEY=your-api-key
```

Get your API key from: https://platform.deepseek.com/api_keys

## Usage

```python
from genkit import Genkit
from genkit.plugins.deepseek import DeepSeek

ai = Genkit(plugins=[DeepSeek()], model='deepseek/deepseek-chat')

response = await ai.generate(prompt='Hello, DeepSeek!')
print(response.text)
```

## Supported Models

| Model | Description |
|-------|-------------|
| `deepseek/deepseek-chat` | General-purpose chat model (V3). Fast and capable. |
| `deepseek/deepseek-reasoner` | Reasoning model (R1). Shows chain-of-thought. |

## Features

- **Text Generation**: Standard chat completions
- **Streaming**: Real-time token streaming
- **Chain-of-Thought**: R1 model shows reasoning steps
- **OpenAI-Compatible**: Uses familiar API format

## Configuration

```python
from genkit.plugins.deepseek import DeepSeek

# With explicit API key
ai = Genkit(plugins=[DeepSeek(api_key='your-key')])

# With custom API URL (for proxies)
ai = Genkit(plugins=[DeepSeek(api_url='https://your-proxy.com')])
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DEEPSEEK_API_KEY` | Your DeepSeek API key | Yes |

## Links

- [DeepSeek API Documentation](https://api-docs.deepseek.com/)
- [DeepSeek Platform](https://platform.deepseek.com/)
- [Genkit Documentation](https://genkit.dev/)
