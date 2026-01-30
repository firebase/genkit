# Python Development Guidelines

## Code Quality & Linting

* **Run Linting**: Always run `./bin/lint` from the repo root (or `py/` directory
  semantics depending on the script) for all Python code changes.
  0 diagnostics should be reported.
* **Type Checkers**: Three type checkers are configured:

  * **ty** (Astral/Ruff) - Blocking, must pass with zero errors (full workspace)
  * **pyrefly** (Meta) - Blocking, must pass with zero errors (full workspace)
  * **pyright** (Microsoft) - Blocking, must pass with zero errors (runs on `packages/` only)

  Treat warnings as errors—do not ignore them. All three checkers run in `bin/lint`.

  **Full Coverage Required**: All type checkers must pass on the entire codebase including:

  * Core framework (`packages/genkit/`)
  * Plugins (`plugins/*/`)
  * Samples (`samples/*/`)
  * Tests (`**/tests/`, `**/*_test.py`)

  Do not exclude or ignore any part of the codebase from type checking.

  **ty configuration**: Module discovery is configured in `py/pyproject.toml` under
  `[tool.ty.environment]`. When adding new packages/plugins/samples, add their source
  paths to `environment.root`.

  **pyrefly and PEP 420 Namespace Packages**: The genkit plugins use PEP 420 namespace
  packages (`genkit.plugins.*`) where intermediate directories (`genkit/` and `genkit/plugins/`)
  don't have `__init__.py` files. This is intentional for allowing multiple packages to
  contribute to the same namespace. However, pyrefly can't resolve these imports statically.
  We configure `ignore-missing-imports = ["genkit.plugins.*"]` in `pyproject.toml` to suppress
  false positive import errors. At runtime, these imports work correctly because Python's
  import system handles PEP 420 namespace packages natively. This is the only acceptable
  import-related suppression.
* **Pass All Tests**: Ensure all unit tests pass (`uv run pytest .`).
* **Production Ready**: The objective is to produce production-grade code.
* **Shift Left**: Employ a "shift left" strategy—catch errors early.
* **Strict Typing**: Strict type checking is required. Do not use `Any` unless
  absolutely necessary and documented.
* **Error Suppression Policy**: Avoid ignoring warnings from the type checker
  (`# type: ignore`, `# pyrefly: ignore`, etc.) or other tools unless there is
  a compelling, documented reason.
  * **Try to fix first**: Before suppressing, try to rework the code to avoid the
    warning entirely. Use explicit type annotations, asserts for type narrowing,
    local variables to capture narrowed types in closures, or refactor the logic.
  * **Acceptable suppressions**: Only suppress when the warning is due to:
    * Type checker limitations (e.g., StrEnum narrowing, Self type compatibility)
    * External library type stub issues (e.g., uvicorn, OpenTelemetry)
    * Intentional design choices (e.g., Pydantic v1 compatibility, covariant overrides)
  * **Minimize surface area**: Suppress on the specific line, not globally in config.
  * **Always add a comment**: Explain why the suppression is needed.
  * **Be specific**: Use the exact error code (e.g., `# pyrefly: ignore[unexpected-keyword]`
    not just `# pyrefly: ignore`).
  * **Example**:
    ```python
    # pyrefly: ignore[unexpected-keyword] - Pydantic populate_by_name=True allows schema_
    schema_=options.output.json_schema if options.output else None,
    ```
* Move imports to the top of the file and avoid using imports inside function
  definitions.

## Generated Files & Data Model

* **Do Not Edit typing.py**: `py/packages/genkit/src/genkit/core/typing.py`
  is an auto-generated file. **DO NOT MODIFY IT DIRECTLY.**
* **Generator/Sanitizer**: Any necessary transformations to the core types must be
  applied to the generator script or the schema sanitizer.
* **Canonical Parity**: The data model MUST be identical to the JSON schema
  defined in the JavaScript (canonical) implementation.

## API & Behavior Parity

* **JS Canonical Conformance**: The Python implementation MUST be identical
  in API structure and runtime behavior to the JavaScript (canonical)
  implementation.

## Detailed Coding Guidelines

### Target Environment

* **Python Version**: Target Python 3.12 or newer.
* **Environment**: Use `uv` for packaging and environment management.

### Typing & Style

* **Syntax**:
  * Use `|` for union types instead of `Union`.
  * Use `| None` instead of `Optional`.
  * Use lowercase `list`, `dict` for type hints (avoid `List`, `Dict`).
  * Use modern generics (PEP 585, 695).
  * Use the `type` keyword for type aliases.
