# Asynchronous vs synchronous Genkit API

## Run the sample

To start the short-lived application normally.

```bash
genkit start -- uv run src/async_vs_sync/main.py
```

To start the short-lived application in dev mode:

```bash
env GENKIT_ENV=dev uv run src/async_vs_sync/main.py
```

To start the server normally:

```bash
uv run src/async_vs_sync/main.py --server
```

To start the server in dev mode:

```bash
env GENKIT_ENV=dev uv run src/async_vs_sync/main.py --server
```
