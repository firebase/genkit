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

"""Workspace health checks for ``releasekit check``.

Checks are split into two categories:

**Universal checks** — always run, language-agnostic:

    cycles, self_deps, orphan_deps, missing_license, missing_readme,
    stale_artifacts, ungrouped_packages, lockfile_staleness

**Language-specific checks** — injected via :class:`CheckBackend`:

    type_markers, version_consistency, naming_convention,
    metadata_completeness, python_version_consistency,
    python_classifiers, dependency_resolution, namespace_init

The :class:`CheckBackend` protocol is the extension point. Each
language/runtime provides its own implementation. The default is
:class:`PythonCheckBackend`, which checks for ``py.typed`` markers,
naming conventions, version sync, ``pyproject.toml``
metadata completeness, Python version consistency, trove classifiers,
dependency resolution, and namespace ``__init__.py`` hygiene.

Architecture::

    ┌───────────────────────────────────────────────────────┐
    │                  run_checks()                         │
    │                                                       │
    │  ┌─────────────────────────────┐                      │
    │  │   Universal Checks          │  Always run          │
    │  │   (cycles, self_deps, ...)  │                      │
    │  └─────────────────────────────┘                      │
    │                                                       │
    │  ┌─────────────────────────────┐                      │
    │  │   CheckBackend (Protocol)   │  Injected            │
    │  │                             │                      │
    │  │  ┌───────────────────────┐  │                      │
    │  │  │ PythonCheckBackend    │  │  Default             │
    │  │  │ GoCheckBackend        │  │  Future              │
    │  │  │ JsCheckBackend        │  │  Future              │
    │  │  │ PluginCheckBackend    │  │  Future (plugins)    │
    │  │  └───────────────────────┘  │                      │
    │  └─────────────────────────────┘                      │
    └───────────────────────────────────────────────────────┘

Check catalogue::

    ┌──────────────────────────┬──────────┬────────────┬──────────────────────────┐
    │ Check                    │ Severity │ Category   │ What it catches          │
    ├──────────────────────────┼──────────┼────────────┼──────────────────────────┤
    │ cycles                   │ error    │ universal  │ Circular dep chains      │
    │ self_deps                │ error    │ universal  │ Self-referencing dep     │
    │ orphan_deps              │ warning  │ universal  │ Missing workspace dep    │
    │ missing_license          │ error    │ universal  │ No LICENSE file          │
    │ missing_readme           │ error    │ universal  │ No README.md             │
    │ stale_artifacts          │ warning  │ universal  │ Leftover .bak/dist/      │
    │ ungrouped_packages       │ warning  │ universal  │ Package not in any group │
    │ lockfile_staleness        │ error    │ universal  │ uv.lock out of date      │
    │ type_markers             │ warning  │ language   │ No py.typed (Python)     │
    │ version_consistency      │ warning  │ language   │ Plugin version drift     │
    │ naming_convention        │ warning  │ language   │ Dir ≠ package name       │
    │ metadata_completeness    │ warning  │ language   │ Missing metadata         │
    │ python_version           │ warning  │ language   │ requires-python mismatch │
    │ python_classifiers       │ warning  │ language   │ Missing version classif. │
    │ dependency_resolution    │ warning  │ language   │ Broken dependency tree   │
    │ namespace_init           │ error    │ language   │ __init__.py in namespace │
    └──────────────────────────┴──────────┴────────────┴──────────────────────────┘

Usage::

    from releasekit.checks import run_checks, PythonCheckBackend
    from releasekit.workspace import discover_packages
    from releasekit.graph import build_graph

    packages = discover_packages(Path('.'))
    graph = build_graph(packages)

    # Default: uses PythonCheckBackend.
    result = run_checks(packages, graph)

    # Explicit backend:
    result = run_checks(packages, graph, backend=PythonCheckBackend())

    # No language-specific checks:
    result = run_checks(packages, graph, backend=None)
"""

from releasekit.checks._constants import DEPRECATED_CLASSIFIERS
from releasekit.checks._protocol import CheckBackend
from releasekit.checks._python import PythonCheckBackend
from releasekit.checks._python_fixers import (
    fix_build_system,
    fix_changelog_url,
    fix_deprecated_classifiers,
    fix_duplicate_dependencies,
    fix_license_classifier_mismatch,
    fix_namespace_init,
    fix_placeholder_urls,
    fix_publish_classifiers,
    fix_readme_content_type,
    fix_readme_field,
    fix_requires_python,
    fix_self_dependencies,
    fix_type_markers,
    fix_version_field,
)
from releasekit.checks._runner import run_checks
from releasekit.checks._universal import (
    fix_missing_license,
    fix_missing_readme,
    fix_stale_artifacts,
)
from releasekit.distro import fix_distro_deps

__all__ = [
    'CheckBackend',
    'DEPRECATED_CLASSIFIERS',
    'PythonCheckBackend',
    'fix_build_system',
    'fix_changelog_url',
    'fix_distro_deps',
    'fix_deprecated_classifiers',
    'fix_duplicate_dependencies',
    'fix_license_classifier_mismatch',
    'fix_missing_license',
    'fix_missing_readme',
    'fix_namespace_init',
    'fix_placeholder_urls',
    'fix_publish_classifiers',
    'fix_readme_content_type',
    'fix_readme_field',
    'fix_requires_python',
    'fix_self_dependencies',
    'fix_stale_artifacts',
    'fix_type_markers',
    'fix_version_field',
    'run_checks',
]
