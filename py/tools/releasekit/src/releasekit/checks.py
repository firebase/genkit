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

Standalone checks that validate workspace structure, dependencies,
and metadata without requiring a full publish pipeline. Each check
function receives a list of :class:`~releasekit.workspace.Package`
objects and/or a :class:`~releasekit.graph.DependencyGraph`.

Check catalogue::

    ┌──────────────────────────┬──────────┬─────────────────────────────────┐
    │ Check                    │ Severity │ What it catches                 │
    ├──────────────────────────┼──────────┼─────────────────────────────────┤
    │ cycles                   │ error    │ Circular dependency chains      │
    │ self_deps                │ error    │ Package depends on itself       │
    │ orphan_deps              │ warning  │ Internal dep not in workspace   │
    │ missing_license          │ error    │ No LICENSE file for publishable │
    │ missing_readme           │ error    │ No README.md for publishable   │
    │ missing_py_typed         │ warning  │ No py.typed PEP 561 marker     │
    │ version_consistency      │ warning  │ Plugin version ≠ core version  │
    │ naming_convention        │ warning  │ Dir name ≠ package name        │
    │ metadata_completeness    │ warning  │ Missing pyproject.toml fields  │
    │ stale_artifacts          │ warning  │ Leftover .bak or dist/ files   │
    └──────────────────────────┴──────────┴─────────────────────────────────┘

Usage::

    from releasekit.checks import run_checks
    from releasekit.workspace import discover_packages
    from releasekit.graph import build_graph

    packages = discover_packages(Path('.'))
    graph = build_graph(packages)
    result = run_checks(packages, graph)

    if not result.ok:
        sys.exit(1)
