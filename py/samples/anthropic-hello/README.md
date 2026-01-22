## Anthropic Sample

### How to Get Your Anthropic API Key

To use the Anthropic plugin, you need an API key from Anthropic.

1.  **Visit the Anthropic Console**: Go to the [Anthropic Console](https://console.anthropic.com/settings/keys) and sign in.
2.  **Create an API Key**: Click on "Create Key" to generate a new API key.
3.  **Add Credits**: You may need to add credits to your account to use the API.

For more details, check out the [official API overview](https://platform.claude.com/docs/en/api/overview).

### Usage

1. Setup environment and install dependencies:
```bash
uv venv
source .venv/bin/activate

uv sync
```

2. Set Anthropic API key:
```bash
export ANTHROPIC_API_KEY=your-api-key
```

3. Run the sample:
```bash
genkit start -- uv run src/main.py
```
