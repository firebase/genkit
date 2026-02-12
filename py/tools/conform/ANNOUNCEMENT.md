# Announcing Conform: Cross-Runtime Model Conformance Testing for Genkit

## TL;DR

**Conform** is a purpose-built model conformance test runner for the
Genkit SDK.  It validates that every model plugin — across Python, JS,
and Go runtimes — behaves correctly and consistently.  The Python
runtime runs **in-process** with zero subprocess overhead; JS and Go
runtimes communicate via async HTTP to their reflection servers.  One
command tests **13 plugins**, runs **150+ test cases**, and reports
results in **under 4 minutes**.

---

## The Problem

The Genkit SDK supports **13+ model plugins** (Anthropic, Google GenAI,
Amazon Bedrock, Mistral, DeepSeek, Cohere, xAI, Ollama, …) across
**3 runtimes** (Python, JS, Go).  Each plugin must correctly:

1. **Generate text** — simple prompts, system messages, multi-turn
2. **Handle structured output** — JSON mode, schema conformance
3. **Support tool calling** — tool requests, tool responses, multi-step
4. **Stream responses** — text chunks, streamed JSON, streamed tool calls
5. **Process media** — image inputs, media outputs
6. **Expose reasoning** — thinking / reasoning content from supported models

Previously, conformance was tested ad hoc:

- Manual spot-checks against live APIs
- Plugin-specific unit tests with mocked responses
- No cross-runtime consistency verification
- No shared test suite between Python, JS, and Go
- Failures discovered in production, not at PR time

---

## The Solution

Conform provides a unified test framework with a single CLI:

```
conform list           →  Show all plugins, runtimes, and env-var readiness
conform check-model    →  Run model conformance tests across all plugins
conform check-plugin   →  Verify every model plugin has conformance specs
```

---

## Features

### Live Conformance Results

Conform runs all plugin tests concurrently (bounded by a configurable
semaphore) and displays a live Rich progress table.  Log lines scroll
above while the summary table stays pinned at the bottom:

