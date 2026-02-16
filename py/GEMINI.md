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
  | Model conformance specs | Model plugins have `model-conformance.yaml` + `conformance_entry.py` | ✅ Automated |

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
  **Import-to-Dependency Completeness** *(common error)*:

  Every non-optional `from genkit.plugins.<name> import ...` statement in a
  package's source code **MUST** have a corresponding `genkit-plugin-<name>`
  entry in that package's `pyproject.toml` `dependencies` list. This is the
  most common dependency error — the code imports a plugin but the
  `pyproject.toml` doesn't declare it, causing `ModuleNotFoundError` at
  runtime when the package is installed standalone.

  **Example of the bug** (real case from `provider-vertex-ai-model-garden`):
  ```python
  # src/main.py imports VertexAI from google_genai plugin
  from genkit.plugins.google_genai import VertexAI  # ← needs genkit-plugin-google-genai
  from genkit.plugins.vertex_ai.model_garden import ModelGardenPlugin  # ← needs genkit-plugin-vertex-ai
  ```
  ```toml
  # pyproject.toml was MISSING genkit-plugin-google-genai
  dependencies = [
    "genkit",
    "genkit-plugin-vertex-ai",  # ✅ present
    # "genkit-plugin-google-genai",  # ❌ MISSING — causes ModuleNotFoundError
  ]
  ```

  **Note**: Imports inside `try/except ImportError` blocks (for optional
  platform auto-detection) are exempt from this rule.

  **Dependency Best Practices**:
  * Add dependencies directly to the package that uses them, not transitively
  * Each plugin's `pyproject.toml` should list all packages it imports
  * Use version constraints (e.g., `>=1.0.0`) to allow flexibility
  * Pin exact versions only when necessary for compatibility
  * Remove unused dependencies to keep packages lean
* **Python Version Consistency**: All packages MUST specify `requires-python = ">=3.10"`.
  **This is automatically checked by `py/bin/check_consistency`.**
  The `.python-version` file specifies `3.12` for local development, but CI tests
  against Python 3.10–3.14. Scripts using `uv run` should use `--active` flag to
  respect the CI matrix Python version.
* **Plugin Version Sync**: All plugin versions stay in sync with the core framework
  version. **This is automatically checked by `py/bin/check_consistency`.**
  * Core framework and all plugins share the same version number
  * Samples can have independent versions (typically `0.1.0`)
  * Use semantic versioning (MAJOR.MINOR.PATCH)
  * Bump versions together during releases
* **Production Ready**: The objective is to produce production-grade code.
* **Shift Left**: Employ a "shift left" strategy—catch errors early.
* **Configurability Over Hardcoding**: All tools, scripts, and libraries MUST be
  configurable rather than hardcoded. This is a hard design requirement that applies
  to URLs, registry endpoints, file paths, tool names, thresholds, timeouts, and
  any other value that a user or CI environment might need to override.

  **Rules**:
  * **Never hardcode URLs** — use constructor parameters, config fields, environment
    variables, or CLI flags. Every URL that appears as a string literal must also be
    overridable (e.g. `base_url` parameter with a sensible default).
  * **Expose constants as class attributes** — use `DEFAULT_BASE_URL` / `TEST_BASE_URL`
    patterns so users can reference well-known values without string literals.
  * **CLI flags override config files** — when both a config file field and a CLI flag
    exist for the same setting, the CLI flag takes precedence.
  * **Config files override defaults** — dataclass/struct defaults are the last
    fallback. Config file values override them. CLI flags override config files.
  * **Environment variables for CI** — settings that CI pipelines commonly override
    (registry URLs, tokens, pool sizes, timeouts) should be readable from environment
    variables when a CLI flag is impractical.
  * **No magic constants in business logic** — extract thresholds, retry counts,
    pool sizes, and timeouts into named constants or config fields with docstrings
    explaining the default value.

  **Priority order** (highest wins):
  ```
  CLI flag  >  environment variable  >  config file  >  class/struct default
  ```

  **Examples**:
  ```python
  # WRONG — hardcoded registry URL, not overridable
  class MyRegistry:
      def check(self, pkg: str) -> bool:
          url = f"https://registry.example.com/api/{pkg}"  # ❌ Hardcoded
          ...

  # CORRECT — configurable with sensible default + well-known constant
  class MyRegistry:
      DEFAULT_BASE_URL: str = "https://registry.example.com"
      TEST_BASE_URL: str = "http://localhost:8080"

      def __init__(self, *, base_url: str = DEFAULT_BASE_URL) -> None:
          self._base_url = base_url.rstrip("/")

      def check(self, pkg: str) -> bool:
          url = f"{self._base_url}/api/{pkg}"  # ✅ Configurable
          ...
  ```

  This principle ensures that every tool can be tested against staging/local
  registries, used in air-gapped environments, and adapted to non-standard
  infrastructure without code changes.
* **Fixer Scripts Over Shell Eval**: When fixing lint errors, formatting issues,
  or performing bulk code transformations, **always write a dedicated fixer script**
  instead of evaluating code snippets or one-liners at the shell. This is a hard
  requirement.

  **Rules**:
  * **Never `eval` or `exec` strings at the command line** to fix code. Shell
    one-liners with `sed`, `awk`, `perl -pi -e`, or `python -c` are fragile,
    unreviewable, and unreproducible. They also bypass linting and type checking.
  * **Write a Python fixer script** (e.g. `py/bin/fix_*.py`) that uses the `ast`
    module or `libcst` for syntax-aware transformations. Text-based regex fixes
    are acceptable only for non-Python files (TOML, YAML, Markdown).
  * **Prefer AST-based transforms** over regex for Python code. The `ast` module
    can parse, inspect, and rewrite Python source without breaking syntax. Use
    `ast.parse()` + `ast.NodeVisitor`/`ast.NodeTransformer` for structural changes.
    Use `libcst` when you need to preserve comments and whitespace.
  * **Use `ruff check --fix`** for auto-fixable lint rules before writing custom
    fixers. Ruff can auto-fix many categories (unused imports, formatting, simple
    refactors). Only write a custom fixer for issues Ruff cannot auto-fix.
  * **Fixer scripts must be idempotent** — running them twice produces the same
    result. This allows safe re-runs and CI integration.
  * **Commit fixer scripts** to the repo (in `py/bin/`) so the team can re-run
    them and review the transformation logic.

  **Example — adding missing docstrings to test methods**:
  ```python
  #!/usr/bin/env python3
  """Add missing docstrings to test methods (fixes D102)."""
  import ast
  import sys
  from pathlib import Path

  def fix_file(path: Path) -> int:
      source = path.read_text(encoding='utf-8')
      tree = ast.parse(source)
      # ... walk tree, find methods without docstrings, insert them ...
      path.write_text(new_source, encoding='utf-8')
      return count

  for p in Path(sys.argv[1]).rglob('*_test.py'):
      fix_file(p)
  ```

  **Why this matters**: Shell one-liners are invisible to code review, cannot be
  tested, and often introduce subtle bugs (wrong quoting, partial matches, broken
  indentation). A committed fixer script is reviewable, testable, and documents
  the transformation for future maintainers.

