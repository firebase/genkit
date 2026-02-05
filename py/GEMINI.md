# Python Development Guidelines

## Code Quality & Linting

* **MANDATORY: Pass `bin/lint`**: Before submitting any PR, you MUST run `./bin/lint`
  from the repo root and ensure it passes with 0 errors. This is a hard requirement.
  PRs with lint failures will not be accepted. The lint script runs:

  * Ruff (formatting and linting)
  * Ty, Pyrefly, Pyright (type checking)
  * PySentry (security vulnerability scanning)
  * License checks (`bin/check_license`)
  * Consistency checks (`py/bin/check_consistency`)

  **Automated Consistency Checks** (`py/bin/check_consistency`):

  | Check | Description | Status |
  |-------|-------------|--------|
  | Python version | All packages use `requires-python = ">=3.10"` | ✅ Automated |
  | Plugin version sync | All plugin versions match core framework | ✅ Automated |
  | Package naming | Directory names match package names | ✅ Automated |
  | Workspace completeness | All packages in `[tool.uv.sources]` | ✅ Automated |
  | Test file naming | Files use `*_test.py` format | ✅ Automated |
  | README files | Plugins and samples have README.md | ✅ Automated |
  | LICENSE files | Publishable packages have LICENSE | ✅ Automated |
  | py.typed markers | PEP 561 type hint markers exist | ✅ Automated |
  | Dependency resolution | `uv pip check` passes | ✅ Automated |
  | In-function imports | Imports at top of file | ✅ Automated (warning) |
  | Required metadata | pyproject.toml has required fields | ✅ Automated |
  | Sample run.sh | Samples have run.sh scripts | ✅ Automated |
  | Hardcoded secrets | No API keys in source code | ✅ Automated |
  | Typos | No spelling errors (via `typos` tool) | ✅ Automated |
  | `__all__` exports | Main package has `__all__` for IDE | ✅ Automated |
  | Broad type ignores | No `# type: ignore` without codes | ✅ Automated |
  | Python classifiers | All packages have 3.10-3.14 classifiers | ✅ Automated |
  | Namespace `__init__.py` | Plugins must not have `__init__.py` in `genkit/` or `genkit/plugins/` | ✅ Automated |

  **Release Checks** (`py/bin/release_check`):

  | Check | Description | Status |
  |-------|-------------|--------|
  | Package metadata | All required pyproject.toml fields | ✅ Automated |
  | Build verification | Packages build successfully | ✅ Automated |
  | Wheel contents | py.typed and LICENSE in wheels | ✅ Automated |
  | Twine check | Package metadata valid for PyPI | ✅ Automated |
  | Dependency issues | deptry check for missing deps | ✅ Automated |
  | Type checking | ty, pyrefly, pyright pass | ✅ Automated |
  | Code formatting | ruff format check | ✅ Automated |
  | Linting | ruff check | ✅ Automated |
  | Typos | Spelling errors | ✅ Automated |
  | Unit tests | pytest passes | ✅ Automated |
  | Security scan | bandit/pip-audit | ✅ Automated |
  | Hardcoded secrets | No API keys in code | ✅ Automated |
  | License headers | Apache 2.0 headers present | ✅ Automated |
  | Dependency licenses | liccheck passes | ✅ Automated |
  | CHANGELOG | Current version documented | ✅ Automated |
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
* **Tests Required**: All new code MUST have accompanying tests. No exceptions.
  PRs without tests for new functionality will not be accepted.
* **Workspace Completeness**: All plugins and samples MUST be included in
  `py/pyproject.toml` under `[tool.uv.sources]`. When adding a new plugin or
  sample, add it to the sources section to ensure it's properly installed in
  the workspace. **This is automatically checked by `py/bin/check_consistency`.**
  Verify with `uv sync` that all packages resolve correctly.
* **Naming Consistency**: Package names MUST match their directory names.
  **This is automatically checked by `py/bin/check_consistency`.**
  * Plugins: `plugins/{name}/` → package name `genkit-plugin-{name}`
  * Samples: `samples/{name}/` → package name `{name}`
  * Use hyphens (`-`) not underscores (`_`) in package names
  * Manual verification:
    ```bash
    # Check plugins
    for d in plugins/*/; do
      name=$(basename "$d")
      pkg=$(grep '^name = ' "$d/pyproject.toml" | cut -d'"' -f2)
      [ "$pkg" != "genkit-plugin-$name" ] && echo "MISMATCH: $d -> $pkg"
    done
    # Check samples
    for d in samples/*/; do
      name=$(basename "$d")
      pkg=$(grep '^name = ' "$d/pyproject.toml" | cut -d'"' -f2)
      [ "$pkg" != "$name" ] && echo "MISMATCH: $d -> $pkg"
    done
    ```
* **Dependency Verification**: All dependencies must resolve correctly. Run these
  checks before submitting PRs:
  ```bash
  # Sync workspace and verify all packages install
  uv sync

  # Check for missing or incompatible dependencies
  uv pip check

  # Verify license compliance
  ./bin/check_license
  ```
  **Dependency Best Practices**:
  * Add dependencies directly to the package that uses them, not transitively
  * Each plugin's `pyproject.toml` should list all packages it imports
  * Use version constraints (e.g., `>=1.0.0`) to allow flexibility
  * Pin exact versions only when necessary for compatibility
  * Remove unused dependencies to keep packages lean
* **Python Version Consistency**: All packages MUST use the same `requires-python`
  version. Currently, all packages should specify `requires-python = ">=3.10"`.
  **This is automatically checked by `py/bin/check_consistency`.**
  Manual verification:
  ```bash
  # Check all pyproject.toml files have consistent Python version
  expected=">=3.10"
  for f in packages/*/pyproject.toml plugins/*/pyproject.toml samples/*/pyproject.toml; do
    version=$(grep 'requires-python' "$f" | cut -d'"' -f2)
    if [ "$version" != "$expected" ]; then
      echo "MISMATCH: $f has '$version' (expected '$expected')"
    fi
  done
  ```
  **Note**: The `.python-version` file specifies `3.12` for local development, but
  CI tests against Python 3.10, 3.11, 3.12, 3.13, and 3.14. Scripts using `uv run`
  should use `--active` flag to respect the CI matrix Python version.
* **Plugin Version Sync**: All plugin versions should stay in sync with the core
  framework version. When releasing, update all plugin versions together.
  **This is automatically checked by `py/bin/check_consistency`.**
  Manual verification:
  ```bash
  # Get core framework version
  core_version=$(grep '^version = ' packages/genkit/pyproject.toml | cut -d'"' -f2)
  echo "Core version: $core_version"

  # Check all plugins have the same version
  for f in plugins/*/pyproject.toml; do
    plugin_version=$(grep '^version = ' "$f" | cut -d'"' -f2)
    plugin_name=$(grep '^name = ' "$f" | cut -d'"' -f2)
    if [ "$plugin_version" != "$core_version" ]; then
      echo "MISMATCH: $plugin_name has version '$plugin_version' (expected '$core_version')"
    fi
  done
  ```
  **Version Policy**:
  * Core framework and all plugins share the same version number
  * Samples can have independent versions (typically `0.1.0`)
  * Use semantic versioning (MAJOR.MINOR.PATCH)
  * Bump versions together during releases
* **Production Ready**: The objective is to produce production-grade code.
* **Shift Left**: Employ a "shift left" strategy—catch errors early.
* **Strict Typing**: Strict type checking is required. Do not use `Any` unless
  absolutely necessary and documented.
* **Security & Async Best Practices**: Ruff is configured with security (S), async (ASYNC),
  and print (T20) rules. These catch common production issues:

  * **S rules (Bandit)**: SQL injection, hardcoded secrets, insecure hashing, etc.
  * **ASYNC rules**: Blocking calls in async functions (use `httpx.AsyncClient` not
    `urllib.request`, use `aiofiles` not `open()` in async code)
  * **T20 rules**: No `print()` statements in production code (use `logging` or `structlog`)

  **Async I/O Best Practices**:

  * Use `httpx.AsyncClient` for HTTP requests in async functions
  * Use `aiofiles` for file I/O in async functions
  * Never use blocking `urllib.request`, `requests`, or `open()` in async code
  * If you must use blocking I/O, run it in a thread with `anyio.to_thread.run_sync()`

  **Example - Async HTTP**:

  ```python
  # WRONG - blocks the event loop
  async def fetch_data(url: str) -> bytes:
      with urllib.request.urlopen(url) as response:  # ❌ Blocking!
          return response.read()

  # CORRECT - non-blocking
  async def fetch_data(url: str) -> bytes:
      async with httpx.AsyncClient() as client:
          response = await client.get(url)
          return response.content
  ```

  **Example - Async File I/O**:

  ```python
  # WRONG - blocks the event loop
  async def read_file(path: str) -> str:
      with open(path) as f:  # ❌ Blocking!
          return f.read()

  # CORRECT - non-blocking
  async def read_file(path: str) -> str:
      async with aiofiles.open(path, encoding='utf-8') as f:
          return await f.read()
  ```

  **CRITICAL: Per-Event-Loop HTTP Client Caching**:

  When making multiple HTTP requests in async code, **do NOT create a new
  `httpx.AsyncClient` for every request**. This has two problems:

  1. **Performance overhead**: Each new client requires connection setup, SSL
     handshake, etc.
  2. **Event loop binding**: `httpx.AsyncClient` instances are bound to the
     event loop they were created in. Reusing a client across different event
     loops causes "bound to different event loop" errors.

  **Use the shared `get_cached_client()` utility** from `genkit.core.http_client`:

  ```python
  from genkit.core.http_client import get_cached_client

  # WRONG - creates new client per request (connection overhead)
  async def call_api(url: str) -> dict:
      async with httpx.AsyncClient() as client:
          response = await client.get(url)
          return response.json()

  # WRONG - stores client at init time (event loop binding issues)
  class MyPlugin:
      def __init__(self):
          self._client = httpx.AsyncClient()  # ❌ Bound to current event loop!

      async def call_api(self, url: str) -> dict:
          response = await self._client.get(url)  # May fail in different loop
          return response.json()

  # CORRECT - uses per-event-loop cached client
  async def call_api(url: str, token: str) -> dict:
      # For APIs with expiring tokens, pass auth headers per-request
      client = get_cached_client(
          cache_key='my-api',
          timeout=60.0,
      )
      response = await client.get(url, headers={'Authorization': f'Bearer {token}'})
      return response.json()

  # CORRECT - for static auth (API keys that don't expire)
  async def call_api_static_auth(url: str) -> dict:
      client = get_cached_client(
          cache_key='my-plugin/api',
          headers={
              'Authorization': f'Bearer {API_KEY}',
              'Content-Type': 'application/json',
          },
          timeout=60.0,
      )
      response = await client.get(url)
      return response.json()
  ```

  **Key patterns**:

  * **Use unique `cache_key`** for each distinct client configuration (e.g.,
    `'vertex-ai-reranker'`, `'cloudflare-workers-ai/account123'`)
  * **Pass expiring auth per-request**: For Google Cloud, Azure, etc. where
    tokens expire, pass auth headers in the request, not in `get_cached_client()`
  * **Static auth in client**: For Cloudflare, OpenAI, etc. where API keys
    don't expire, include auth headers in `get_cached_client()`
  * **WeakKeyDictionary cleanup**: The cache automatically cleans up clients
    when their event loop is garbage collected