![conform check-model results](https://raw.githubusercontent.com/firebase/genkit/main/py/tools/conform/docs/images/conform_results.png)

13 plugins.  150+ tests.  Under 4 minutes wall time.

### In-Process Python Runner

The Python runtime uses an **InProcessRunner** that imports the
plugin's entry point directly — no subprocess, no HTTP server, no
genkit CLI dependency:

```python
class ActionRunner(Protocol):
    async def run_action(
        self, key: str, input_data: dict, *, stream: bool = False,
    ) -> tuple[dict, list[dict]]: ...
    async def close(self) -> None: ...
```

| Runner | When | How |
|--------|------|-----|
| **InProcessRunner** | Python (default) | Imports entry point, calls `action.arun_raw()` directly |
| **ReflectionRunner** | JS / Go | Subprocess → async HTTP to reflection server |
| **genkit CLI** | `--use-cli` flag | Delegates to `genkit dev:test-model` |

### 10 Validators — 1:1 Parity with JS

Every validator is ported from the canonical JS implementation:

| Validator | What it checks |
|-----------|----------------|
| `text-includes` | Response text contains expected substring |
| `text-starts-with` | Response text starts with expected prefix |
| `text-not-empty` | Response text is non-empty |
| `valid-json` | Response text is valid JSON |
| `has-tool-request` | Response contains a tool request part |
| `valid-media` | Response contains a media part with valid URL |
| `reasoning` | Response contains a reasoning / thinking part |
| `stream-text-includes` | Streamed chunks contain expected text |
| `stream-has-tool-request` | Streamed chunks contain a tool request |
| `stream-valid-json` | Final streamed chunk is valid JSON |

New validators: decorate a function with `@register('name')`.

### YAML-Driven Test Specs

Each plugin defines its tests in a declarative YAML file:

```yaml
models:
  - name: "anthropic/claude-sonnet-4"
    supported_features: [text, json, tools, streaming, reasoning]
    tests:
      - name: "basic text generation"
        prompt: "Say 'hello' and nothing else"
        assertions:
          - type: text-includes
            value: hello

      - name: "streaming structured output"
        prompt: "Output a JSON object with a 'name' field"
        stream: true
        output:
          format: json
          schema: { "type": "object" }
        assertions:
          - type: stream-valid-json
```

### Full Feature Matrix

| Feature | Description |
|---------|-------------|
| **In-process Python runner** | Zero-overhead native execution — no subprocess, no HTTP |
| **Reflection runner** | Cross-runtime support via async HTTP (JS, Go) |
| **10 validators** | Ported 1:1 from canonical JS source |
| **YAML-driven specs** | Declarative test definitions per plugin |
| **Live progress table** | Rich terminal UI with real-time updates |
| **Concurrent execution** | Semaphore-bounded parallelism across plugins |
| **Pre-flight checks** | Validates specs, entry points, and env vars before running |
| **CI integration** | `check-plugin` runs in `bin/lint` on every PR |
| **Multi-runtime** | Python, JS, Go from a single command |
| **Rust-style diagnostics** | Unique error codes with actionable help messages |
| **TOML configuration** | Concurrency, env vars, runtime paths — all configurable |
| **Legacy CLI fallback** | `--use-cli` delegates to `genkit dev:test-model` |

---

## Architecture

```
conform check-model google-genai
        │
        ├── Auto-detect runtimes with entry points
        │   ├── python? ──→ InProcessRunner
        │   │       Import conformance_entry.py
        │   │       Call action.arun_raw() directly
        │   │       No subprocess · No HTTP · No reflection server
        │   │
        │   ├── js? ──→ ReflectionRunner
        │   │       Start conformance_entry.ts subprocess
        │   │       Async HTTP (httpx) → reflection API
        │   │
        │   └── go? ──→ ReflectionRunner (same as JS)
        │
        All runners share:
        ├── ActionRunner Protocol   ← common interface
        ├── Validators              ← 10 validators, Protocol + @register
        ├── Test cases              ← 12 built-in, 1:1 with JS
        └── Rich console output     ← live progress + summary table
```

### Layout

```
py/
├── tools/conform/                  ← The CLI tool
│   ├── pyproject.toml              ← Private package + [tool.conform] config
│   └── src/conform/
│       ├── cli.py                  ← Argument parsing + subcommand dispatch
│       ├── config.py               ← TOML config loader
│       ├── checker.py              ← check-plugin: verify conformance files
│       ├── display.py              ← Rich tables, Rust-style errors
│       ├── plugins.py              ← Plugin discovery + env-var checking
│       ├── reflection.py           ← Async HTTP client for reflection API
│       ├── util_test_model.py      ← Native test runner (ActionRunner)
│       ├── util_test_cases.py      ← 12 built-in test cases
│       ├── types.py                ← Shared types (PluginResult, Status)
│       └── validators/             ← Protocol-based validator registry
│           ├── __init__.py         ← Validator Protocol + @register
│           ├── json.py             ← valid-json
│           ├── streaming.py        ← stream-* validators
│           ├── text.py             ← text-* validators
│           └── tool.py             ← has-tool-request
│
└── tests/conform/                  ← Per-plugin conformance specs
    ├── anthropic/
    │   ├── model-conformance.yaml
    │   ├── conformance_entry.py
    │   ├── conformance_entry.ts
    │   └── conformance_entry.go
    ├── google-genai/
    ├── amazon-bedrock/
    ├── vertex-ai/
    └── ... (13 plugins total)
```

---

## Impact

| Metric | Before | After |
|--------|--------|-------|
| **Cross-plugin testing** | Manual spot-checks | 150+ automated tests |
| **Cross-runtime parity** | Not verified | Unified test suite |
| **Time to run all plugins** | Hours (manual) | < 4 minutes |
| **New plugin onboarding** | Write custom tests | Add YAML spec + entry point |
| **CI coverage** | Unit tests only | Unit + conformance on every PR |
| **Failure diagnosis** | Dig through logs | Rust-style errors with codes |
| **Validator extensibility** | N/A | `@register` decorator |

### CI Integration

1. **PR checks** (`bin/lint` → `conform check-plugin`) — verifies every
   model plugin has conformance specs and entry points.
2. **Conformance runs** (`conform check-model`) — full test suite
   against live APIs with real model calls.

---

## Try It

```bash
# List all plugins and their readiness
uv run --active conform list

# Run conformance tests for a single plugin
uv run --active conform check-model google-genai

# Run all plugins (Python runtime)
uv run --active conform check-model

# Run with verbose output
uv run --active conform check-model -v

# Filter to a specific runtime
uv run --active conform --runtime python check-model

# Verify all plugins have conformance specs (used by bin/lint)
uv run --active conform check-plugin
```

---

## Links

- **Source**: `py/tools/conform/`
- **Specs**: `py/tests/conform/`
- **Documentation**: `py/tools/conform/README.md`
- **Validators**: `py/tools/conform/src/conform/validators/`
