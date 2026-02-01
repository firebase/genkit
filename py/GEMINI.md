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
* **Import Placement**: All imports must be at the top of the file, outside any
  function definitions. This is a strict Python convention that ensures:
  * Predictable module loading behavior
  * Easier code review and maintenance
  * Proper type checking and tooling support

  **Correct (Top-Level Imports)**:

  ```python
  import asyncio
  import json
  import os
  import random
  import tempfile
  from collections.abc import Callable

  from pydantic import BaseModel, Field

  from genkit.types import Media, MediaPart, Part, TextPart


  async def main() -> None:
      """Entry point - uses imports from top of file."""
      await asyncio.Event().wait()


  def process_data(data: dict) -> str:
      """Uses json from top-level import."""
      return json.dumps(data)
  ```

  **Incorrect (In-Function Imports)**:

  ```python
  async def main() -> None:
      """WRONG: Import inside function."""
      import asyncio  # ❌ Should be at top of file

      await asyncio.Event().wait()


  def describe_image(url: str) -> Part:
      """WRONG: Import inside function."""
      from genkit.types import MediaPart  # ❌ Should be at top of file

      return MediaPart(media=Media(url=url))
  ```

  **Note**: There are NO legitimate use cases for in-function imports in this
  codebase. The only traditionally acceptable reasons (circular imports, optional
  dependencies, heavy import cost) do not apply here because:
  * Circular imports should be resolved through proper module design
  * All dependencies in this codebase are mandatory
  * Standard library imports are negligible cost

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
  * **ELI5 (Explain Like I'm 5)**: Include ELI5 documentation to help newcomers
    quickly understand what a module does without reading all the code.
    
    **Requirements by module type:**
    
    | Module Type | Concepts Table | Data Flow Diagram |
    |-------------|----------------|-------------------|
    | **Plugins** (`plugins/*/`) | Required | Required |
    | **Core packages** (`packages/*/`) | Required | Required for complex modules |
    | **Samples** (`samples/*/`) | Required | Only for complex samples* |
    
    *Complex samples include: RAG/vector search demos, multi-step pipelines,
    telemetry demos, tool interrupts, multi-server setups, etc.
    
    **1. Concepts Table** - Required for all modules:
    
    ```
    Key Concepts (ELI5)::
    
        ┌─────────────────────┬────────────────────────────────────────────────┐
        │ Concept             │ ELI5 Explanation                               │
        ├─────────────────────┼────────────────────────────────────────────────┤
        │ Span                │ A "timer" that records how long something      │
        │                     │ took. Like a stopwatch for one task.           │
        ├─────────────────────┼────────────────────────────────────────────────┤
        │ Trace               │ A collection of spans showing a request's      │
        │                     │ journey. Like breadcrumbs through your code.   │
        ├─────────────────────┼────────────────────────────────────────────────┤
        │ Exporter            │ Ships your traces somewhere (X-Ray, Jaeger).   │
        │                     │ Like a postal service for telemetry data.      │
        ├─────────────────────┼────────────────────────────────────────────────┤
        │ Propagator          │ Passes trace IDs between services. Like a      │
        │                     │ relay baton in a race.                         │
        ├─────────────────────┼────────────────────────────────────────────────┤
        │ Sampler             │ Decides which traces to keep. Like a bouncer   │
        │                     │ at a club deciding who gets in.                │
        └─────────────────────┴────────────────────────────────────────────────┘
    ```
    
    **2. Data Flow Diagram** - Required for plugins, optional for simple samples:
    
    ```
    Data Flow::
    
        User Request
             │
             ▼
        ┌─────────┐     ┌─────────┐     ┌─────────┐
        │ Flow A  │ ──▶ │ Model   │ ──▶ │ Tool    │
        │ (span)  │     │ (span)  │     │ (span)  │
        └─────────┘     └─────────┘     └─────────┘
             │               │               │
             └───────────────┼───────────────┘
                             ▼
                      ┌─────────────┐
                      │  Exporter   │  ──▶  AWS X-Ray / GCP Trace
                      └─────────────┘
    ```
    
    **Guidelines for ELI5 content:**
    * Use analogies from everyday life (mailman, bouncer, stopwatch, etc.)
    * Keep explanations to 1-2 lines per concept
    * Focus on the "what" and "why", not implementation details
    * Use box-drawing characters for professional appearance
    
* **Required Sections**:
  * **Overview**: One-liner description followed by rationale.
  * **Key Operations**: Purpose of the component.
  * **Args/Attributes**: Required for callables/classes.
  * **Returns**: Required for callables.
  * **Examples**: Required for user-facing API.
  * **Caveats**: Known limitations or edge cases.
  * **Implementation Notes & Edge Cases**: For complex modules (especially plugins),
    document implementation details that differ from typical patterns or other
    similar implementations. Explain both **why** the edge case exists and **what**
    the solution is.
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
* **Plugin Architecture Diagrams**: Every plugin MUST include an ASCII architecture
  diagram in its module docstring (typically in `__init__.py` or `typing.py`).
  This helps developers understand the plugin structure at a glance:

  ```
  ┌─────────────────────────────────────────────────────────────────────────┐
  │                         Plugin Name                                     │
  ├─────────────────────────────────────────────────────────────────────────┤
  │  Plugin Entry Point (__init__.py)                                       │
  │  ├── plugin_factory() - Plugin factory function                         │
  │  ├── Model References (model_a, model_b, ...)                           │
  │  └── Helper Functions (name_helper, config_helper, ...)                 │
  ├─────────────────────────────────────────────────────────────────────────┤
  │  typing.py - Type-Safe Configuration Classes                            │
  │  ├── BaseConfig (base configuration)                                    │
  │  ├── ProviderAConfig, ProviderBConfig, ...                              │
  │  └── Provider-specific enums and types                                  │
  ├─────────────────────────────────────────────────────────────────────────┤
  │  plugin.py - Plugin Implementation                                      │
  │  ├── PluginClass (registers models/embedders/tools)                     │
  │  └── Configuration and client initialization                            │
  ├─────────────────────────────────────────────────────────────────────────┤
  │  models/model.py - Model Implementation                                 │
  │  ├── ModelClass (API integration)                                       │
  │  ├── Request/response conversion                                        │
  │  └── Streaming support                                                  │
  ├─────────────────────────────────────────────────────────────────────────┤
  │  models/model_info.py - Model Registry (if applicable)                  │
  │  ├── SUPPORTED_MODELS                                                   │
  │  └── SUPPORTED_EMBEDDING_MODELS                                         │
  └─────────────────────────────────────────────────────────────────────────┘
  ```

  **Guidelines for architecture diagrams**:
  * Use box-drawing characters (`┌ ┐ └ ┘ ─ │ ├ ┤ ┬ ┴ ┼`) for clean appearance
  * Show file/module organization and their responsibilities
  * Highlight key classes, functions, and exports
  * Include model registries and configuration classes
  * Keep the diagram updated when plugin structure changes
* Always update module docstrings and function docstrings when updating code
  to reflect updated reality of any file you add or modify.
* Scan documentation for every module you edit and keep it up-to-date.
* In sample code, always add instructions about testing the demo.
* **Document Edge Cases in Module Docstrings**: When a module handles edge cases
  differently from typical patterns or other similar implementations, document
  these in a dedicated "Implementation Notes & Edge Cases" section. Include:
  * **Why** the edge case exists (API limitations, platform differences, etc.)
  * **What** the solution is (the implementation approach)
  * **Comparison** with how other similar systems handle it (if relevant)

  Example from the AWS Bedrock plugin module docstring:

  ```python
  """AWS Bedrock model implementation for Genkit.

  ...

  Implementation Notes & Edge Cases
  ---------------------------------

  **Media URL Fetching (Bedrock-Specific Requirement)**

  Unlike other AI providers (Anthropic, OpenAI, Google GenAI, xAI) that accept
  media URLs directly in their APIs and fetch the content server-side, AWS
  Bedrock's Converse API **only accepts inline bytes**.

  This means we must fetch media content client-side before sending to Bedrock::

      # Other providers (e.g., Anthropic):
      {'type': 'url', 'url': 'https://example.com/image.jpg'}  # API fetches it

      # AWS Bedrock requires:
      {'image': {'format': 'jpeg', 'source': {'bytes': b'...actual bytes...'}}}

  We use ``httpx.AsyncClient`` for true async HTTP requests. This approach:

  - Uses httpx which is already a genkit core dependency
  - True async I/O (no thread pool needed)
  - Doesn't block the event loop during network I/O

  **JSON Output Mode (Prompt Engineering)**

  The Bedrock Converse API doesn't have native JSON mode. When JSON output is
  requested, we inject instructions into the system prompt to guide the model.
  """
  ```

  This helps future maintainers understand non-obvious implementation choices
  and prevents accidental regressions when the code is modified.

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

* **Sample Media URLs**: When samples need to reference an image URL (e.g., for
  multimodal/vision demonstrations), use this public domain image from Wikimedia:

  ```
  https://upload.wikimedia.org/wikipedia/commons/1/13/Cute_kitten.jpg
  ```

  This ensures:
  * Consistent testing across all samples
  * No licensing concerns (public domain)
  * Reliable availability (Wikimedia infrastructure)
  * Known working URL that has been tested with various providers

* **Rich Tracebacks**: Use `rich` for beautiful, Rust-like colored exception
  messages in samples. Add to imports and call after all imports:

  ```python
  from rich.traceback import install as install_rich_traceback

  # After all imports, before any code:
  install_rich_traceback(show_locals=True, width=120, extra_lines=3)
  ```

  Add `"rich>=13.0.0"` to the sample's `pyproject.toml` dependencies.

### Avoiding Hardcoding

Avoid hardcoding region-specific values, URLs, or other configuration that varies by
deployment environment. This makes the code more portable and user-friendly globally.

* **Environment Variables First**: Always check environment variables before falling back
  to defaults. Prefer raising clear errors over silently using defaults that may not work
  for all users.

  ```python
  # Good: Clear error if not configured
  region = os.environ.get('AWS_REGION') or os.environ.get('AWS_DEFAULT_REGION')
  if region is None:
      raise ValueError('AWS region is required. Set AWS_REGION environment variable.')

  # Bad: Silent default that only works in US
  region = os.environ.get('AWS_REGION', 'us-east-1')
  ```

* **Named Constants**: Extract hardcoded values into named constants at module level.
  This makes them discoverable and documents their purpose.

  ```python
  # Good: Named constant with clear purpose
  DEFAULT_OLLAMA_SERVER_URL = 'http://127.0.0.1:11434'

  class OllamaPlugin:
      def __init__(self, server_url: str | None = None):
          self.server_url = server_url or DEFAULT_OLLAMA_SERVER_URL

  # Bad: Inline hardcoded value
  class OllamaPlugin:
      def __init__(self, server_url: str = 'http://127.0.0.1:11434'):
          ...
  ```

* **Region-Agnostic Helpers**: For cloud services with regional endpoints, provide helper
  functions that auto-detect the region instead of hardcoding a specific region.

  ```python
  # Good: Helper that detects region from environment
  def get_inference_profile_prefix(region: str | None = None) -> str:
      if region is None:
          region = os.environ.get('AWS_REGION')
      if region is None:
          raise ValueError('Region is required.')
      # Map region to prefix...

  # Bad: Hardcoded US default
  def get_inference_profile_prefix(region: str = 'us-east-1') -> str:
      ...
  ```

* **Documentation Examples**: In documentation and docstrings, use placeholder values
  that are clearly examples, not real values users might accidentally copy.

  ```python
  # Good: Clear placeholder
  endpoint='https://your-resource.openai.azure.com/'

  # Bad: Looks like it might work
  endpoint='https://eastus.api.example.com/'
  ```

* **What IS Acceptable to Hardcode**:
  * Official API endpoints that don't vary (e.g., `https://api.deepseek.com`)
  * Default ports for local services (e.g., `11434` for Ollama)
  * AWS/cloud service names (e.g., `'bedrock-runtime'`)
  * Factual values from documentation (e.g., embedding dimensions)

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

## Git Commit Message Guidelines

This project uses [Conventional Commits](https://www.conventionalcommits.org/) for
all commit messages. This enables automated changelog generation and semantic
versioning via release-please.

### Format

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Commit Types

| Type | Description | Example |
|------|-------------|---------|
| `feat` | New feature | `feat(py/plugins/aws): add X-Ray telemetry` |
| `fix` | Bug fix | `fix(py): resolve import order issue` |
| `docs` | Documentation only | `docs(py): update plugin README` |
| `style` | Code style (formatting) | `style(py): run ruff format` |
| `refactor` | Code refactoring | `refactor(py): extract helper function` |
| `perf` | Performance improvement | `perf(py): optimize model streaming` |
| `test` | Adding/updating tests | `test(py): add bedrock model tests` |
| `chore` | Maintenance tasks | `chore(py): update dependencies` |

### Scopes

For Python code, use these scopes:

| Scope | When to use |
|-------|-------------|
| `py` | General Python SDK changes |
| `py/plugins/<name>` | Specific plugin changes |
| `py/samples` | Sample application changes |
| `py/core` | Core framework changes |

### Breaking Changes

**IMPORTANT**: Use `!` after the type/scope to indicate breaking changes:

```
feat(py)!: rename generate() to invoke()

BREAKING CHANGE: The `generate()` method has been renamed to `invoke()`.
Existing code using `ai.generate()` must be updated to `ai.invoke()`.
```

Or in the footer:

```
refactor(py): restructure plugin API

BREAKING CHANGE: Plugin initialization now requires explicit configuration.
```

### Guidelines

* Draft a plain-text commit message after you're done with changes.
* Do not include absolute file paths as links in commit messages.
* Since lines starting with `#` are treated as comments, use a simpler format.
* Add a rationale paragraph explaining the **why** and the **what** before
  listing all the changes.
* For scope, refer to release-please configuration if available.
* Keep the subject line short and simple.

## Pull Request Description Guidelines

All Python PRs must include comprehensive descriptions following these standards.
Well-documented PRs enable faster reviews and better knowledge transfer.

### Required Sections

Every PR description MUST include:

1. **Summary** - One-paragraph overview of what the PR does and why
2. **Changes** - Bullet list of specific modifications
3. **Test Plan** - How the changes were verified

### Prefer Tables for Information

Use markdown tables whenever presenting structured information such as:
- Configuration options and their defaults
- API parameter lists
- Comparison of before/after behavior
- File changes summary

Tables are easier to scan and review than prose or bullet lists.

### Architecture Diagrams

For PRs that add new plugins or modify system architecture, include ASCII diagrams:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    PLUGIN ARCHITECTURE                                  │
│                                                                         │
│    Your Genkit App                                                      │
│         │                                                               │
│         │  (1) Initialize Plugin                                        │
│         ▼                                                               │
│    ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐  │
│    │  PluginClass    │────▶│  Provider       │────▶│  SpanProcessor  │  │
│    │  (Manager)      │     │  (Config)       │     │  (Export)       │  │
│    └─────────────────┘     └─────────────────┘     └────────┬────────┘  │
│                                                              │          │
│                            (2) Process data                  │          │
│                                                              ▼          │
│    ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐  │
│    │  Logger         │────▶│  Trace ID       │────▶│  HTTP/OTLP      │  │
│    │  (Structured)   │     │  Injection      │     │  (Auth)         │  │
│    └─────────────────┘     └─────────────────┘     └────────┬────────┘  │
│                                                              │          │
│                            (3) Export to backend             │          │
│                                                              ▼          │
│                                                    ┌─────────────────┐  │
│                                                    │   Cloud Service │  │
│                                                    │   (X-Ray, etc.) │  │
│                                                    └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

### Data Flow Diagrams

For PRs involving data processing or multi-step operations:

```
Data Flow::

    User Request
         │
         ▼
    ┌─────────┐     ┌─────────┐     ┌─────────┐
    │ Flow    │ ──▶ │ Model   │ ──▶ │ Tool    │
    │ (span)  │     │ (span)  │     │ (span)  │
    └─────────┘     └─────────┘     └─────────┘
         │               │               │
         └───────────────┼───────────────┘
                         ▼
                  ┌─────────────┐
                  │  Exporter   │  ──▶  Cloud Backend
                  └─────────────┘
```

### PR Template Examples

**Feature PR (New Plugin)**:

```markdown
## Summary

This PR introduces the **AWS Telemetry Plugin** (`py/plugins/aws/`) for exporting
Genkit telemetry to AWS X-Ray and CloudWatch.

### Plugin Features

- **AWS X-Ray Integration**: Distributed tracing with automatic trace ID generation
- **CloudWatch Logs**: Structured logging with X-Ray trace correlation
- **SigV4 Authentication**: Secure OTLP export using AWS credentials

[Architecture diagram here]

## Changes

### New Files
- `py/plugins/aws/` - Complete AWS telemetry plugin with tests
- `py/samples/aws-hello/` - Sample demonstrating AWS telemetry

### Updated Files
- `py/GEMINI.md` - Documentation requirements
- All plugin `__init__.py` files - Added ELI5 concepts tables

## Test Plan

- [x] All existing tests pass (`bin/lint`)
- [x] New plugin tests pass (`py/plugins/aws/tests/aws_telemetry_test.py`)
- [ ] Manual testing with AWS credentials
```

**Fix/Refactor PR**:

```markdown
## Summary

Clean up in-function imports to follow PEP 8 conventions. Moves all imports
to the top of files for better code quality and tooling support.

## Rationale

Python's PEP 8 style guide recommends placing all imports at the top of the
module. In-function imports can:
- Make dependencies harder to discover
- Cause subtle performance issues from repeated import lookups
- Reduce code readability and tooling support

## Changes

### Plugins
- **aws-bedrock**: Cleaned up `plugin.py` imports
- **google-cloud**: Cleaned up `telemetry/metrics.py` imports

### Samples
Moved in-function imports to top of file:
- **anthropic-hello**: `random`, `genkit.types` imports
- **aws-bedrock-hello**: `asyncio`, `random`, `genkit.types` imports
- [additional samples...]

## Test Plan

- [x] `bin/lint` passes locally
- [x] No functional behavior changes (import reorganization only)
```

### Documentation PR

```markdown
## Summary

This PR adds comprehensive planning documentation for [Topic] and updates
plugin categorization guides.

## Changes

### New Planning Documents (engdoc/planning/)
- **FILE_NAME.md** - Description of integration plan
- **ROADMAP.md** - Status and effort metrics

### Updated Documentation
- **py/plugins/README.md** - Updated categorization guide

## Test Plan

- [x] Documentation integrity check
- [x] All relative links verified
- [x] Markdown linting passes
```

### Checklist Requirements

Every PR should address:

- [ ] **Code Quality**: `bin/lint` passes with zero errors
- [ ] **Type Safety**: All type checkers pass (ty, pyrefly, pyright)
- [ ] **Tests**: Unit tests added/updated as needed
- [ ] **Documentation**: Docstrings and README files updated
- [ ] **Samples**: Demo code updated if applicable
