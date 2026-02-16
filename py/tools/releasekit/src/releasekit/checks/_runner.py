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

"""Orchestrator that runs all workspace health checks.

Individual checks are dispatched concurrently via
:func:`asyncio.gather` + :func:`asyncio.to_thread`.
:class:`~releasekit.preflight.PreflightResult` is thread-safe,
so concurrent writes from multiple checks are safe.
"""

from __future__ import annotations

import asyncio
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

SkipMap = dict[str, frozenset[str]]
"""Package name → frozenset of check names to skip for that package."""


def _filter_pkgs(
    packages: list[Package],
    check_name: str,
    skip_map: SkipMap | None,
) -> list[Package]:
    """Return packages that have not opted out of *check_name*."""
    if not skip_map:
        return packages
    return [p for p in packages if check_name not in skip_map.get(p.name, frozenset())]


async def run_checks_async(
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
    skip_map: SkipMap | None = None,
) -> PreflightResult:
    """Run all workspace health checks concurrently.

    **Universal checks** always run (cycles, self_deps, orphan_deps,
    missing_license, missing_readme, stale_artifacts).

    **Language-specific checks** run via the injected ``backend``.
    If no backend is specified, defaults to :class:`PythonCheckBackend`.
    Pass ``backend=None`` to skip language-specific checks entirely.

    All checks are dispatched concurrently via :func:`asyncio.gather`
    and :func:`asyncio.to_thread` since the check functions are
    synchronous. :class:`PreflightResult` is thread-safe.

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
        skip_map: Per-package check skip map. Keys are package names,
            values are frozensets of check names to skip for that
            package. Built from ``PackageConfig.skip_checks``.

    Returns:
        A :class:`PreflightResult` with all check outcomes.
    """
    result = PreflightResult()

    # Collect all check tasks for concurrent execution.
    tasks: list[asyncio.Task[None]] = []

    fp = _filter_pkgs
    _t = asyncio.to_thread

    # Universal checks.
    tasks.append(asyncio.create_task(_t(_check_cycles, graph, result)))
    tasks.append(
        asyncio.create_task(
            _t(_check_self_deps, fp(packages, 'self_deps', skip_map), result),
        )
    )
    tasks.append(
        asyncio.create_task(
            _t(_check_orphan_deps, fp(packages, 'orphan_deps', skip_map), result),
        )
    )
    tasks.append(
        asyncio.create_task(
            _t(_check_missing_license, fp(packages, 'missing_license', skip_map), result),
        )
    )
    tasks.append(
        asyncio.create_task(
            _t(_check_missing_readme, fp(packages, 'missing_readme', skip_map), result),
        )
    )
    tasks.append(
        asyncio.create_task(
            _t(_check_stale_artifacts, fp(packages, 'stale_artifacts', skip_map), result),
        )
    )
    tasks.append(
        asyncio.create_task(
            _t(_check_ungrouped_packages, packages, groups or {}, result),
        )
    )
    if workspace_root is not None:
        tasks.append(
            asyncio.create_task(
                _t(_check_lockfile_staleness, workspace_root, result),
            )
        )

    if backend is _USE_DEFAULT:
        backend = PythonCheckBackend(
            core_package=core_package,
            plugin_prefix=plugin_prefix,
            namespace_dirs=namespace_dirs,
            library_dirs=library_dirs,
            plugin_dirs=plugin_dirs,
        )

    if backend is not None and isinstance(backend, CheckBackend):
        # Each check gets a filtered package list excluding per-package skips.
        _backend_checks: list[tuple[str, str]] = [
            ('check_type_markers', 'type_markers'),
            ('check_version_consistency', 'version_consistency'),
            ('check_naming_convention', 'naming_convention'),
            ('check_metadata_completeness', 'metadata_completeness'),
            ('check_python_version_consistency', 'python_version_consistency'),
            ('check_python_classifiers', 'python_classifiers'),
            ('check_dependency_resolution', 'dependency_resolution'),
            ('check_namespace_init', 'namespace_init'),
            ('check_readme_field', 'readme_field'),
            ('check_changelog_url', 'changelog_url'),
            ('check_test_filename_collisions', 'test_filename_collisions'),
            ('check_build_system', 'build_system'),
            ('check_version_field', 'version_field'),
            ('check_duplicate_dependencies', 'duplicate_dependencies'),
            ('check_pinned_deps_in_libraries', 'pinned_deps_in_libraries'),
            ('check_requires_python', 'requires_python'),
            ('check_readme_content_type', 'readme_content_type'),
            ('check_version_pep440', 'version_pep440'),
            ('check_placeholder_urls', 'placeholder_urls'),
            ('check_legacy_setup_files', 'legacy_setup_files'),
            ('check_deprecated_classifiers', 'deprecated_classifiers'),
            ('check_license_classifier_mismatch', 'license_classifier_mismatch'),
            ('check_unreachable_extras', 'unreachable_extras'),
            ('check_self_dependencies', 'self_dependencies'),
            ('check_distro_deps', 'distro_deps'),
        ]
        for method_name, check_name in _backend_checks:
            method = getattr(backend, method_name)
            filtered = fp(packages, check_name, skip_map)
            tasks.append(asyncio.create_task(_t(method, filtered, result)))

        # publish_classifier_consistency has an extra arg.
        tasks.append(
            asyncio.create_task(
                _t(
                    backend.check_publish_classifier_consistency,
                    fp(packages, 'publish_classifier_consistency', skip_map),
                    result,
                    exclude_publish,
                )
            )
        )

    await asyncio.gather(*tasks)

    logger.info('checks_complete', summary=result.summary())
    return result


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
    skip_map: SkipMap | None = None,
) -> PreflightResult:
    """Synchronous wrapper around :func:`run_checks_async`.

    Creates a new event loop if none is running, otherwise uses
    the existing loop. This preserves backward compatibility for
    callers that don't use ``await``.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        # Already inside an event loop (e.g. pytest-asyncio).
        # Fall back to sequential execution to avoid nested loop issues.
        return _run_checks_sync(
            packages,
            graph,
            backend,
            exclude_publish,
            groups,
            workspace_root,
            core_package=core_package,
            plugin_prefix=plugin_prefix,
            namespace_dirs=namespace_dirs,
            library_dirs=library_dirs,
            plugin_dirs=plugin_dirs,
            skip_map=skip_map,
        )

    return asyncio.run(
        run_checks_async(
            packages,
            graph,
            backend,
            exclude_publish,
            groups,
            workspace_root,
            core_package=core_package,
            plugin_prefix=plugin_prefix,
            namespace_dirs=namespace_dirs,
            library_dirs=library_dirs,
            plugin_dirs=plugin_dirs,
            skip_map=skip_map,
        )
    )


def _run_checks_sync(
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
    skip_map: SkipMap | None = None,
) -> PreflightResult:
    """Sequential fallback when already inside a running event loop."""
    result = PreflightResult()

    fp = _filter_pkgs
    _check_cycles(graph, result)
    _check_self_deps(fp(packages, 'self_deps', skip_map), result)
    _check_orphan_deps(fp(packages, 'orphan_deps', skip_map), result)
    _check_missing_license(fp(packages, 'missing_license', skip_map), result)
    _check_missing_readme(fp(packages, 'missing_readme', skip_map), result)
    _check_stale_artifacts(fp(packages, 'stale_artifacts', skip_map), result)
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
        backend.check_type_markers(fp(packages, 'type_markers', skip_map), result)
        backend.check_version_consistency(fp(packages, 'version_consistency', skip_map), result)
        backend.check_naming_convention(fp(packages, 'naming_convention', skip_map), result)
        backend.check_metadata_completeness(fp(packages, 'metadata_completeness', skip_map), result)
        backend.check_python_version_consistency(fp(packages, 'python_version_consistency', skip_map), result)
        backend.check_python_classifiers(fp(packages, 'python_classifiers', skip_map), result)
        backend.check_dependency_resolution(fp(packages, 'dependency_resolution', skip_map), result)
        backend.check_namespace_init(fp(packages, 'namespace_init', skip_map), result)
        backend.check_readme_field(fp(packages, 'readme_field', skip_map), result)
        backend.check_changelog_url(fp(packages, 'changelog_url', skip_map), result)
        backend.check_publish_classifier_consistency(
            fp(packages, 'publish_classifier_consistency', skip_map),
            result,
            exclude_publish,
        )
        backend.check_test_filename_collisions(fp(packages, 'test_filename_collisions', skip_map), result)
        backend.check_build_system(fp(packages, 'build_system', skip_map), result)
        backend.check_version_field(fp(packages, 'version_field', skip_map), result)
        backend.check_duplicate_dependencies(fp(packages, 'duplicate_dependencies', skip_map), result)
        backend.check_pinned_deps_in_libraries(fp(packages, 'pinned_deps_in_libraries', skip_map), result)
        backend.check_requires_python(fp(packages, 'requires_python', skip_map), result)
        backend.check_readme_content_type(fp(packages, 'readme_content_type', skip_map), result)
        backend.check_version_pep440(fp(packages, 'version_pep440', skip_map), result)
        backend.check_placeholder_urls(fp(packages, 'placeholder_urls', skip_map), result)
        backend.check_legacy_setup_files(fp(packages, 'legacy_setup_files', skip_map), result)
        backend.check_deprecated_classifiers(fp(packages, 'deprecated_classifiers', skip_map), result)
        backend.check_license_classifier_mismatch(fp(packages, 'license_classifier_mismatch', skip_map), result)
        backend.check_unreachable_extras(fp(packages, 'unreachable_extras', skip_map), result)
        backend.check_self_dependencies(fp(packages, 'self_dependencies', skip_map), result)
        backend.check_distro_deps(fp(packages, 'distro_deps', skip_map), result)

    logger.info('checks_complete', summary=result.summary())
    return result
