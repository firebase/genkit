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

"""Universal (language-agnostic) workspace checks and fixers."""

from __future__ import annotations

import fnmatch
import importlib.resources as _resources
import shutil
import subprocess  # noqa: S404 - intentional use for uv lock check
from pathlib import Path

from releasekit.graph import DependencyGraph, detect_cycles
from releasekit.logging import get_logger
from releasekit.preflight import PreflightResult
from releasekit.security_insights import (
    SecurityInsightsConfig,
    generate_security_insights,
)
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
    locations: list[str] = []
    for pkg in packages:
        if pkg.name in pkg.internal_deps:
            offenders.append(pkg.name)
            locations.append(str(pkg.manifest_path))
    if offenders:
        result.add_failure(
            check_name,
            f'Packages depend on themselves: {", ".join(offenders)}',
            hint='Remove the package from its own [project.dependencies] list.',
            context=locations,
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
    locations: list[str] = []
    for pkg in packages:
        for dep in pkg.internal_deps:
            if dep not in known_names:
                orphans.append(f'{pkg.name} → {dep}')
                locations.append(str(pkg.manifest_path))
    if orphans:
        result.add_warning(
            check_name,
            f'Internal deps not found in workspace: {", ".join(orphans)}',
            hint='Add the missing packages to the workspace or remove the stale dependency.',
            context=locations,
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
    locations: list[str] = []
    for pkg in packages:
        if not pkg.is_publishable:
            continue
        license_path = pkg.path / 'LICENSE'
        if not license_path.exists():
            missing.append(pkg.name)
            locations.append(str(pkg.path))
    if missing:
        result.add_failure(
            check_name,
            f'Missing LICENSE file: {", ".join(missing)}',
            hint='Copy the Apache 2.0 LICENSE file into each listed package directory.',
            context=locations,
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
    locations: list[str] = []
    for pkg in packages:
        if not pkg.is_publishable:
            continue
        readme_path = pkg.path / 'README.md'
        if not readme_path.exists():
            missing.append(pkg.name)
            locations.append(str(pkg.path))
    if missing:
        result.add_failure(
            check_name,
            f'Missing README.md file: {", ".join(missing)}',
            hint='Create a README.md in each listed package directory describing the package.',
            context=locations,
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
    locations: list[str] = []
    for pkg in packages:
        bak_files = list(pkg.path.glob('*.bak'))
        if bak_files:
            stale.append(f'{pkg.name}: {len(bak_files)} .bak file(s)')
            locations.extend(str(f) for f in bak_files)

        dist_dir = pkg.path / 'dist'
        if dist_dir.is_dir():
            dist_files = list(dist_dir.iterdir())
            if dist_files:
                stale.append(f'{pkg.name}: dist/ has {len(dist_files)} file(s)')
                locations.append(str(dist_dir))

    if stale:
        result.add_warning(
            check_name,
            f'Stale artifacts: {"; ".join(stale)}',
            hint='Remove stale files with: rm -f *.bak && rm -rf dist/',
            context=locations,
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
    locations: list[str] = []
    for pkg in packages:
        if not any(fnmatch.fnmatch(pkg.name, pat) for pat in all_patterns):
            ungrouped.append(pkg.name)
            locations.append(str(pkg.manifest_path))

    if ungrouped:
        result.add_warning(
            check_name,
            f'Packages not in any config group: {", ".join(sorted(ungrouped))}',
            hint='Add each package to a [groups] entry in releasekit.toml so it is covered by exclusion rules.',
            context=locations,
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
                context=[str(workspace_root / 'uv.lock')],
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


def fix_stale_artifacts(
    packages: list[Package],
    *,
    dry_run: bool = False,
) -> list[str]:
    """Delete stale ``.bak`` files and ``dist/`` directories.

    These are leftovers from previous builds or crash-safe pin
    restoration. They should not be committed to version control.

    Args:
        packages: All discovered workspace packages.
        dry_run: If ``True``, report what would change without writing.

    Returns:
        List of human-readable descriptions of changes made.
    """
    changes: list[str] = []

    for pkg in packages:
        # Delete .bak files.
        for bak_file in pkg.path.rglob('*.bak'):
            relative = bak_file.relative_to(pkg.path)
            action = f'{pkg.name}: deleted {relative}'
            changes.append(action)
            if not dry_run:
                bak_file.unlink()
                logger.warning('fix_stale_artifacts', action=action, path=str(bak_file))

        # Delete dist/ directories.
        dist_dir = pkg.path / 'dist'
        if dist_dir.is_dir():
            action = f'{pkg.name}: deleted dist/'
            changes.append(action)
            if not dry_run:
                shutil.rmtree(dist_dir)
                logger.warning('fix_stale_artifacts', action=action, path=str(dist_dir))

    return changes


def fix_missing_readme(
    packages: list[Package],
    *,
    dry_run: bool = False,
) -> list[str]:
    """Create an empty ``README.md`` for packages that don't have one.

    Args:
        packages: All discovered workspace packages.
        dry_run: If ``True``, report what would change without writing.

    Returns:
        List of human-readable descriptions of changes made.
    """
    changes: list[str] = []

    for pkg in packages:
        readme_path = pkg.path / 'README.md'
        if readme_path.exists():
            continue

        action = f'{pkg.name}: created empty README.md'
        changes.append(action)
        if not dry_run:
            readme_path.write_text(f'# {pkg.name}\n', encoding='utf-8')
            logger.warning('fix_missing_readme', action=action, path=str(readme_path))

    return changes


def fix_missing_security_insights(
    workspace_root: Path,
    *,
    dry_run: bool = False,
    project_name: str = '',
    repo_url: str = '',
) -> list[str]:
    """Generate ``SECURITY-INSIGHTS.yml`` if it does not exist.

    Uses :mod:`releasekit.security_insights` to produce an OpenSSF
    Security Insights v2 file at the repository root.

    Args:
        workspace_root: Path to the repository root.
        dry_run: If ``True``, report what would change without writing.
        project_name: Project name for the generated file.
            Defaults to the workspace directory name.
        repo_url: Repository URL for the generated file.

    Returns:
        List of human-readable descriptions of changes made.
    """
    candidates = [
        workspace_root / 'SECURITY-INSIGHTS.yml',
        workspace_root / 'SECURITY_INSIGHTS.yml',
        workspace_root / '.github' / 'SECURITY-INSIGHTS.yml',
    ]
    for path in candidates:
        if path.is_file():
            return []

    si_path = workspace_root / 'SECURITY-INSIGHTS.yml'
    si_config = SecurityInsightsConfig(
        project_name=project_name or workspace_root.name,
        repo_url=repo_url,
    )

    changes: list[str] = []
    action = f'created SECURITY-INSIGHTS.yml at {si_path.relative_to(workspace_root)}'

    if dry_run:
        changes.append(f'(dry-run) {action}')
        logger.info('fix_missing_security_insights', action=action, dry_run=True)
    else:
        result = generate_security_insights(si_config, output_path=si_path)
        if result.generated:
            changes.append(action)
            logger.warning('fix_missing_security_insights', action=action, path=str(si_path))
        elif result.reason:
            logger.warning(
                'fix_missing_security_insights_failed',
                reason=result.reason,
            )

    return changes


def _get_bundled_license() -> str:
    """Read the Apache 2.0 LICENSE bundled with the releasekit package.

    Searches two locations:

    1. **Installed package** — ``importlib.resources`` finds the LICENSE
       file force-included inside the ``releasekit`` package directory
       in the wheel.  This works in tox venvs and pip installs.
    2. **Development tree** — Walk up from ``__file__`` to the project
       root (``tools/releasekit/LICENSE``).  This works when running
       from the source checkout without installing.
    """
    # 1. Try importlib.resources (works in installed environments).
    try:
        ref = _resources.files('releasekit').joinpath('LICENSE')
        license_text = ref.read_text(encoding='utf-8')
        if license_text:
            return license_text
    except (FileNotFoundError, ModuleNotFoundError, TypeError):
        pass

    # 2. Fall back to walking up from __file__ (dev tree).
    pkg_root = Path(__file__).resolve().parent.parent.parent.parent
    license_path = pkg_root / 'LICENSE'
    if license_path.is_file():
        return license_path.read_text(encoding='utf-8')
    logger.warning('bundled_license_not_found', path=str(license_path))
    return ''


def fix_missing_license(
    packages: list[Package],
    *,
    dry_run: bool = False,
) -> list[str]:
    """Create a ``LICENSE`` file for packages that don't have one.

    Copies the Apache 2.0 LICENSE bundled with the releasekit package
    itself. If the bundled license cannot be found, this fixer is a
    no-op.

    Args:
        packages: All discovered workspace packages.
        dry_run: If ``True``, report what would change without writing.

    Returns:
        List of human-readable descriptions of changes made.
    """
    license_text = _get_bundled_license()
    if not license_text:
        return []

    changes: list[str] = []

    for pkg in packages:
        license_path = pkg.path / 'LICENSE'
        if license_path.exists():
            continue

        action = f'{pkg.name}: created LICENSE (Apache 2.0)'
        changes.append(action)
        if not dry_run:
            license_path.write_text(license_text, encoding='utf-8')
            logger.warning('fix_missing_license', action=action, path=str(license_path))

    return changes
