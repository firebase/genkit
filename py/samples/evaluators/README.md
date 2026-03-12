# Evaluators

Custom evaluators (regex, LLM) for `genkit eval:run`.

```bash
export GEMINI_API_KEY=your-api-key
uv sync
genkit start -- uv run main.py
```

Then:

```bash
genkit eval:run datasets/regex_dataset.json --evaluators=byo/regex_match_url,byo/regex_match_us_phone
genkit eval:run datasets/pii_detection_dataset.json --evaluators=byo/pii_detection
genkit eval:run datasets/funniness_dataset.json --evaluators=byo/funniness
genkit eval:run datasets/deliciousness_dataset.json --evaluators=byo/deliciousness
```

Results at http://localhost:4000.
