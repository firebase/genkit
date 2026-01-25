# OpenAI Sample.

## Setup environment

### How to Get Your OpenAI API Key

To use the OpenAI plugin, you need an OpenAI API key.

1.  **Visit OpenAI Platform**: Go to [OpenAI API Keys](https://platform.openai.com/api-keys) and sign in.
2.  **Create API Key**: Click on "Create new secret key".
3.  **Add Credits**: You may need to add credits to your account.

For more details, check out the [official documentation](https://platform.openai.com/docs/quickstart).

Export the API key as env variable `OPENAI_API_KEY`:

```bash
export OPENAI_API_KEY=<Your api key>
```

```bash
uv venv
source .venv/bin/activate
```

### Monitoring and Running

For an enhanced development experience, use the provided `run.sh` script to start the sample with automatic reloading:

```bash
./run.sh
```

This script uses `watchmedo` to monitor changes in:
- `src/` (Python logic)
- `../../packages` (Genkit core)
- `../../plugins` (Genkit plugins)
- File patterns: `*.py`, `*.prompt`, `*.json`

Changes will automatically trigger a restart of the sample. You can also pass command-line arguments directly to the script, e.g., `./run.sh --some-flag`.

## Run the sample

TODO

```bash
genkit start -- uv run src/main.py
```
