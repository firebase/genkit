## Python coding guidelines

This is for both bots and humans.

Target: Python >= 3.10

### Typing & Style

- Use `|` for union types instead of `Union` and `| None` instead of `Optional`.
- Use lowercase `list`, `dict` for type hints (not `List`, `Dict`).
- Use modern generics (PEP 585, 695).
- Import types such as `Callable`, `Awaitable` that are deprecated in `typing`
  from `collections.abc` instead.
- Apply type hints strictly, including `-> None` for functions returning nothing.
- Use the `type` keyword for type aliases.
- Use enum types like `StrEnum` instead of `(str, Enum)` for string-based enums.
- Code against interfaces, not implementations.
- Use the adapter pattern for optional implementations.
- Use proper punctuation in comments.
- Avoid comments explaining obvious code or actions.
- Add TODO comments such as `TODO: Fix this later.` when adding stub implementations.

### Docstrings

- Write comprehensive Google-style docstrings for modules, classes, and
functions.
- Include the following sections as needed:
  - Overview (required as a one liner description with follow-up paragraphs as
    rationale)
  - Key operations/purpose
  - Arguments/attributes (required for callables)
  - Returns (required for callables)
  - Examples (required for user-facing API)
  - Caveats

### Formatting

- Format code using ruff (or `bin/fmt` or `scripts/fmt` if present).
- Max line length: 120 characters to make it easy to read code vertically.
- Refer to the `.editorconfig` or workspace-root `pyproject.toml` for
  other formatting rules.
- Wrap long lines and strings appropriately.

### Testing

- Write comprehensive unit tests using `pytest` and `unittest`.
- Add docstrings to test modules, classes, and functions explaining their scope.
- Run tests via `uv run --directory ${PYTHON_WORKSPACE_DIR} pytest .` where
  the `PYTHON_WORKSPACE_DIR` corresponds to the workspace directory.
- Fix underlying code issues rather than special-casing tests.
- If porting tests: Maintain 1:1 logic parity accurately; do not invent behavior.

### Tooling & Environment

- Use `uv` for packaging and environment management.
- Use `mypy` for static type checking.
- Target Python 3.12 or newer. Aim for PyPy compatibility (optional).

### Logging

- Use `structlog` for structured logging.
- Use `structlog`'s async API (`await logger.ainfo(...)`) within coroutines
- Avoid f-strings for async logging.

### Porting

- If porting from another language (e.g., JS or TypeScript), maintain 1:1 logic
parity in implementation and tests.

### Licensing

Include the following Apache 2.0 license header at the top of each file,
updating the year:

```python
# Copyright 2025 Google LLC
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