* **Error Suppression Policy**: Avoid ignoring warnings from the type checker
  (`# type: ignore`, `# pyrefly: ignore`, etc.) or linter (`# noqa`) unless there is
  a compelling, documented reason.
  * **Try to fix first**: Before suppressing, try to rework the code to avoid the
    warning entirely. Use explicit type annotations, asserts for type narrowing,
    local variables to capture narrowed types in closures, or refactor the logic.
  * **Acceptable suppressions**: Only suppress when the warning is due to:
    * Type checker limitations (e.g., StrEnum narrowing, Self type compatibility)
    * External library type stub issues (e.g., uvicorn, OpenTelemetry)
    * Intentional design choices (e.g., Pydantic v1 compatibility, covariant overrides)
    * False positives (e.g., `S105` for enum values that look like passwords)
    * Intentional behavior (e.g., `S110` for silent exception handling in parsers)
  * **Minimize surface area**: Suppress on the specific line, not globally in config.
    **NEVER use per-file-ignores for security rules** - always use line-level `# noqa`.
  * **Always add a comment**: Explain why the suppression is needed.
  * **Be specific**: Use the exact error code (e.g., `# noqa: S105 - enum value, not a password`
    not just `# noqa`).
  * **Examples**:
    ```python
    # Type checker suppression
    # pyrefly: ignore[unexpected-keyword] - Pydantic populate_by_name=True allows schema_
    schema_=options.output.json_schema if options.output else None,

    # Security false positive - enum value looks like password
    PASS_ = 'PASS'  # noqa: S105 - enum value, not a password

    # Intentional silent exception handling
    except Exception:  # noqa: S110 - intentionally silent, parsing partial JSON
        pass

    # Print in atexit handler where logger is unavailable
    print(f'Removing file: {path}')  # noqa: T201 - atexit handler, logger unavailable
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
    | **Samples** (`samples/*/`) | Required | Only for complex samples\* |

    \*Complex samples include: RAG/vector search demos, multi-step pipelines,
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

* **Sample Entry Points**: All samples MUST use `ai.run_main()` to start
  the Genkit server and enable the DevUI. This is the only supported way
  to run samples:

  ```python
  import asyncio

  async def main():
    # ...
    await asyncio.Event().wait()

  # At the bottom of main.py
  if __name__ == '__main__':

      ai.run_main(main())
  ```

  This pattern ensures:

  * The DevUI starts at http://localhost:4000
  * Hot reloading works correctly with watchmedo
  * Flows are properly registered with the reflection API

### Plugin Development

When developing Genkit plugins, follow these additional guidelines:

* **Environment Variable Naming**: Use the **provider's official environment
  variable names** wherever they exist. This makes the plugin feel native
  to users already familiar with the provider's tooling.

  **CRITICAL**: Before implementing any plugin, research the provider's official
  documentation to find their standard environment variable names. Using the
  exact same names ensures:

  * Users can reuse existing credentials without reconfiguration
  * Documentation and tutorials from the provider work seamlessly
  * The plugin integrates naturally with the provider's ecosystem

  **Official Environment Variables by Provider**:

  | Provider | Official Env Vars | Source Documentation |
  |----------|-------------------|---------------------|
  | **AWS** | `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION` | [AWS SDK Environment Variables](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-envvars.html) |
  | **Google Cloud** | `GOOGLE_CLOUD_PROJECT`, `GOOGLE_APPLICATION_CREDENTIALS`, `GCLOUD_PROJECT` | [GCP Application Default Credentials](https://cloud.google.com/docs/authentication/application-default-credentials) |
  | **Azure** | `APPLICATIONINSIGHTS_CONNECTION_STRING`, `AZURE_TENANT_ID`, `AZURE_CLIENT_ID` | [Azure Monitor OpenTelemetry](https://learn.microsoft.com/azure/azure-monitor/app/opentelemetry-configuration) |
  | **OpenAI** | `OPENAI_API_KEY`, `OPENAI_ORG_ID` | [OpenAI API Reference](https://platform.openai.com/docs/api-reference/authentication) |
  | **Anthropic** | `ANTHROPIC_API_KEY` | [Anthropic API Reference](https://docs.anthropic.com/en/api/getting-started) |
  | **Cloudflare** | `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN` | [Cloudflare API Tokens](https://developers.cloudflare.com/fundamentals/api/get-started/create-token/) |
  | **Sentry** | `SENTRY_DSN`, `SENTRY_ENVIRONMENT`, `SENTRY_RELEASE` | [Sentry Configuration Options](https://docs.sentry.io/platforms/python/configuration/options/) |
  | **Honeycomb** | `HONEYCOMB_API_KEY`, `HONEYCOMB_DATASET`, `HONEYCOMB_API_ENDPOINT` | [Honeycomb API Keys](https://docs.honeycomb.io/configure/environments/manage-api-keys/) |
  | **Datadog** | `DD_API_KEY`, `DD_SITE`, `DD_APP_KEY` | [Datadog Agent Environment Variables](https://docs.datadoghq.com/agent/guide/environment-variables/) |
  | **Axiom** | `AXIOM_TOKEN`, `AXIOM_DATASET`, `AXIOM_ORG_ID` | [Axiom API Tokens](https://axiom.co/docs/reference/tokens) |
  | **Grafana Cloud** | `GRAFANA_OTLP_ENDPOINT`, `GRAFANA_USER_ID`, `GRAFANA_API_KEY`\* | [Grafana Cloud OTLP](https://grafana.com/docs/grafana-cloud/monitor-applications/application-observability/setup/collector/opentelemetry-collector/) |
  | **OpenTelemetry** | `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_HEADERS`, `OTEL_SERVICE_NAME` | [OTel SDK Environment Variables](https://opentelemetry.io/docs/specs/otel/configuration/sdk-environment-variables/) |
  | **Mistral AI** | `MISTRAL_API_KEY` | [Mistral AI Clients](https://docs.mistral.ai/getting-started/clients/) |
  | **Hugging Face** | `HF_TOKEN`, `HF_HOME` | [Hugging Face Hub Documentation](https://huggingface.co/docs/huggingface_hub/en/package_reference/environment_variables) |
  | **xAI** | `XAI_API_KEY` | [xAI API Documentation](https://docs.x.ai/api) |
  | **DeepSeek** | `DEEPSEEK_API_KEY` | [DeepSeek API Documentation](https://api-docs.deepseek.com/) |
  | **OpenRouter** | `OPENROUTER_API_KEY` | [OpenRouter API Keys](https://openrouter.ai/docs/api-keys) |

  \*Grafana Cloud uses standard OTel env vars with Basic auth. The `GRAFANA_*` vars are
  Genkit-specific for convenience. The plugin encodes `GRAFANA_USER_ID:GRAFANA_API_KEY`
  as Base64 for the `Authorization: Basic` header.

  **When to Create Custom Environment Variables**:

  Only create custom env vars when the provider doesn't have an official
  standard for that specific configuration. When you must create custom vars:

  1. Use a consistent prefix (e.g., `GENKIT_`, `CF_` for Cloudflare-specific)
  2. Document clearly that this is a Genkit-specific variable
  3. Follow the naming pattern: `PREFIX_RESOURCE_ATTRIBUTE`
     * Example: `CF_OTLP_ENDPOINT` (Cloudflare OTLP endpoint, not standard CF var)

  **Verification Checklist**:

  * \[ ] Searched provider's official documentation for env var names
  * \[ ] Verified env var names match exactly (case-sensitive)
  * \[ ] Documented the source URL for each env var in code comments
  * \[ ] Tested that existing provider credentials work without changes

* **Model Configuration Parameters**: Support **exhaustive model configuration**
  so users can access all provider-specific features through the DevUI:

  1. **Research provider documentation**: Before implementing a model plugin,
     thoroughly review the provider's API documentation to enumerate ALL
     available parameters.

  2. **Support all generation parameters**: Include every parameter the model
     supports, not just common ones like temperature and max\_tokens:

     ```python
     # Good: Exhaustive model config (Anthropic example)
     class AnthropicModelConfig(BaseModel):
         temperature: float | None = None
         max_tokens: int | None = None
         top_p: float | None = None
         top_k: int | None = None
         stop_sequences: list[str] | None = None
         # Provider-specific parameters
         thinking: ThinkingConfig | None = None  # Extended thinking
         system: str | None = None  # System prompt override
         metadata: dict[str, Any] | None = None  # Request metadata

     # Bad: Only basic parameters
     class AnthropicModelConfig(BaseModel):
         temperature: float | None = None
         max_tokens: int | None = None
     ```

  3. **Document provider-specific features**: Add docstrings explaining
     provider-specific parameters that may not be self-explanatory:

     ```python
     class BedrockModelConfig(BaseModel):
         """AWS Bedrock model configuration.

         Attributes:
             guardrailIdentifier: ID of a Bedrock Guardrail to apply.
             guardrailVersion: Version of the guardrail (default: "DRAFT").
             performanceConfig: Controls latency optimization settings.
         """
         guardrailIdentifier: str | None = None
         guardrailVersion: str | None = None
         performanceConfig: PerformanceConfiguration | None = None
     ```

  4. **Maintain a model capability registry**: For plugins with multiple models,
     track which features each model supports:

     ```python
     SUPPORTED_MODELS: dict[str, ModelInfo] = {
         'claude-3-5-sonnet': ModelInfo(
             supports=Supports(
                 multiturn=True,
                 tools=True,
                 media=True,
                 systemRole=True,
                 output=['text', 'json'],
             ),
             max_output_tokens=8192,
         ),
     }
     ```

* **Telemetry Plugin Conventions**: For telemetry/observability plugins:

  1. **Entry point function naming**: Use `add_<provider>_telemetry()`:
     * `add_aws_telemetry()`
     * `add_azure_telemetry()`
     * `add_cf_telemetry()`

  2. **PII redaction default**: Always default to redacting model inputs/outputs:
     ```python
     def add_azure_telemetry(
         log_input_and_output: bool = False,  # Safe default
     ) -> None:
     ```

  3. **Environment resolution order**: Check parameters first, then env vars:
     ```python
     def _resolve_connection_string(conn_str: str | None = None) -> str | None:
         if conn_str:
             return conn_str
         return os.environ.get('APPLICATIONINSIGHTS_CONNECTION_STRING')
     ```

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

### Packaging (PEP 420 Namespace Packages)

Genkit plugins use **PEP 420 implicit namespace packages** to allow multiple packages
to contribute to the `genkit.plugins.*` namespace. This requires special care in
build configuration.

#### Directory Structure

```
plugins/
├── anthropic/
│   ├── pyproject.toml
│   └── src/
│       └── genkit/               # NO __init__.py (namespace)
│           └── plugins/          # NO __init__.py (namespace)
│               └── anthropic/    # HAS __init__.py (regular package)
│                   ├── __init__.py
│                   ├── models.py
│                   └── py.typed
```

**CRITICAL**: The `genkit/` and `genkit/plugins/` directories must NOT have
`__init__.py` files. Only the final plugin directory (e.g., `anthropic/`) should
have `__init__.py`.

#### Hatch Wheel Configuration

For PEP 420 namespace packages, use `only-include` to specify exactly which
directory to package:

```toml
[build-system]
build-backend = "hatchling.build"
requires      = ["hatchling"]

[tool.hatch.build.targets.wheel]
only-include = ["src/genkit/plugins/<plugin_name>"]
sources = ["src"]
```

**Why `sources = ["src"]` is Required:**

The `sources` key tells hatch to rewrite paths by stripping the `src/` directory prefix.
Without it, the wheel would have paths like `src/genkit/plugins/...` instead of
`genkit/plugins/...`, which would break Python imports at runtime.

| With `sources = ["src"]` | Without `sources` |
|--------------------------|-------------------|
| ✅ `genkit/plugins/anthropic/__init__.py` | ❌ `src/genkit/plugins/anthropic/__init__.py` |
| `from genkit.plugins.anthropic import ...` works | Import fails |

**Why `only-include` instead of `packages`:**

Using `packages = ["src/genkit", "src/genkit/plugins"]` causes hatch to traverse
both paths, including the same files twice. This creates wheels with duplicate
entries that PyPI rejects with:

```
400 Invalid distribution file. ZIP archive not accepted: 
Duplicate filename in local headers.
```

**Configuration Examples:**

| Plugin Directory | `only-include` Value |
|------------------|---------------------|
| `plugins/anthropic/` | `["src/genkit/plugins/anthropic"]` |
| `plugins/google-genai/` | `["src/genkit/plugins/google_genai"]` |
| `plugins/vertex-ai/` | `["src/genkit/plugins/vertex_ai"]` |
| `plugins/amazon-bedrock/` | `["src/genkit/plugins/amazon_bedrock"]` |

Note: Internal Python directory names use underscores (`google_genai`), while
the plugin directory uses hyphens (`google-genai`).

#### Verifying Wheel Contents

Always verify wheels don't have duplicates before publishing:

```bash
# Build the package
uv build --package genkit-plugin-<name>

# Check for duplicates (should show each file only once)
unzip -l dist/genkit_plugin_*-py3-none-any.whl

# Look for duplicate warnings during build
# BAD: "UserWarning: Duplicate name: 'genkit/plugins/...'"
# GOOD: No warnings, clean build
```

#### Common Build Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Duplicate filename in local headers` | Files included twice in wheel | Use `only-include` instead of `packages` |
| Empty wheel (no Python files) | Wrong `only-include` path | Verify path matches actual directory structure |
| `ModuleNotFoundError` at runtime | Missing `__init__.py` in plugin dir | Add `__init__.py` to the final plugin directory |

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

### Test Coverage

**All new code must have test coverage.** Tests are essential for maintaining code
quality, preventing regressions, and enabling confident refactoring.

#### Coverage Requirements

| Component Type | Minimum Coverage | Notes |
|----------------|------------------|-------|
| **Core packages** | 80%+ | Critical path code |
| **Plugins** | 70%+ | Model/embedder/telemetry plugins |
| **Utilities** | 90%+ | Helper functions, converters |
| **New features** | 100% of new lines | All new code paths tested |

#### Running Coverage

```bash
# Run tests with coverage report
cd py
uv run pytest --cov=packages --cov=plugins --cov-report=term-missing

# Generate HTML coverage report
uv run pytest --cov=packages --cov=plugins --cov-report=html
# Open htmlcov/index.html in browser

# Check coverage for a specific plugin
uv run pytest plugins/mistral/tests/ --cov=plugins/mistral/src --cov-report=term-missing
```

#### What to Test

1. **Happy Path**: Normal operation with valid inputs
2. **Edge Cases**: Empty inputs, boundary values, None handling
3. **Error Handling**: Invalid inputs, API errors, network failures
4. **Type Conversions**: Message/tool/response format conversions
5. **Streaming**: Both streaming and non-streaming code paths
6. **Configuration**: Different config options and their effects

#### Test Structure for Plugins

Each plugin should have tests covering:

```
plugins/{name}/tests/
├── {name}_plugin_test.py      # Plugin initialization, registration
├── {name}_models_test.py      # Model generate(), streaming
├── {name}_embedders_test.py   # Embedder functionality (if applicable)
└── conftest.py                # Shared fixtures (optional)
```

#### Mocking External Services

* **Always mock external API calls** - Tests must not make real network requests
* Use `unittest.mock.patch` or `pytest-mock` for mocking
* Mock at the HTTP client level or SDK client level
* Provide realistic mock responses based on actual API documentation

```python
from unittest.mock import AsyncMock, patch

@patch('genkit.plugins.mistral.models.Mistral')
async def test_generate(mock_client_class):
    mock_client = AsyncMock()
    mock_client_class.return_value = mock_client
    mock_client.chat.complete_async.return_value = mock_response
    # ... test code
```

#### Coverage Exceptions

Some code may be excluded from coverage requirements:

* `# pragma: no cover` - Use sparingly for truly untestable code
* Type stubs and protocol definitions
* Abstract base class methods (tested via implementations)
* Debug/development-only code paths

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

* Configuration options and their defaults
* API parameter lists
* Comparison of before/after behavior
* File changes summary

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
- **amazon-bedrock**: Cleaned up `plugin.py` imports
- **google-cloud**: Cleaned up `telemetry/metrics.py` imports

### Samples
Moved in-function imports to top of file:
- **anthropic-hello**: `random`, `genkit.types` imports
- **amazon-bedrock-hello**: `asyncio`, `random`, `genkit.types` imports
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

* \[ ] **Code Quality**: `bin/lint` passes with zero errors
* \[ ] **Type Safety**: All type checkers pass (ty, pyrefly, pyright)
* \[ ] **Tests**: Unit tests added/updated as needed
* \[ ] **Documentation**: Docstrings and README files updated
* \[ ] **Samples**: Demo code updated if applicable

### Automated Code Review Workflow

After addressing all CI checks and reviewer comments, trigger Gemini code review
by posting a single-line comment on the PR:

```
/gemini review
```

**Iterative Review Process:**

1. Address all existing review comments and fix CI failures
2. Push changes to the PR branch
3. Post `/gemini review` comment to trigger automated review
4. Wait for Gemini's review comments (typically 1-3 minutes)
5. Address any new comments raised by Gemini
6. **Resolve addressed comments** - Reply to each comment explaining the fix, then resolve
   the conversation (unless the discussion is open-ended and requires more thought)
7. Repeat steps 2-6 up to 3 times until no new comments are received
8. Once clean, request human reviewer approval

**Best Practices:**

| Practice | Description |
|----------|-------------|
| Fix before review | Always fix known issues before requesting review |
| Batch fixes | Combine multiple fixes into one push to reduce review cycles |
| Address all comments | Don't leave unresolved comments from previous reviews |
| Resolve conversations | Reply with fix explanation and resolve unless discussion is ongoing |
| Document decisions | If intentionally not addressing a comment, explain why |

### Splitting Large Branches into Multiple PRs

When splitting a feature branch with multiple commits into independent PRs:

1. **Squash before splitting** - Use `git merge --squash` to consolidate commits into
   a single commit before creating new branches. This avoids problems with:
   - Commit ordering issues (commits appearing in wrong order across PRs)
   - Interdependent changes that span multiple commits
   - Cherry-pick conflicts when commits depend on earlier changes

2. **Create independent branches** - For each logical unit of work:
   ```bash
   # From main, create a new branch
   git checkout main && git checkout -b feature/part-1
   
   # Selectively checkout files from the squashed branch
   git checkout squashed-branch -- path/to/files
   
   # Commit and push
   git commit -m "feat: description of part 1"
   git push -u origin HEAD
   ```

3. **Order PRs by dependency** - If PRs have dependencies:
   - Create the base PR first (e.g., shared utilities)
   - Stack dependent PRs on top, or wait for the base to merge
   - Document dependencies in PR descriptions

**Common Gemini Review Feedback:**

| Category | Examples | How to Address |
|----------|----------|----------------|
| Type safety | Missing return types, `Any` usage | Add explicit type annotations |
| Error handling | Unhandled exceptions, missing try/except | Add proper error handling with specific exceptions |
| Code duplication | Similar logic in multiple places | Extract into helper functions |
| Documentation | Missing docstrings, unclear comments | Add comprehensive docstrings |
| Test coverage | Missing edge cases, untested paths | Add tests for identified gaps |

## Plugin Verification Against Provider Documentation

When implementing or reviewing plugins, always cross-check against the provider's
official documentation. This ensures accuracy and prevents integration issues.

### Verification Checklist

For each plugin, verify:

1. **Environment Variables**: Match provider's official names exactly (case-sensitive)
2. **Model Names/IDs**: Use exact model identifiers from provider's API docs
3. **API Parameters**: Parameter names, types, and valid ranges match docs
4. **Authentication**: Use provider's recommended auth mechanism and headers
5. **Endpoints**: URLs match provider's documented endpoints

### Common Issues Found During Verification

| Issue Type | Example | How to Fix |
|------------|---------|------------|
| **Wrong model prefix** | `@cf/mistral/...` vs `@hf/mistral/...` | Check provider's model catalog for exact prefixes |
| **Outdated model names** | Using deprecated model IDs | Review provider's current model list |
| **Custom env var names** | `MY_API_KEY` vs `PROVIDER_API_KEY` | Use provider's official env var names |
| **Incorrect auth headers** | Wrong header name or format | Check provider's authentication docs |
| **Missing model capabilities** | Not supporting vision for multimodal models | Review model capabilities in provider docs |

### Provider Documentation Links

Keep these bookmarked for verification:

| Provider | Documentation | Key Pages |
|----------|---------------|-----------|
| **Anthropic** | [docs.anthropic.com](https://docs.anthropic.com/) | [Models](https://docs.anthropic.com/en/docs/about-claude/models), [API Reference](https://docs.anthropic.com/en/api/) |
| **Google AI** | [ai.google.dev](https://ai.google.dev/) | [Gemini Models](https://ai.google.dev/gemini-api/docs/models/gemini), [API Reference](https://ai.google.dev/api/) |
| **AWS Bedrock** | [docs.aws.amazon.com/bedrock](https://docs.aws.amazon.com/bedrock/) | [Model IDs](https://docs.aws.amazon.com/bedrock/latest/userguide/model-ids.html), [Converse API](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html) |
| **Azure OpenAI** | [learn.microsoft.com](https://learn.microsoft.com/azure/ai-services/openai/) | [Models](https://learn.microsoft.com/azure/ai-services/openai/concepts/models), [API Reference](https://learn.microsoft.com/azure/ai-services/openai/reference) |
| **xAI** | [docs.x.ai](https://docs.x.ai/) | [Models](https://docs.x.ai/docs/models), [API Reference](https://docs.x.ai/api) |
| **DeepSeek** | [api-docs.deepseek.com](https://api-docs.deepseek.com/) | [Models](https://api-docs.deepseek.com/quick_start/pricing), [API Reference](https://api-docs.deepseek.com/api/create-chat-completion) |
| **Cloudflare AI** | [developers.cloudflare.com/workers-ai](https://developers.cloudflare.com/workers-ai/) | [Models](https://developers.cloudflare.com/workers-ai/models/), [API Reference](https://developers.cloudflare.com/workers-ai/configuration/open-ai-compatibility/) |
| **Ollama** | [github.com/ollama/ollama](https://github.com/ollama/ollama) | [API Docs](https://github.com/ollama/ollama/blob/main/docs/api.md), [Models](https://ollama.com/library) |
| **Sentry** | [docs.sentry.io](https://docs.sentry.io/) | [OTLP](https://docs.sentry.io/concepts/otlp/), [Configuration](https://docs.sentry.io/platforms/python/configuration/options/) |
| **Honeycomb** | [docs.honeycomb.io](https://docs.honeycomb.io/) | [API Keys](https://docs.honeycomb.io/configure/environments/manage-api-keys/), [OpenTelemetry](https://docs.honeycomb.io/send-data/opentelemetry/) |
| **Datadog** | [docs.datadoghq.com](https://docs.datadoghq.com/) | [OTLP Ingest](https://docs.datadoghq.com/opentelemetry/setup/otlp_ingest/), [API Keys](https://docs.datadoghq.com/account_management/api-app-keys/) |
| **Grafana Cloud** | [grafana.com/docs](https://grafana.com/docs/grafana-cloud/) | [OTLP Setup](https://grafana.com/docs/grafana-cloud/send-data/otlp/send-data-otlp/), [Authentication](https://grafana.com/docs/grafana-cloud/account-management/authentication-and-permissions/) |
| **Axiom** | [axiom.co/docs](https://axiom.co/docs/) | [OpenTelemetry](https://axiom.co/docs/send-data/opentelemetry), [API Tokens](https://axiom.co/docs/reference/tokens) |
| **Mistral AI** | [docs.mistral.ai](https://docs.mistral.ai/) | [Models](https://docs.mistral.ai/getting-started/models/models_overview/), [API Reference](https://docs.mistral.ai/api/) |
| **Hugging Face** | [huggingface.co/docs](https://huggingface.co/docs/api-inference/) | [Inference API](https://huggingface.co/docs/api-inference/), [Inference Providers](https://huggingface.co/docs/inference-providers/) |

### URL Verification

**All URLs in documentation and code must be verified to work.** Broken links degrade
developer experience and erode trust in the documentation.

#### Verification Requirements

1. **Before Adding URLs**: Verify the URL returns HTTP 200 and shows expected content
2. **During Code Review**: Check that all new/modified URLs are accessible
3. **Periodic Audits**: Run URL checks on documentation files periodically

#### How to Check URLs

Extract and test URLs from the codebase:

```bash
# Extract unique URLs from Python source and docs
cd py
grep -roh 'https://[^[:space:])\"'"'"'`>]*' plugins/ samples/ packages/ *.md \
  | sort -u | grep -v '{' | grep -v '\[' | grep -v 'example\.com'

# Test a specific URL
curl -s -o /dev/null -w "%{http_code}" -L --max-time 10 "https://docs.mistral.ai/"
```

#### Common URL Issues

| Issue | Example | Fix |
|-------|---------|-----|
| **Trailing punctuation** | `https://api.example.com.` | Remove trailing `.` |
| **Outdated paths** | `/v1/` changed to `/v2/` | Update to current path |
| **Moved documentation** | Provider reorganized docs | Find new canonical URL |
| **Regional endpoints** | `api.eu1.` vs `api.` | Use correct regional URL |

#### URLs That Don't Need Verification

* Placeholder URLs: `https://your-endpoint.com`, `https://example.com`
* Template URLs with variables: `https://{region}.api.com`
* Test/mock URLs in test files

### Telemetry Plugin Authentication Patterns

Different observability backends use different authentication mechanisms:

| Backend | Auth Type | Header Format | Example |
|---------|-----------|---------------|---------|
| **Sentry** | Custom | `x-sentry-auth: sentry sentry_key={key}` | Parse DSN to extract key |
| **Honeycomb** | Custom | `x-honeycomb-team: {api_key}` | Direct API key |
| **Datadog** | Custom | `DD-API-KEY: {api_key}` | Direct API key |
| **Grafana Cloud** | Basic Auth | `Authorization: Basic {base64(user:key)}` | Encode user\_id:api\_key |
| **Axiom** | Bearer | `Authorization: Bearer {token}` | Direct token |
| **Azure Monitor** | Connection String | N/A (SDK handles) | Use official SDK |
| **Generic OTLP** | Bearer | `Authorization: Bearer {token}` | Standard OTLP |

### Model Provider Plugin Patterns

When implementing model provider plugins:

1. **Use dynamic model discovery** when possible (Google GenAI, Vertex AI)
2. **Maintain a `SUPPORTED_MODELS` registry** for static model lists
3. **Document model capabilities** accurately (vision, tools, JSON mode)
4. **Support all provider-specific parameters** (reasoning\_effort, thinking, etc.)
5. **Handle model-specific restrictions** (e.g., grok-4 doesn't support frequency\_penalty)

### Verification Workflow

When reviewing or updating a plugin:

```
1. Read the plugin's current implementation
   └── Focus on: env vars, model names, API params, auth

2. Search provider's official documentation
   └── Find: current model list, env var names, API reference

3. Compare and document differences
   └── Create: table of inconsistencies found

4. Fix issues and update documentation
   └── Update: code, docstrings, README, GEMINI.md

5. Run linter and type checkers
   └── Verify: bin/lint passes with 0 errors

6. Update PR description with verification status
   └── Include: table showing what was verified
```

### Python Version Compatibility

When using features from newer Python versions:

1. **StrEnum** (Python 3.11+): Use conditional import with `strenum` package fallback

   ```python
   import sys

   if sys.version_info >= (3, 11):
       from enum import StrEnum
   else:
       from strenum import StrEnum
   ```

2. **Check `requires-python`**: Ensure all `pyproject.toml` files specify `>=3.10`
   to maintain compatibility with CI/CD pipelines running Python 3.10 or 3.11

3. **Type hints**: Use `from __future__ import annotations` for forward references
   in Python 3.10 compatibility

## Session Learning Documentation

**IMPORTANT**: At the end of each development session, document new learnings,
patterns, and insights discovered during the session into this file (`py/GEMINI.md`).

This creates a feedback loop where:

1. Future sessions benefit from past learnings
2. Patterns and best practices are captured permanently
3. Common issues and their solutions are documented
4. The guidelines evolve based on real-world experience

### What to Document

After completing tasks in a session, add relevant learnings to appropriate sections:

| Learning Type | Where to Add | Example |
|---------------|--------------|---------|
| **New provider env vars** | "Official Environment Variables by Provider" table | `MISTRAL_API_KEY` for Mistral AI |
| **Plugin verification findings** | "Provider Documentation Links" table | New provider docs URLs |
| **Authentication patterns** | "Telemetry Plugin Authentication Patterns" | New auth header formats |
| **Common issues** | "Common Issues Found During Verification" | Model prefix mistakes |
| **Python compatibility** | "Python Version Compatibility" | New conditional imports |
| **New coding patterns** | Appropriate section or create new | Reusable patterns discovered |

### Session Documentation Workflow

```
1. Complete development tasks
   └── Implement features, fix bugs, verify plugins

2. Identify learnings worth preserving
   └── New patterns, gotchas, best practices, provider details

3. Update py/GEMINI.md with learnings
   └── Add to existing sections or create new ones

4. Commit changes
   └── Include GEMINI.md updates in the commit
```

### Example Learnings to Document

* Added Mistral AI and Hugging Face to provider documentation table
* Documented that `@hf/` prefix is used for Hugging Face-hosted models on Cloudflare
* Added OpenRouter as a viable option via `compat-oai` plugin
* Sentry uses `x-sentry-auth` header format, not standard Bearer token
* Grafana Cloud requires Base64 encoding of `user_id:api_key`
* Added structured logging pattern for trace correlation

### Session Learnings (2026-02-01): Mistral AI and Hugging Face Plugins

#### New Provider Environment Variables

| Provider | Variable | Documentation |
|----------|----------|---------------|
| Mistral AI | `MISTRAL_API_KEY` | [Mistral Console](https://console.mistral.ai/) |
| Hugging Face | `HF_TOKEN` | [HF Tokens](https://huggingface.co/settings/tokens) |

#### Mistral SDK Patterns

* **Streaming Response**: Mistral SDK's `CompletionChunk` has `choices` directly on the chunk object, NOT `chunk.data.choices`. The streaming API returns chunks directly:

  ```python
  async for chunk in stream:
      if chunk.choices:  # NOT chunk.data.choices
          choice = chunk.choices[0]
  ```

* **Content Types**: Mistral response content can be `str` or `list[TextChunk | ...]`. Handle both:

  ```python
  if isinstance(msg_content, str):
      content.append(Part(root=TextPart(text=msg_content)))
  elif isinstance(msg_content, list):
      for chunk in msg_content:
          if isinstance(chunk, TextChunk):
              content.append(Part(root=TextPart(text=chunk.text)))
  ```

#### Hugging Face SDK Patterns

* **InferenceClient**: Use `huggingface_hub.InferenceClient` for chat completions
* **Inference Providers**: Support 17+ providers (Cerebras, Groq, Together) via `provider` parameter
* **Model IDs**: Use full HF model IDs like `meta-llama/Llama-3.3-70B-Instruct`

#### Type Annotation Patterns

* **Config dictionaries**: When passing config to `ai.generate()`, explicitly type as `dict[str, object]`:

  ```python
  configs: dict[str, dict[str, object]] = {
      'creative': {'temperature': 0.9, 'max_tokens': 200},
  }
  config: dict[str, object] = configs.get(task, configs['creative'])
  ```

* **StreamingCallback**: `ctx.send_chunk` is synchronous (`Callable[[object], None]`), NOT async. Do NOT use `await`:

  ```python
  # Correct
  ctx.send_chunk(GenerateResponseChunk(...))

  # Wrong - send_chunk is not async
  await ctx.send_chunk(GenerateResponseChunk(...))
  ```

#### Genkit Type Patterns

* **Usage**: Use `GenerationUsage` directly, not `Usage` wrapper:

  ```python
  usage = GenerationUsage(
      input_tokens=response.usage.prompt_tokens,
      output_tokens=response.usage.completion_tokens,
  )
  ```

* **FinishReason**: Use `FinishReason` enum, not string literals:

  ```python
  finish_reason = FinishReason.STOP  # NOT 'stop'
  ```

#### Tool Calling Implementation Patterns

* **Mistral Tool Definition**: Use `Function` class from `mistralai.models`, not dict:

  ```python
  from mistralai.models import Function, Tool

  Tool(
      type='function',
      function=Function(
          name=tool.name,
          description=tool.description or '',
          parameters=parameters,
      ),
  )
  ```

* **Tool Call Arguments**: Mistral SDK may return arguments as `str` or `dict`. Handle both:

  ```python
  func_args = tool_call.function.arguments
  if isinstance(func_args, str):
      try:
          args = json.loads(func_args)
      except json.JSONDecodeError:
          args = func_args
  elif isinstance(func_args, dict):
      args = func_args
  ```

* **Streaming Tool Calls**: Track tool calls by index during streaming. Ensure index is `int`:

  ```python
  idx: int = tool_call.index if hasattr(tool_call, 'index') and tool_call.index is not None else 0
  ```

* **Tool Response Messages**: Use `ToolMessage` for Mistral, dict with `role: 'tool'` for HF:

  ```python
  # Mistral
  ToolMessage(tool_call_id=ref, name=name, content=output_str)

  # Hugging Face
  {'role': 'tool', 'tool_call_id': ref, 'content': output_str}
  ```

#### Structured Output Implementation

* **Mistral JSON Mode**: Use `response_format` parameter with `json_schema` type:

  ```python
  params['response_format'] = {
      'type': 'json_schema',
      'json_schema': {
          'name': output.schema.get('title', 'Response'),
          'schema': output.schema,
          'strict': True,
      },
  }
  ```

* **Hugging Face JSON Mode**: Use `response_format` with `type: 'json'`:

  ```python
  params['response_format'] = {
      'type': 'json',
      'value': output.schema,  # Optional schema
  }
  ```

#### License Check Configuration

* **Unknown Licenses**: When `liccheck` reports a package as "UNKNOWN", verify the actual
  license and add to `[tool.liccheck.authorized_packages]` in `py/pyproject.toml`:

  ```toml
  [tool.liccheck.authorized_packages]
  mistralai = ">=1.9.11"  # Apache-2.0 "https://github.com/mistralai/client-python/blob/main/LICENSE"
  ```

* **Ignore Patterns**: Add generated directories to `bin/check_license` and `bin/add_license`:

  ```bash
  -ignore '**/.tox/**/*' \
  -ignore '**/.nox/**/*' \
  ```

