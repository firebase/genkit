# Short-n-long

An example demonstrating running flows as both a short-lived application and a
server.

## Setup environment

### How to Get Your Gemini API Key

To use the Google GenAI plugin, you need a Gemini API key.

1.  **Visit AI Studio**: Go to [Google AI Studio](https://aistudio.google.com/).
2.  **Create API Key**: Click on "Get API key" and create a key in a new or existing Google Cloud project.

For more details, check out the [official documentation](https://ai.google.dev/gemini-api/docs/api-key).

Export the API key as env variable `GEMINI_API_KEY` in your shell configuration.

```bash
export GEMINI_API_KEY='<Your api key>'
```

## Run the sample

To start the short-lived application normally.

```bash
uv run src/main.py
```

To start the short-lived application in dev mode:

```bash
genkit start -- uv run src/main.py
```

To start as a server normally:

```bash
uv run src/main.py --server
```

To start as a server in dev mode:

```bash
genkit start -- uv run src/main.py --server
```

## Running with a specific version of Python

```bash
genkit start -- uv run --python python3.10 src/main.py
```
