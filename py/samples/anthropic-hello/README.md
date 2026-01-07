## Anthropic Sample

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