## Release Process

### Automated Release Scripts

The following scripts automate the release process:

| Script | Description |
|--------|-------------|
| `py/bin/release_check` | Comprehensive release readiness validation |
| `py/bin/bump_version` | Bump version across all packages |
| `py/bin/check_consistency` | Verify workspace consistency |
| `py/bin/fix_package_metadata.py` | Add missing package metadata |

### Pre-Release Checklist

Before releasing, run the release check script:

```bash
# Full release readiness check
./py/bin/release_check

# With verbose output
./py/bin/release_check --verbose

# CI mode (optimized for CI pipelines)
./py/bin/release_check --ci

# Skip tests (when tests are run separately in CI)
./py/bin/release_check --skip-tests
```

The release check validates:

1. **Package Metadata**: All packages have required fields (name, version, description, license, authors, classifiers)
2. **Build Verification**: Lock file is current, dependencies resolve, packages build successfully
3. **Code Quality**: Type checking, formatting, linting all pass
4. **Tests**: All unit tests pass (can be skipped with `--skip-tests`)
5. **Security & Compliance**: No vulnerabilities, licenses are approved
6. **Documentation**: README files exist, CHANGELOG has current version entry

> **Note**: The CI workflow runs release checks on every PR to ensure every commit
> is release-worthy. This catches issues early and ensures consistent quality.

