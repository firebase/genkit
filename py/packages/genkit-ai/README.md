# genkit-ai

## Setup Instructions

1. Install `uv` from https://docs.astral.sh/uv/getting-started/installation/

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Install required tools using `uv`

```bash
uv pip install -r pyproject.toml
```

3. If you are using VSCode, install the `Ruff` extension from the marketplace to
   add linter support.

## Run test app

See the README.md in the samples folder.


## Run all unit tests

``` bash
uv run pytest .
```


