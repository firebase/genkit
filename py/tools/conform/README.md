# Conform — Model Conformance Test Runner

A private (non-publishable) tool for running Genkit model conformance
tests across all configured runtimes (Python, JS, Go).

Supports the Python runtime natively (in-process, no subprocess)
and all other runtimes via async HTTP to their reflection servers.
**No genkit CLI dependency.**

## Quick Start

```bash
# List available plugins, runtimes, and env-var readiness
conform list

# Run a single plugin's model conformance tests (all runtimes)
conform test-model google-genai

# Run against a specific runtime only
conform --runtime python test-model google-genai

# Run all plugins across all runtimes (parallel, uses genkit CLI)
conform check-model

# Run specific plugins only
conform check-model anthropic deepseek

# Check that every model plugin has conformance files (used by bin/lint)
conform check-plugin
```

## Architecture

```
conform test-model google-genai
        │
        ├── Auto-detect runtimes with entry points
        │   ├── python? ──→ InProcessRunner
        │   │   │   Import conformance_entry.py
        │   │   │   Get `ai` (Genkit instance)
        │   │   │   Call action.arun_raw() directly
        │   │   │   No subprocess, no HTTP, no reflection server
        │   │   └── ✅ Fastest path
        │   │
        │   ├── js? ──→ ReflectionRunner
        │   │   │   Start conformance_entry.ts subprocess
        │   │   │   Poll .genkit/runtimes/ for URL
        │   │   │   Async HTTP (httpx) → reflection API
        │   │   └── ✅ Cross-runtime
        │   │
        │   └── go? ──→ ReflectionRunner
        │       └── Same as JS

        All runners share:
        ├── ActionRunner Protocol  ← common interface
        ├── Validators (10 validators, Protocol + @register)
        ├── Test cases (12 built-in, 1:1 with JS)
        └── Rich console output + summary
```

### ActionRunner Protocol

All execution modes implement the same `ActionRunner` protocol:

```python
class ActionRunner(Protocol):
    async def run_action(
        self, key: str, input_data: dict, *, stream: bool = False,
    ) -> tuple[dict, list[dict]]: ...
    async def close(self) -> None: ...
```

Three implementations:

| Runner | When | How |
|--------|------|-----|
| `InProcessRunner` | Python runtime (default) | Imports entry point, calls `action.arun_raw()` via Genkit SDK |
| `ReflectionRunner` | JS/Go/other runtimes | Subprocess + async HTTP to reflection server |
| genkit CLI (legacy) | `--use-cli` flag | Delegates to `genkit dev:test-model` via `runner.py` |

## Layout

```
py/
├── tools/conform/                  ← This package (the CLI tool)
│   ├── pyproject.toml              ← Private package + [tool.conform] config
│   ├── README.md
│   └── src/conform/
│       ├── cli.py                  ← Argument parsing + subcommand dispatch
│       ├── config.py               ← TOML config loader
│       ├── checker.py              ← check-plugin: verify conformance files exist
│       ├── display.py              ← Rich tables, Rust-style errors, emoji status
│       ├── paths.py                ← Path constants derived from package location
│       ├── plugins.py              ← Plugin discovery and env-var checking
│       ├── reflection.py           ← Async HTTP client for reflection API (httpx)
│       ├── runner.py               ← Legacy parallel runner (genkit CLI subprocess)
│       ├── test_cases.py           ← 12 built-in test cases (1:1 parity with JS)
│       ├── test_model.py           ← Native test runner with ActionRunner Protocol
│       ├── types.py                ← Shared types (PluginResult, Status, Runtime)
│       └── validators/             ← Protocol-based validator registry
│           ├── __init__.py         ← Validator Protocol + @register decorator
│           ├── helpers.py          ← Shared response parsing utilities
│           ├── json.py             ← valid-json
│           ├── media.py            ← valid-media
│           ├── reasoning.py        ← reasoning
│           ├── streaming.py        ← stream-text-includes, stream-has-tool-request, stream-valid-json
│           ├── text.py             ← text-includes, text-starts-with, text-not-empty
│           └── tool.py             ← has-tool-request
│
└── tests/conform/                  ← Conformance spec files (per plugin)
    ├── anthropic/
    │   ├── model-conformance.yaml ← Test suite spec
    │   └── conformance_entry.py   ← Genkit entry point (Python)
    │   └── conformance_entry.ts   ← Genkit entry point (JS)
    │   └── conformance_entry.go   ← Genkit entry point (Go)
    ├── google-genai/
    │   └── ...
    └── ...
```

## Global Flags

These flags apply to all subcommands and must appear before the
subcommand name:

| Flag | Description |
|------|-------------|
| `--runtime NAME` | Runtime to use (default: all configured runtimes) |
| `--specs-dir DIR` | Override specs directory |

## Subcommands

### `conform test-model PLUGIN`

The primary command.  Runs model conformance tests for a single plugin
across all runtimes that have an entry point for it.