### Version Bumping

Use the version bump script to update all packages simultaneously:

```bash
# Bump to specific version
./py/bin/bump_version 0.5.0

# Bump minor version (0.4.0 -> 0.5.0)
./py/bin/bump_version --minor

# Bump patch version (0.4.0 -> 0.4.1)
./py/bin/bump_version --patch

# Bump major version (0.4.0 -> 1.0.0)
./py/bin/bump_version --major

# Dry run (preview changes)
./py/bin/bump_version --minor --dry-run
```

### Release Steps

1. **Update CHANGELOG.md** with release notes
2. **Bump version**: `./py/bin/bump_version <version>`
3. **Run release check**: `./py/bin/release_check`
4. **Commit changes**: `git commit -am "chore: release v<version>"`
5. **Create tag**: `git tag -a py-v<version> -m "Python SDK v<version>"`
6. **Push**: `git push && git push --tags`
7. **Build and publish**: `./py/bin/build_dists && ./py/bin/publish_dists`

### Package Metadata Requirements

All publishable packages (core and plugins) MUST have:

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Package name (e.g., `genkit-plugin-anthropic`) |
| `version` | Yes | Semantic version matching core framework |
| `description` | Yes | Short description of the package |
| `license` | Yes | `Apache-2.0` |
| `requires-python` | Yes | `>=3.10` |
| `authors` | Yes | `[{ name = "Google" }]` |
| `classifiers` | Yes | PyPI classifiers for discoverability |
| `keywords` | Recommended | Search keywords for PyPI |
| `readme` | Recommended | `README.md` |
| `[project.urls]` | Recommended | Links to docs, repo, issues |

