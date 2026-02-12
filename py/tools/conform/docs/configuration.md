# Configuration

All configuration lives in `py/tools/conform/pyproject.toml` under
`[tool.conform]`.

## Concurrency

```toml
[tool.conform]
concurrency = 4
```

Override with `-j N`:

```bash
conform check-model --all -j 8
```

## Environment variables

Required env vars per plugin:

```toml
[tool.conform.env]
google-genai          = ["GEMINI_API_KEY"]
anthropic             = ["ANTHROPIC_API_KEY"]
ollama                = []                        # No credentials needed
microsoft-foundry     = ["AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT"]
```

Plugins with missing env vars are **skipped** (not failed) during
`check-model`.

## Additional model plugins

Plugins that use dynamic model registration (no `model_info.py`):

```toml
[tool.conform]
additional-model-plugins = ["google-genai", "vertex-ai", "ollama"]
```

These are included in `check-plugin` verification even though they
lack a `model_info.py` file.

## Adding a new plugin

1. Add the plugin's env vars to `[tool.conform.env]`
2. Create `py/tests/conform/<plugin>/model-conformance.yaml`
3. Create `py/tests/conform/<plugin>/conformance_entry.py`
4. Run `conform check-plugin` to verify
5. Run `conform check-model <plugin>` to test
