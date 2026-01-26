# Python Development Guidelines

## Code Quality & Linting

* **Run Linting**: Always run `./bin/lint` from the repo root (or `py/` directory semantics depending on the script) for all Python code changes.
* **Pass All Tests**: Ensure all unit tests pass (`uv run pytest .`).
* **Production Ready**: The objective is to produce production-grade code.
* **Shift Left**: Employ a "shift left" strategy—catch errors early.
* **Strict Typing**: Strict type checking is required. Do not use `Any` unless absolutely necessary and documented.
* **No Warning Suppression**: Avoid ignoring warnings from the type checker (`# type: ignore`) or other tools unless there is a compelling, documented reason.

## Generated Files & Data Model

* **Do Not Edit typing.py**: `py/packages/genkit/src/genkit/core/typing.py` is an auto-generated file. **DO NOT MODIFY IT DIRECTLY.**
* **Generator/Sanitizer**: Any necessary changes to the core types must be applied to the generator script or the schema sanitizer.
* **Canonical Parity**: The data model MUST be identical to the JSON schema defined in the JavaScript (canonical) implementation.

## API & Behavior Parity

* **JS Canonical**: The Python implementation MUST be identical in API structure and runtime behavior to the JavaScript (canonical) implementation.

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
* **Imports**: Import types like `Callable`, `Awaitable` from `collections.abc`, not `typing`.
* **Enums**: Use `StrEnum` instead of `(str, Enum)`.
* **Strictness**: Apply type hints strictly, including `-> None` for void functions.
* **Design**:
  * Code against interfaces, not implementations.
  * Use the adapter pattern for optional implementations.
* **Comments**:
  * Use proper punctuation.
  * Avoid comments explaining obvious code.
  * Use `TODO: Fix this later.` format for stubs.
* Ensure that `bin/lint` passes without errors.

### Docstrings

* **Format**: Write comprehensive Google-style docstrings for modules, classes, and functions.
* **Content**:
  * **Explain Concepts**: Explain the terminology and concepts used in the code to someone unfamiliar with the code so that first timers can easily understand these ideas.
  * **Visuals**: Prefer using tabular format and ascii diagrams in the docstrings to break down complex concepts or list terminology.
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

### Implementation

* Always update module docstrings and function docstrings when updating code
  to reflect updated reality.
* Always add unit tests to improve coverage.
* Scan documentation for every module you edit and keep it up-to-date.
* When there is a conflict between the JavaScript implementation and the
  Python implementation, please refer to the JavaScript implementation for
  the same.
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
* Please keep the `README.md` file for each sample up to date with the `run.sh`
  script.
* Prompt for API keys and other configuration required for the sample
  in Python.
* When creating shell scripts using bash, please use `#!/usr/bin/env bash` as
  the shebang line and `set -euo pipefail`.
* Avoid mentioning sample specific stuff in core framework or plugin code.

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
* **Porting**: Maintain 1:1 logic parity accurately if porting tests. Do not invent behavior.
* **Fixes**: Fix underlying code issues rather than special-casing tests.

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

## Git commit message guidelines

* Please draft a plain-text commit message after you're done with changes.
* Please do not include absolute file paths as links in commit messages.
* Since lines starting with `#` are treated as comments, please use a simpler
  format for headings.
* Add a rationale paragraph explaining the why and the what before listing
  all the changes.
* Please use conventional commits as the format.
* For scope, please refer to release-please configuration if available.
* Keep it short and simple.