### Required Files

Each publishable package directory MUST contain:

| File | Required | Description |
|------|----------|-------------|
| `pyproject.toml` | Yes | Package configuration and metadata |
| `LICENSE` | Yes | Apache 2.0 license file (copy from `py/LICENSE`) |
| `README.md` | Recommended | Package documentation |
| `src/` | Yes | Source code directory |
| `src/.../py.typed` | Yes | PEP 561 type hint marker file |

To copy LICENSE files to all packages:

```bash
# Copy LICENSE to core package
cp py/LICENSE py/packages/genkit/LICENSE

# Copy LICENSE to all plugins
for d in py/plugins/*/; do cp py/LICENSE "$d/LICENSE"; done
```

### PEP 561 Type Hints (py.typed)

All packages MUST include a `py.typed` marker file to indicate they support type hints.
This enables type checkers like mypy, pyright, and IDE autocompletion to use the package's
type annotations.

```bash
# Add py.typed to core package
touch py/packages/genkit/src/genkit/py.typed

# Add py.typed to all plugins
for d in py/plugins/*/src/genkit/plugins/*/; do touch "$d/py.typed"; done
```

### Required Classifiers

All packages MUST include these PyPI classifiers:

```toml
classifiers = [
  "Development Status :: 3 - Alpha",  # or 4 - Beta, 5 - Production/Stable
  "Intended Audience :: Developers",
  "License :: OSI Approved :: Apache Software License",
  "Programming Language :: Python :: 3.10",
  "Programming Language :: Python :: 3.11",
  "Programming Language :: Python :: 3.12",
  "Programming Language :: Python :: 3.13",
  "Typing :: Typed",  # Required for typed packages
  "Topic :: Scientific/Engineering :: Artificial Intelligence",
]
```

