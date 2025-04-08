# Short-n-long

An example demonstrating running flows as both a short-lived application and a
server.

## Setup environment

Obtain an API key from [ai.dev](https://ai.dev).

Export the API key as env variable `GEMINI\_API\_KEY` in your shell
configuration.

```bash
export GEMINI_API_KEY='<Your api key>'
```

## Run the sample

To start the short-lived application normally.

```bash
uv run src/short_n_long/main.py
```

To start the short-lived application in dev mode:

```bash
genkit start -- uv run src/short_n_long/main.py
```

To start as a server normally:

```bash
uv run src/short_n_long/main.py --server
```

To start as a server in dev mode:

```bash
genkit start -- uv run src/short_n_long/main.py --server
```

## Running with a specific version of Python

```bash
genkit start -- uv run --python python3.10 src/short_n_long/main.py
```
