## DeepSeek Sample

1. Setup environment and install dependencies:
```bash
uv venv
source .venv/bin/activate

uv sync
```

2. Set DeepSeek API key (get one from [DeepSeek Platform](https://platform.deepseek.com/)):
```bash
export DEEPSEEK_API_KEY=your-api-key
```

3. Run the sample:
```bash
genkit start -- uv run src/main.py
```
