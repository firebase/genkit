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

## Run the sample

TODO

```bash
genkit start -- uv run src/main.py
```