**Python runtime:** Imports the entry point in-process — no subprocess,
no HTTP server, no genkit CLI.  This is the fastest path.

**Other runtimes (JS, Go):** Starts the entry point as a subprocess,
discovers the reflection server URL from `.genkit/runtimes/`, and
communicates via async HTTP.

| Flag | Description |
|------|-------------|
| `--use-cli` | Use genkit CLI instead of native runner |

### `conform check-model [PLUGIN...]`

Runs `genkit dev:test-model` against plugins concurrently using
`asyncio`.  By default runs **all plugins across all runtimes**.
Optionally filter by plugin name.

A live Rich progress table updates as results arrive, followed by a
final summary table with emojis.

**Concurrency control:** An `asyncio.Queue` with a fixed worker pool
bounds the number of concurrent plugin tests.  The default is 4
(configurable via TOML or `-j` flag).

**Pre-flight checks:** Before spawning a subprocess, the runner verifies
that the plugin's spec file, entry point, and required environment
variables exist.  Missing env vars cause the plugin to be skipped (not
errored).

| Flag | Description |
|------|-------------|
| `-j N` | Maximum concurrent plugins |
| `-v` | Print full stdout/stderr for failures |

### `conform check-plugin`

Verifies that every model plugin has:
1. `tests/conform/<plugin>/model-conformance.yaml`
2. `tests/conform/<plugin>/conformance_entry.py`

This subcommand is called by `py/bin/check_consistency` (check 21)
during `bin/lint`.

### `conform list`

Displays a table of all plugins with conformance specs, showing:

- **Runtimes** — which runtimes have entry points (green = available,
  dim = not available)
- **Environment variables** — which are set (blue) and missing (red)
- **Readiness** — green ● = ready, red ○ = missing env vars

## Validators

10 validators ported 1:1 from the canonical JS source
(`genkit-tools/cli/src/commands/dev-test-model.ts`):

| Validator | Module | What it checks |
|-----------|--------|----------------|
| `text-includes` | `text.py` | Response text contains expected substring |
| `text-starts-with` | `text.py` | Response text starts with expected prefix |
| `text-not-empty` | `text.py` | Response text is non-empty |
| `valid-json` | `json.py` | Response text is valid JSON |
| `has-tool-request` | `tool.py` | Response contains a tool request part |
| `valid-media` | `media.py` | Response contains a media part with valid URL |
| `reasoning` | `reasoning.py` | Response contains a reasoning/thinking part |
| `stream-text-includes` | `streaming.py` | Streamed chunks contain expected text |
| `stream-has-tool-request` | `streaming.py` | Streamed chunks contain a tool request |
| `stream-valid-json` | `streaming.py` | Final streamed chunk is valid JSON |

Custom validators can be added by creating a function and decorating it
with `@register('name')` in a new module under `validators/`.

## Configuration

The tool reads `[tool.conform]` from its own `pyproject.toml`:

```toml
[tool.conform]
concurrency = 4
additional-model-plugins = ["google-genai", "vertex-ai", "ollama"]

[tool.conform.env]
anthropic = ["ANTHROPIC_API_KEY"]
google-genai = ["GEMINI_API_KEY"]
# ...

[tool.conform.runtimes.python]
specs-dir = "py/tests/conform"
plugins-dir = "py/plugins"
entry-command = ["uv", "run", "--project", "py", "--active"]

[tool.conform.runtimes.js]
specs-dir = "py/tests/conform"
plugins-dir = "js/plugins"
entry-command = ["npx", "tsx"]
```

CLI flags override TOML values:

| Flag | TOML Key | Description |
|------|----------|-------------|
| `--runtime NAME` | — | Filter to a single runtime |
| `--specs-dir DIR` | `runtimes.<name>.specs-dir` | Override specs directory |
| `-j N` | `concurrency` | Max concurrent plugins |
| `--verbose` | — | Print full output for failures |

## Adding a New Plugin

1. Create `tests/conform/<plugin>/model-conformance.yaml` with test
   suites.
2. Create entry points for each runtime:
   - `tests/conform/<plugin>/conformance_entry.py` (Python)
   - `tests/conform/<plugin>/conformance_entry.ts` (JS)
   - `tests/conform/<plugin>/conformance_entry.go` (Go)
3. Add the plugin's env vars to `[tool.conform.env]` in
   `tools/conform/pyproject.toml`.
4. If the plugin lacks `model_info.py`, add it to
   `additional-model-plugins`.
5. Run `conform check-plugin` to verify.

## Python Version Support

Supports Python 3.10 through 3.14.  On Python 3.10, the `tomli` package
is used as a backport for `tomllib` (added in 3.11).

## Design: Canonical JS Parity

The validators, test cases, and reflection client are ported from the
canonical JS implementation in:

    genkit-tools/cli/src/commands/dev-test-model.ts

The `waitForActions` function was also backported to the JS source to
ensure both implementations poll for model action registration before
dispatching tests (prevents 404 race conditions).