* **Imports**: Import types like `Callable`, `Awaitable` from `collections.abc`,
  not standard library `typing`.
* **Enums**: Use `StrEnum` instead of `(str, Enum)`.
* **Strictness**: Apply type hints strictly, including `-> None` for void functions.
* **Design**:
  * Code against interfaces, not implementations.
  * Use the adapter pattern for optional implementations.
* **Comments**:
  * Use proper punctuation.
  * Avoid comments explaining obvious code.
  * Use `TODO: Fix this later.` format for stubs.
  * **Do not add section marker comments** (e.g., `# ============` banners).
    Keep code clean and let structure speak for itself.
* Ensure that `bin/lint` passes without errors.

### Docstrings

* **Format**: Write comprehensive Google-style docstrings for modules, classes,
  and functions.
* **Content**:
  * **Explain Concepts**: Explain the terminology and concepts used in the
    code to someone unfamiliar with the code so that first timers can easily
    understand these ideas.
  * **Visuals**: Prefer using tabular format and ascii diagrams in the
    docstrings to break down complex concepts or list terminology.
* **Required Sections**:
  * **Overview**: One-liner description followed by rationale.
  * **Key Operations**: Purpose of the component.
  * **Args/Attributes**: Required for callables/classes.
  * **Returns**: Required for callables.
  * **Examples**: Required for user-facing API.
  * **Caveats**: Known limitations or edge cases.
* **References**:
  * Please use the descriptions from genkit.dev and
    github.com/genkit-ai/docsite as the source of truth for the API and
    concepts.
  * When you are not sure about the API or concepts, please refer to the
    JavaScript implementation for the same.
* Keep examples in documentation and docstrings simple.
* Add links to relevant documentation on the Web or elsewhere
  in the relevent places in docstrings.
* Add ASCII diagrams to illustrate relationships, flows, and concepts.
* Always update module docstrings and function docstrings when updating code
  to reflect updated reality of any file you add or modify.
* Scan documentation for every module you edit and keep it up-to-date.
* In sample code, always add instructions about testing the demo.

### Implementation

* Always add unit tests to improve coverage.
* When there is a conflict between the JavaScript implementation and the
  Python implementation, please refer to the JavaScript implementation for
  the same.
* When aiming to achieve parity the API and behavior should be identical to the
  JS canonical implementation.
* Always add/update samples to demonstrate the usage of the API or
  functionality.
* Use default input values for flows and actions to make them easier to use
  in the DevUI so that bug bashes can be faster and more effective.
* Support hot reloading in samples by using the `watchdog` library that
  exposes a `watchmedo` command line tool. See other samples for example.
  Since we want to reload examples when data files such as `.prompt` or `.pdf`
  or `.json` change, please include them in the watched patterns whenever
  required.
* Add a `run.sh` script to samples that can be used to run the sample.
  The script should also perform any setup required for the sample, such as
  installing dependencies or setting up environment variables.
* **IMPORTANT**: The `run.sh` script MUST use this exact command structure:

  ```bash
  genkit start -- \
    uv tool run --from watchdog watchmedo auto-restart \
      -d src \
      -d ../../packages \
      -d ../../plugins \
      -p '*.py;*.prompt;*.json' \
      -R \
      -- uv run src/main.py "$@"
  ```

  Key points:

  * `genkit start` must be OUTSIDE watchmedo (starts once and stays running)
  * watchmedo only restarts the Python script, NOT the genkit server
  * Use `uv tool run --from watchdog watchmedo` (not `uv run watchmedo`)
  * Watch `../../packages` and `../../plugins` to reload on core library changes
  * Use `-p '*.py;*.prompt;*.json'` pattern to watch relevant file types

  **Wrong** (causes continuous restart loop):

  ```bash
  uv run watchmedo auto-restart ... -- uv run genkit start -- python src/main.py
  ```
* Please keep the `README.md` file for each sample up to date with the `run.sh`
  script.
* In the samples, explain the whys, hows, and whats of the sample in the module
  docstring so the user learns more about the feature being demonstrated.
  Also explain how to test the sample.
* Prompt for API keys and other configuration required for the sample
  in Python.
* When creating shell scripts using bash, please use `#!/usr/bin/env bash` as
  the shebang line and `set -euo pipefail`.
* Avoid mentioning sample specific stuff in core framework or plugin code.
* Always check for missing dependencies in pyproject.toml for each sample
  and add them if we're using them.
* When working on model provider plugins such as Google Genai or Anthropic,
  ensure that model-spec.md is followed.
