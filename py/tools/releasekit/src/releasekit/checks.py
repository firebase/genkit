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
``genkit-plugin-*`` naming, plugin version sync, ``pyproject.toml``
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

from __future__ import annotations

import fnmatch
import shutil
import subprocess  # noqa: S404 - intentional use for uv pip check
from pathlib import Path
from typing import Protocol, runtime_checkable

import tomlkit

from releasekit.graph import DependencyGraph, detect_cycles
from releasekit.logging import get_logger
from releasekit.preflight import PreflightResult
from releasekit.workspace import Package

logger = get_logger(__name__)


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

    def check_python_version_consistency(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that all packages declare the same ``requires-python``.

        Mixed Python version requirements within a workspace cause
        install failures and CI matrix confusion.
        """
        ...

    def check_python_classifiers(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that publishable packages have Python version classifiers.

        Missing classifiers cause PyPI to display incorrect Python
        version support information to users.
        """
        ...

    def check_dependency_resolution(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that all dependencies resolve correctly.

        Runs the ecosystem's dependency checker (e.g. ``uv pip check``)
        to verify no missing or incompatible dependencies.
        """
        ...

    def check_namespace_init(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check for accidental ``__init__.py`` in namespace directories.

        PEP 420 namespace packages (e.g. ``genkit/plugins/``) must NOT
        have ``__init__.py`` in intermediate namespace directories.
        An accidental ``__init__.py`` breaks import discovery for
        packages that contribute to the same namespace.
        """
        ...

    def check_readme_field(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that publishable packages declare ``readme`` in ``[project]``.

        Without this field, PyPI displays an empty page with no description,
        which gives a poor first impression to potential users.
        """
        ...

    def check_changelog_url(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that publishable packages have a ``Changelog`` entry in ``[project.urls]``.

        PyPI renders ``[project.urls]`` entries as sidebar links. A
        ``Changelog`` link is a widely expected convention that helps
        users track what changed between versions.
        """
        ...

    def check_publish_classifier_consistency(
        self,
        packages: list[Package],
        result: PreflightResult,
        exclude_publish: list[str] | None = None,
    ) -> None:
        """Check that ``Private :: Do Not Upload`` is consistent with ``exclude_publish``.

        Warns when a package is scheduled for publish but has the
        private classifier, or is excluded but lacks it.
        """
        ...


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
            hint='Break the cycle by removing one of the mutual dependencies in pyproject.toml.',
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
            hint='Remove the package from its own [project.dependencies] list.',
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
            hint='Copy the Apache 2.0 LICENSE file into each listed package directory.',
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
            hint='Create a README.md in each listed package directory describing the package.',
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
            hint='Remove stale files with: rm -f *.bak && rm -rf dist/',
        )
    else:
        result.add_pass(check_name)


def _check_ungrouped_packages(
    packages: list[Package],
    groups: dict[str, list[str]],
    result: PreflightResult,
) -> None:
    """Check that every discovered package belongs to at least one config group.

    When a new package is added to the workspace but not included in any
    ``[groups]`` pattern in the config, it becomes invisible to the
    exclusion system (``exclude_publish``, ``exclude_bump``). This check
    warns about such packages so they can be assigned to the correct group.

    Args:
        packages: All discovered workspace packages.
        groups: Group name → pattern list mapping from config.
        result: Accumulator for check outcomes.
    """
    check_name = 'ungrouped_packages'
    if not groups:
        result.add_pass(check_name)
        return

    all_patterns: list[str] = []
    for patterns in groups.values():
        for pat in patterns:
            if not pat.startswith('group:'):
                all_patterns.append(pat)

    ungrouped: list[str] = []
    for pkg in packages:
        if not any(fnmatch.fnmatch(pkg.name, pat) for pat in all_patterns):
            ungrouped.append(pkg.name)

    if ungrouped:
        result.add_warning(
            check_name,
            f'Packages not in any config group: {", ".join(sorted(ungrouped))}',
            hint='Add each package to a [groups] entry in releasekit.toml so it is covered by exclusion rules.',
        )
    else:
        result.add_pass(check_name)


def _check_lockfile_staleness(
    workspace_root: Path,
    result: PreflightResult,
) -> None:
    """Check that ``uv.lock`` is up to date with ``pyproject.toml``.

    Runs ``uv lock --check`` which exits non-zero if the lockfile needs
    regeneration. This catches a common PR issue where dependencies are
    added or changed but ``uv lock`` wasn't run.

    Gracefully passes if ``uv`` is not installed (the workspace may use
    a different package manager).

    Args:
        workspace_root: Path to the workspace root containing ``uv.lock``.
        result: Accumulator for check outcomes.
    """
    check_name = 'lockfile_staleness'

    if not shutil.which('uv'):
        result.add_pass(check_name)
        return

    try:
        proc = subprocess.run(  # noqa: S603 - intentional subprocess call
            ['uv', 'lock', '--check'],  # noqa: S607 - uv is a known tool
            cwd=workspace_root,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if proc.returncode == 0:
            result.add_pass(check_name)
        else:
            result.add_failure(
                check_name,
                'uv.lock is out of date with pyproject.toml dependencies.',
                hint="Run 'uv lock' to regenerate the lockfile.",
            )
    except subprocess.TimeoutExpired:
        result.add_warning(
            check_name,
            'uv lock --check timed out after 60 seconds.',
            hint="Run 'uv lock' manually to verify the lockfile.",
        )
    except Exception as exc:
        result.add_warning(
            check_name,
            f'Failed to run uv lock --check: {exc}',
            hint="Ensure 'uv' is installed and working.",
        )


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

    def check_python_version_consistency(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that all packages declare the same ``requires-python``.

        Mixed Python version requirements within a workspace cause install
        failures and CI matrix confusion. All publishable packages should
        agree on the minimum supported Python version.
        """
        check_name = 'python_version'
        versions: dict[str, list[str]] = {}

        for pkg in packages:
            if not pkg.is_publishable:
                continue
            try:
                content = pkg.pyproject_path.read_text(encoding='utf-8')
                data = tomlkit.parse(content)
            except Exception:
                logger.debug('parse_failed', path=str(pkg.pyproject_path))
                continue

            project: dict[str, object] = data.get('project', {})
            requires_python = project.get('requires-python')
            if isinstance(requires_python, str):
                versions.setdefault(requires_python, []).append(pkg.name)

        if not versions:
            result.add_pass(check_name)
            return

        if len(versions) == 1:
            result.add_pass(check_name)
        else:
            parts: list[str] = []
            for ver, pkgs in sorted(versions.items()):
                parts.append(f'{ver}: {len(pkgs)} packages')
            result.add_warning(
                check_name,
                f'Inconsistent requires-python: {"; ".join(parts)}',
            )

    def check_python_classifiers(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check publishable packages have Python 3.10–3.14 classifiers.

        Missing classifiers cause PyPI to display incorrect Python version
        support. All publishable packages should include
        ``Programming Language :: Python :: 3.{10..14}`` classifiers.
        """
        check_name = 'python_classifiers'
        expected_versions = {'3.10', '3.11', '3.12', '3.13', '3.14'}
        issues: list[str] = []

        for pkg in packages:
            if not pkg.is_publishable:
                continue
            try:
                content = pkg.pyproject_path.read_text(encoding='utf-8')
                data = tomlkit.parse(content)
            except Exception:
                logger.debug('parse_failed', path=str(pkg.pyproject_path))
                continue

            project: dict[str, object] = data.get('project', {})
            classifiers = project.get('classifiers', [])
            if not isinstance(classifiers, list):
                continue

            # Extract Python version classifiers.
            found_versions: set[str] = set()
            prefix = 'Programming Language :: Python :: '
            for classifier in classifiers:
                if isinstance(classifier, str) and classifier.startswith(prefix):
                    version = classifier[len(prefix) :]
                    found_versions.add(version)

            missing = expected_versions - found_versions
            if missing:
                issues.append(
                    f'{pkg.name}: missing classifiers for Python {", ".join(sorted(missing))}',
                )

        if issues:
            result.add_warning(
                check_name,
                f'Missing Python classifiers: {"; ".join(issues)}',
            )
        else:
            result.add_pass(check_name)

    def check_dependency_resolution(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Run ``uv pip check`` to verify all dependencies resolve.

        This catches missing, incompatible, or conflicting dependencies
        before a release attempt. Requires ``uv`` to be installed.
        """
        check_name = 'dependency_resolution'
        try:
            proc = subprocess.run(
                ['uv', 'pip', 'check'],  # noqa: S603, S607 - intentional partial path
                capture_output=True,
                text=True,
                timeout=60,
            )
        except FileNotFoundError:
            result.add_warning(
                check_name,
                'uv not found; skipping dependency resolution check.',
            )
            return
        except subprocess.TimeoutExpired:
            result.add_warning(
                check_name,
                'uv pip check timed out after 60 seconds.',
            )
            return

        if proc.returncode == 0:
            result.add_pass(check_name)
        else:
            output = (proc.stdout or proc.stderr or '').strip()
            # Truncate long output to keep error messages readable.
            if len(output) > 500:
                output = output[:500] + '...'
            result.add_warning(
                check_name,
                f'Dependency issues: {output}',
            )

    def check_namespace_init(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check for accidental ``__init__.py`` in namespace directories.

        PEP 420 namespace packages (``genkit/`` and ``genkit/plugins/``)
        must NOT have ``__init__.py`` in intermediate directories. An
        accidental ``__init__.py`` breaks ``pip install`` by preventing
        Python from discovering contributions from other packages in
        the same namespace.

        Only checks plugin packages (those under ``plugins/``) since
        namespace packaging is primarily a concern for plugin architectures.
        """
        check_name = 'namespace_init'
        # Namespace directories that must NOT contain __init__.py.
        # These are relative to the package's src/ directory.
        namespace_dirs = ['genkit', 'genkit/plugins']
        offenders: list[str] = []

        for pkg in packages:
            if pkg.path.parent.name != 'plugins':
                continue
            src_dir = pkg.path / 'src'
            if not src_dir.exists():
                continue

            for ns_dir in namespace_dirs:
                init_file = src_dir / ns_dir / '__init__.py'
                if init_file.exists():
                    relative = init_file.relative_to(pkg.path)
                    offenders.append(f'{pkg.name}: {relative}')

        if offenders:
            result.add_failure(
                check_name,
                f'Namespace dirs must not have __init__.py: {", ".join(offenders)}',
            )
        else:
            result.add_pass(check_name)

    def check_readme_field(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that publishable packages declare ``readme`` in ``[project]``.

        Without ``readme``, PyPI displays an empty page body — no
        description, no usage instructions, nothing. This is the single
        most impactful metadata field for user experience on PyPI.
        """
        check_name = 'readme_field'
        missing: list[str] = []

        for pkg in packages:
            if not pkg.is_publishable:
                continue
            try:
                content = pkg.pyproject_path.read_text(encoding='utf-8')
                data = tomlkit.parse(content)
            except Exception:
                missing.append(f'{pkg.name}: cannot parse pyproject.toml')
                continue

            project: dict[str, object] = data.get('project', {})
            if 'readme' not in project or not project['readme']:
                missing.append(pkg.name)

        if missing:
            result.add_warning(
                check_name,
                f'Missing readme field: {", ".join(missing)}',
                hint='Add readme = "README.md" to the [project] section in pyproject.toml.',
            )
        else:
            result.add_pass(check_name)

    def check_changelog_url(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that publishable packages have a ``Changelog`` entry in ``[project.urls]``.

        PyPI renders URL entries as sidebar links. The ``Changelog`` key
        is a well-known convention (alongside ``Homepage``, ``Repository``,
        ``Documentation``, ``Bug Tracker``) that users expect.
        """
        check_name = 'changelog_url'
        missing: list[str] = []

        for pkg in packages:
            if not pkg.is_publishable:
                continue
            try:
                content = pkg.pyproject_path.read_text(encoding='utf-8')
                data = tomlkit.parse(content)
            except Exception:
                missing.append(f'{pkg.name}: cannot parse pyproject.toml')
                continue

            project: dict[str, object] = data.get('project', {})
            urls_val = project.get('urls', {})
            urls = urls_val if isinstance(urls_val, dict) else {}
            has_changelog = any(key.lower() == 'changelog' for key in urls)
            if not has_changelog:
                missing.append(pkg.name)

        if missing:
            result.add_warning(
                check_name,
                f'Missing Changelog URL in [project.urls]: {", ".join(missing)}',
                hint='Add Changelog = "https://github.com/.../CHANGELOG.md" to [project.urls] in pyproject.toml.',
            )
        else:
            result.add_pass(check_name)

    def check_publish_classifier_consistency(
        self,
        packages: list[Package],
        result: PreflightResult,
        exclude_publish: list[str] | None = None,
    ) -> None:
        """Check that ``Private :: Do Not Upload`` classifier is consistent.

        Warns when:
        - A package is scheduled for publish (not in ``exclude_publish``)
          but has the ``Private :: Do Not Upload`` classifier.
        - A package is in ``exclude_publish`` but does NOT have the
          classifier (the config and the classifier should agree).
        """
        check_name = 'publish_classifier_consistency'
        if not exclude_publish:
            result.add_pass(check_name)
            return

        issues: list[str] = []
        for pkg in packages:
            is_excluded = any(fnmatch.fnmatch(pkg.name, pat) for pat in exclude_publish)
            has_private_classifier = not pkg.is_publishable

            if not is_excluded and has_private_classifier:
                issues.append(
                    f'{pkg.name}: has Private :: Do Not Upload but is NOT in exclude_publish',
                )
            elif is_excluded and not has_private_classifier:
                issues.append(
                    f'{pkg.name}: in exclude_publish but missing Private :: Do Not Upload classifier',
                )

        if issues:
            result.add_warning(
                check_name,
                f'Publish classifier mismatch: {"; ".join(issues)}',
                hint='Ensure exclude_publish patterns and Private :: Do Not Upload classifiers agree.',
            )
        else:
            result.add_pass(check_name)


_USE_DEFAULT = object()


def run_checks(
    packages: list[Package],
    graph: DependencyGraph,
    backend: CheckBackend | object = _USE_DEFAULT,
    exclude_publish: list[str] | None = None,
    groups: dict[str, list[str]] | None = None,
    workspace_root: Path | None = None,
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
    _check_ungrouped_packages(packages, groups or {}, result)
    if workspace_root is not None:
        _check_lockfile_staleness(workspace_root, result)

    # --- Language-specific checks (via backend) ---
    if backend is _USE_DEFAULT:
        backend = PythonCheckBackend()

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

    logger.info('checks_complete', summary=result.summary())
    return result


__all__ = [
    'CheckBackend',
    'PythonCheckBackend',
    'run_checks',
]