* **Rust-Style Errors with Hints**: Every user-facing error MUST follow the Rust
  compiler's diagnostic style: a **machine-readable error code**, a **human-readable
  message**, and an actionable **hint** that tells the user (or an AI agent) exactly
  how to fix the problem.

  **Rules**:
  * Every custom exception raise MUST include a non-empty `hint` (or equivalent
    guidance field). A raise site without a hint is a bug.
  * The `hint` must be **actionable** — it tells the reader what to do, not just
    what went wrong. Good: `"Run 'git fetch --unshallow' to fetch full history."`
    Bad: `"The repository is shallow."` (that's the message, not a hint).
  * Error codes should use a `PREFIX-NAMED-KEY` format (e.g. `RK-CONFIG-NOT-FOUND`,
    `GK-PLUGIN-NOT-FOUND`). Define codes as enums, not raw strings.
  * For CLI tools, render errors in Rust-style format:
    ```
    error[RK-CONFIG-NOT-FOUND]: No releasekit.toml found in /repo.
      |
      = hint: Run 'releasekit init' to generate a default configuration.
    ```

  **Why hints matter**: Hints are the single most important part of an error for
  both humans and AI agents. An AI reading a hint can self-correct without
  needing to understand the full codebase. A human reading a hint can fix the
  issue without searching docs. Treat a missing hint as a P1 bug.
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

  **Blocking I/O Audit Checklist**:

  When writing or reviewing async code, check for these common sources of
  event-loop blocking. Each pattern looks innocent but can stall the event
  loop for 50-500ms:

  | Pattern | Where it hides | Fix |
  |---------|---------------|-----|
  | `credentials.refresh(Request())` | Google Cloud auth, plugin init | `await asyncio.to_thread(credentials.refresh, req)` |
  | `boto3.client(...)` / `client.invoke(...)` | AWS SDK calls | Use `aioboto3` with `async with session.client(...)` |
  | `requests.get(url)` | Third-party HTTP in async code | Use `httpx.AsyncClient` or `get_cached_client()` |
  | `pathlib.Path.open()` / `open()` | File reads/writes in async methods | Use `aiofiles.open()` |
  | `json.load(open(...))` | Loading config/data in async code | `aiofiles.open()` + `json.loads(await f.read())` |
  | `os.scandir()` / `os.listdir()` | Directory scanning | `await asyncio.to_thread(os.scandir, path)` |
  | `subprocess.run()` | Shelling out from async code | `asyncio.create_subprocess_exec()` |
  | `time.sleep(n)` | Delays in async code | `await asyncio.sleep(n)` |

  **Detection strategy**: Search for these patterns in `async def` functions:

  ```bash
  # Find sync file I/O in async functions
  rg -n 'open\(' --glob '*.py' | rg -v 'aiofiles'

  # Find sync HTTP in async code
  rg -n 'requests\.(get|post|put)' --glob '*.py'
  rg -n 'httpx\.Client\(\)' --glob '*.py'

  # Find blocking credential refresh
  rg -n 'credentials\.refresh' --glob '*.py'

  # Find sync subprocess calls
  rg -n 'subprocess\.(run|call|check_output)' --glob '*.py'
  ```

  **When blocking I/O is acceptable**:

  * **Startup-only code** (e.g., `load_prompt_folder()` reading small `.prompt`
    files): If the I/O happens once during initialization with small files,
    the latency is negligible (~1ms for a few KB). Document the choice.
  * **OpenTelemetry exporters**: The OTEL SDK calls `export()` from its own
    background thread via `BatchSpanProcessor`, so sync HTTP there is by design.
  * **`atexit` handlers**: These run during interpreter shutdown when the event
    loop is already closed. Sync I/O is the only option.
  * **Sync tool functions**: Genkit's `@ai.tool()` can wrap sync functions.
    The framework handles thread offloading. However, prefer async tools for
    network-bound operations.

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
  * **Testing**: Mock `get_cached_client` instead of `httpx.AsyncClient`:
    ```python
    @patch('my_module.get_cached_client')
    async def test_api_call(mock_get_client):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client
        result = await my_api_call()
    ```
  * **Related**: [#4420](https://github.com/firebase/genkit/issues/4420)
* **Security Vulnerability Checks**: Beyond Ruff's S rules, the codebase enforces
  additional security invariants. ReleaseKit has an automated security test suite
  (`py/tools/releasekit/tests/rk_security_test.py`) that demonstrates the pattern.
  Apply these checks to all Python code in the repository:

  **Automated Checks (enforced in CI via test suites)**:

  | # | Check | What It Catches | Severity |
  |---|-------|-----------------|----------|
  | 1 | No `shell=True` | Command injection via subprocess | Critical |
  | 2 | No `pickle`/`yaml.load`/`eval`/`exec` | Arbitrary code execution via deserialization | Critical |
  | 3 | No hardcoded secrets | Literal tokens, AWS keys, GitHub PATs in source | Critical |
  | 4 | No `verify=False` / `CERT_NONE` | TLS certificate verification bypass | Critical |
  | 5 | `NamedTemporaryFile(delete=False)` in `try/finally` | Temp file leak on exception | High |
  | 6 | No bare `except:` | Swallows `KeyboardInterrupt`/`SystemExit` | Medium |
  | 7 | API backends define `__repr__` | Credential leak in tracebacks/logs | High |
  | 8 | Lock files use `O_CREAT\|O_EXCL` | TOCTOU race condition | High |
  | 9 | No `http://` URLs in runtime code | Plaintext traffic (no TLS) | Medium |
  | 10 | State files use `mkstemp` + `os.replace` | Crash corruption on partial writes | High |
  | 11 | `resolve()` on discovered paths | Symlink traversal attacks | Medium |
  | 12 | No `${{ inputs.* }}` string interpolation in CI `run:` | GitHub Actions script injection | Critical |
  | 13 | `hooks.py` uses `shlex.split` + `run_command` | Hook template command injection | High |
  | 14 | No `os.system()` calls | Implicit `shell=True` command injection | Critical |

  **Manual Review Checklist** (for PR reviews):

  | Category | What to Look For | Fix |
  |----------|-----------------|-----|
  | TOCTOU races | Check-then-act on files without atomic ops | `O_CREAT\|O_EXCL`, `mkstemp` + `os.replace` |
  | Log injection | User data in structlog event names | Literals for event names; user data in kwargs |
  | Path traversal | `Path(user_input)` without validation | `.resolve()` + verify under expected root |
  | Credential logging | Objects with tokens in `log.*()` calls | `__repr__` that redacts sensitive fields |
  | Subprocess args | User input in command lists | Validate inputs; never `shell=True` |
  | Temp file cleanup | `NamedTemporaryFile(delete=False)` | Wrap in `try/finally` with `os.unlink` |
  | Atomic writes | `write_text()` for state/config files | `mkstemp` + `os.write` + `os.replace` |
  | Exception swallowing | `except Exception` hiding real errors | Log exception; re-raise if not recoverable |
  | ReDoS | Regex with nested quantifiers on untrusted input | Avoid catastrophic backtracking patterns |
  | CI `${{ inputs }}` | String-type inputs in `run:` blocks | Pass via `env:` block; reference as `$ENV_VAR` |
  | Async/sync boundary | `asyncio.run()` wrapping async from sync | Make caller `async def` and `await` directly |

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
  * **Place `# noqa` on the exact line Ruff flags**: Ruff reports errors on the
    specific line containing the violation, not the statement's opening line. For
    multi-line calls, a `# noqa` comment on the wrong line is silently ignored.

    ```python
    # WRONG — S607 fires on line 2 (the list literal), noqa on line 1 is ignored
    proc = subprocess.run(  # noqa: S603, S607
        ['uv', 'lock', '--check'],  # ← Ruff flags THIS line for S607
        ...
    )

    # CORRECT — each noqa on the line Ruff actually flags
    proc = subprocess.run(  # noqa: S603 - intentional subprocess call
        ['uv', 'lock', '--check'],  # noqa: S607 - uv is a known tool
        ...
    )
    ```
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
  * **Optional Dependencies**: For optional dependencies used in typing (e.g., `litestar`,
    `starlette`) that type checkers can't resolve, **do NOT use inline ignore comments**.
    Instead, add the dependency to the `lint` dependency group in `pyproject.toml`:
    ```toml
    # In pyproject.toml [project.optional-dependencies]
    lint = [
      # ... other lint deps ...
      "litestar>=2.0.0",  # For web/typing.py type resolution
    ]
    ```
    This ensures type checkers can resolve the imports during CI while keeping the
    package optional for runtime.
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

* **No Kitchen-Sink `utils.py`**: Do not dump unrelated helpers into a single
  `utils.py` file. Instead, organise shared utilities into focused modules
  grouped by domain:

  ```
  utils/
  ├── __init__.py
  ├── date.py        # UTC date/time helpers
  ├── packaging.py   # PEP 503/508 name normalisation
  └── text.py        # String formatting helpers
  ```

  **Rules**:
  * Each module in `utils/` must have a single, clear responsibility described
    in its module docstring.
  * If a helper is only used by one module, keep it private in that module
    (prefixed with `_`). Only promote to `utils/` when a second consumer appears.
  * Never create a bare `utils.py` at the package root — always use a `utils/`
    package with sub-modules.
  * Name the sub-module after the *domain* it serves (e.g. `date`, `packaging`,
    `text`), not after the caller (e.g. ~~`prepare_helpers`~~).


## Shell Scripts Reference

The repository provides shell scripts in two locations: `bin/` for repository-wide
tools and `py/bin/` for Python-specific tools.

### Repository-Wide Scripts (`bin/`)

Development workflow scripts at the repository root:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Development Workflow                                 │
│                                                                             │
│   Developer                                                                 │
│      │                                                                      │
│      ├──► bin/setup ──────► Install all tools (Go, Node, Python, Rust)     │
│      │                                                                      │
│      ├──► bin/fmt ────────► Format code (TOML, Python, Go, TypeScript)     │
│      │         │                                                            │
│      │         ├──► bin/add_license ───► Add Apache 2.0 headers            │
│      │         └──► bin/format_toml_files ► Format pyproject.toml          │
│      │                                                                      │
│      ├──► bin/lint ───────► Run all linters and type checkers              │
│      │         │                                                            │
│      │         └──► bin/check_license ──► Verify license headers           │
│      │                                                                      │
│      └──► bin/killports ──► Kill processes on specific ports               │
└─────────────────────────────────────────────────────────────────────────────┘
```

| Script | Purpose | Usage |
|--------|---------|-------|
| `bin/setup` | Install all development tools and dependencies | `./bin/setup -a eng` (full) or `./bin/setup -a ci` (CI) |
| `bin/fmt` | Format all code (TOML, Python, Go, TS) | `./bin/fmt` |
| `bin/lint` | Run all linters and type checkers | `./bin/lint` (from repo root) |
| `bin/add_license` | Add Apache 2.0 license headers to files | `./bin/add_license` |
| `bin/check_license` | Verify license headers and compliance | `./bin/check_license` |
| `bin/format_toml_files` | Format all pyproject.toml files | `./bin/format_toml_files` |
| `bin/golang` | Run commands with specific Go version | `./bin/golang 1.22 test ./...` |
| `bin/run_go_tests` | Run Go tests | `./bin/run_go_tests` |
| `bin/killports` | Kill processes on TCP ports | `./bin/killports 3100..3105 8080` |
| `bin/update_deps` | Update all dependencies | `./bin/update_deps` |
| `bin/install_cli` | Install Genkit CLI binary | `curl -sL cli.genkit.dev \| bash` |

### Python Scripts (`py/bin/`)

Python-specific development and release scripts:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Python Development                                  │
│                                                                             │
│   Developer                                                                 │
│      │                                                                      │
│      ├──► py/bin/run_sample ────────► Interactive sample runner            │
│      │                                                                      │
│      ├──► py/bin/run_python_tests ──► Run tests (all Python versions)      │
│      │                                                                      │
│      └──► py/bin/check_consistency ─► Workspace consistency checks         │
│                                                                             │
│   Release Manager                                                           │
│      │                                                                      │
│      ├──► py/bin/bump_version ──────► Bump version in all packages         │
│      │                                                                      │
│      ├──► py/bin/release_check ─────► Pre-release validation               │
│      │                                                                      │
│      ├──► py/bin/build_dists ───────► Build wheel/sdist packages           │
│      │                                                                      │
│      ├──► py/bin/create_release ────► Create GitHub release                │
│      │                                                                      │
│      └──► py/bin/publish_pypi.sh ───► Publish to PyPI                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

| Script | Purpose | Usage |
|--------|---------|-------|
| **Development** | | |
| `py/bin/run_sample` | Interactive sample runner with fzf/gum | `py/bin/run_sample [sample-name]` |
| `py/bin/test_sample_flows` | Test flows in a sample | `py/bin/test_sample_flows [sample-name]` |
| `py/bin/run_python_tests` | Run tests across Python versions | `py/bin/run_python_tests` |
| `py/bin/watch_python_tests` | Watch mode for tests | `py/bin/watch_python_tests` |
| `py/bin/check_consistency` | Workspace consistency checks | `py/bin/check_consistency` |
| `py/bin/check_versions` | Check version consistency | `py/bin/check_versions` |
| `py/bin/cleanup` | Clean build artifacts | `py/bin/cleanup` |
| **Code Generation** | | |
| `py/bin/generate_schema_typing` | Generate typing.py from JSON schema | `py/bin/generate_schema_typing` |
| **Release** | | |
| `py/bin/bump_version` | Bump version in all packages | `py/bin/bump_version 0.6.0` |
| `py/bin/release_check` | Pre-release validation suite | `py/bin/release_check` |
| `py/bin/validate_release_docs` | Validate release documentation | `py/bin/validate_release_docs` |
| `py/bin/build_dists` | Build wheel and sdist packages | `py/bin/build_dists` |
| `py/bin/create_release` | Create GitHub release | `py/bin/create_release` |
| `py/bin/publish_pypi.sh` | Publish to PyPI | `py/bin/publish_pypi.sh` |
| **Security** | | |
| `py/bin/run_python_security_checks` | Run security scanners | `py/bin/run_python_security_checks` |

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

* **Test Files**: All public classes, methods, and functions in test files MUST
  have docstrings. This includes:
  * **Test classes** (`class TestFoo:`) — describe what is being tested
  * **Test methods** (`def test_bar(self):`) — describe what the test verifies
  * **Fixtures** (`@pytest.fixture def bb():`) — describe what the fixture provides
  * **Helper functions** (`def make_packages():`) — describe what the helper does

  Ruff enforces D101 (missing class docstring), D102 (missing method docstring),
  and D103 (missing function docstring) on all public names. A name is public if
  it does not start with an underscore. Prefix helpers with `_` if they are
  internal to the test module and don't need a docstring.

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

### Core Framework Patterns

**Action Input Validation (Gotcha)**

When implementing low-level action execution (like `arun_raw`), **always check if `raw_input` is `None`** before passing it to Pydantic's `validate_python()`.

* **The Problem**: `validate_python(None)` raises a generic, cryptic `ValidationError` ("Input should be a valid dictionary") instead of telling you the input is missing.
* **The Fix**: Explicitly check for `None` and raise `GenkitError(status='INVALID_ARGUMENT')`.

```python
# WRONG - raises cryptic ValidationError on None
input_action = self._input_type.validate_python(raw_input)

# CORRECT - raises clear GenkitError
if self._input_type is not None:
    if raw_input is None:
        raise GenkitError(
            message=f"Action '{self.name}' requires input.",
            status='INVALID_ARGUMENT'
        )
    input_action = self._input_type.validate_python(raw_input)
```

* This is critical for the Dev UI, which sends `None` payload when the user clicks "Run" without providing JSON input.

### Documentation Best Practices

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
  update relevant documentation and samples. **This is mandatory — every plugin
  change MUST include a sample audit:**
  * Check if any sample under `py/samples/` uses the updated plugin.
  * If new models or features were added, add demo flows to the appropriate
    sample (e.g., `media-models-demo` for new media models, `compat-oai-hello`
    for OpenAI models).
  * Update `README.md` files in affected samples.
  * Update the conformance test specs under `py/tests/conformance/` if model
    capabilities changed.

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

* **Library**: Use `structlog` exclusively for all logging. **Do NOT use the
  standard library `logging` module** (`import logging`) in any new code.
  Existing code using stdlib `logging` should be migrated to structlog when
  touched.

* **Helper**: Use `genkit.core.logging.get_logger(__name__)` to obtain a
  properly typed structlog logger. This is a thin wrapper around
  `structlog.get_logger()` that returns a typed `Logger` instance:

  ```python
  from genkit.core.logging import get_logger

  logger = get_logger(__name__)

  # Sync logging
  logger.info('Model registered', model_name=name, plugin='anthropic')
  logger.debug('Request payload', payload=payload)
  logger.warning('Deprecated config', key=key)

  # Async logging (inside coroutines)
  await logger.ainfo('Generation complete', tokens=usage.total_tokens)
  await logger.adebug('Streaming chunk', index=i)
  ```

* **Async**: Use `await logger.ainfo(...)`, `await logger.adebug(...)`, etc.
  within coroutines. Never use the sync variants (`logger.info(...)`) inside
  `async def` functions — structlog's async methods ensure proper event loop
  integration.

* **Format**: Use structured key-value pairs, not f-strings:

  ```python
  # WRONG - f-string logging
  logger.info(f'Processing model {model_name} with {num_tokens} tokens')

  # CORRECT - structured key-value logging
  logger.info('Processing model', model_name=model_name, num_tokens=num_tokens)
  ```

* **Known Violations**: The following plugins still use stdlib `logging` and
  should be migrated to `genkit.core.logging.get_logger()` when next modified:

  | Plugin | Files |
  |--------|-------|
  | `anthropic` | `models.py`, `utils.py` |
  | `checks` | `plugin.py`, `middleware.py`, `guardrails.py`, `evaluation.py` |
  | `deepseek` | `models.py`, tests |
  | `google-cloud` | `telemetry/tracing.py` |

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

### Dependency Update PRs

When updating `py/uv.lock` (e.g., via `uv sync` or `uv lock --upgrade`), the PR description
MUST include a table of all upgraded packages:

| Package | Old Version | New Version |
|---------|-------------|-------------|
| anthropic | 0.77.0 | 0.78.0 |
| ruff | 0.14.14 | 0.15.0 |
| ... | ... | ... |

To generate this table, use:

```bash
git diff HEAD~1 HEAD -- py/uv.lock | grep -B10 "^-version = " | grep "^.name = " | sed 's/^.name = "\(.*\)"/\1/' | sort -u
```

Then cross-reference with the version changes. This helps reviewers quickly assess the
scope and risk of dependency updates.

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

For PRs involving data processing or multi-step operations, include ASCII data
flow diagrams. See the "Docstrings > Data Flow Diagram" section above for the
standard format and examples.

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

### Model Catalog Accuracy (Mandatory)

**CRITICAL: Never invent model names or IDs.** Every model ID in a plugin's catalog
MUST be verified against the provider's official API documentation before being added.

#### Verification Steps

1. **Check the provider's official model page** (see Provider Documentation Links below)
2. **Confirm the exact API model ID string** — not the marketing name, but the string
   you pass to the API (e.g., `claude-opus-4-6-20260205`, not "Claude Opus 4.6")
3. **Verify the model is GA (Generally Available)** — do not add models that are only
   announced, in private preview, or behind waitlists
4. **Confirm capabilities** — check if the model supports vision, tools, system role,
   structured output, etc. from the official docs
5. **Use date-suffixed IDs as versions** — store the alias (e.g., `claude-opus-4-6`)
   as the key and the dated ID (e.g., `claude-opus-4-6-20260205`) in `versions=[]`

#### Provider API Model Pages

| Provider | Where to verify model IDs |
|----------|---------------------------|
| Anthropic | https://docs.anthropic.com/en/docs/about-claude/models |
| OpenAI | https://platform.openai.com/docs/models |
| xAI | https://docs.x.ai/docs/models |
| Mistral | https://docs.mistral.ai/getting-started/models/models_overview/ |
| DeepSeek | https://api-docs.deepseek.com/quick_start/pricing |
| HuggingFace | https://huggingface.co/docs/api-inference/ |
| AWS Bedrock | https://docs.aws.amazon.com/bedrock/latest/userguide/model-ids.html |
| Azure/Foundry | https://ai.azure.com/catalog/models |
| Cloudflare | https://developers.cloudflare.com/workers-ai/models/ |

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

Document new learnings, patterns, and gotchas at the end of each development
session. Add to existing sections when possible; create new subsections only
when the topic is genuinely new.

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

### Session Learnings (2026-02-07): OpenTelemetry ReadableSpan Wrapper Pitfall

**Issue:** When wrapping OpenTelemetry's `ReadableSpan` without calling
`super().__init__()`, the OTLP trace encoder crashes with `AttributeError`
on `dropped_attributes`, `dropped_events`, or `dropped_links`.

**Root Cause:** The base `ReadableSpan` class defines these properties to access
private instance variables (`_attributes`, `_events`, `_links`) that are only
initialized by `ReadableSpan.__init__()`. If your wrapper skips `super().__init__()`
(intentionally, to avoid duplicating span state), those fields are missing.

**Fix Pattern:** Override all `dropped_*` properties to delegate to the wrapped span:

```python
class MySpanWrapper(ReadableSpan):
    def __init__(self, span: ReadableSpan, ...) -> None:
        # Intentionally skipping super().__init__()
        self._span = span

    @property
    def dropped_attributes(self) -> int:
        return self._span.dropped_attributes

    @property
    def dropped_events(self) -> int:
        return self._span.dropped_events

    @property
    def dropped_links(self) -> int:
        return self._span.dropped_links
```

**Testing:** Use `pytest.mark.parametrize` to test all three properties in a
single test function to reduce duplication (per code review feedback).

**Reference:** PR #4494, Issue #4493.

### Session Learnings (2026-02-10): Code Review Patterns from releasekit PR #4550

Code review feedback from PR #4550 surfaced several reusable patterns:

#### 1. Never Duplicate Defaults

When a dataclass defines field defaults, the factory function that constructs
it should **not** re-specify them. Use `**kwargs` unpacking to let the
dataclass own its defaults:

```python
# BAD — defaults duplicated between dataclass and factory
@dataclass(frozen=True)
class Config:
    tag_format: str = '{name}-v{version}'

def load_config(raw: dict) -> Config:
    return Config(tag_format=raw.get('tag_format', '{name}-v{version}'))  # duplicated!

# GOOD — dataclass is the single source of truth
def load_config(raw: dict) -> Config:
    return Config(**raw)  # dataclass handles missing keys with its own defaults
```

#### 2. Extract Allowed Values as Module-Level Constants

Enum-like validation values should be `frozenset` constants at module level,
not inline literals inside validation functions:

```python
# BAD — allowed values hidden inside function
def _validate_publish_from(value: str) -> None:
    allowed = {'local', 'ci'}  # not discoverable
    if value not in allowed: ...

# GOOD — discoverable, reusable, testable
ALLOWED_PUBLISH_FROM: frozenset[str] = frozenset({'local', 'ci'})

def _validate_publish_from(value: str) -> None:
    if value not in ALLOWED_PUBLISH_FROM: ...
```

#### 3. Wrap All File I/O in try/except

Every `read_text()`, `write_text()`, or `open()` call should be wrapped
with `try/except OSError` to produce a structured error instead of an
unhandled traceback:

```python
# BAD — unprotected I/O
text = path.read_text(encoding='utf-8')

# GOOD — consistent error handling
try:
    text = path.read_text(encoding='utf-8')
except OSError as exc:
    raise ValueError(f'Failed to read {path}: {exc}') from exc
    # In releasekit: raise ReleaseKitError(code=E.PARSE_ERROR, ...) from exc
```

#### 4. Validate Collection Item Types

When validating a config value is a `list`, also validate that the items
inside the list are the expected type:

```python
# BAD — only checks container type
if not isinstance(value, list): raise ...
# A list of ints would pass silently

# GOOD — also checks item types
if not isinstance(value, list): raise ...
for item in value:
    if not isinstance(item, str):
        raise TypeError(f"items must be strings, got {type(item).__name__}")
```

#### 5. Separate Path Globs from Name Globs

Workspace excludes (path globs like `samples/*`) and config excludes (name
globs like `sample-*`) operate in different namespaces and must never be mixed
into a single list. Apply them in independent filter stages.

#### 6. Test File Basename Uniqueness

The `check_consistency` script (check 19/20) enforces unique test file
basenames across the entire workspace. When adding tests to tools or samples,
prefix with a unique identifier:

```
# BAD — collides with samples/web-endpoints-hello/tests/config_test.py
tools/releasekit/tests/config_test.py

# GOOD — unique basename
tools/releasekit/tests/rk_config_test.py
```

#### 7. Use Named Error Codes

Prefer human-readable error codes (`RK-CONFIG-NOT-FOUND`) over numeric
ones (`RK-0001`). Named codes are self-documenting in logs and error
messages without requiring a lookup table.

#### 8. Use `packaging` for PEP 508 Parsing

Never manually parse dependency specifiers by splitting on operators.
Use `packaging.requirements.Requirement` which handles all valid PEP 508
strings correctly (extras, markers, version constraints). For a fallback,
use `re.split(r'[<>=!~,;\[]', spec, maxsplit=1)` — always pass `maxsplit`
as a keyword argument (Ruff B034 requires this to avoid positional
argument confusion).

#### 9. Use `assert` Over `if/pytest.fail` in Tests

Tests should use idiomatic `assert` statements, not `if/pytest.fail()`:

```python
# BAD — verbose and non-standard
if len(graph) != 0:
    pytest.fail(f'Expected empty graph, got {len(graph)}')

# GOOD — idiomatic pytest
assert len(graph) == 0, f'Expected empty graph, got {len(graph)}'
```

**Caution**: When batch-converting `pytest.fail` to `assert` via sed/regex,
the closing `)` from `pytest.fail(...)` can corrupt f-string expressions.
Always re-run lint and tests after automated refactors.

#### 10. Check Dict Key Existence, Not Value Truthiness

When validating whether a config key exists, check `key not in dict`
rather than `not dict.get(key)`. An empty value (e.g., `[]`) is valid
config and should not be treated as missing:

```python
# BAD — empty list raises "unknown group" error
patterns = groups.get(name, [])
if not patterns:
    raise Error("Unknown group")

# GOOD — distinguishes missing from empty
if name not in groups:
    raise Error("Unknown group")
patterns = groups[name]  # may be [], which is valid
```

#### 11. Keyword Arguments for Ambiguous Positional Parameters

Ruff B034 flags `re.split`, `re.sub`, etc. when positional arguments
could be confused (e.g., `maxsplit` vs `flags`). Always use keyword
arguments for clarity:

```python
# BAD — Ruff B034 error
re.split(r'[<>=]', spec, 1)

# GOOD
re.split(r'[<>=]', spec, maxsplit=1)
```

#### 12. Automated Refactors Need Manual Verification

Batch find-and-replace (sed, regex scripts) can introduce subtle bugs:

- **Broken f-strings**: `pytest.fail(f'got {len(x)}')` → the closing `)`
  can end up inside the f-string expression as `{len(x}')`.
- **Missing variable assignments**: removing a multi-line `if/pytest.fail`
  block can accidentally delete the variable assignment above it.
- **Always re-run** `ruff check`, `ruff format`, and `pytest` after any
  automated refactor. Never trust the script output alone.

**Reference:** PR #4550.

### Session Learnings (2026-02-10): Code Review Patterns from releasekit PR #4555

#### 13. Signal Handlers Must Use SIG_DFL + os.kill, Not default_int_handler

`signal.default_int_handler` is only valid for SIGINT (raises
`KeyboardInterrupt`) and doesn't accept the expected arguments. For
general signal cleanup (SIGTERM/SIGINT):

```python
# BAD — only works for SIGINT, wrong argument types
signal.default_int_handler(signum, frame)

# GOOD — works for any signal
signal.signal(signum, signal.SIG_DFL)
os.kill(os.getpid(), signum)
```

#### 14. Extract Shared Parsing Logic into Helper Functions (DRY)

When the same parsing logic appears for both regular and optional
dependencies (or any parallel structures), extract it into a helper:

```python
# BAD — duplicated dep name extraction in two loops
for i, dep in enumerate(deps):
    bare_name = dep.split('[')[0].split('>')[0]...  # fragile, duplicated

# GOOD — helper + packaging.Requirement
def _extract_dep_name(dep_spec: str) -> str:
    try:
        return Requirement(dep_spec).name
    except InvalidRequirement:
        return re.split(r'[<>=!~,;\[]', dep_spec, maxsplit=1)[0].strip()

def _pin_dep_list(deps, version_map) -> int:
    ...  # single implementation, called for both dep lists
```

#### 15. Fail Fast on Required Fields in Serialized Data

When loading JSON/TOML for CI handoff, required fields must fail fast
with a clear error, not silently default to empty strings:

```python
# BAD — silent default hides missing data in downstream CI
git_sha = data.get('git_sha', '')

# GOOD — fail fast with documented ValueError
try:
    git_sha = data['git_sha']
except KeyError as exc:
    raise ValueError(f'Missing required field: git_sha') from exc
```

#### 16. Remove Dead Code Before Submitting

Unused variables and unreachable code paths should be caught during
self-review. Tools like `ruff` catch unused imports, but unused local
variables assigned in loops require manual inspection.

#### 17. Narrow Exception Types in Catch Blocks

Catching `Exception` masks `KeyboardInterrupt`, `SystemExit`, and
unexpected programming errors. Always catch the most specific type:

```python
# BAD — catches KeyboardInterrupt, SystemExit, etc.
except Exception:
    logger.warning('operation failed')

# GOOD — catches only expected failure modes
except OSError:
    logger.warning('operation failed')
```

**Reference:** PR #4555.

#### 18. Scope Commits Per-Package via `vcs.log(paths=...)`

When computing version bumps in a monorepo, each package must only see
commits that touched *its own files*. Fetching all commits globally and
then trying to map them via `diff_files` is error-prone. Instead, use
the VCS backend's `paths` filter:

```python
# BAD — associates ALL commits with any package that has changes
all_commits = vcs.log(format='%H %s')
for pkg in packages:
    changed = vcs.diff_files(since_tag=tag)
    # Tries to match commits to files — misses per-commit scoping

# GOOD — per-package log query with path filtering
for pkg in packages:
    log_lines = vcs.log(since_tag=tag, paths=[str(pkg.path)])
    # Only commits that touched files in pkg.path are returned
```

#### 19. Use `shutil.move` for Atomic File Restore

When restoring from a backup file, `shutil.copy2()` + `unlink()` is
two operations that can leave orphaned backups. `shutil.move()` is
atomic on POSIX same-filesystem (uses `rename(2)`):

```python
# BAD — non-atomic: if unlink fails, backup is orphaned
shutil.copy2(backup_path, target_path)
backup_path.unlink()

# GOOD — atomic on same filesystem
shutil.move(backup_path, target_path)
```

#### 20. Test Orchestration Functions with Fake Backends

Functions like `compute_bumps` that orchestrate multiple subsystems (VCS,
package discovery, commit parsing) need integration tests with fake
backends. A `FakeVCS` that maps paths to log output catches scoping bugs
that unit tests on individual helpers miss.

**Reference:** PR #4555.

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
| 14 | **Create blog article** | Optional: draft in PR description or external blog |
| 15 | **Verify code examples** | Test all code snippets match actual API patterns |
| 16 | **Run release validation** | `./bin/validate_release_docs` (see below) |
| 17 | **Commit with --no-verify** | `git commit --no-verify -m "docs(py): ..."` |
| 18 | **Push with --no-verify** | `git push --no-verify` |
| 19 | **Update PR on GitHub** | `gh pr edit <NUM> --body-file py/.github/PR_DESCRIPTION_X.Y.Z.md` |

#### Automated Release Documentation Validation

Run `py/bin/validate_release_docs` before finalizing release documentation. It
checks branding ("Genkit" not "Firebase Genkit"), non-existent plugin names,
unshipped feature references, blog code syntax, contributor link formatting,
and import validity.

#### Key Principles

1. **Exhaustive contributions**: List every significant feature, fix, and improvement
2. **Clickable GitHub links**: Format as `[@username](https://github.com/username)`
3. **Real names when different**: Show as `@MengqinShen (Elisa Shen)`
4. **Categorize by type**: Use bold headers like **Core**, **Plugins**, **Type Safety**
5. **Include PR numbers**: Every major item should have `(#1234)`
6. **Match table formats**: External repo tables should have same columns as main table
7. **Cross-check repositories**: Check both firebase/genkit and google/dotprompt for Python work
8. **Use --no-verify**: For documentation-only changes, skip hooks for faster iteration
9. **Consider a blog article**: Major releases may warrant a blog article
10. **Branding**: Use "Genkit" not "Firebase Genkit" (rebranded as of 2025)

#### Blog Article Guidelines

Major releases may include a blog article (e.g. in the PR description or an external blog).

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

**Code Example Accuracy** — verify ALL examples match the actual API:

| Pattern | Correct | Wrong |
|---------|---------|-------|
| Text response | `response.text` | `response.text()` |
| Structured output | `output=Output(schema=Model)` | `output_schema=Model` |
| Dynamic tools | `ai.dynamic_tool(name, fn, description=...)` | `@ai.action_provider()` |
| Main function | `ai.run_main(main())` | `asyncio.run(main())` |
| Genkit init | Module-level `ai = Genkit(...)` | Inside `async def main()` |
| Imports | `from genkit.ai import Genkit, Output` | `from genkit import Genkit` |

Cross-check against actual samples: `grep -r "pattern" py/samples/*/src/main.py`.
Only document shipped features — never reference DAP, MCP, etc. unless actually shipped.

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

```bash
# Commits, contributors, and file changes since last release
git log "genkit-python@PREV"..HEAD --oneline -- py/ | wc -l
git log "genkit-python@PREV"..HEAD --pretty=format:"%an" -- py/ | sort | uniq -c | sort -rn
git diff --stat "genkit-python@PREV"..HEAD -- py/ | tail -1

# Map git names to GitHub handles (requires gh CLI)
gh pr list --state merged --search "label:python" --json author --limit 200 \
  | jq -r '.[].author | "\(.name) -> @\(.login)"' | sort -u
```

#### PR Description & Contributors

Create `.github/PR_DESCRIPTION_X.Y.Z.md` for each major release. Required sections:

| Section | Purpose |
|---------|---------|
| **Impact Summary** | Quick overview table with categories |
| **Critical Fixes** | Race conditions, thread safety, security (with PR #s) |
| **Breaking Changes** | Migration guide with before/after examples |
| **Contributors** | Table with PRs, commits, and key contributions |

Contributor table format — use clickable GitHub links:

```markdown
| Contributor | PRs | Commits | Key Contributions |
|-------------|-----|---------|-------------------|
| [**@user**](https://github.com/user) | 91 | 93 | Core framework, plugins |
```

- Only include contributors with commits under `py/`
- For cross-name contributors: `@GitHubName (Real Name)`
- For external repos (e.g., dotprompt), add a separate table with same columns
- Use `--no-verify` for documentation-only commits/pushes
- Update PR body: `gh pr edit <NUM> --body-file py/.github/PR_DESCRIPTION_X.Y.Z.md`

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

### Version Consistency

See "Plugin Version Sync" in the Code Quality section and "Version Bumping"
above for version management details.

## Code Reviewer Preferences

These preferences were distilled from reviewer feedback on Python PRs and should
be followed to minimize review round-trips.

### DRY (Don't Repeat Yourself)

* **Eliminate duplicated logic aggressively.** If the same pattern appears more
  than once (even twice), extract it into a helper function or use data-driven
  lookup tables (`dict`, `enum`).
* **Prefer data-driven patterns over repeated conditionals.** Instead of:
  ```python
  if 'image' in name:
      do_thing(ImageModel, IMAGE_REGISTRY)
  elif 'tts' in name:
      do_thing(TTSModel, TTS_REGISTRY)
  elif 'stt' in name:
      do_thing(STTModel, STT_REGISTRY)
  ```
  Use a lookup table:
  ```python
  _CONFIG: dict[ModelType, tuple[type[Model], dict[str, ModelInfo]]] = {
      ModelType.IMAGE: (ImageModel, IMAGE_REGISTRY),
      ModelType.TTS: (TTSModel, TTS_REGISTRY),
      ModelType.STT: (STTModel, STT_REGISTRY),
  }
  config = _CONFIG.get(model_type)
  if config:
      do_thing(*config)
  ```
* **Shared utility functions across sibling modules.** When two modules
  (e.g., `audio.py` and `image.py`) have identical helper functions, consolidate
  into one and import from the other. Re-export with an alias if needed for
  backward compatibility.
* **Extract common logic into utility functions that can be tested
  independently and exhaustively.** Data URI parsing, config extraction,
  media extraction, and similar reusable patterns should live in a `utils.py`
  module with comprehensive unit tests covering edge cases (malformed input,
  empty strings, missing fields, etc.). This improves coverage and makes the
  correct behavior verifiable without mocking external APIs.
* **Extract shared info dict builders.** When the same metadata serialization
  logic (e.g., `model_info.model_dump()` with fallback) appears in both Action
  creation and ActionMetadata creation, extract a single helper like
  `_get_multimodal_info_dict(name, model_type, registry)` and call it from both.
* **Re-assert `isinstance` after `next()` for type narrowing.** Type checkers
  can't track narrowing inside generator expressions. After `next()`, re-assert
  `isinstance(part.root, MediaPart)` locally so the checker can narrow:
  ```python
  part_with_media = next(
      (p for p in content if isinstance(p.root, MediaPart)),
      None,
  )
  if part_with_media:
      # Re-assert to help type checkers narrow the type of part_with_media.root
      assert isinstance(part_with_media.root, MediaPart)
      # Now the type checker knows part_with_media.root is a MediaPart
      url = part_with_media.root.media.url
  ```
* **Hoist constant lookup tables to module level.** Don't recreate `dict`
  literals inside functions on every call. Define them once at module scope:
  ```python
  # Module level — created once.
  _CONTENT_TYPE_TO_EXTENSION: dict[str, str] = {'audio/mpeg': 'mp3', ...}

  def _to_stt_params(...):
      ext = _CONTENT_TYPE_TO_EXTENSION.get(content_type, 'mp3')
  ```
### Type Safety and Redundancy

* **Remove redundant `str()` casts after `isinstance` checks.** If you guard
  with `isinstance(part.root, TextPart)`, then `part.root.text` is already `str`.
  Don't wrap it in `str()` again.
* **Remove unnecessary fallbacks on required fields.** If a Pydantic model field
  is required (not `Optional`), don't write `str(field or '')` — just use `field`
  directly.
* **Use `isinstance` over `hasattr` for type checks.** Prefer
  `isinstance(part.root, TextPart)` over `hasattr(part.root, 'text')` for
  type-safe attribute access.

### Pythonic Idioms

* **Use `next()` with generators for find-first patterns.** Instead of a loop
  with `break`:
  ```python
  # Don't do this:
  result = None
  for item in collection:
      if condition(item):
          result = item
          break

  # Do this:
  result = next((item for item in collection if condition(item)), None)
  ```
* **Use `split(',', 1)` over `index(',')` for parsing.** `split` with `maxsplit`
  is more robust and Pythonic for separating a string into parts:
  ```python
  # Don't do this:
  data = s[s.index(',') + 1:]

  # Do this:
  _, data = s.split(',', 1)
  ```

### Async/Sync Correctness

* **Don't mark functions `async` if they contain only synchronous code.** A
  function that only does `response.read()`, `base64.b64encode()`, etc., should
  be a regular `def`, not `async def`.
* **Use `AsyncOpenAI` consistently for async code paths.** New async model
  classes should use `AsyncOpenAI`, not the synchronous `OpenAI` client.
* **Never use sync clients for network calls inside `async` methods.** If
  `list_actions` or `resolve` is `async def`, all network calls within it must
  use the async client and `await`. A sync call like
  `self._openai_client.models.list()` blocks the event loop.
* **Update tests when switching sync→async.** When changing a method to use
  the async client, update the corresponding test mocks to use `AsyncMock`
  and patch the `_async_client` attribute instead of the sync one.

### Threading, Asyncio & Event-Loop Audit Checklist

When reviewing code that involves concurrency, locks, or shared mutable state,
check for every issue in this list. These are real bugs found during audits —
not theoretical concerns.

#### Lock type mismatches

* **Never use `threading.Lock` or `threading.RLock` in async code.** These
  block the *entire* event loop thread while held. Use `asyncio.Lock` instead.
  This applies to locks you create *and* to locks inside third-party libraries
  you call (e.g. `pybreaker` uses a `threading.RLock` internally).
  ```python
  # BAD — blocks event loop
  self._lock = threading.Lock()
  with self._lock:
      ...

  # GOOD — cooperatively yields
  self._lock = asyncio.Lock()
  async with self._lock:
      ...
  ```
* **Be wary of third-party libraries that use threading locks internally.**
  If you wrap a sync library for async use and access its internals (private
  `_lock`, `_state_storage`, etc.), you inherit its threading-lock problem.
  This is a reason to prefer custom async-native implementations over
  wrapping sync-only libraries — see the OSS evaluation notes below.

#### Time functions

* **Use `time.monotonic()` for interval/duration measurement, not
  `time.time()` or `datetime.now()`.** Wall-clock time is subject to NTP
  corrections that can jump forward or backward, breaking timeouts, TTLs,
  and retry-after calculations. `time.monotonic()` only moves forward.
  ```python
  # BAD — subject to NTP jumps
  start = time.time()
  elapsed = time.time() - start

  # BAD — same problem, datetime edition
  opened_at = datetime.now(timezone.utc)
  elapsed = datetime.now(timezone.utc) - opened_at

  # GOOD — monotonically increasing
  start = time.monotonic()
  elapsed = time.monotonic() - start
  ```
* **Call time functions once and reuse the value** when the same timestamp
  is needed in multiple expressions. Two calls can return different values.
* **Clamp computed `retry_after` values** to a reasonable range (e.g.
  `[0, 3600]`) to guard against anomalous clock behavior.

#### Race conditions (TOCTOU)

* **Check-then-act on shared state must be atomic.** If you check a condition
  (e.g. cache miss) and then act on it (execute expensive call + store result),
  the two steps must be inside the same lock acquisition or protected by
  per-key coalescing. Otherwise concurrent coroutines all see the same "miss"
  and duplicate the work (cache stampede / thundering herd).
  ```python
  # BAD — stampede window between check and set
  async with self._lock:
      entry = self._store.get(key)
      if entry is not None:
          return entry.value
  result = await expensive_call()  # N coroutines all reach here
  async with self._lock:
      self._store[key] = result

  # GOOD — per-key lock prevents concurrent duplicate calls
  async with self._get_key_lock(key):
      async with self._store_lock:
          entry = self._store.get(key)
          if entry is not None:
              return entry.value
      result = await expensive_call()  # only 1 coroutine per key
      async with self._store_lock:
          self._store[key] = result
  ```
* **Half-open circuit breaker probes** must be gated so only one probe
  coroutine is in flight. Without a flag or counter checked inside the lock,
  the lock is released before `await fn()`, and multiple coroutines can all
  transition to half-open and probe simultaneously.
* **`exists()` + `delete()` is a TOCTOU race.** The key can expire or be
  deleted between the two calls. Prefer a single `delete()` call.

#### Blocking the event loop

* **Any synchronous library call that does network I/O will block the event
  loop.** This includes: Redis clients, Memcached clients, database drivers,
  HTTP clients, file I/O, and DNS resolution. Wrap in `asyncio.to_thread()`
  or use an async-native library.
* **Sub-microsecond sync calls are acceptable** (dict lookups, counter
  increments, in-memory data structure operations) — wrapping them in
  `to_thread()` would add more overhead than the call itself.

#### Counter and stat safety

* **Integer `+=` between `await` points is safe** in single-threaded asyncio
  (CPython's GIL ensures `+=` on an int is atomic at the bytecode level, and
  no other coroutine can interleave between the read and write without an
  `await`). But this assumption is fragile:
  - Document it explicitly in docstrings.
  - If the counter is mutated near `await` calls, move it inside a lock.
  - If the code might run from multiple threads (e.g. `to_thread()`), use
    a lock or `asyncio.Lock`.

#### OSS library evaluation: when custom is better

* **Prefer custom async-native implementations** over wrapping sync-only
  libraries when the wrapper must access private internals, reimplement half
  the library's logic, or ends up the same line count. Specific examples:
  - `pybreaker` — sync-only, uses `threading.RLock`, requires accessing
    `_lock`, `_state_storage`, `_handle_error`, `_handle_success` (all
    private). Uses `datetime.now()` instead of `time.monotonic()`.
  - `aiocache.SimpleMemoryCache` — no LRU eviction, no stampede prevention,
    weak type hints (`Any` return). Custom `OrderedDict` cache is fewer lines.
  - `limits` — sync-only API, uses `time.time()`, fixed-window algorithm
    allows boundary bursts. Custom token bucket is ~25 lines.
* **Prefer OSS when the library is genuinely async, well-typed, and provides
  functionality you'd otherwise have to maintain.** Example: `secure` for
  OWASP security headers — it tracks evolving browser standards and header
  deprecations (e.g. X-XSS-Protection removal) that are tedious to follow
  manually.

### Configuration and State

* **Never mutate `request.config` in-place.** Always `.copy()` the config dict
  before calling `.pop()` on it to avoid side effects on callers:
  ```python
  # Don't do this:
  config = request.config  # mutates caller's dict!
  model = config.pop('version', None)

  # Do this:
  config = request.config.copy()
  model = config.pop('version', None)
  ```

### Metadata and Fallbacks

* **Always provide default metadata for dynamically discovered models.** When a
  model isn't found in a registry, provide sensible defaults (label, supports)
  rather than returning an empty dict. This ensures all resolved actions have
  usable metadata.

### Testing Style

* **Use `assert` statements, not `if: pytest.fail()`.** For consistency:
  ```python
  # Don't do this:
  if not isinstance(part, MediaPart):
      pytest.fail('Expected MediaPart')

  # Do this:
  assert isinstance(part, MediaPart)
  ```
* **Add `assert obj is not None` before accessing optional attributes.** This
  satisfies type checker null-safety checks and serves as documentation:
  ```python
  got = some_function()
  assert got.message is not None
  part = got.message.content[0].root
  ```

### Exports and Organization

* **Keep `__all__` lists sorted alphabetically (case-sensitive).** Uppercase
  names sort before lowercase (e.g., `'OpenAIModel'` before `'get_default_model_info'`).
  This makes diffs cleaner and items easier to find.

### Module Dependencies

* **Never import between sibling model modules.** If `image.py` and `audio.py`
  share utility functions, move the shared code to a `utils.py` in the same
  package. This avoids creating fragile coupling between otherwise independent
  model implementations.

### Input Validation and Robustness

* **Validate data URI schemes explicitly.** Don't rely on heuristics like
  `',' in url` to detect data URIs. Check for known prefixes:
  ```python
  # Don't do this:
  if ',' in url:
      _, data = url.split(',', 1)
  else:
      data = url  # Could be https://... which will crash b64decode

  # Do this:
  if url.startswith('data:'):
      _, data = url.split(',', 1)
      result = base64.b64decode(data)
  elif url.startswith(('http://', 'https://')):
      raise ValueError('Remote URLs not supported; provide a data URI')
  else:
      result = base64.b64decode(url)  # raw base64 fallback
  ```
* **Wrap decode calls in try/except.** `base64.b64decode` and `split` can fail
  on malformed input. Wrap with descriptive `ValueError`:
  ```python
  try:
      _, b64_data = media_url.split(',', 1)
      audio_bytes = base64.b64decode(b64_data)
  except (ValueError, TypeError) as e:
      raise ValueError('Invalid data URI format') from e
  ```
* **Use `TypeAlias` for complex type annotations.** When a type hint is long
  or repeated, extract a `TypeAlias` for readability:
  ```python
  from typing import TypeAlias

  _MultimodalModel: TypeAlias = OpenAIImageModel | OpenAITTSModel | OpenAISTTModel
  _MultimodalModelConfig: TypeAlias = tuple[type[_MultimodalModel], dict[str, ModelInfo]]

  _MULTIMODAL_CONFIG: dict[_ModelType, _MultimodalModelConfig] = { ... }
  ```
* **Use raising helpers and non-raising helpers.** When the same extraction
  logic is needed in both required and optional contexts, split into two
  functions — one that returns `None` on failure, and a strict wrapper:
  ```python
  def _find_text(request) -> str | None:
      """Non-raising: returns None if not found."""
      ...

  def _extract_text(request) -> str:
      """Raising: delegates to _find_text, raises ValueError on None."""
      text = _find_text(request)
      if text is not None:
          return text
      raise ValueError('No text content found')
  ```

### Defensive Action Resolution

* **Guard symmetrically against misrouted action types in `resolve()`.** Apply
  `_classify_model` checks in both directions — prevent embedders from being
  resolved as models AND prevent non-embedders from being resolved as embedders:
  ```python
  if action_type == ActionKind.EMBEDDER:
      if _classify_model(name) != _ModelType.EMBEDDER:
          return None  # Not an embedder name.
      return self._create_embedder_action(name)

  if action_type == ActionKind.MODEL:
      model_type = _classify_model(name)
      if model_type == _ModelType.EMBEDDER:
          return None  # Embedder name shouldn't create a model action.
      ...
  ```

### Code Simplification

* **Collapse multi-branch conditionals into single expressions.** When multiple
  branches assign a value and fall through to a default:
  ```python
  # Don't do this:
  if custom_format:
      params['response_format'] = custom_format
  elif output_format == 'json':
      params['response_format'] = 'json'
  elif output_format == 'text':
      params['response_format'] = 'text'
  else:
      params.setdefault('response_format', 'text')

  # Do this:
  response_format = config.pop('response_format', None)
  if not response_format and request.output and request.output.format in ('json', 'text'):
      response_format = request.output.format
  params['response_format'] = response_format or 'text'
  ```
* **Separate find-first from processing.** When using `next()` to find an
  element and then processing it, keep both steps distinct. Don't combine
  complex processing logic inside the generator expression:
  ```python
  # Do this:
  part = next(
      (p for p in content if isinstance(p.root, MediaPart) and p.root.media),
      None,
  )
  if not part:
      raise ValueError('No media found')
  media = part.root.media
  # ... process media ...
  ```
* **Avoid `continue` in loops when a simple conditional suffices.** Compute
  the value first, then conditionally use it:
  ```python
  # Don't do this:
  for image in images:
      if image.url:
          url = image.url
      elif image.b64_json:
          url = f'data:...;base64,{image.b64_json}'
      else:
          continue
      content.append(...)

  # Do this:
  for image in images:
      url = image.url
      if not url and image.b64_json:
          url = f'data:...;base64,{image.b64_json}'
      if url:
          content.append(...)
  ```

### Security Design & Production Hardening

When building samples, plugins, or services in this repository, follow these
security design principles. These are not theoretical guidelines — they come
from real issues found during audits of the `web-endpoints-hello` sample and
apply broadly to any Python service that uses Genkit.

#### Secure-by-default philosophy

* **Every default must be the restrictive option.** If someone deploys with
  zero configuration, the system should be locked down. Development
  convenience (Swagger UI, open CORS, colored logs, gRPC reflection) requires
  explicit opt-in.
  ```python
  # BAD — open by default, must remember to close
  cors_allowed_origins: str = "*"
  debug: bool = True

  # GOOD — closed by default, must opt in
  cors_allowed_origins: str = ""   # same-origin only
  debug: bool = False              # no Swagger, no reflection
  ```
* **When adding a new setting, ask:** "If someone forgets to configure this,
  should the system be open or closed?" Always choose closed.
* **Log a warning for insecure configurations** at startup so operators notice
  immediately. Don't silently accept an insecure state.
  ```python
  # GOOD — warn when host-header validation is disabled in production
  if not trusted_hosts and not debug:
      logger.warning(
          "No TRUSTED_HOSTS configured — Host-header validation is disabled."
      )
  ```

#### Debug mode gating

* **Gate all development-only features behind a single `debug` flag.**
  This includes: API documentation (Swagger UI, ReDoc, OpenAPI schema), gRPC
  reflection, relaxed Content-Security-Policy, verbose error responses,
  wildcard CORS fallbacks, and colored console log output.
  ```python
  # GOOD — single flag controls all dev features
  app = FastAPI(
      docs_url="/docs" if debug else None,
      redoc_url="/redoc" if debug else None,
      openapi_url="/openapi.json" if debug else None,
  )
  ```
* **Never expose API schema in production.** Swagger UI, ReDoc, `/openapi.json`,
  and gRPC reflection all reveal the full API surface. Disable them when
  `debug=False`.
* **Use `--debug` as the CLI flag** and `DEBUG` as the env var. The `run.sh`
  dev script should pass `--debug` automatically; production entry points
  (gunicorn, Kubernetes manifests, Cloud Run) should never set it.

#### Content-Security-Policy

* **Production CSP should be `default-src none`** for API-only servers. This
  blocks all resource loading (scripts, styles, images, fonts, frames).
* **Debug CSP must explicitly allowlist CDN origins** for Swagger UI (e.g.
  `cdn.jsdelivr.net` for JS/CSS, `fastapi.tiangolo.com` for the favicon).
  Never use `unsafe-eval`.
* **Use the `secure` library** rather than hand-crafting header values. It
  tracks evolving OWASP recommendations (e.g. it dropped `X-XSS-Protection`
  before most people noticed the deprecation).

#### CORS

* **Default to same-origin (empty allowlist)**, not wildcard. Wildcard CORS
  allows any website to make cross-origin requests to your API.
  ```python
  # BAD — any website can call your API
  cors_allowed_origins: str = "*"

  # GOOD — deny cross-origin by default
  cors_allowed_origins: str = ""
  ```
* **In debug mode, fall back to `["*"]`** when no origins are configured so
  Swagger UI and local dev tools work without manual config.
* **Use explicit `allow_headers` lists**, not `["*"]`. Wildcard allowed headers
  let arbitrary custom headers through CORS preflight, enabling cache
  poisoning or header injection attacks.
  ```python
  # BAD — any header allowed
  allow_headers=["*"]

  # GOOD — only headers the API actually uses
  allow_headers=["Content-Type", "Authorization", "X-Request-ID"]
  ```

#### Rate limiting

* **Apply rate limits at both REST and gRPC layers.** They share the same
  algorithm (token bucket per client IP / peer) but are independent middleware.
* **Exempt health check paths** (`/health`, `/healthz`, `/ready`, `/readyz`)
  from rate limiting so orchestration platforms can always probe.
* **Include `Retry-After` in 429 responses** so well-behaved clients know when
  to retry.
* **Use `time.monotonic()` for token bucket timing**, not `time.time()`. See
  the "Threading, Asyncio & Event-Loop Audit Checklist" above.

#### Request body limits

* **Enforce body size limits before parsing.** Use an ASGI middleware that
  checks `Content-Length` before the framework reads the body. This prevents
  memory exhaustion from oversized payloads.
* **Apply the same limit to gRPC** via `grpc.max_receive_message_length`.
* **Default to 1 MB** (1,048,576 bytes). LLM API requests are typically text,
  not file uploads.

#### Input validation

* **Use Pydantic `Field` constraints on every input model** — `max_length`,
  `min_length`, `ge`, `le`, `pattern`. This rejects malformed input before
  it reaches any flow or LLM call.
* **Use `pattern` for freeform string fields** that should be constrained
  (e.g. programming language names: `^[a-zA-Z#+]+$`).
* **Sanitize text before passing to the LLM** — `strip()` whitespace and
  truncate to a reasonable maximum. This is a second line of defense after
  Pydantic validation.

#### ASGI middleware stack order

* **Apply middleware inside-out** in `apply_security_middleware()`. The
  request-flow order is:

  ```
  AccessLog → GZip → CORS → TrustedHost → Timeout → MaxBodySize
    → ExceptionHandler → SecurityHeaders → RequestId → App
  ```

  The response passes through the same layers in reverse.

#### Security headers (OWASP)

* **Use pure ASGI middleware**, not framework-specific mechanisms. This ensures
  headers are applied identically across FastAPI, Litestar, Quart, or any
  future framework.
* **Mandatory headers** for every HTTP response:

  | Header | Value | Purpose |
  |--------|-------|---------|
  | `Content-Security-Policy` | `default-src none` | Block resource loading |
  | `X-Content-Type-Options` | `nosniff` | Prevent MIME-sniffing |
  | `X-Frame-Options` | `DENY` | Block clickjacking |
  | `Referrer-Policy` | `strict-origin-when-cross-origin` | Limit referrer leakage |
  | `Permissions-Policy` | `geolocation=(), camera=(), microphone=()` | Disable browser APIs |
  | `Cross-Origin-Opener-Policy` | `same-origin` | Isolate browsing context |

* **Add HSTS conditionally** — only when the request arrived over HTTPS.
  Sending `Strict-Transport-Security` over plaintext HTTP is meaningless and
  can confuse testing.
* **Omit `X-XSS-Protection`** — the browser XSS auditor it controlled was
  removed from all modern browsers, and setting it can introduce XSS in
  older browsers (OWASP recommendation since 2023).

#### Request ID / correlation

* **Generate or propagate `X-Request-ID` on every request.** If the client
  sends one (e.g. from a load balancer), reuse it for end-to-end tracing.
  Otherwise, generate a UUID4.
* **Bind the ID to structlog context vars** so every log line includes
  `request_id` without manual passing.
* **Echo the ID in the response header** for client-side correlation.

#### Trusted host validation

* **Validate the `Host` header** when running behind a reverse proxy. Without
  this, host-header poisoning can cause cache poisoning, password-reset
  hijacking, and SSRF.
* **Log a warning at startup** if `TRUSTED_HOSTS` is empty in production
  mode so operators notice immediately.

#### Structured logging & secret masking

* **Default to JSON log format** in production. Colored console output is
  human-friendly but breaks log aggregation pipelines (CloudWatch, Stackdriver,
  Datadog).
* **Override to `console` in `local.env`** for development.
* **Include `request_id` in every log entry** (via structlog context vars).
* **Never log secrets.** Use a structlog processor to automatically redact
  API keys, tokens, passwords, and DSNs from log output. Match patterns like
  `AIza...`, `Bearer ...`, `token=...`, `password=...`, and any field whose
  name contains `key`, `secret`, `token`, `password`, `credential`, or `dsn`.
  Show only the first 4 and last 2 characters (e.g. `AI****Qw`).

#### HTTP access logging

* **Log every request** with method, path, status code, and duration. This is
  essential for observability and debugging latency issues.
* **Place the access log middleware outermost** so timing includes all
  middleware layers (security checks, compression, etc.).

#### Per-request timeout

* **Enforce a per-request timeout** via ASGI middleware. If a handler exceeds
  the configured timeout, return 504 Gateway Timeout immediately instead of
  letting it hang indefinitely.
* **Make the timeout configurable** via `REQUEST_TIMEOUT` env var and CLI flag.
  Default to a generous value (120s) for LLM calls.

#### Global exception handler

* **Catch unhandled exceptions in middleware** and return a consistent JSON
  error body (`{"error": "Internal Server Error", "detail": "..."}`).
* **Never expose stack traces to clients in production.** Log the full
  traceback server-side (via structlog / Sentry) for debugging.
* **In debug mode**, include the traceback in the response for developer
  convenience.

#### Server header suppression

* **Remove the `Server` response header** to prevent version fingerprinting.
  ASGI servers (uvicorn, granian, hypercorn) emit `Server: ...` by default,
  which reveals the server software and version to attackers.

#### Cache-Control

* **Set `Cache-Control: no-store`** on all API responses. This prevents
  intermediaries (CDNs, proxies) and browsers from caching sensitive API
  responses.

#### GZip response compression

* **Compress responses above a configurable threshold** (default: 500 bytes)
  using `GZipMiddleware`. This reduces bandwidth for JSON-heavy API responses.
* **Make the minimum size configurable** via `GZIP_MIN_SIZE` env var and CLI.

#### Graceful shutdown

* **Handle SIGTERM with a configurable grace period.** Cloud Run sends SIGTERM
  and gives 10s by default. Kubernetes may give 30s.
* **Drain in-flight requests** before exiting. For gRPC, use
  `server.stop(grace=N)`. For ASGI servers, rely on the server's native
  shutdown signal handling.

#### Connection tuning

* **Set keep-alive timeout above the load balancer's idle timeout.** If the LB
  has a 60s idle timeout (typical for Cloud Run, ALB), set the server's
  keep-alive to 75s. Otherwise the server closes the connection while the LB
  thinks it's still alive, causing 502s.
* **Set explicit LLM API timeouts.** The default should be generous (120s) but
  not infinite. Without a timeout, a hung LLM call ties up a worker forever.
* **Cap connection pool size** to prevent unbounded outbound connections (e.g.
  100 max connections, 20 keepalive).

#### Circuit breaker

* **Use async-native circuit breakers** (not sync wrappers like `pybreaker`
  that use `threading.RLock` — see the async/event-loop checklist above).
* **States**: Closed (normal) → Open (fail fast) → Half-open (probe).
* **Use `time.monotonic()`** for recovery timeout measurement.
* **Gate half-open probes** so only one coroutine probes at a time (prevent
  stampede on recovery).

#### Response cache

* **Use per-key request coalescing** to prevent cache stampedes. Without it,
  N concurrent requests for the same key all trigger N expensive LLM calls
  (thundering herd).
* **Use `asyncio.Lock` per cache key**, not a single global lock (which
  serializes all cache operations).
* **Use `time.monotonic()` for TTL**, not `time.time()`.
* **Hash cache keys with SHA-256** for fixed-length, collision-resistant keys.

#### Container security

* **Use distroless base images** (`gcr.io/distroless/python3-debian13:nonroot`):
  - No shell — cannot `exec` into the container
  - No package manager — no `apt install` attack vector
  - No `setuid` binaries
  - Runs as uid 65534 (`nonroot`)
  - ~50 MB (vs ~150 MB for `python:3.13-slim`)
* **Multi-stage builds** — install dependencies in a builder stage, copy only
  the virtual environment and source code to the final distroless stage.
* **Pin base image digests** in production Containerfiles to prevent supply
  chain attacks from tag mutations.
* **Never copy `.env` files or secrets into container images.** Pass secrets
  via environment variables or a secrets manager at runtime.

#### Dependency auditing

* **Run `pip-audit` in CI** to check for known CVEs in dependencies.
* **Run `pysentry-rs`** against frozen (exact) dependency versions, not version
  ranges from `pyproject.toml`. Version ranges can report false positives for
  vulnerabilities fixed in later versions.
  ```bash
  # BAD — false positives from minimum version ranges
  pysentry-rs pyproject.toml

  # GOOD — audit exact installed versions
  uv pip freeze > /tmp/requirements.txt
  pysentry-rs /tmp/requirements.txt
  ```
* **Run `liccheck`** to verify all dependencies use approved licenses (Apache-2.0,
  MIT, BSD, PSF, ISC, MPL-2.0). Add exceptions for packages with unknown
  metadata to `[tool.liccheck.authorized_packages]` in `pyproject.toml`.
* **Run `addlicense`** to verify all source files have the correct license header.

#### Platform telemetry auto-detection

* **Auto-detect cloud platform at startup** by checking environment variables
  set by the platform (e.g. `K_SERVICE` for Cloud Run, `AWS_EXECUTION_ENV`
  for ECS).
* **Don't trigger on ambiguous signals.** `GOOGLE_CLOUD_PROJECT` is set on
  most developer machines for `gcloud` CLI use — it doesn't mean the app is
  running on GCP. Require a stronger signal (`K_SERVICE`, `GCE_METADATA_HOST`)
  or an explicit opt-in (`GENKIT_TELEMETRY_GCP=1`).
* **Guard all platform plugin imports with `try/except ImportError`** since
  they are optional dependencies. Log a warning (not an error) if the plugin
  is not installed.

#### Sentry integration

* **Only activate when `SENTRY_DSN` is set** (no DSN = completely disabled).
* **Set `send_default_pii=False`** to strip personally identifiable information.
* **Auto-detect the active framework** (FastAPI, Litestar, Quart) and enable
  the matching Sentry integration. Don't require the operator to configure it.
* **Include gRPC integration** so both REST and gRPC errors are captured.

#### Error tracking and responses

* **Never expose stack traces to clients in production.** Framework default
  error handlers may include tracebacks in HTML responses. Use middleware or
  exception handlers to return consistent JSON error bodies.
* **Consistent error format** for all error paths:
  ```json
  {"error": "Short Error Name", "detail": "Human-readable explanation"}
  ```
* **Log the full traceback server-side** (via structlog / Sentry) for debugging.

#### Health check endpoints

* **Provide both `/health` (liveness) and `/ready` (readiness)** probes.
* **Keep them lightweight** — don't call the LLM API or do expensive work.
* **Exempt them from rate limiting** so orchestration platforms can always probe.
* **Return minimal JSON** (`{"status": "ok"}`) — don't expose internal state,
  version numbers, or configuration in health responses.

#### Environment variable conventions

* **Use `SCREAMING_SNAKE_CASE`** for all environment variables.
* **Use pydantic-settings `BaseSettings`** to load from env vars and `.env`
  files with type validation.
* **Support `.env` file layering**: `.env` (shared defaults) → `.<env>.env`
  (environment-specific overrides, e.g. `.local.env`, `.staging.env`).
* **Gitignore all `.env` files** (`**/*.env`) to prevent secret leakage.
  Commit only the `local.env.example` template.

#### Production hardening checklist

When reviewing a sample or service for production readiness, verify each item:

| Check | What to verify |
|-------|---------------|
| `DEBUG=false` | Swagger UI, gRPC reflection, relaxed CSP all disabled |
| CORS locked down | `CORS_ALLOWED_ORIGINS` is not `*` (or empty for same-origin) |
| Trusted hosts set | `TRUSTED_HOSTS` configured for the deployment domain |
| Rate limits tuned | `RATE_LIMIT_DEFAULT` appropriate for expected traffic |
| Body size limit | `MAX_BODY_SIZE` set for the expected payload sizes |
| Request timeout | `REQUEST_TIMEOUT` set appropriately (default: 120s) |
| Secret masking | Log processor redacts API keys, tokens, passwords, DSNs |
| Access logging | Every request logged with method, path, status, duration |
| Exception handler | Global middleware returns JSON 500; no tracebacks to clients |
| Server header removed | `Server` response header suppressed (no version fingerprinting) |
| Cache-Control | `no-store` on all API responses |
| GZip compression | `GZIP_MIN_SIZE` tuned for response payload sizes |
| HSTS enabled | `HSTS_MAX_AGE` set; only sent over HTTPS |
| Log format | `LOG_FORMAT=json` for structured log aggregation |
| Secrets managed | No `.env` files in production; use secrets manager |
| TLS termination | HTTPS via load balancer or reverse proxy |
| Error tracking | `SENTRY_DSN` set (or equivalent monitoring) |
| Container hardened | Distroless, nonroot, no shell, no secrets baked in |
| Dependencies audited | `pip-audit` and `liccheck` pass in CI |
| Telemetry configured | Platform telemetry or OTLP endpoint set |
| Graceful shutdown | `SHUTDOWN_GRACE` appropriate for the platform |
| Keep-alive tuned | Server keep-alive > load balancer idle timeout |

## GitHub Actions Security

### Avoid `eval` in Shell Steps

Never use `eval "$CMD"` to run dynamically-constructed commands in GitHub
Actions `run:` steps. Free-form inputs (like `extra-args`) can inject
arbitrary commands.

**Use bash arrays** to build and execute commands:

```yaml
# WRONG — eval enables injection from free-form inputs
CMD="uv run releasekit ${{ inputs.command }}"
if [[ -n "${{ inputs.extra-args }}" ]]; then
  CMD="$CMD ${{ inputs.extra-args }}"
fi
eval "$CMD"

# CORRECT — array execution prevents injection
cmd_array=(uv run releasekit ${{ inputs.command }})
if [[ -n "${{ inputs.extra-args }}" ]]; then
  read -ra extra <<< "${{ inputs.extra-args }}"
  cmd_array+=("${extra[@]}")
fi
"${cmd_array[@]}"
```

Key rules:

* **Build commands as arrays**, not strings
* **Execute with `"${cmd_array[@]}"`**, not `eval`
* **Quote all `${{ inputs.* }}`** references in array additions
* **Use `read -ra`** to safely split free-form inputs into array elements
* **Capture output** with `$("${cmd_array[@]}")`, not `$(eval "$CMD")`

### Pin Dependencies with Version Constraints

Always pin dependencies with `>=` version constraints, especially for
packages with known CVEs. This ensures CI and production use the patched
version:

```toml
# WRONG — allows any version, including vulnerable ones
dependencies = ["pillow"]

# CORRECT — pins to patched version (GHSA-cfh3-3jmp-rvhc)
dependencies = ["pillow>=12.1.1"]
```

After pinning, always run `uv lock` to regenerate the lockfile.
