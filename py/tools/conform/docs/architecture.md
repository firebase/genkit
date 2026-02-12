# Architecture

## Module structure

The tool follows a clean dependency graph with no circular imports:

```
types.py          ← Shared types (Status, PluginResult, Runtime Protocol)
   ↑
config.py         ← TOML config loader, RuntimeConfig (satisfies Runtime)
   ↑
plugins.py        ← Plugin discovery, env-var checking
   ↑
display.py        ← Rich tables, Rust-style messages
   ↑
checker.py        ← File existence checking (check-plugin)
runner.py         ← Async parallel test runner (check-model)
   ↑
cli.py            ← CLI entry point, argparse, dispatch
   ↑
__main__.py       ← python -m conform support
```

## Key design decisions

### Types in a separate module

`Status`, `PluginResult`, and the `Runtime` Protocol live in `types.py`
which has **zero internal dependencies**. This breaks what would otherwise
be a circular import between `display.py` (needs `PluginResult` for type
signatures) and `runner.py` (needs display functions for output).

### Runtime Protocol

```python
@runtime_checkable
class Runtime(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def specs_dir(self) -> Path: ...

    @property
    def plugins_dir(self) -> Path: ...

    @property
    def entry_command(self) -> list[str]: ...
```

The `RuntimeConfig` dataclass in `config.py` satisfies this protocol.
New runtimes can be added by:

1. Adding a `[tool.conform.runtimes.<name>]` section to `pyproject.toml`
2. Or creating a new class that satisfies the protocol

### Concurrency model

```
┌─────────────┐
│   cli.py    │  asyncio.run()
└──────┬──────┘
       ▼
┌─────────────┐
│  runner.py  │  asyncio.Queue + N workers
└──────┬──────┘
       ├──► Worker 1: pulls from queue, runs test
       ├──► Worker 2: pulls from queue, runs test
       └──► Worker N: (bounded by config.concurrency)
```

The runner creates an `asyncio.Queue` of plugins to test and a pool of
`N` worker coroutines. Each worker pulls a plugin from the queue and runs
it as a subprocess using `asyncio.create_subprocess_exec`. The number
of workers limits concurrency (default: 4, configurable via `-j` or TOML).
