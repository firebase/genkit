# Hello world

## Setup environment

```bash
uv venv
source .venv/bin/activate
```

## Run the sample

TODO

```bash
genkit start -- python3 hello.py # Doesn't currently work with the venv configuration.
genkit start -- uv run hello.py  # Starts but runtime detection fails.
genkit start -- uv run python3 hello.py  # Starts but runtime detection fails.
```
