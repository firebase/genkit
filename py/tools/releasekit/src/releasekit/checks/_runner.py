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

"""Orchestrator that runs all workspace health checks."""

from __future__ import annotations

from pathlib import Path

from releasekit.checks._protocol import CheckBackend
from releasekit.checks._python import PythonCheckBackend
from releasekit.checks._universal import (
    _check_cycles,
    _check_lockfile_staleness,
    _check_missing_license,
    _check_missing_readme,
    _check_orphan_deps,
    _check_self_deps,
    _check_stale_artifacts,
    _check_ungrouped_packages,
)
from releasekit.graph import DependencyGraph
from releasekit.logging import get_logger
from releasekit.preflight import PreflightResult
from releasekit.workspace import Package

logger = get_logger(__name__)

_USE_DEFAULT = object()


def run_checks(
    packages: list[Package],
    graph: DependencyGraph,
    backend: CheckBackend | object = _USE_DEFAULT,
    exclude_publish: list[str] | None = None,
    groups: dict[str, list[str]] | None = None,
    workspace_root: Path | None = None,
    *,
    core_package: str = '',
    plugin_prefix: str = '',
    namespace_dirs: list[str] | None = None,
    library_dirs: list[str] | None = None,
    plugin_dirs: list[str] | None = None,
) -> PreflightResult:
    """Run all workspace health checks.

    **Universal checks** always run (cycles, self_deps, orphan_deps,
    missing_license, missing_readme, stale_artifacts).

    **Language-specific checks** run via the injected ``backend``.
    If no backend is specified, defaults to :class:`PythonCheckBackend`.
    Pass ``backend=None`` to skip language-specific checks entirely.

    Args:
        packages: All discovered workspace packages.
        graph: The workspace dependency graph.
        backend: Language-specific check backend. Defaults to
            :class:`PythonCheckBackend`. Pass ``None`` to skip
            language-specific checks.
        exclude_publish: Glob patterns for packages excluded from
            publishing (passed to publish classifier consistency check).
        groups: Group name → pattern list mapping from config.
            Used by the ungrouped-packages check.
        workspace_root: Path to the workspace root. Used by the
            lockfile staleness check.
        core_package: Core package name for version consistency checks.
        plugin_prefix: Expected prefix for package names in
            ``plugin_dirs``.
        namespace_dirs: PEP 420 namespace directories that must not
            have ``__init__.py``.
        library_dirs: Parent directory names whose children are
            publishable library packages requiring ``py.typed``.
        plugin_dirs: Parent directory names whose children follow
            the naming convention and need namespace init checks.

    Returns:
        A :class:`PreflightResult` with all check outcomes.
    """
    result = PreflightResult()

    _check_cycles(graph, result)
    _check_self_deps(packages, result)
    _check_orphan_deps(packages, result)
    _check_missing_license(packages, result)
    _check_missing_readme(packages, result)
    _check_stale_artifacts(packages, result)
    _check_ungrouped_packages(packages, groups or {}, result)
    if workspace_root is not None:
        _check_lockfile_staleness(workspace_root, result)

    if backend is _USE_DEFAULT:
        backend = PythonCheckBackend(
            core_package=core_package,
            plugin_prefix=plugin_prefix,
            namespace_dirs=namespace_dirs,
            library_dirs=library_dirs,
            plugin_dirs=plugin_dirs,
        )

    if backend is not None and isinstance(backend, CheckBackend):
        backend.check_type_markers(packages, result)
        backend.check_version_consistency(packages, result)
        backend.check_naming_convention(packages, result)
        backend.check_metadata_completeness(packages, result)
        backend.check_python_version_consistency(packages, result)
        backend.check_python_classifiers(packages, result)
        backend.check_dependency_resolution(packages, result)
        backend.check_namespace_init(packages, result)
        backend.check_readme_field(packages, result)
        backend.check_changelog_url(packages, result)
        backend.check_publish_classifier_consistency(packages, result, exclude_publish)
        backend.check_test_filename_collisions(packages, result)
        backend.check_build_system(packages, result)
        backend.check_version_field(packages, result)
        backend.check_duplicate_dependencies(packages, result)
        backend.check_pinned_deps_in_libraries(packages, result)
        backend.check_requires_python(packages, result)
        backend.check_readme_content_type(packages, result)
        backend.check_version_pep440(packages, result)
        backend.check_placeholder_urls(packages, result)
        backend.check_legacy_setup_files(packages, result)
        backend.check_deprecated_classifiers(packages, result)
        backend.check_license_classifier_mismatch(packages, result)
        backend.check_unreachable_extras(packages, result)
        backend.check_self_dependencies(packages, result)

    logger.info('checks_complete', summary=result.summary())
    return result
