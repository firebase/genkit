# Architecture

## Module structure

The tool follows a clean dependency graph with no circular imports:

```
types.py          ← Shared types (Status, PluginResult, Runtime Protocol)
   ↑
config.py         ← TOML config loader, RuntimeConfig (satisfies Runtime)
   ↑
paths.py          ← Path constants (REPO_ROOT, PY_DIR, TOOL_DIR)
   ↑
plugins.py        ← Plugin discovery, env-var checking
   ↑
display.py        ← Rich tables, Rust-style messages, formatting helpers
   ↑
┌──────────────┬──────────────────┬──────────────────────┐
│ checker.py   │ runner.py        │ test_model.py        │
│ (check-plugin)│ (--use-cli)     │ (check-model default)│
│              │ legacy CLI runner│ ActionRunner Protocol │
└──────────────┴──────────────────┴──────────────────────┘
   ↑                                      ↑
   │              ┌────────────┬──────────┘
   │              │            │
   │     reflection.py    test_cases.py
   │     (httpx client)   (12 built-in)
   │              │
   │     validators/
   │     ├── __init__.py   ← Protocol + @register decorator
   │     ├── helpers.py    ← Response parsing utilities
   │     ├── json.py       ← valid-json
   │     ├── media.py      ← valid-media
   │     ├── reasoning.py  ← reasoning
   │     ├── streaming.py  ← stream-text-includes, stream-has-tool-request, stream-valid-json
   │     ├── text.py       ← text-includes, text-starts-with, text-not-empty
   │     └── tool.py       ← has-tool-request
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

### ActionRunner Protocol

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

### Concurrency model (check-model)

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

### Validator registry

Validators use a Protocol + `@register` decorator pattern:

```python
@register('has-tool-request')
def has_tool_request(
    response: dict, arg: str | None = None, chunks: list[dict] | None = None,
) -> None:
    ...  # raise ValidationError on failure
```

10 validators are ported 1:1 from the canonical JS source
(`genkit-tools/cli/src/commands/dev-test-model.ts`).
