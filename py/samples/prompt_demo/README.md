An example demonstrating how to manage prompts using Genkit's prompt loading system.

## Setup environment

Obtain an API key from [ai.dev](https://ai.dev).

Export the API key as env variable `GEMINI_API_KEY` in your shell
configuration.

```bash
export GEMINI_API_KEY='<Your api key>'
```

## Run the sample

```bash
genkit start -- uv run src/prompt_demo.py
```

## Prompt Structure

- `data/`: Contains `.prompt` files (using [Dotprompt](https://genkit.dev/docs/dotprompt)).
- `data/_shared_partial.prompt`: A partial that can be included in other prompts.
- `data/nested/nested_hello.prompt`: A prompt demonstrating nested structure and partial inclusion.
