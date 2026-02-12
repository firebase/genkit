# Multi-Runtime Support

The `conform` tool is designed to test Genkit plugins across multiple
runtimes (Python, JavaScript, Go, Dart, Java, Rust).

## How it works

Each runtime has its own `[tool.conform.runtimes.<name>]` section in
`pyproject.toml` defining three things:

| Key | Purpose |
|-----|---------|
| `specs-dir` | Directory containing conformance specs |
| `plugins-dir` | Directory containing plugin source trees |
| `entry-command` | Command prefix to execute an entry point |

## Runtime configuration

```toml
[tool.conform.runtimes.python]
specs-dir = "py/tests/conform"
plugins-dir = "py/plugins"
entry-command = ["uv", "run", "--project", "py", "--active"]
```

## Using a different runtime

```bash
# Run Python conformance tests (default)
conform check-model --all

# Run JavaScript conformance tests
conform check-model --all --runtime js

# Run Go conformance tests
conform check-model --all --runtime go
```

## The Runtime Protocol

The runner depends on the `Runtime` Protocol, not any concrete class:

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

This means you can also create custom runtime implementations
programmatically without using TOML configuration.

## Adding a new runtime

1. Add a `[tool.conform.runtimes.<name>]` section to `pyproject.toml`:

    ```toml
    [tool.conform.runtimes.js]
    specs-dir = "js/tests/conform"
    plugins-dir = "js/plugins"
    entry-command = ["npx", "tsx"]
    ```

2. Create the spec directory structure:

    ```
    js/tests/conform/
    ├── <plugin>/
    │   ├── model-conformance.yaml
    │   └── conformance_entry.ts
    ```

3. Run tests:

    ```bash
    conform check-model --all --runtime js
    ```

!!! note "Current status"

    Only the Python runtime is fully configured. JS and Go sections
    are commented out in `pyproject.toml` as placeholders for future
    implementation.