### CHANGELOG Format

Follow [Keep a Changelog](https://keepachangelog.com/) format:

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- New features

### Changed
- Changes to existing functionality

### Deprecated
- Features to be removed in future

### Removed
- Removed features

### Fixed
- Bug fixes

### Security
- Security fixes
```

### Session Learnings (2026-02-03): HTTP Client Event Loop Binding

#### The Problem: `httpx.AsyncClient` Event Loop Binding

`httpx.AsyncClient` instances are **bound to the event loop** they were created in.
This causes issues in production when:

1. **Different event loops**: The client was created in one event loop but is used
   in another (common in test frameworks, async workers, or web servers)
2. **Closed event loops**: The original event loop was closed but the client is
   still being used

**Error message**: `RuntimeError: Event loop is closed` or
`RuntimeError: cannot schedule new futures after interpreter shutdown`

#### The Solution: Per-Event-Loop Client Caching

Created `genkit.core.http_client` module with a shared utility:

```python
from genkit.core.http_client import get_cached_client

# Get or create cached client for current event loop
client = get_cached_client(
    cache_key='my-plugin',
    headers={'Authorization': 'Bearer token'},
    timeout=60.0,
)
```

**Key design decisions**:

| Decision | Rationale |
|----------|-----------|
| **WeakKeyDictionary** | Automatically cleanup when event loop is GC'd |
| **Two-level cache** | `loop -> cache_key -> client` allows multiple configs per loop |
| **Per-request auth** | For expiring tokens (GCP), pass headers in request not client |
| **Static auth in client** | For static API keys (Cloudflare), include in cached client |

#### Plugins Updated

| Plugin | Change |
|--------|--------|
| **cloudflare-workers-ai** | Refactored `_get_client()` to use `get_cached_client()` |
| **google-genai/rerankers** | Changed from `async with httpx.AsyncClient()` to cached client |
| **google-genai/evaluators** | Changed from `async with httpx.AsyncClient()` to cached client |

#### When to Use Which Pattern

| Pattern | Use When |
|---------|----------|
| `async with httpx.AsyncClient()` | One-off requests, infrequent calls |
| `get_cached_client()` | Frequent requests, performance-critical paths |
| Client stored at init | **Never** - causes event loop binding issues |

#### Testing Cached Clients

When mocking HTTP clients in tests, mock `get_cached_client` instead of
`httpx.AsyncClient`:

```python
from unittest.mock import AsyncMock, patch

@patch('my_module.get_cached_client')
async def test_api_call(mock_get_client):
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.is_closed = False
    mock_get_client.return_value = mock_client

    result = await my_api_call()

    mock_client.post.assert_called_once()
```

#### Related Issue

* GitHub Issue: [#4420](https://github.com/firebase/genkit/issues/4420)

### Session Learnings (2026-02-04): Release PRs and Changelogs

When drafting release PRs and changelogs, follow these guidelines to create
comprehensive, contributor-friendly release documentation.

#### Release PR Checklist

Use this checklist when drafting a release PR:

| Step | Task | Command/Details |
|------|------|-----------------|
| 1 | **Count commits** | `git log "genkit-python@PREV"..HEAD --oneline -- py/ \| wc -l` |
| 2 | **Count file changes** | `git diff --stat "genkit-python@PREV"..HEAD -- py/ \| tail -1` |
| 3 | **List contributors** | `git log "genkit-python@PREV"..HEAD --pretty=format:"%an" -- py/ \| sort \| uniq -c \| sort -rn` |
| 4 | **Get PR counts** | `gh pr list --state merged --search "label:python merged:>=DATE" --json author --limit 200 \| jq ...` |
| 5 | **Map git names to GitHub** | `gh pr list --json author --limit 200 \| jq '.[].author \| "\(.name) -> @\(.login)"'` |
| 6 | **Get each contributor's commits** | `git log --pretty=format:"%s" --author="Name" -- py/ \| head -30` |
| 7 | **Check external repos** (e.g., dotprompt) | Review GitHub contributors page or clone and run git log |
| 8 | **Create CHANGELOG.md section** | Follow Keep a Changelog format with Impact Summary |
| 9 | **Create PR_DESCRIPTION_X.Y.Z.md** | Put in `.github/` directory |
| 10 | **Add contributor tables** | Include GitHub links, PR/commit counts, exhaustive contributions |
| 11 | **Categorize contributions** | Use bold categories: **Core**, **Plugins**, **Fixes**, etc. |
| 12 | **Include PR numbers** | Add (#1234) for each major contribution |
| 13 | **Add dotprompt table** | Same format as main table with PRs, Commits, Key Contributions |
| 14 | **Create blog article** | `py/engdoc/blog-genkit-python-X.Y.Z.md` |
| 15 | **Verify code examples** | Test all code snippets match actual API patterns |
| 16 | **Run release validation** | `./bin/validate_release_docs` (see below) |
| 17 | **Commit with --no-verify** | `git commit --no-verify -m "docs(py): ..."` |
| 18 | **Push with --no-verify** | `git push --no-verify` |
| 19 | **Update PR on GitHub** | `gh pr edit <NUM> --body-file py/.github/PR_DESCRIPTION_X.Y.Z.md` |

#### Automated Release Documentation Validation

Run this validation script before finalizing any release documentation. Save as
`py/bin/validate_release_docs` and run before committing:

```bash
#!/bin/bash
# Release Documentation Validator
# Run from py/ directory: ./bin/validate_release_docs

set -e
echo "=== Release Documentation Validation ==="
ERRORS=0

# 1. Check branding: No "Firebase Genkit" references
echo -n "Checking branding (no 'Firebase Genkit')... "
if grep -ri "Firebase Genkit" engdoc/ .github/PR_DESCRIPTION_*.md CHANGELOG.md 2>/dev/null; then
    echo "FAIL: Found 'Firebase Genkit' - use 'Genkit' instead"
    ERRORS=$((ERRORS + 1))
else
    echo "OK"
fi

# 2. Check for non-existent plugins
echo -n "Checking plugin names... "
FAKE_PLUGINS="genkit-plugin-aim|genkit-plugin-firestore"
if grep -rE "$FAKE_PLUGINS" engdoc/ .github/PR_DESCRIPTION_*.md CHANGELOG.md 2>/dev/null; then
    echo "FAIL: Found non-existent plugin names"
    ERRORS=$((ERRORS + 1))
else
    echo "OK"
fi

# 3. Check for unshipped features (DAP, MCP unless actually shipped)
echo -n "Checking for unshipped features... "
UNSHIPPED="Dynamic Action Provider|DAP factory|MCP resource|action_provider"
if grep -rE "$UNSHIPPED" engdoc/ .github/PR_DESCRIPTION_*.md CHANGELOG.md 2>/dev/null; then
    echo "WARN: Found references to features that may not be shipped yet"
    # Not a hard error, just a warning
else
    echo "OK"
fi

# 4. Check blog code syntax errors
echo -n "Checking blog code syntax... "
WRONG_PATTERNS='response\.text\(\)|output_schema=|asyncio\.run\(main|from genkit import Genkit[^.]'
if grep -rE "$WRONG_PATTERNS" engdoc/blog-*.md 2>/dev/null; then
    echo "FAIL: Found incorrect API patterns in blog code examples"
    ERRORS=$((ERRORS + 1))
else
    echo "OK"
fi

# 5. Verify all mentioned plugins exist
echo -n "Verifying plugin references... "
for plugin in $(grep -ohE 'genkit-plugin-[a-z-]+' engdoc/ .github/PR_DESCRIPTION_*.md CHANGELOG.md 2>/dev/null | sort -u); do
    dir_name=$(echo "$plugin" | sed 's/genkit-plugin-//')
    if [ ! -d "plugins/$dir_name" ]; then
        echo "FAIL: Plugin $plugin does not exist (no plugins/$dir_name/)"
        ERRORS=$((ERRORS + 1))
    fi
done
echo "OK"

# 6. Check contributor GitHub links are properly formatted
echo -n "Checking contributor links... "
if grep -E '\[@[a-zA-Z0-9]+\]' .github/PR_DESCRIPTION_*.md CHANGELOG.md 2>/dev/null | \
   grep -vE '\[@[a-zA-Z0-9_-]+\]\(https://github\.com/[a-zA-Z0-9_-]+\)' 2>/dev/null; then
    echo "WARN: Some contributor links may not have GitHub URLs"
else
    echo "OK"
fi

# 7. Check blog article exists for version in CHANGELOG
echo -n "Checking blog article exists... "
VERSION=$(grep -m1 '## \[' CHANGELOG.md | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
if [ -f "engdoc/blog-genkit-python-$VERSION.md" ]; then
    echo "OK (found blog-genkit-python-$VERSION.md)"
else
    echo "FAIL: Missing engdoc/blog-genkit-python-$VERSION.md"
    ERRORS=$((ERRORS + 1))
fi

# 8. Verify imports work
echo -n "Checking Python imports... "
if python -c "from genkit.ai import Genkit, Output; print('OK')" 2>/dev/null; then
    :
else
    echo "WARN: Could not verify imports (genkit may not be installed)"
fi

# Summary
echo ""
echo "=== Validation Complete ==="
if [ $ERRORS -gt 0 ]; then
    echo "FAILED: $ERRORS error(s) found. Fix before releasing."
    exit 1
else
    echo "PASSED: All checks passed!"
    exit 0
fi
```

**Quick manual validation commands:**

```bash
# All-in-one check for common issues
cd py && grep -rE \
  'Firebase Genkit|genkit-plugin-aim|response\.text\(\)|DAP factory|output_schema=' \
  engdoc/ .github/PR_DESCRIPTION_*.md CHANGELOG.md

# List all plugin references and verify they exist  
for p in $(grep -ohE 'genkit-plugin-[a-z-]+' CHANGELOG.md | sort -u); do
    d=$(echo $p | sed 's/genkit-plugin-//'); 
    [ -d "plugins/$d" ] && echo "✓ $p" || echo "✗ $p (not found)";
done
```

#### Key Principles

1. **Exhaustive contributions**: List every significant feature, fix, and improvement
2. **Clickable GitHub links**: Format as `[@username](https://github.com/username)`
3. **Real names when different**: Show as `@MengqinShen (Elisa Shen)`
4. **Categorize by type**: Use bold headers like **Core**, **Plugins**, **Type Safety**
5. **Include PR numbers**: Every major item should have `(#1234)`
6. **Match table formats**: External repo tables should have same columns as main table
7. **Cross-check repositories**: Check both firebase/genkit and google/dotprompt for Python work
8. **Use --no-verify**: For documentation-only changes, skip hooks for faster iteration
9. **Always include blog article**: Every release needs a blog article in `py/engdoc/`
10. **Branding**: Use "Genkit" not "Firebase Genkit" (rebranded as of 2025)

#### Blog Article Guidelines

Every release MUST include a blog article at `py/engdoc/blog-genkit-python-X.Y.Z.md`.

**Branding Note**: The project is called **"Genkit"** (not "Firebase Genkit"). While the
repository is hosted at `github.com/firebase/genkit` and some blog posts may be published
on the Firebase blog, the product name is simply "Genkit". Use this consistently in all
documentation, blog articles, and release notes.

**Required Sections:**
1. **Headline**: "Genkit Python SDK X.Y.Z: [Catchy Subtitle]"
2. **Stats paragraph**: Commits, files changed, contributors, PRs
3. **What's New**: Plugin expansion, architecture changes, new features
4. **Code Examples**: Accurate, tested examples (see below)
5. **Critical Fixes & Security**: Important bug fixes
6. **Developer Experience**: Tooling improvements
7. **Plugin Tables**: All available plugins with status
8. **Get Started**: Installation and quick start
9. **Contributors**: Acknowledgment table
10. **What's Next**: Roadmap items
11. **Get Involved**: Community links

**Code Example Accuracy Checklist:**

Before publishing, verify ALL code examples match the actual API:

| Pattern | Correct | Wrong |
|---------|---------|-------|
| Text response | `response.text` | `response.text()` |
| Structured output | `output=Output(schema=Model)` | `output_schema=Model` |
| Dynamic tools | `ai.dynamic_tool(name, fn, description=...)` | `@ai.action_provider()` |
| Partials | `ai.define_partial('name', 'template')` | `Dotprompt.define_partial()` |
| Main function | `ai.run_main(main())` | `asyncio.run(main())` |
| Genkit init | Module-level `ai = Genkit(...)` | Inside `async def main()` |
| Imports | `from genkit.ai import Genkit, Output` | `from genkit import Genkit` |

**Verify examples against actual samples:**

```bash
# Check API patterns in existing samples
grep -r "response.text" py/samples/*/src/main.py | head -5
grep -r "Output(schema=" py/samples/*/src/main.py | head -5
grep -r "ai.run_main" py/samples/*/src/main.py | head -5
```

**Verify blog code syntax matches codebase patterns:**

CRITICAL: Before publishing any blog article, extract and validate ALL code snippets
against the actual codebase to ensure they would compile/run correctly.

```bash
# Extract Python code blocks from a blog article and check for common errors
grep -A 50 '```python' py/engdoc/blog-genkit-python-*.md | grep -E \
  'response\.text\(\)|output_schema=|asyncio\.run\(|from genkit import Genkit'

# Verify import statements match actual module structure
python -c "from genkit.ai import Genkit, Output; print('Imports OK')"

# Check that decorator patterns exist in codebase
grep -r "@ai.flow()" py/samples/*/src/main.py | head -3
grep -r "@ai.tool()" py/samples/*/src/main.py | head -3

# Validate a blog article's code examples by syntax checking
python -m py_compile <(grep -A 20 '```python' py/engdoc/blog-genkit-python-*.md | \
  grep -v '```' | head -50) 2>&1 || echo "Syntax errors found!"
```

**Blog Article Code Review Checklist:**

Before finalizing a blog article, manually verify:

| Check | How to Verify |
|-------|---------------|
| No `response.text()` | Search for `\.text\(\)` - should find nothing |
| Correct Output usage | Search for `output=Output(schema=` |
| Module-level Genkit | `ai = Genkit(...)` outside any function |
| `ai.run_main()` used | Not `asyncio.run()` for samples with Dev UI |
| Pydantic imports | `from pydantic import BaseModel, Field` |
| Tool decorator | `@ai.tool()` with Pydantic input schema |
| Flow decorator | `@ai.flow()` for async functions |
| No fictional features | DAP, MCP, etc. - only document shipped features |

**Verify plugin names exist before documenting:**

CRITICAL: Always verify plugin names against actual packages before including them in
release documentation. Non-existent plugins will confuse users.

```bash
# List all actual plugin package names
grep "^name = " py/plugins/*/pyproject.toml | sort

# Verify a specific plugin exists
ls -la py/plugins/<plugin-name>/pyproject.toml
```

Common mistakes to avoid:
- `genkit-plugin-aim` does NOT exist (use `genkit-plugin-firebase` or `genkit-plugin-observability`)
- `genkit-plugin-firestore` does NOT exist (it's `genkit-plugin-firebase`)
- Always double-check plugin names match directory names (with `genkit-plugin-` prefix)

#### CHANGELOG.md Structure

Follow [Keep a Changelog](https://keepachangelog.com/) format with these sections:

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Impact Summary
| Category | Description |
|----------|-------------|
| **New Capabilities** | Brief summary |
| **Critical Fixes** | Brief summary |
| **Performance** | Brief summary |
| **Breaking Changes** | Brief summary |

### Added
- **Category Name** - Feature description

### Changed
- **Category Name** - Change description

### Fixed
- **Category Name** - Fix description

### Security
- **Category Name** - Security fix description

### Performance
- **Per-Event-Loop HTTP Client Caching** - Performance improvement description

### Deprecated
- Item being deprecated

### Contributors
... (see contributor section below)
```

#### Gathering Release Statistics

Use these commands to gather comprehensive release statistics:

```bash
# Count commits since previous version
git log "genkit-python@0.4.0"..HEAD --oneline -- py/ | wc -l

# Get contributors by commit count
git log "genkit-python@0.4.0"..HEAD --pretty=format:"%an" -- py/ | sort | uniq -c | sort -rn

# Get commits by each contributor with messages
git log "genkit-python@0.4.0"..HEAD --pretty=format:"%an|%s" -- py/

# Get PR counts by contributor (requires gh CLI)
gh pr list --repo firebase/genkit --state merged \
  --search "label:python merged:>=2025-05-26" \
  --json author,number,title --limit 200 | \
  jq -r '.[].author.login' | sort | uniq -c | sort -rn

# Get files changed count
git diff --stat "genkit-python@0.4.0"..HEAD -- py/ | tail -1
```

#### Contributor Acknowledgment Table

Include a detailed contributors table with both PRs and commits:

```markdown
### Contributors

This release includes contributions from **N developers** across **M PRs**.
Thank you to everyone who contributed!

| Contributor | PRs | Commits | Key Contributions |
|-------------|-----|---------|-------------------|
| **Name** | 91 | 93 | Core framework, type safety, plugins |
| **Name** | 42 | 42 | Resource support, samples |
...

**[external/repo](https://github.com/org/repo) Contributors** (Feature integration):

| Contributor | PRs | Key Contributions |
|-------------|-----|-------------------|
| **Name** | 42 | CI/CD improvements, release automation |
```

#### PR Description File

Create a `.github/PR_DESCRIPTION_X.Y.Z.md` file for each major release:

```markdown
# Genkit Python SDK vX.Y.Z Release

## Overview

Brief description of the release (one paragraph).

## Impact Summary

| Category | Description |
|----------|-------------|
| **New Capabilities** | Summary |
| **Breaking Changes** | Summary |
| **Performance** | Summary |

## New Features

### Feature Category 1
- **Feature Name**: Description

## Breaking Changes

### Change 1
**Before**: Old behavior...
**After**: New behavior...
**Migration**: How to migrate...

## Critical Fixes

- **Fix Name**: Description (PR #)

## Testing

All X plugins and Y+ samples have been tested. CI runs on Python 3.10-3.14.

## Contributors
(Same table format as CHANGELOG)

## Full Changelog

See [CHANGELOG.md](py/CHANGELOG.md) for the complete list of changes.
```

#### Updating the PR on GitHub

Use gh CLI to update the PR body from the file:

```bash
gh pr edit <PR_NUMBER> --body-file py/.github/PR_DESCRIPTION_X.Y.Z.md
```

#### Key Sections to Include

| Section | Purpose |
|---------|---------|
| **Impact Summary** | Quick overview table with categories |
| **Critical Fixes** | Highlight race conditions, thread safety, security |
| **Performance** | Document speedups and optimizations |
| **Breaking Changes** | Migration guide with before/after examples |
| **Contributors** | Table with PRs, commits, and key contributions |

#### Commit Messages for Release Documentation

Use conventional commits with `--no-verify` for release documentation:

```bash
git commit --no-verify -m "docs(py): add contributor acknowledgments to changelog

Genkit Python SDK Contributors (N developers):
- Name: Core framework, type safety
- Name: Plugins, samples
...

External Contributors:
- Name: CI/CD improvements"
```

#### Highlighting Critical Information

**When documenting fixes, emphasize:**

1. **Race conditions**: Dev server startup, async operations
2. **Thread safety**: Event loop binding, HTTP client caching
3. **Security**: CVE/CWE references, audit results
4. **Infinite recursion**: Cycle detection, recursion limits

**Example format:**

```markdown
### Critical Fixes

- **Race Condition**: Dev server startup race condition resolved (#4225)
- **Thread Safety**: Per-event-loop HTTP client caching prevents event loop
  binding errors (#4419, #4429)
- **Infinite Recursion**: Cycle detection in Handlebars partial resolution
- **Security**: Path traversal hardening (CWE-22), SigV4 signing (#4402)
```

#### External Project Contributions

When integrating external projects (e.g., dotprompt), include their contributors:

```bash
# Check commits in external repo
# Navigate to GitHub contributors page or use git log on local clone
```

Include a separate table linking to the external repository.

#### Contributor Profile Links and Exhaustive Contributions

**Always include clickable GitHub profile links** for contributors in release notes:

```markdown
| Contributor | PRs | Commits | Key Contributions |
|-------------|-----|---------|-------------------|
| [**@username**](https://github.com/username) | 91 | 93 | Exhaustive list... |
```

**Finding GitHub usernames from git log names:**

```bash
# Get GitHub username from PR data (most reliable)
gh pr list --repo firebase/genkit --state merged \
  --search "author:USERNAME label:python" \
  --json author,title --limit 5

# Map git log author names to GitHub handles
gh pr list --repo firebase/genkit --state merged \
  --search "label:python" \
  --json author --limit 200 | \
  jq -r '.[].author | "\(.name) -> @\(.login)"' | sort -u
```

**Make key contributions exhaustive by reviewing each contributor's commits:**

```bash
# Get detailed commits for each contributor
git log "genkit-python@0.4.0"..HEAD --pretty=format:"%s" \
  --author="Contributor Name" -- py/ | head -20
```

Then summarize their work comprehensively, including:
- Specific plugins/features implemented
- Specific samples maintained
- API/config changes made
- Bug fix categories
- Documentation contributions

**Handle cross-name contributors:**

If a contributor uses different names in git vs GitHub (e.g., "Elisa Shen" in git but
"@MengqinShen" on GitHub), add the real name in parentheses:

```markdown
| [**@MengqinShen**](https://github.com/MengqinShen) (Elisa Shen) | 42 | 42 | ... |
```

**Filter contributors by SDK:**

For Python SDK releases, only include contributors with commits under `py/`:

```bash
# Get ONLY Python contributors
git log "genkit-python@0.4.0"..HEAD --pretty=format:"%an" -- py/ | sort | uniq -c | sort -rn
```

Exclude contributors whose work is Go-only, JS-only, or infrastructure-only (unless
their infrastructure work directly benefits the Python SDK).

#### Separate External Repository Contributors

When the Python SDK integrates external projects (like dotprompt), add a separate
contributor table for that project with the **same columns** as the main table:

```markdown
**[google/dotprompt](https://github.com/google/dotprompt) Contributors** (Dotprompt Python integration):

| Contributor | PRs | Commits | Key Contributions |
|-------------|-----|---------|-------------------|
| [**@username**](https://github.com/username) | 50+ | 100+ | **Category**: Feature descriptions with PR numbers. |
| [**@contributor2**](https://github.com/contributor2) | 42 | 45 | **CI/CD**: Package publishing, release automation. |
```

This clearly distinguishes between core SDK contributions and external project contributions.

#### Fast Iteration with --no-verify

When iterating on release documentation, use `--no-verify` to skip pre-commit/pre-push
hooks for faster feedback:

```bash
# Fast commit
git commit --no-verify -m "docs(py): update contributor tables"

# Fast push
git push --no-verify
```

**Only use this for documentation-only changes** where CI verification is not critical.
For code changes, always run full verification.

#### Updating PR Description on GitHub

After updating the PR description file, push it to GitHub:

```bash
# Update the PR body from the file
gh pr edit <PR_NUMBER> --body-file py/.github/PR_DESCRIPTION_X.Y.Z.md
```

### Release Publishing Process

After the release PR is merged, follow these steps to complete the release.

#### Step 1: Merge the Release PR

```bash
# Merge via GitHub UI or CLI
gh pr merge <PR_NUMBER> --squash
```

#### Step 2: Create the Release Tag

```bash
# Ensure you're on main with latest changes
git checkout main
git pull origin main

# Create an annotated tag for the release
git tag -a py/vX.Y.Z -m "Genkit Python SDK vX.Y.Z

See CHANGELOG.md for full release notes."

# Push the tag
git push origin py/vX.Y.Z
```

#### Step 3: Create GitHub Release

Use the PR description as the release body with all contributors mentioned:

```bash
# Create release using the PR description file
gh release create py/vX.Y.Z \
  --title "Genkit Python SDK vX.Y.Z" \
  --notes-file py/.github/PR_DESCRIPTION_X.Y.Z.md
```

**Important:** The GitHub release should include:
- Full contributor tables with GitHub links
- Impact summary
- What's new section
- Critical fixes and security
- Breaking changes (if any)

#### Step 4: Publish to PyPI

Use the publish workflow with the "all" option:

1. Go to **Actions** → **Publish Python Package**
2. Click **Run workflow**
3. Select `publish_scope: all`
4. Click **Run workflow**

This publishes all 23 packages in parallel:

| Package Category | Packages |
|------------------|----------|
| **Core** | `genkit` |
| **Model Providers** | `genkit-plugin-anthropic`, `genkit-plugin-amazon-bedrock`, `genkit-plugin-cloudflare-workers-ai`, `genkit-plugin-deepseek`, `genkit-plugin-google-genai`, `genkit-plugin-huggingface`, `genkit-plugin-mistral`, `genkit-plugin-microsoft-foundry`, `genkit-plugin-ollama`, `genkit-plugin-vertex-ai`, `genkit-plugin-xai` |
| **Telemetry** | `genkit-plugin-aws`, `genkit-plugin-cloudflare-workers-ai`, `genkit-plugin-google-cloud`, `genkit-plugin-observability` (Azure telemetry is included in `genkit-plugin-microsoft-foundry`) |
| **Data/Retrieval** | `genkit-plugin-dev-local-vectorstore`, `genkit-plugin-evaluators`, `genkit-plugin-firebase` |
| **Other** | `genkit-plugin-flask`, `genkit-plugin-compat-oai`, `genkit-plugin-mcp` |

For single package publish (e.g., hotfix):
1. Select `publish_scope: single`
2. Select appropriate `project_type` (packages/plugins)
3. Select the specific `project_name`

#### Step 5: Verify Publication

```bash
# Check versions on PyPI
pip index versions genkit
pip index versions genkit-plugin-google-genai

# Test installation
python -m venv /tmp/genkit-test
source /tmp/genkit-test/bin/activate
pip install genkit genkit-plugin-google-genai
python -c "from genkit.ai import Genkit; print('Success!')"
```

#### v0.5.0 Release Summary

For the v0.5.0 release specifically:

| Metric | Value |
|--------|-------|
| **Commits** | 178 |
| **Files Changed** | 680+ |
| **Contributors** | 13 developers |
| **PRs** | 188 |
| **New PyPI Packages** | 14 (first publish) |
| **Updated PyPI Packages** | 9 (from v0.4.0) |
| **Total Packages** | 23 |

**Packages on PyPI (existing - v0.4.0 → v0.5.0):**
- genkit, genkit-plugin-compat-oai, genkit-plugin-dev-local-vectorstore
- genkit-plugin-firebase, genkit-plugin-flask, genkit-plugin-google-cloud
- genkit-plugin-google-genai, genkit-plugin-ollama, genkit-plugin-vertex-ai

**New Packages (first publish at v0.5.0):**
- genkit-plugin-anthropic, genkit-plugin-aws, genkit-plugin-amazon-bedrock
- genkit-plugin-cloudflare-workers-ai
- genkit-plugin-deepseek, genkit-plugin-evaluators, genkit-plugin-huggingface
- genkit-plugin-mcp, genkit-plugin-mistral, genkit-plugin-microsoft-foundry
- genkit-plugin-observability, genkit-plugin-xai

#### Full Release Guide

For detailed release instructions, see:
- `py/engdoc/release-publishing-guide.md` - Complete step-by-step guide
- `py/.github/PR_DESCRIPTION_0.5.0.md` - v0.5.0 PR description template
- `py/CHANGELOG.md` - Full changelog format

### Version Consistency

All packages (core, plugins, and samples) must have the same version. Use these scripts:

```bash
# Check version consistency
./bin/check_versions

# Fix version mismatches
./bin/check_versions --fix
# or
./bin/bump_version 0.5.0

# Bump to next version
./bin/bump_version --minor    # 0.5.0 -> 0.6.0
./bin/bump_version --patch    # 0.5.0 -> 0.5.1
./bin/bump_version --major    # 0.5.0 -> 1.0.0
```

The `bump_version` script dynamically discovers all packages:
- `packages/genkit` (core)
- `plugins/*/` (all plugins)
- `samples/*/` (all samples)

### Shell Script Linting

All shell scripts in `bin/` and `py/bin/` must pass `shellcheck`. This is enforced
by `bin/lint` and `py/bin/release_check`.

```bash
# Run shellcheck on all scripts
shellcheck bin/* py/bin/*

# Install shellcheck if not present
brew install shellcheck  # macOS
apt install shellcheck   # Debian/Ubuntu
```

**Common shellcheck fixes:**
- Use `"${var}"` instead of `$var` for safer expansion
- Add `# shellcheck disable=SC2034` for intentionally unused variables
- Use `${var//search/replace}` instead of `echo "$var" | sed 's/search/replace/'`

### Shell Script Standards

All shell scripts must follow these standards:

**1. Shebang Line (line 1):**
```bash
#!/usr/bin/env bash
```
- Use `#!/usr/bin/env bash` for portability (not `#!/bin/bash`)
- Must be the **first line** of the file (before license header)

**2. Strict Mode:**
```bash
set -euo pipefail
```
- `-e`: Exit immediately on command failure
- `-u`: Exit on undefined variable usage  
- `-o pipefail`: Exit on pipe failures

**3. Verification Script:**
```bash
# Check all scripts for proper shebang and pipefail
for script in bin/* py/bin/*; do
  if [ -f "$script" ] && file "$script" | grep -qE "shell|bash"; then
    shebang=$(head -1 "$script")
    if [[ "$shebang" != "#!/usr/bin/env bash" ]]; then
      echo "❌ SHEBANG: $script"
    fi
    if ! grep -q "set -euo pipefail" "$script"; then
      echo "❌ PIPEFAIL: $script"
    fi
  fi
done
```

**Exception:** `bin/install_cli` intentionally omits `pipefail` as it's a user-facing
install script that handles errors differently for better user experience.
