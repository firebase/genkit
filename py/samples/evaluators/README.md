# Evaluators Sample

Minimal evaluators: plugin (`genkitEval`) + custom LLM-based (`byo`):

- **`genkitEval/regex`** — Regex match (no LLM, reference = pattern)
- **`byo/maliciousness`** — LLM: does output intend to harm, deceive, or exploit?
- **`byo/answer_accuracy`** — LLM: rates output vs reference (4/2/0)

```bash
export GEMINI_API_KEY=your-api-key
uv sync
uv run src/main.py
```

**genkitEval/regex** (no API calls):

```bash
genkit eval:run datasets/genkit_eval_dataset.json --evaluators=genkitEval/regex
```

**Maliciousness** (LLM):

```bash
genkit eval:run datasets/maliciousness_dataset.json --evaluators=byo/maliciousness
```

**Answer Accuracy** (LLM):

```bash
genkit eval:run datasets/answer_accuracy_dataset.json --evaluators=byo/answer_accuracy
```
