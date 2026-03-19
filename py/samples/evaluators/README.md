# Evaluators Sample

Two minimal evaluators:

- **`byo/url`** — Regex match (no LLM)
- **`byo/deliciousness`** — LLM-as-judge

```bash
export GEMINI_API_KEY=your-api-key
uv sync
uv run src/main.py
```

**Regex** (no API calls):

```bash
genkit eval:run datasets/regex_dataset.json --evaluators=byo/url
```

**LLM evaluator**:

```bash
genkit eval:run datasets/deliciousness_dataset.json --evaluators=byo/deliciousness
```
