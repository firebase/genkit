# Genkit Conformance Runner

A parallel model conformance test runner for Genkit plugins across
multiple runtimes (Python, JS, Go).

---

## What it does

The `conform` tool runs model conformance tests against Genkit plugins.
It uses a **native runner** by default:

- **Python runtime** — imports the entry point in-process (no subprocess,
  no HTTP).  **No genkit CLI dependency.**
- **JS/Go runtimes** — communicates with reflection servers via async HTTP.
- **Legacy fallback** — `--use-cli` flag delegates to `genkit dev:test-model`.

## Quick start

```bash
# From anywhere in the repo
py/bin/conform check-model                 # Run all plugins (all runtimes)
py/bin/conform check-model anthropic xai   # Run specific plugins
py/bin/conform check-model --use-cli       # Legacy genkit CLI runner
py/bin/conform --runtime python check-model  # Single runtime only
py/bin/conform check-plugin                # Verify plugin files exist
py/bin/conform list                        # Show runtimes and env-var readiness
py/bin/conform                             # Help + plugin table
```

## Subcommands

| Command | Purpose |
|---------|---------|
| `check-model [PLUGIN...]` | Run model conformance tests (native runner by default) |
| `check-plugin` | Lint-time check that plugins have conformance files |
| `list` | Show plugins, runtimes, and environment variable readiness |

## Key features

- **Native test runner** — in-process for Python, async HTTP for JS/Go (no genkit CLI needed)
- **Parallel execution** — `asyncio.Semaphore` bounds concurrency, configurable via `-j N`
- **Live progress** — Rich table pinned at bottom, log lines scroll above
- **Error log** — last 15 lines per failure, full output with `-v`
- **10 validators** — ported 1:1 from the canonical JS implementation
- **Rust-style messages** — color-coded errors and warnings
- **Multi-runtime** — runs across Python, JS, Go runtimes by default
- **TOML-configured** — all settings in `pyproject.toml`, CLI overrides

!!! info "Installation"

    The tool is installed automatically as part of the workspace via
    `uv sync`. No separate installation needed.