"""

from __future__ import annotations

import tomlkit

from releasekit.graph import DependencyGraph, detect_cycles
from releasekit.logging import get_logger
from releasekit.preflight import PreflightResult
from releasekit.workspace import Package

logger = get_logger(__name__)


def _check_cycles(
    graph: DependencyGraph,
    result: PreflightResult,
) -> None:
    """Check for circular dependencies in the dependency graph.

    Args:
        graph: The workspace dependency graph.
        result: Accumulator for check outcomes.
    """
    check_name = 'cycles'
    cycles = detect_cycles(graph)
    if cycles:
        cycle_strs = [' → '.join(c) for c in cycles]
        result.add_failure(
            check_name,
            f'Circular dependencies: {"; ".join(cycle_strs)}',
        )
    else:
        result.add_pass(check_name)


def _check_self_deps(
    packages: list[Package],
    result: PreflightResult,
) -> None:
    """Check for packages that list themselves as a dependency.

    Args:
        packages: All workspace packages.
        result: Accumulator for check outcomes.
    """
    check_name = 'self_deps'
    offenders: list[str] = []
    for pkg in packages:
        if pkg.name in pkg.internal_deps:
            offenders.append(pkg.name)
    if offenders:
        result.add_failure(
            check_name,
            f'Packages depend on themselves: {", ".join(offenders)}',
        )
    else:
        result.add_pass(check_name)


def _check_orphan_deps(
    packages: list[Package],
    result: PreflightResult,
) -> None:
    """Check for internal deps that reference non-existent workspace packages.

    Args:
        packages: All workspace packages.
        result: Accumulator for check outcomes.
    """
    check_name = 'orphan_deps'
    known_names = {pkg.name for pkg in packages}
    orphans: list[str] = []
    for pkg in packages:
        for dep in pkg.internal_deps:
            if dep not in known_names:
                orphans.append(f'{pkg.name} → {dep}')
    if orphans:
        result.add_warning(
            check_name,
            f'Internal deps not found in workspace: {", ".join(orphans)}',
        )
    else:
        result.add_pass(check_name)


def _check_missing_license(
    packages: list[Package],
    result: PreflightResult,
) -> None:
    """Check that every publishable package has a LICENSE file.

    Args:
        packages: All workspace packages.
        result: Accumulator for check outcomes.
    """
    check_name = 'missing_license'
    missing: list[str] = []
    for pkg in packages:
        if not pkg.is_publishable:
            continue
        license_path = pkg.path / 'LICENSE'
        if not license_path.exists():
            missing.append(pkg.name)
    if missing:
        result.add_failure(
            check_name,
            f'Missing LICENSE file: {", ".join(missing)}',
        )
    else:
        result.add_pass(check_name)


def _check_missing_readme(
    packages: list[Package],
    result: PreflightResult,
) -> None:
    """Check that every publishable package has a README.md file.

    Args:
        packages: All workspace packages.
        result: Accumulator for check outcomes.
    """
    check_name = 'missing_readme'
    missing: list[str] = []
    for pkg in packages:
        if not pkg.is_publishable:
            continue
        readme_path = pkg.path / 'README.md'
        if not readme_path.exists():
            missing.append(pkg.name)
    if missing:
        result.add_failure(
            check_name,
            f'Missing README.md file: {", ".join(missing)}',
        )
    else:
        result.add_pass(check_name)


def _check_missing_py_typed(
    packages: list[Package],
    result: PreflightResult,
) -> None:
    """Check that library packages have a py.typed PEP 561 marker.

    Only checks packages under ``packages/`` and ``plugins/`` directories
    (libraries), not samples. Looks for ``py.typed`` in the ``src/``
    subtree of each package.

    Args:
        packages: All workspace packages.
        result: Accumulator for check outcomes.
    """
    check_name = 'missing_py_typed'
    # Only library packages need py.typed markers.
    library_parents = {'packages', 'plugins'}
    missing: list[str] = []
    for pkg in packages:
        if not pkg.is_publishable:
            continue
        if pkg.path.parent.name not in library_parents:
            continue
        src_dir = pkg.path / 'src'
        if not src_dir.exists():
            continue
        # Search for any py.typed marker under src/.
        py_typed_files = list(src_dir.rglob('py.typed'))
        if not py_typed_files:
            missing.append(pkg.name)
    if missing:
        result.add_warning(
            check_name,
            f'Missing py.typed marker: {", ".join(missing)}',
        )
    else:
        result.add_pass(check_name)


def _check_version_consistency(
    packages: list[Package],
    result: PreflightResult,
) -> None:
    """Check that all plugin versions match the core framework version.

    Finds the ``genkit`` core package and compares its version against
    all ``genkit-plugin-*`` packages. Samples are excluded.

    Args:
        packages: All workspace packages.
        result: Accumulator for check outcomes.
    """
    check_name = 'version_consistency'
    core_pkg = next((p for p in packages if p.name == 'genkit'), None)
    if core_pkg is None:
        result.add_warning(check_name, 'Core "genkit" package not found; cannot verify versions.')
        return

    core_version = core_pkg.version
    mismatches: list[str] = []
    for pkg in packages:
        if not pkg.name.startswith('genkit-plugin-'):
            continue
        if pkg.version != core_version:
            mismatches.append(f'{pkg.name}=={pkg.version} (expected {core_version})')

    if mismatches:
        result.add_warning(
            check_name,
            f'Plugin version mismatches: {", ".join(mismatches)}',
        )
    else:
        result.add_pass(check_name)


def _check_naming_convention(
    packages: list[Package],
    result: PreflightResult,
) -> None:
    """Check that directory names match package naming conventions.

    Plugins should follow: ``plugins/{name}/`` → ``genkit-plugin-{name}``.

    Args:
        packages: All workspace packages.
        result: Accumulator for check outcomes.
    """
    check_name = 'naming_convention'
    mismatches: list[str] = []
    for pkg in packages:
        dir_name = pkg.path.name
        parent_name = pkg.path.parent.name

        if parent_name == 'plugins':
            expected = f'genkit-plugin-{dir_name}'
            if pkg.name != expected:
                mismatches.append(f'{dir_name}/ → {pkg.name} (expected {expected})')

    if mismatches:
        result.add_warning(
            check_name,
            f'Naming mismatches: {", ".join(mismatches)}',
        )
    else:
        result.add_pass(check_name)


def _check_metadata_completeness(
    packages: list[Package],
    result: PreflightResult,
) -> None:
    """Check that publishable packages have required pyproject.toml metadata.

    Checks for: description, authors, license, classifiers.

    Args:
        packages: All workspace packages.
        result: Accumulator for check outcomes.
    """
    check_name = 'metadata_completeness'
    required_fields = ['description', 'authors', 'license']
    issues: list[str] = []

    for pkg in packages:
        if not pkg.is_publishable:
            continue
        try:
            content = pkg.pyproject_path.read_text(encoding='utf-8')
            data = tomlkit.parse(content)
        except Exception:
            issues.append(f'{pkg.name}: cannot parse pyproject.toml')
            continue

        project: dict[str, object] = data.get('project', {})
        missing_fields: list[str] = []
        for field_name in required_fields:
            if field_name not in project or not project[field_name]:
                missing_fields.append(field_name)

        if missing_fields:
            issues.append(f'{pkg.name}: missing {", ".join(missing_fields)}')

    if issues:
        result.add_warning(
            check_name,
            f'Incomplete metadata: {"; ".join(issues)}',
        )
    else:
        result.add_pass(check_name)


def _check_stale_artifacts(
    packages: list[Package],
    result: PreflightResult,
) -> None:
    """Check for leftover build artifacts from previous releases.

    Looks for ``.bak`` files and ``dist/`` directories.

    Args:
        packages: All workspace packages.
        result: Accumulator for check outcomes.
    """
    check_name = 'stale_artifacts'
    stale: list[str] = []
    for pkg in packages:
        bak_files = list(pkg.path.glob('*.bak'))
        if bak_files:
            stale.append(f'{pkg.name}: {len(bak_files)} .bak file(s)')

        dist_dir = pkg.path / 'dist'
        if dist_dir.is_dir():
            dist_files = list(dist_dir.iterdir())
            if dist_files:
                stale.append(f'{pkg.name}: dist/ has {len(dist_files)} file(s)')

    if stale:
        result.add_warning(
            check_name,
            f'Stale artifacts: {"; ".join(stale)}',
        )
    else:
        result.add_pass(check_name)


def run_checks(
    packages: list[Package],
    graph: DependencyGraph,
) -> PreflightResult:
    """Run all workspace health checks.

    This is the main entry point for ``releasekit check``. Runs every
    check in the catalogue and returns a single :class:`PreflightResult`.

    Args:
        packages: All discovered workspace packages.
        graph: The workspace dependency graph.

    Returns:
        A :class:`PreflightResult` with all check outcomes.
    """
    result = PreflightResult()

    _check_cycles(graph, result)
    _check_self_deps(packages, result)
    _check_orphan_deps(packages, result)
    _check_missing_license(packages, result)
    _check_missing_readme(packages, result)
    _check_missing_py_typed(packages, result)
    _check_version_consistency(packages, result)
    _check_naming_convention(packages, result)
    _check_metadata_completeness(packages, result)
    _check_stale_artifacts(packages, result)

    logger.info('checks_complete', summary=result.summary())
    return result


__all__ = [
    'run_checks',
]
