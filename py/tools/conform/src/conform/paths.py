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

"""Path constants for the ``conform`` tool.

In an editable install (``uv sync``), ``__file__`` resolves to the actual
source tree, so relative navigation reliably finds the conformance specs,
the ``py/`` workspace root, and the repository root.

Layout::

    <repo>/
    ├── py/
    │   ├── tools/conform/src/conform/   ← this package
    │   ├── tests/conform/              ← spec files per plugin
    │   └── plugins/                     ← plugin source trees
    └── ...                              ← other runtimes (js/, go/, etc.)
"""

from __future__ import annotations

from pathlib import Path

# tools/conform/src/conform/paths.py
#   → src/conform/  → src/  → tools/conform/  → tools/  → py/
PACKAGE_DIR: Path = Path(__file__).resolve().parent
TOOL_DIR: Path = PACKAGE_DIR.parent.parent
PY_DIR: Path = TOOL_DIR.parent.parent
REPO_ROOT: Path = PY_DIR.parent

# Conformance spec directory (YAML specs + entry points per plugin).
CONFORMANCE_DIR: Path = PY_DIR / 'tests' / 'conform'

# Plugin source trees.
PLUGINS_DIR: Path = PY_DIR / 'plugins'
