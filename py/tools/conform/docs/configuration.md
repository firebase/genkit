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
conform check-model -j 8
```

## Environment variables

Required env vars per plugin:

```toml
[tool.conform.env]
google-genai          = ["GEMINI_API_KEY"]
anthropic             = ["ANTHROPIC_API_KEY"]
compat-oai            = ["OPENAI_API_KEY"]
mistral               = ["MISTRAL_API_KEY"]
deepseek              = ["DEEPSEEK_API_KEY"]
xai                   = ["XAI_API_KEY"]
cohere                = ["COHERE_API_KEY"]
amazon-bedrock        = ["AWS_REGION"]
huggingface           = ["HF_TOKEN"]
microsoft-foundry     = ["AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT"]
cloudflare-workers-ai = ["CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_API_TOKEN"]
vertex-ai             = ["GOOGLE_CLOUD_PROJECT"]
ollama                = []                        # No credentials needed
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

## Runtime configuration

Each runtime defines how to locate specs, plugins, and what command
to use for running entry points:

```toml
[tool.conform.runtimes.python]
specs-dir     = "py/tests/conform"
plugins-dir   = "py/plugins"
entry-command = ["uv", "run", "--project", "py", "--active"]

[tool.conform.runtimes.js]
specs-dir     = "py/tests/conform"
plugins-dir   = "js/plugins"
entry-command = ["npx", "tsx"]
cwd           = "js"

[tool.conform.runtimes.go]
specs-dir     = "py/tests/conform"
plugins-dir   = "go/plugins"
entry-command = ["go", "run"]
cwd           = "go"
```

Runtime-specific entry filenames and model markers default to
sensible values per runtime but can be overridden:

| Runtime | `entry-filename` | `model-marker` |
|---------|-------------------|----------------|
| python  | `conformance_entry.py` | `model_info.py` |
| js      | `conformance_entry.ts` | `models.ts` |
| go      | `conformance_entry.go` | `model_info.go` |

## CLI flags vs TOML

CLI flags override TOML values:

| Flag | TOML Key | Description |
|------|----------|-------------|
| `--runtime NAME` | — | Filter to a single runtime |
| `--specs-dir DIR` | `runtimes.<name>.specs-dir` | Override specs directory |
| `-j N` | `concurrency` | Max concurrent plugins |
| `--verbose` | — | Print full output for failures |

## Adding a new plugin

1. Add the plugin's env vars to `[tool.conform.env]`
2. Create `py/tests/conform/<plugin>/model-conformance.yaml`
3. Create entry points for each runtime:
    - `conformance_entry.py` (Python)
    - `conformance_entry.ts` (JS)
    - `conformance_entry.go` (Go)
4. Run `conform check-plugin` to verify
5. Run `conform check-model <plugin>` to test
