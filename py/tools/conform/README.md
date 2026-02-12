# Conform — Parallel Model Conformance Test Runner

A private (non-publishable) tool for running Genkit model conformance
tests in parallel.  Currently targets the Python runtime; designed to be
extended to other runtimes (JS, Go, Dart, Java, Rust) in the future.

## Quick Start

```bash
# List available plugins and env-var readiness
conform list

# Run all plugins in parallel
conform run --all

# Run specific plugins
conform run anthropic deepseek

# Run with 6 concurrent workers and verbose output
conform run --all -j 6 -v

# Check that every model plugin has conformance files (used by bin/lint)
conform check-model
```

## Layout

```
py/
├── tools/conform/                  ← This package (the CLI tool)
│   ├── pyproject.toml              ← Private package + [tool.conform] config
│   ├── README.md
│   └── src/conform/
│       ├── cli.py                  ← Argument parsing + subcommand dispatch
│       ├── config.py               ← TOML config loader
│       ├── checker.py              ← check-model: verify conformance files exist
│       ├── display.py              ← Rich tables, Rust-style errors, emoji status
│       ├── paths.py                ← Path constants derived from package location
│       ├── plugins.py              ← Plugin discovery and env-var checking
│       └── runner.py               ← Async parallel test runner (asyncio)
│
└── tests/conform/                  ← Conformance spec files (per plugin)
    ├── anthropic/
    │   ├── model-conformance.yaml  ← Test suite spec
    │   └── conformance_entry.py    ← Genkit entry point
    ├── deepseek/
    │   └── ...
    └── ...
```

## Subcommands

### `conform run`

Runs `genkit dev:test-model` against one or more plugins concurrently
using `asyncio`.  A live Rich progress table updates as results arrive,
followed by a final summary table with emojis.

**Concurrency control:** An `asyncio.Semaphore` bounds the number of
concurrent plugin tests.  The default is 4 (configurable via TOML or
`-j` flag).

**Pre-flight checks:** Before spawning a subprocess, the runner verifies
that the plugin's spec file, entry point, and required environment
variables exist.  Missing env vars cause the plugin to be skipped (not
errored).

### `conform check-model`

Verifies that every model plugin has:
1. `tests/conform/<plugin>/model-conformance.yaml`
2. `tests/conform/<plugin>/conformance_entry.py`

Model plugins are discovered by scanning for `model_info.py` in plugin
source trees, plus an explicit list of additional providers in the TOML
config (for plugins using dynamic model registration).

This subcommand is called by `py/bin/check_consistency` (check 21)
during `bin/lint`.

### `conform list`

Displays a table of all plugins with conformance specs, showing which
environment variables are set (blue) and which are missing (red).

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
```

CLI flags override TOML values:

| Flag | TOML Key | Description |
|------|----------|-------------|
| `-j N` | `concurrency` | Max concurrent plugins |
| `--verbose` | — | Print full output for failures |
| `--all` | — | Test all available plugins |

## Adding a New Plugin

1. Create `tests/conform/<plugin>/model-conformance.yaml` with test
   suites.
2. Create `tests/conform/<plugin>/conformance_entry.py` that
   initializes Genkit with the plugin and calls `asyncio.Event().wait()`.
3. Add the plugin's env vars to `[tool.conform.env]` in
   `tools/conform/pyproject.toml`.
4. If the plugin lacks `model_info.py`, add it to
   `additional-model-plugins`.
5. Run `conform check-model` to verify.

## Python Version Support

Supports Python 3.10 through 3.14.  On Python 3.10, the `tomli` package
is used as a backport for `tomllib` (added in 3.11).

## Future: Multi-Runtime Support

This tool is designed to be extended to drive conformance tests for all
Genkit runtimes (JS, Go, Dart, Java, Rust).  The current implementation
focuses on the Python runtime.  Extension points include:

- `[tool.conform]` config can be extended with per-runtime sections
- `paths.py` already derives `REPO_ROOT` for cross-runtime access
- The `runner.py` subprocess model is runtime-agnostic (just change the
  command invoked per runtime)
