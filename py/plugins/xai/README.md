# xAI Sample

1. Setup environment and install dependencies:
```bash
uv venv
source .venv/bin/activate

uv sync
```

2. Set xAI API key:
```bash
export XAI_API_KEY=your-api-key
```

3. Run the sample:
```bash
genkit start -- uv run src/xai_hello.py
```
