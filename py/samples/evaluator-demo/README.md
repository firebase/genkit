# Evaluator Demo

An example demonstrating running flows using the Google GenAI plugin.

## Setup environment

Obtain an API key from [ai.dev](https://ai.dev).

Export the API key as env variable `GEMINI\_API\_KEY` in your shell
configuration.

```bash
export GEMINI_API_KEY='<Your api key>'
```

## Run the sample

Start the Genkit Developer UI:

```bash
genkit start -- uv run src/eval_demo.py
```

## Evaluations

### Simple inference and evaluation

Use the `run_eval_demo` command to run a flow against a set of input samples and
evaluate the generated outputs. Input (JSON) = "{}"


## Run tests

To run the automated tests for this sample:

```bash
uv run pytest -v src/eval_demo.py
```
