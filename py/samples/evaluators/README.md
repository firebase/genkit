# Evaluators Sample

Demonstrates two custom evaluator patterns:

- **Regex** (`byo/url`) — checks output for a URL pattern, no LLM required
- **LLM-as-judge** (`byo/deliciousness`) — uses a model to score output

Run the file once to see the regex evaluator shape:

```bash
uv run src/main.py
```

To run full Genkit evaluations:

```bash
export GEMINI_API_KEY=your-api-key
genkit eval:run
```