* Update the roadmap.md file as and when features are implemented.
* When a plugin such as a model provider is updated or changes, please also
  update relevant documentation and samples.
* Try to make running the sample flows a one-click operation by always defining
  default input values.
* **IMPORTANT**: For default values to appear in the Dev UI input fields, use
  a `pydantic.BaseModel` for flow input (preferred) or `Annotated` with
  `pydantic.Field`:

  **Preferred** (BaseModel - defaults always show in Dev UI):

  ```python
  from pydantic import BaseModel, Field

  class MyFlowInput(BaseModel):
      prompt: str = Field(default='Hello world', description='User prompt')

  @ai.flow()
  async def my_flow(input: MyFlowInput) -> str:
      return await ai.generate(prompt=input.prompt)
  ```

  **Alternative** (Annotated - may work for simple types):

  ```python
  from typing import Annotated
  from pydantic import Field

  @ai.flow()
  async def my_flow(
      prompt: Annotated[str, Field(default='Hello world')] = 'Hello world',
  ) -> str:
      ...
  ```

  **Wrong** (defaults won't show in Dev UI):

  ```python
  @ai.flow()
  async def my_flow(prompt: str = 'Hello world') -> str:
      ...
  ```

* **Rich Tracebacks**: Use `rich` for beautiful, Rust-like colored exception
  messages in samples. Add to imports and call after all imports:

  ```python
  from rich.traceback import install as install_rich_traceback

  # After all imports, before any code:
  install_rich_traceback(show_locals=True, width=120, extra_lines=3)
  ```

  Add `"rich>=13.0.0"` to the sample's `pyproject.toml` dependencies.

### Formatting

* **Tool**: Format code using `ruff` (or `bin/fmt`).
* **Line Length**: Max 120 characters.
* **Strings**: Wrap long lines and strings appropriately.
* **Config**: Refer to `.editorconfig` or `pyproject.toml` for rules.

### Testing

* **Framework**: Use `pytest` and `unittest`.
* **Scope**: Write comprehensive unit tests.
* **Documentation**: Add docstrings to test modules/functions explaining their scope.
* **Execution**: Run via `uv run pytest .`.
* **Porting**: Maintain 1:1 logic parity accurately if porting tests.
  Do not invent behavior.
* **Fixes**: Fix underlying code issues rather than special-casing tests.
* **Test File Naming**: Test files **MUST** have unique names across the entire
  repository to avoid pytest module collection conflicts. Use the format
  `{plugin_name}_{component}_test.py`:
  
  | Plugin | Test File | Status |
  |--------|-----------|--------|
  | `cloud-sql-pg` | `cloud_sql_pg_engine_test.py` | ✅ Correct |
  | `cloud-sql-pg` | `engine_test.py` | ❌ Wrong (conflicts with other plugins) |
  | `chroma` | `chroma_retriever_test.py` | ✅ Correct |
  | `checks` | `checks_evaluator_test.py` | ✅ Correct |
  
  **Requirements:**
  * Prefix test files with the plugin/package name, replacing any hyphens (`-`) with underscores (`_`).
  * Use the `foo_test.py` suffix format (not `test_foo.py`)
  * Do **NOT** add `__init__.py` to `tests/` directories (causes module conflicts)
  * Place tests in `plugins/{name}/tests/` or `packages/{name}/tests/`

### Logging

* **Library**: Use `structlog` for structured logging.
* **Async**: Use `await logger.ainfo(...)` within coroutines.
* **Format**: Avoid f-strings for async logging; use structured key-values.

### Licensing

Include the Apache 2.0 license header at the top of each file (update year as needed):

```python
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0
```

## Dependency Management

When updating dependencies for the Python SDK, ensure consistency across both files:

1. **`py/pyproject.toml`** - Workspace-level dependencies (pinned versions with `==`)
2. **`py/packages/genkit/pyproject.toml`** - Package-level dependencies (minimum versions with `>=`)

Both files must be updated together to avoid inconsistencies where developers test
against one version but users of the published `genkit` package might install a
different version.

After updating dependencies, regenerate the lock file:

```bash
# Run from the repository root
cd py && uv lock
```

## Git commit message guidelines

* Please draft a plain-text commit message after you're done with changes.
* Please do not include absolute file paths as links in commit messages.
* Since lines starting with `#` are treated as comments, please use a simpler
  format for headings.
* Add a rationale paragraph explaining the why and the what before listing
  all the changes.
* Please use conventional commits for the format.
* For scope, please refer to release-please configuration if available.
* Keep it short and simple.
