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
    stale_artifacts

**Language-specific checks** — injected via :class:`CheckBackend`:

    type_markers, version_consistency, naming_convention,
    metadata_completeness

The :class:`CheckBackend` protocol is the extension point. Each
language/runtime provides its own implementation. The default is
:class:`PythonCheckBackend`, which checks for ``py.typed`` markers,
``genkit-plugin-*`` naming, plugin version sync, and ``pyproject.toml``
metadata completeness.

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

    ┌──────────────────────────┬──────────┬────────────┬──────────────────────┐
    │ Check                    │ Severity │ Category   │ What it catches      │
    ├──────────────────────────┼──────────┼────────────┼──────────────────────┤
    │ cycles                   │ error    │ universal  │ Circular dep chains  │
    │ self_deps                │ error    │ universal  │ Self-referencing dep │
    │ orphan_deps              │ warning  │ universal  │ Missing workspace dep│
    │ missing_license          │ error    │ universal  │ No LICENSE file      │
    │ missing_readme           │ error    │ universal  │ No README.md         │
    │ stale_artifacts          │ warning  │ universal  │ Leftover .bak/dist/  │
    │ type_markers             │ warning  │ language   │ No py.typed (Python) │
    │ version_consistency      │ warning  │ language   │ Plugin version drift │
    │ naming_convention        │ warning  │ language   │ Dir ≠ package name   │
    │ metadata_completeness    │ warning  │ language   │ Missing metadata     │
    └──────────────────────────┴──────────┴────────────┴──────────────────────┘

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

from __future__ import annotations

from typing import Protocol, runtime_checkable

import tomlkit

from releasekit.graph import DependencyGraph, detect_cycles
from releasekit.logging import get_logger
from releasekit.preflight import PreflightResult
from releasekit.workspace import Package

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# CheckBackend protocol — the extension point for language-specific checks
# ---------------------------------------------------------------------------


@runtime_checkable
class CheckBackend(Protocol):
    """Protocol for language-specific workspace checks.

    Each language/runtime implements this protocol to provide checks
    that are specific to its ecosystem. The methods receive the full
    package list and a :class:`PreflightResult` accumulator.

    Future implementations might include ``GoCheckBackend`` (checking
    for ``go.sum`` consistency, ``go vet`` compliance) or
    ``JsCheckBackend`` (checking for ``package.json`` completeness,
    ``@scope/`` naming conventions).

    A plugin system can compose multiple backends by calling each
    one's methods in sequence on the same :class:`PreflightResult`.
    """

    def check_type_markers(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check for language-specific type annotation markers.

        Examples: ``py.typed`` (Python PEP 561), ``d.ts`` (TypeScript),
        ``go vet`` (Go).
        """
        ...

    def check_version_consistency(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that package versions follow ecosystem conventions.

        Examples: plugin versions matching core (Python genkit), workspace
        protocol versions (npm), module versions (Go).
        """
        ...

    def check_naming_convention(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that package names follow ecosystem naming rules.

        Examples: ``genkit-plugin-{dir}`` (Python), ``@genkit/{dir}``
        (npm), ``genkit/{dir}`` (Go modules).
        """
        ...

    def check_metadata_completeness(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that package metadata files are complete.

        Examples: ``pyproject.toml`` fields (Python), ``package.json``
        fields (npm), ``go.mod`` directives (Go).
        """
        ...


# ---------------------------------------------------------------------------
# Universal checks — always run regardless of language/runtime
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# PythonCheckBackend — language-specific checks for Python/uv workspaces
# ---------------------------------------------------------------------------


class PythonCheckBackend:
    """Python-specific workspace checks for uv/pip workspaces.

    Checks for:
    - ``py.typed`` PEP 561 markers in library packages
    - Plugin version consistency with core ``genkit`` package
    - ``genkit-plugin-{dir}`` naming convention
    - ``pyproject.toml`` metadata completeness (description, authors, license)
    """

    def check_type_markers(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that library packages have a ``py.typed`` PEP 561 marker.

        Only checks packages under ``packages/`` and ``plugins/``
        directories (libraries), not samples.
        """
        check_name = 'type_markers'
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

    def check_version_consistency(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that all ``genkit-plugin-*`` versions match the core version."""
        check_name = 'version_consistency'
        core_pkg = next((p for p in packages if p.name == 'genkit'), None)
        if core_pkg is None:
            result.add_warning(
                check_name,
                'Core "genkit" package not found; cannot verify versions.',
            )
            return

        core_version = core_pkg.version
        mismatches: list[str] = []
        for pkg in packages:
            if not pkg.name.startswith('genkit-plugin-'):
                continue
            if pkg.version != core_version:
                mismatches.append(
                    f'{pkg.name}=={pkg.version} (expected {core_version})',
                )

        if mismatches:
            result.add_warning(
                check_name,
                f'Plugin version mismatches: {", ".join(mismatches)}',
            )
        else:
            result.add_pass(check_name)

    def check_naming_convention(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check ``plugins/{name}/`` → ``genkit-plugin-{name}`` convention."""
        check_name = 'naming_convention'
        mismatches: list[str] = []
        for pkg in packages:
            dir_name = pkg.path.name
            parent_name = pkg.path.parent.name

            if parent_name == 'plugins':
                expected = f'genkit-plugin-{dir_name}'
                if pkg.name != expected:
                    mismatches.append(
                        f'{dir_name}/ → {pkg.name} (expected {expected})',
                    )

        if mismatches:
            result.add_warning(
                check_name,
                f'Naming mismatches: {", ".join(mismatches)}',
            )
        else:
            result.add_pass(check_name)

    def check_metadata_completeness(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check ``pyproject.toml`` has description, authors, and license."""
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
                issues.append(
                    f'{pkg.name}: missing {", ".join(missing_fields)}',
                )

        if issues:
            result.add_warning(
                check_name,
                f'Incomplete metadata: {"; ".join(issues)}',
            )
        else:
            result.add_pass(check_name)


# ---------------------------------------------------------------------------
# run_checks — main entry point
# ---------------------------------------------------------------------------

# Sentinel to distinguish "use default" from "explicitly no backend".
_USE_DEFAULT = object()


def run_checks(
    packages: list[Package],
    graph: DependencyGraph,
    backend: CheckBackend | object = _USE_DEFAULT,
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

    Returns:
        A :class:`PreflightResult` with all check outcomes.
    """
    result = PreflightResult()

    # --- Universal checks (always run) ---
    _check_cycles(graph, result)
    _check_self_deps(packages, result)
    _check_orphan_deps(packages, result)
    _check_missing_license(packages, result)
    _check_missing_readme(packages, result)
    _check_stale_artifacts(packages, result)

    # --- Language-specific checks (via backend) ---
    if backend is _USE_DEFAULT:
        backend = PythonCheckBackend()

    if backend is not None and isinstance(backend, CheckBackend):
        backend.check_type_markers(packages, result)
        backend.check_version_consistency(packages, result)
        backend.check_naming_convention(packages, result)
        backend.check_metadata_completeness(packages, result)

    logger.info('checks_complete', summary=result.summary())
    return result


__all__ = [
    'CheckBackend',
    'PythonCheckBackend',
    'run_checks',
]
