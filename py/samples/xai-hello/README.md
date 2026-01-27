# xAI Hello Sample

Simple sample demonstrating the xAI (Grok) plugin for Genkit.

## How to Get Your xAI API Key

To use the xAI plugin, you need an API key from xAI.

1.  **Visit the xAI Console**: Go to the [xAI Console](https://console.x.ai/) and sign in.
2.  **Create an API Key**: Navigate to the API Keys section and create a new key.
3.  **Add Credits**: You may need to add credits to your account to use the API.

For a more detailed guide, check out the [official tutorial](https://docs.x.ai/docs/tutorial).

### Monitoring and Running

For an enhanced development experience, use the provided `run.sh` script to start the sample with automatic reloading:

```bash
./run.sh
```

This script uses `watchmedo` to monitor changes in:
- `src/` (Python logic)
- `../../packages` (Genkit core)
- `../../plugins` (Genkit plugins)
- File patterns: `*.py`, `*.prompt`, `*.json`

Changes will automatically trigger a restart of the sample. You can also pass command-line arguments directly to the script, e.g., `./run.sh --some-flag`.

## Setup


```bash
export XAI_API_KEY=your_api_key_here
```

## Run

```bash
cd py/samples/xai-hello
uv run src/main.py
```

## Features

- Simple text generation
- Streaming generation
- Custom configuration (temperature, max_output_tokens)
- xAI-specific parameters (reasoning_effort)
