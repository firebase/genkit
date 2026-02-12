# Genkit Conformance Runner

A parallel model conformance test runner for Genkit plugins.

---

## What it does

The `conform` tool runs `genkit dev:test-model` against multiple plugins
concurrently, collecting results in a live progress table and printing a
summary with error logs when complete.

## Quick start

```bash
# From anywhere in the repo
py/bin/conform check-model --all           # Run all plugins
py/bin/conform check-model anthropic xai   # Run specific plugins
py/bin/conform check-plugin                # Verify plugin files exist
py/bin/conform list                        # Show env-var readiness
py/bin/conform                             # Help + plugin table
```

## Subcommands

| Command | Purpose |
|---------|---------|
| `check-model` | Run model conformance tests in parallel |
| `check-plugin` | Lint-time check that plugins have conformance files |
| `list` | Show plugins and environment variable readiness |

## Key features

- **Parallel execution** — `asyncio.Queue` worker pool, configurable via `-j N`
- **Live progress** — Rich table updates as tests complete
- **Error log** — last 15 lines per failure, full output with `-v`
- **Rust-style messages** — color-coded errors and warnings
- **Multi-runtime** — `--runtime` flag selects Python, JS, Go, etc.
- **TOML-configured** — all settings in `pyproject.toml`, CLI overrides

!!! info "Installation"

    The tool is installed automatically as part of the workspace via
    `uv sync`. No separate installation needed.
