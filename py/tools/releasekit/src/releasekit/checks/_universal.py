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
import re
import shutil
import subprocess  # noqa: S404 - intentional use for uv lock check
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, cast

import httpx
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

from releasekit.checks._license_detect import _detect_license_file, detect_license
from releasekit.checks._license_fetch import (
    LicenseFetchRequest,
    fetch_license_texts,
)
from releasekit.checks._license_graph import LicenseGraph
from releasekit.checks._license_lookup import extract_license_from_pypi_json
from releasekit.checks._license_resolve import LicenseResolver
from releasekit.checks._license_tree import (
    DepNode,
    DepStatus,
    LicenseTree,
    PackageTree,
    format_license_tree,
    registry_url_for,
    should_use_color,
)
from releasekit.checks._lockfile import (
    all_transitive_external_deps,
    parse_uv_lock,
    transitive_deps as _transitive_deps,
)
from releasekit.graph import DependencyGraph, detect_cycles
from releasekit.logging import get_logger
from releasekit.preflight import PreflightResult, SourceContext
from releasekit.security_insights import (
    SecurityInsightsConfig,
    generate_security_insights,
)
from releasekit.spdx_expr import (
    LicenseId,
    ParseError as SpdxParseError,
    is_compatible,
    license_ids,
    parse as spdx_parse,
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


# ── SPDX header enforcement ──────────────────────────────────────────

_SPDX_HEADER_RE: Final[re.Pattern[str]] = re.compile(
    r'SPDX-License-Identifier:\s*\S+',
)

# Source file extensions to check for SPDX headers.
_SPDX_SOURCE_EXTENSIONS: Final[frozenset[str]] = frozenset({
    '.py',
    '.js',
    '.ts',
    '.jsx',
    '.tsx',
    '.go',
    '.rs',
    '.java',
    '.kt',
    '.dart',
    '.c',
    '.h',
    '.cpp',
    '.hpp',
    '.cc',
    '.cxx',
    '.cs',
    '.swift',
    '.rb',
    '.sh',
    '.bash',
    '.zsh',
    '.toml',
    '.yaml',
    '.yml',
})

# Directories to skip when scanning for SPDX headers.
_SPDX_SKIP_DIRS: Final[frozenset[str]] = frozenset({
    '.git',
    '.hg',
    '__pycache__',
    'node_modules',
    '.venv',
    'venv',
    '.tox',
    '.mypy_cache',
    '.ruff_cache',
    '.pytest_cache',
    'dist',
    'build',
    '.eggs',
    '*.egg-info',
    'vendor',
    'third_party',
    '_vendor',
    '.dart_tool',
    '.pub-cache',
})


def _should_skip_dir(name: str) -> bool:
    """Check if a directory name should be skipped during SPDX scan."""
    if name in _SPDX_SKIP_DIRS:
        return True
    return name.endswith('.egg-info')


def _check_spdx_headers(
    packages: list[Package],
    result: PreflightResult,
) -> None:
    """Check that source files have ``SPDX-License-Identifier`` headers.

    Scans all source files (by extension) in each publishable package
    and reports files missing the SPDX header. This follows the
    `REUSE <https://reuse.software>`_ specification.

    Args:
        packages: All workspace packages.
        result: Accumulator for check outcomes.
    """
    check_name = 'spdx_headers'
    missing: list[str] = []
    missing_contexts: list[str | SourceContext] = []
    max_report = 20  # Cap to avoid overwhelming output.

    for pkg in packages:
        if not pkg.is_publishable:
            continue
        for src_file in _walk_source_files(pkg.path):
            if len(missing) >= max_report:
                break
            try:
                # Only read the first 4KB — header should be near the top.
                head = src_file.read_text(encoding='utf-8', errors='replace')[:4096]
            except OSError:
                continue
            if not _SPDX_HEADER_RE.search(head):
                rel = src_file.relative_to(pkg.path)
                missing.append(f'{pkg.name}/{rel}')
                missing_contexts.append(
                    SourceContext(
                        path=str(src_file),
                        line=1,
                        key='SPDX-License-Identifier',
                        label='missing SPDX header',
                    )
                )

    if missing:
        suffix = ''
        if len(missing) >= max_report:
            suffix = f' (showing first {max_report})'
        result.add_warning(
            check_name,
            f'Files missing SPDX-License-Identifier header: {len(missing)}{suffix}',
            hint=(
                'Add an SPDX-License-Identifier comment to each source file. '
                'Example: # SPDX-License-Identifier: Apache-2.0\n'
                'See https://reuse.software for the full specification.'
            ),
            context=missing_contexts,
        )
    else:
        result.add_pass(check_name)


def _walk_source_files(root: Path) -> list[Path]:
    """Walk *root* and return source files matching known extensions.

    Skips directories in :data:`_SPDX_SKIP_DIRS`.
    """
    results: list[Path] = []
    if not root.is_dir():
        return results
    for child in sorted(root.iterdir()):
        if child.is_dir():
            if _should_skip_dir(child.name):
                continue
            results.extend(_walk_source_files(child))
        elif child.is_file() and child.suffix in _SPDX_SOURCE_EXTENSIONS:
            results.append(child)
    return results


def fix_missing_spdx_headers(
    packages: list[Package],
    *,
    dry_run: bool = False,
    copyright_holder: str = 'Google LLC',
    license_type: str = 'apache',
    license_file: str = '',
    spdx_only: bool = False,
    year: str = '',
    ignore: list[str] | None = None,
    verbose: bool = False,
) -> list[str]:
    """Fix missing license headers by shelling out to ``addlicense``.

    Uses `google/addlicense <https://github.com/google/addlicense>`_
    to add copyright license headers to source files that are missing
    them. The tool must be installed (``go install
    github.com/google/addlicense@latest``).

    Args:
        packages: All workspace packages.
        dry_run: If ``True``, run in check-only mode (``-check``).
        copyright_holder: Copyright holder string (``-c`` flag).
        license_type: License type: ``apache``, ``bsd``, ``mit``,
            ``mpl`` (``-l`` flag).
        license_file: Path to a custom license header file (``-f``).
        spdx_only: If ``True``, only add the SPDX identifier line
            (``-s=only``).
        year: Copyright year(s) string (``-y`` flag).
        ignore: Glob patterns to ignore (``-ignore`` flags).
        verbose: Print names of modified files (``-v`` flag).

    Returns:
        List of human-readable descriptions of changes made.
    """
    addlicense = shutil.which('addlicense')
    if addlicense is None:
        logger.warning(
            'addlicense_not_found',
            hint='Install with: go install github.com/google/addlicense@latest',
        )
        return ['addlicense not found on PATH — skipping header fix']

    changes: list[str] = []

    for pkg in packages:
        if not pkg.is_publishable:
            continue

        cmd: list[str] = [addlicense]

        # Build flags from config.
        cmd.extend(['-c', copyright_holder])

        if license_file:
            cmd.extend(['-f', license_file])
        else:
            cmd.extend(['-l', license_type])

        if spdx_only:
            cmd.append('-s=only')

        if year:
            cmd.extend(['-y', year])

        if verbose:
            cmd.append('-v')

        if dry_run:
            cmd.append('-check')

        # Add ignore patterns.
        for pattern in ignore or []:
            cmd.extend(['-ignore', pattern])

        # Target the package directory.
        cmd.append(str(pkg.path))

        action = f'{pkg.name}: {"check" if dry_run else "fix"} license headers'
        if dry_run:
            changes.append(f'(dry-run) {action}: {" ".join(cmd)}')
            continue

        try:
            result = subprocess.run(  # noqa: S603
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode == 0:
                changes.append(f'{action}: OK')
            else:
                stderr = result.stderr.strip()[:200] if result.stderr else ''
                changes.append(f'{action}: addlicense exited {result.returncode}')
                if stderr:
                    changes.append(f'  stderr: {stderr}')
        except FileNotFoundError:
            changes.append(f'{action}: addlicense binary not found')
            break
        except subprocess.TimeoutExpired:
            changes.append(f'{action}: timed out after 120s')

        logger.warning('fix_spdx_headers', action=action, path=str(pkg.path))

    return changes


async def fix_missing_license_files(
    packages: list[Package],
    *,
    dry_run: bool = False,
    try_github: bool = True,
    try_pypi_source: bool = True,
    concurrency: int = 8,
) -> list[str]:
    """Fetch and write LICENSE files for packages that are missing them.

    For each publishable package that has a detected SPDX license ID
    but no LICENSE file on disk, this fixer:

    1. Tries to fetch the LICENSE from the package's GitHub repo
       (preferred — may contain copyright-holder-specific text).
    2. Falls back to the canonical SPDX license text from the
       `spdx/license-list-data <https://github.com/spdx/license-list-data>`_
       repository.

    All fetches run concurrently via :func:`asyncio.gather` with a
    configurable concurrency semaphore.

    Args:
        packages: All workspace packages.
        dry_run: If ``True``, report what would change without writing.
        try_github: Whether to try fetching from GitHub repos.
        try_pypi_source: Whether to resolve source URLs from PyPI
            when the package has no explicit source URL.
        concurrency: Maximum concurrent HTTP requests.

    Returns:
        List of human-readable descriptions of changes made.
    """
    license_names = frozenset({
        'LICENSE',
        'LICENSE.md',
        'LICENSE.txt',
        'LICENCE',
        'LICENCE.md',
        'LICENCE.txt',
        'COPYING',
        'COPYING.md',
    })

    # Identify packages missing a LICENSE file but with a known SPDX ID.
    fetch_requests: list[LicenseFetchRequest] = []
    pkg_map: dict[str, Package] = {}

    for pkg in packages:
        if not pkg.is_publishable:
            continue

        # Check if any license file already exists.
        has_license = any((pkg.path / name).is_file() for name in license_names)
        if has_license:
            continue

        # Detect the SPDX ID from manifest metadata.
        detected = detect_license(pkg)
        if not detected.found:
            continue

        fetch_requests.append(
            LicenseFetchRequest(
                package=pkg.name,
                spdx_id=detected.value,
            )
        )
        pkg_map[pkg.name] = pkg

    if not fetch_requests:
        return []

    # Fetch all LICENSE texts concurrently.
    fetched = await fetch_license_texts(
        fetch_requests,
        concurrency=concurrency,
        try_github=try_github,
        try_pypi_source=try_pypi_source,
    )

    changes: list[str] = []
    for req in fetch_requests:
        result = fetched.get(req.package)
        if result is None or not result.ok:
            changes.append(f'{req.package}: could not fetch LICENSE for {req.spdx_id}')
            continue

        pkg = pkg_map[req.package]
        license_path = pkg.path / 'LICENSE'
        action = f'{req.package}: wrote LICENSE ({req.spdx_id}) from {result.source}'

        if dry_run:
            changes.append(f'(dry-run) {action}')
        else:
            license_path.write_text(result.text, encoding='utf-8')
            changes.append(action)
            logger.info(
                'fix_missing_license',
                package=req.package,
                spdx_id=req.spdx_id,
                source=result.source,
                path=str(license_path),
            )

    return changes


# ── Deep source scan for vendored / embedded licenses ────────────────

# Directories that commonly contain vendored code.
_VENDOR_DIR_NAMES: Final[frozenset[str]] = frozenset({
    'vendor',
    'vendored',
    '_vendor',
    'third_party',
    'thirdparty',
    '3rdparty',
    'extern',
    'external',
    'bundled',
})


@dataclass(frozen=True)
class EmbeddedLicense:
    """A license found in a vendored or embedded file.

    Attributes:
        path: Absolute path to the license file.
        relative_path: Path relative to the package root.
        spdx_id: Detected SPDX ID (or raw text).
        source: Where the license was found (e.g. 'vendor/foo/LICENSE').
        package_name: Parent package name.
        is_vendored: Whether this is inside a known vendor directory.
    """

    path: str
    relative_path: str
    spdx_id: str
    source: str
    package_name: str
    is_vendored: bool = False


def _check_deep_license_scan(
    packages: list[Package],
    result: PreflightResult,
    *,
    project_license: str = '',
) -> None:
    """Deep scan for vendored/embedded files with different licenses.

    Walks each publishable package looking for LICENSE files in
    subdirectories (especially vendor/third_party dirs) and checks
    whether their detected license differs from the project license.

    Args:
        packages: All workspace packages.
        result: Accumulator for check outcomes.
        project_license: The project's SPDX license ID.
    """
    check_name = 'deep_license_scan'
    mismatches: list[str] = []
    mismatch_contexts: list[str | SourceContext] = []
    all_embedded: list[EmbeddedLicense] = []

    license_names = frozenset({
        'LICENSE',
        'LICENSE.md',
        'LICENSE.txt',
        'LICENCE',
        'LICENCE.md',
        'LICENCE.txt',
        'COPYING',
        'COPYING.md',
        'NOTICE',
        'NOTICE.md',
    })

    for pkg in packages:
        if not pkg.is_publishable:
            continue
        for lic_file in _walk_license_files(
            pkg.path,
            license_names,
            include_vendor=True,
        ):
            # Skip the top-level LICENSE (already checked elsewhere).
            try:
                rel = lic_file.relative_to(pkg.path)
            except ValueError:
                continue
            if str(rel) in license_names:
                continue

            # Detect the license in this embedded file.
            from releasekit.checks._license_detect import (
                _LICENSE_FILE_PATTERNS,
            )

            try:
                text = lic_file.read_text(
                    encoding='utf-8',
                    errors='replace',
                )[:2000]
            except OSError:
                continue

            detected_spdx = ''
            for compiled_re, spdx_id in _LICENSE_FILE_PATTERNS:
                if compiled_re.search(text):
                    detected_spdx = spdx_id
                    break

            is_vendored = any(part in _VENDOR_DIR_NAMES for part in rel.parts[:-1])

            embedded = EmbeddedLicense(
                path=str(lic_file),
                relative_path=str(rel),
                spdx_id=detected_spdx or '(unknown)',
                source=str(rel),
                package_name=pkg.name,
                is_vendored=is_vendored,
            )
            all_embedded.append(embedded)

            # Flag if it differs from the project license.
            if project_license and detected_spdx and detected_spdx != project_license:
                mismatches.append(f'{pkg.name}/{rel} ({detected_spdx} ≠ project {project_license})')
                mismatch_contexts.append(
                    SourceContext(
                        path=str(lic_file),
                        line=1,
                        key=detected_spdx,
                        label=f'embedded license differs: {detected_spdx}',
                    )
                )

    # Store all embedded licenses in context for downstream use.
    result.context.setdefault('embedded_licenses', cast(Sequence[str | SourceContext], all_embedded))

    if mismatches:
        result.add_warning(
            check_name,
            f'Embedded files with different licenses: {"; ".join(mismatches[:10])}',
            hint=(
                'Vendored or bundled code may carry a different license. '
                'Verify compatibility and include proper attribution in '
                'your NOTICE file.'
            ),
            context=mismatch_contexts,
        )
    elif all_embedded:
        result.add_pass(check_name)
    else:
        result.add_pass(check_name)


def _walk_license_files(
    root: Path,
    names: frozenset[str],
    *,
    include_vendor: bool = False,
) -> list[Path]:
    """Recursively find license files under *root*.

    Args:
        root: Directory to walk.
        names: Set of license file names to match.
        include_vendor: If ``True``, walk into vendor/third_party dirs
            (used by the deep scan). Default skips them.
    """
    results: list[Path] = []
    if not root.is_dir():
        return results
    for child in sorted(root.iterdir()):
        if child.is_dir():
            if not include_vendor and _should_skip_dir(child.name):
                continue
            # Always skip .git, __pycache__, .venv even in deep mode.
            if include_vendor and child.name in {
                '.git',
                '.hg',
                '__pycache__',
                '.venv',
                'venv',
                '.tox',
                '.mypy_cache',
                '.ruff_cache',
                '.pytest_cache',
                'dist',
                'build',
                '.eggs',
                '.dart_tool',
                '.pub-cache',
            }:
                continue
            if include_vendor and child.name.endswith('.egg-info'):
                continue
            results.extend(
                _walk_license_files(child, names, include_vendor=include_vendor),
            )
        elif child.is_file() and child.name in names:
            results.append(child)
    return results


# ── License change detection ─────────────────────────────────────────


@dataclass(frozen=True)
class LicenseChange:
    """A detected license change between dependency versions.

    Attributes:
        package_name: The dependency that changed.
        old_version: Previous version string.
        new_version: Current version string.
        old_license: Previous license SPDX ID.
        new_license: Current license SPDX ID.
    """

    package_name: str
    old_version: str
    new_version: str
    old_license: str
    new_license: str


def _check_license_changes(
    packages: list[Package],
    result: PreflightResult,
    *,
    previous_licenses: dict[str, str] | None = None,
) -> None:
    """Detect dependencies that changed their license between versions.

    Compares the currently detected license for each dependency against
    a previously recorded snapshot (``previous_licenses``). This catches
    cases like Elasticsearch moving from Apache-2.0 to SSPL.

    Args:
        packages: All workspace packages.
        result: Accumulator for check outcomes.
        previous_licenses: Mapping from package name to previously
            known SPDX ID. If ``None``, the check is skipped.
    """
    check_name = 'license_changes'

    if previous_licenses is None:
        result.add_pass(check_name)
        return

    changes: list[LicenseChange] = []
    change_msgs: list[str] = []
    change_contexts: list[str | SourceContext] = []

    # Build current license map.
    current_licenses: dict[str, str] = {}
    for pkg in packages:
        detected = detect_license(pkg)
        if detected.found:
            resolved = LicenseResolver(LicenseGraph.load()).resolve(detected.value)
            if resolved.resolved:
                current_licenses[pkg.name] = resolved.spdx_id

    for pkg_name, old_spdx in previous_licenses.items():
        new_spdx = current_licenses.get(pkg_name)
        if new_spdx and new_spdx != old_spdx:
            change = LicenseChange(
                package_name=pkg_name,
                old_version='',
                new_version='',
                old_license=old_spdx,
                new_license=new_spdx,
            )
            changes.append(change)
            change_msgs.append(f'{pkg_name}: {old_spdx} → {new_spdx}')
            # Find the package for context.
            for pkg in packages:
                if pkg.name == pkg_name:
                    change_contexts.append(
                        SourceContext(
                            path=str(pkg.manifest_path),
                            line=0,
                            key=pkg_name,
                            label=f'license changed: {old_spdx} → {new_spdx}',
                        )
                    )
                    break

    result.context.setdefault('license_change_details', cast(Sequence[str | SourceContext], changes))

    if changes:
        result.add_warning(
            check_name,
            f'License changed for: {"; ".join(change_msgs)}',
            hint=(
                'A dependency changed its license between versions. '
                'Review the new license for compatibility with your '
                'project before upgrading.'
            ),
            context=change_contexts,
        )
    else:
        result.add_pass(check_name)


# ── L5: Dual-license OR choice enforcement ───────────────────────────

# SPDX OR expressions that require a documented choice.
_OR_RE: Final[re.Pattern[str]] = re.compile(r'\bOR\b', re.IGNORECASE)


def _check_dual_license_choice(
    packages: list[Package],
    result: PreflightResult,
    *,
    license_choices: dict[str, str] | None = None,
) -> None:
    """Check that dual-licensed deps have a documented license choice.

    When a dependency uses an SPDX ``OR`` expression (e.g.
    ``MIT OR Apache-2.0``), some organisations require the chosen side
    to be documented. This check warns about deps with undocumented
    choices unless they appear in *license_choices*.

    Args:
        packages: All workspace packages.
        result: Accumulator for check outcomes.
        license_choices: Mapping from package name to the chosen SPDX
            ID. If ``None``, the check is skipped.
    """
    check_name = 'dual_license_choice'

    if license_choices is None:
        result.add_pass(check_name)
        return

    undocumented: list[str] = []
    undocumented_contexts: list[str | SourceContext] = []

    for pkg in packages:
        if not pkg.is_publishable:
            continue
        for dep_name in pkg.internal_deps + pkg.external_deps:
            detected = detect_license(pkg)
            if not detected.found:
                continue
            raw = detected.value
            if not _OR_RE.search(raw):
                continue
            if dep_name in license_choices:
                continue
            undocumented.append(f'{pkg.name} → {dep_name} ({raw})')
            undocumented_contexts.append(
                _make_source_context(
                    pkg.manifest_path,
                    dep_name,
                    f'dual-license: {raw}',
                )
            )

    if undocumented:
        result.add_warning(
            check_name,
            f'Dual-licensed deps without documented choice: {"; ".join(undocumented)}',
            hint=(
                'Add a [license.choices] section to releasekit.toml '
                'mapping each dual-licensed package to the chosen SPDX ID. '
                'Example: [license.choices]\n'
                '"serde" = "MIT"  # chose MIT side of MIT OR Apache-2.0'
            ),
            context=undocumented_contexts,
        )
    else:
        result.add_pass(check_name)


# ── L6: Patent clause flagging ───────────────────────────────────────
#
# Patent grant / retaliation data is now stored in licenses.toml
# (``patent_grant`` and ``patent_retaliation`` boolean fields) and
# queried via ``LicenseGraph.patent_grant_licenses()`` /
# ``LicenseGraph.patent_retaliation_licenses()``.


def _check_patent_clauses(
    packages: list[Package],
    result: PreflightResult,
) -> None:
    """Flag dependencies with patent grant or retaliation clauses.

    This is informational — it does not fail the check, but warns
    about licenses that have patent-related clauses that legal teams
    should be aware of.  The sets of affected licenses are driven by
    the ``patent_grant`` / ``patent_retaliation`` fields in
    ``licenses.toml``, not hardcoded.

    Args:
        packages: All workspace packages.
        result: Accumulator for check outcomes.
    """
    check_name = 'patent_clauses'
    flagged: list[str] = []

    try:
        graph = LicenseGraph.load()
    except Exception:  # noqa: BLE001
        result.add_pass(check_name)
        return

    patent_grant_ids = graph.patent_grant_licenses()
    patent_retaliation_ids = graph.patent_retaliation_licenses()
    resolver = LicenseResolver(graph)

    for pkg in packages:
        if not pkg.is_publishable:
            continue
        detected = detect_license(pkg)
        if not detected.found:
            continue
        resolved = resolver.resolve(detected.value)
        if not resolved.resolved:
            continue

        spdx = resolved.spdx_id
        clauses: list[str] = []
        if spdx in patent_grant_ids:
            clauses.append('patent-grant')
        if spdx in patent_retaliation_ids:
            clauses.append('patent-retaliation')
        if clauses:
            flagged.append(f'{pkg.name} ({spdx}): {", ".join(clauses)}')

    if flagged:
        result.add_warning(
            check_name,
            f'Packages with patent clauses: {"; ".join(flagged)}',
            hint=(
                'These licenses contain patent grant and/or patent '
                'retaliation clauses. Ensure your legal team has '
                'reviewed the implications for your project.'
            ),
        )
    else:
        result.add_pass(check_name)


# ── L9: License text completeness verification ──────────────────────


def _check_license_text_completeness(
    packages: list[Package],
    result: PreflightResult,
) -> None:
    """Verify that LICENSE file content matches the declared SPDX ID.

    Checks that the LICENSE file text is non-empty and contains
    patterns consistent with the declared license. Catches truncated,
    empty, or mismatched LICENSE files.

    Args:
        packages: All workspace packages.
        result: Accumulator for check outcomes.
    """
    check_name = 'license_text_completeness'
    issues: list[str] = []
    issue_contexts: list[str | SourceContext] = []

    try:
        graph = LicenseGraph.load()
    except Exception:  # noqa: BLE001
        result.add_pass(check_name)
        return

    resolver = LicenseResolver(graph)

    for pkg in packages:
        if not pkg.is_publishable:
            continue

        # Get the declared license from manifest.
        detected = detect_license(pkg)
        if not detected.found:
            continue
        resolved = resolver.resolve(detected.value)
        if not resolved.resolved:
            continue
        declared_spdx = resolved.spdx_id

        # Read the LICENSE file.
        license_text = ''
        license_path: Path | None = None
        for name in ('LICENSE', 'LICENSE.md', 'LICENSE.txt', 'LICENCE', 'COPYING'):
            candidate = pkg.path / name
            if candidate.is_file():
                try:
                    license_text = candidate.read_text(
                        encoding='utf-8',
                        errors='replace',
                    )
                    license_path = candidate
                except OSError:
                    pass
                break

        if license_path is None:
            # No LICENSE file — _check_missing_license handles this.
            continue

        # Check 1: Empty or near-empty LICENSE file.
        stripped = license_text.strip()
        if len(stripped) < 20:
            issues.append(f'{pkg.name}: LICENSE file is empty or truncated')
            issue_contexts.append(
                SourceContext(
                    path=str(license_path),
                    line=1,
                    key=pkg.name,
                    label='empty or truncated LICENSE',
                )
            )
            continue

        # Check 2: Verify text matches declared SPDX ID.
        # Use the same pattern matching as _detect_license_file.
        detected_from_text = _detect_license_file(pkg.path, pkg.name)
        if detected_from_text is not None and detected_from_text.found:
            text_resolved = resolver.resolve(detected_from_text.value)
            if text_resolved.resolved and text_resolved.spdx_id != declared_spdx:
                issues.append(
                    f'{pkg.name}: manifest says {declared_spdx} but LICENSE text looks like {text_resolved.spdx_id}'
                )
                issue_contexts.append(
                    SourceContext(
                        path=str(license_path),
                        line=1,
                        key=pkg.name,
                        label=(f'declared {declared_spdx}, text matches {text_resolved.spdx_id}'),
                    )
                )

    if issues:
        result.add_warning(
            check_name,
            f'License text issues: {"; ".join(issues)}',
            hint=(
                'Ensure each LICENSE file contains the full text of '
                'the declared license. Empty, truncated, or mismatched '
                'LICENSE files can cause compliance failures.'
            ),
            context=issue_contexts,
        )
    else:
        result.add_pass(check_name)


# ── NOTICE / attribution file generation ─────────────────────────────


@dataclass
class NoticeEntry:
    """A single entry in a NOTICE/attribution file.

    Attributes:
        package_name: Dependency package name.
        license_spdx: Resolved SPDX ID.
        copyright_text: Copyright line(s) extracted from LICENSE file.
        license_text: Full license text (for attribution).
    """

    package_name: str
    license_spdx: str = ''
    copyright_text: str = ''
    license_text: str = ''


_COPYRIGHT_RE: Final[re.Pattern[str]] = re.compile(
    r'(?i)^(?:copyright\b.*\d{4}.*|©.*\d{4}.*)$',
    re.MULTILINE,
)


def generate_notice_file(
    packages: list[Package],
    project_name: str = '',
    project_license: str = '',
    external_licenses: dict[str, str] | None = None,
) -> str:
    """Generate a NOTICE file with attribution for all dependencies.

    Scans each package for LICENSE files, extracts copyright lines,
    and assembles a NOTICE file following the Apache-2.0 §4(d)
    convention.

    When *external_licenses* is provided (e.g. from transitive dep
    resolution via ``uv.lock`` + PyPI lookup), those packages are
    included in a separate "External Dependencies" section so the
    NOTICE covers the full transitive closure.

    Args:
        packages: All workspace packages.
        project_name: Name of the project for the header.
        project_license: Project's SPDX license ID.
        external_licenses: Mapping from external package name to
            SPDX license ID (e.g. from :func:`_resolve_external_licenses`
            or lockfile transitive dep resolution).

    Returns:
        The NOTICE file content as a string.
    """
    entries: list[NoticeEntry] = []

    for pkg in packages:
        detected = detect_license(pkg)
        spdx_id = detected.value if detected.found else ''

        # Try to read the LICENSE file for copyright and text.
        copyright_text = ''
        license_text = ''
        for name in ('LICENSE', 'LICENSE.md', 'LICENSE.txt', 'LICENCE', 'COPYING'):
            lic_path = pkg.path / name
            if lic_path.is_file():
                try:
                    text = lic_path.read_text(encoding='utf-8', errors='replace')
                    license_text = text
                    # Extract copyright lines.
                    matches = _COPYRIGHT_RE.findall(text)
                    if matches:
                        copyright_text = '\n'.join(matches)
                except OSError:
                    pass
                break

        entries.append(
            NoticeEntry(
                package_name=pkg.name,
                license_spdx=spdx_id,
                copyright_text=copyright_text,
                license_text=license_text,
            )
        )

    # Assemble the NOTICE file.
    lines: list[str] = []
    header = project_name or 'This project'
    lines.append(f'{header}')
    if project_license:
        lines.append(f'Licensed under {project_license}')
    lines.append('')
    lines.append('This product includes software developed by third parties.')
    lines.append('=' * 72)
    lines.append('')

    # Workspace packages section.
    workspace_names = {pkg.name for pkg in packages}
    for entry in sorted(entries, key=lambda e: e.package_name):
        lines.append(f'## {entry.package_name}')
        if entry.license_spdx:
            lines.append(f'License: {entry.license_spdx}')
        if entry.copyright_text:
            lines.append(entry.copyright_text)
        lines.append('')

    # External / transitive dependencies section.
    ext = external_licenses or {}
    ext_entries = {name: spdx for name, spdx in ext.items() if name not in workspace_names}
    if ext_entries:
        lines.append('=' * 72)
        lines.append('External Dependencies (transitive)')
        lines.append('=' * 72)
        lines.append('')
        for name in sorted(ext_entries):
            spdx = ext_entries[name]
            lines.append(f'## {name}')
            if spdx:
                lines.append(f'License: {spdx}')
            lines.append('')

    return '\n'.join(lines)


def fix_missing_notice(
    packages: list[Package],
    workspace_root: Path,
    *,
    dry_run: bool = False,
    project_name: str = '',
    project_license: str = '',
    external_licenses: dict[str, str] | None = None,
) -> list[str]:
    """Generate a ``NOTICE`` file if one does not exist.

    Args:
        packages: All workspace packages.
        workspace_root: Path to the repository root.
        dry_run: If ``True``, report what would change without writing.
        project_name: Project name for the NOTICE header.
        project_license: Project's SPDX license ID.
        external_licenses: Mapping from external package name to
            SPDX license ID for transitive deps.

    Returns:
        List of human-readable descriptions of changes made.
    """
    notice_path = workspace_root / 'NOTICE'
    if notice_path.is_file():
        return []

    content = generate_notice_file(
        packages,
        project_name=project_name,
        project_license=project_license,
        external_licenses=external_licenses,
    )

    changes: list[str] = []
    action = 'created NOTICE file with dependency attribution'

    if dry_run:
        changes.append(f'(dry-run) {action}')
    else:
        notice_path.write_text(content, encoding='utf-8')
        changes.append(action)
        logger.warning('fix_missing_notice', action=action, path=str(notice_path))

    return changes


@dataclass(frozen=True)
class LicenseExemptions:
    """Configuration for license compatibility exemptions.

    Attributes:
        exempt_packages: Package names that are unconditionally exempt
            from license compatibility checks (e.g. commercially
            licensed deps).
        allow_licenses: SPDX IDs that are always considered compatible
            regardless of graph edges (global allow-list).
        deny_licenses: SPDX IDs that are unconditionally blocked.
            Any dependency whose resolved license (or any leaf ID in
            an SPDX expression) appears here is a hard failure.
            Checked **before** compatibility — even if the graph says
            compatible, a denied license still fails.
        license_overrides: Mapping from package name → SPDX expression
            string. Overrides the auto-detected license for a dep.
            Useful when detection is wrong or the dep has a private
            license agreement.
        project_exceptions: Mapping from package name → frozenset of
            SPDX IDs that are exempted from the deny-list **for that
            package only**. Use this when a specific project has
            negotiated an exception to the corporate deny policy.
        workspace_exceptions: SPDX IDs exempted from the deny-list
            for the **entire workspace**. Use this when a workspace
            has a blanket exception (e.g. an internal monorepo that
            is allowed to use AGPL internally).

    Example ``releasekit.toml`` config::

        [license]
        project = "Apache-2.0"

        # Packages with commercial licenses — skip compatibility check.
        exempt_packages = ["oracle-jdbc", "some-proprietary-sdk"]

        # Licenses always allowed (e.g. your org has a blanket CLA).
        allow_licenses = ["SSPL-1.0"]

        # Licenses unconditionally blocked by corporate policy.
        deny_licenses = ["AGPL-3.0-only", "AGPL-3.0-or-later", "SSPL-1.0"]

        # Workspace-wide exception to the deny-list.
        workspace_exceptions = ["AGPL-3.0-only"]

        # Override detected license for specific packages.
        [license.overrides]
        "weird-lib" = "MIT"               # detection was wrong
        "dual-lib" = "MIT OR GPL-2.0-only" # pick the right expression

        # Per-project exceptions to the deny-list.
        [license.project_exceptions]
        "internal-tool" = ["SSPL-1.0"]  # approved for this project only
    """

    exempt_packages: frozenset[str] = frozenset()
    allow_licenses: frozenset[str] = frozenset()
    deny_licenses: frozenset[str] = frozenset()
    license_overrides: dict[str, str] = field(default_factory=dict)
    project_exceptions: dict[str, frozenset[str]] = field(default_factory=dict)
    workspace_exceptions: frozenset[str] = frozenset()


def _resolve_all_ids(
    raw_license: str,
    resolver: LicenseResolver,
) -> set[str]:
    """Resolve all SPDX IDs mentioned in a raw license string.

    Tries to parse as an SPDX expression first to extract all leaf
    IDs.  Falls back to single-ID resolution.

    Returns:
        Set of resolved canonical SPDX IDs (may be empty).
    """
    try:
        expr = spdx_parse(raw_license)
        return license_ids(expr)
    except SpdxParseError:
        pass

    resolved = resolver.resolve(raw_license)
    if resolved.resolved:
        return {resolved.spdx_id}
    return set()


def _is_expression_compatible(
    raw_license: str,
    proj_spdx: str,
    graph: LicenseGraph,
    resolver: LicenseResolver,
    allow_licenses: frozenset[str],
) -> bool:
    """Check if a raw license string is compatible with the project license.

    Tries to parse *raw_license* as an SPDX expression first (handling
    ``OR`` / ``AND`` / ``WITH`` / ``+``).  Falls back to single-ID
    resolution if parsing fails.

    Args:
        raw_license: The raw license string (may be an SPDX expression).
        proj_spdx: The resolved project SPDX ID.
        graph: The license compatibility graph.
        resolver: The fuzzy resolver.
        allow_licenses: Global allow-list of SPDX IDs.
    """
    # Try parsing as a full SPDX expression.
    try:
        expr = spdx_parse(raw_license)
        # If the parsed expression is a simple LicenseId that the graph
        # doesn't recognise (e.g. bare "BSD" or "PSF"), skip straight to
        # the fuzzy resolver which can map it via aliases.
        if isinstance(expr, LicenseId) and not graph.known(expr.id):
            pass  # fall through to resolver below
        else:
            return is_compatible(expr, graph, proj_spdx)
    except SpdxParseError:
        pass

    # Fall back to single-ID resolution.
    resolved = resolver.resolve(raw_license)
    if not resolved.resolved:
        return False
    if resolved.spdx_id in allow_licenses:
        return True
    return graph.is_compatible(proj_spdx, resolved.spdx_id)


def _find_dep_line(manifest_path: Path, dep_name: str) -> int:
    """Find the line number where *dep_name* appears in a manifest file.

    Returns 0 if the file cannot be read or the dep is not found.
    """
    try:
        content = manifest_path.read_text(encoding='utf-8')
    except Exception:  # noqa: BLE001
        return 0
    for i, line in enumerate(content.splitlines(), 1):
        if dep_name in line:
            return i
    return 0


def _make_source_context(
    manifest_path: Path,
    dep_name: str,
    label: str,
) -> SourceContext:
    """Build a :class:`SourceContext` pointing at *dep_name* in the manifest."""
    line = _find_dep_line(manifest_path, dep_name)
    return SourceContext(
        path=str(manifest_path),
        line=line,
        key=dep_name,
        label=label,
    )


def _resolve_external_licenses(
    dep_names: set[str],
    pkg_raw_licenses: dict[str, str],
    pkg_license_sources: dict[str, str] | None = None,
) -> None:
    """Resolve licenses for external deps via PyPI registry lookup.

    This is a synchronous helper that queries PyPI's JSON API for each
    unresolved external dependency. Results are merged into
    *pkg_raw_licenses* in-place.

    Uses :func:`~releasekit.checks._license_lookup.extract_license_from_pypi_json`
    for the actual response parsing to avoid duplicating extraction logic.

    Shows a Rich progress bar during fetching so users know the command
    isn't hung. Displays cache hit/miss/error stats on completion.

    Only PyPI is queried because the workspace discovery currently only
    supports Python ecosystems. When other ecosystems are added, this
    should dispatch to the appropriate registry.

    Args:
        dep_names: Set of external dependency names to look up.
        pkg_raw_licenses: Mutable mapping to update with results.
        pkg_license_sources: Optional mutable mapping to update with
            detection source strings (e.g. ``'PyPI registry'``).
    """
    sorted_deps = sorted(dep_names)
    total = len(sorted_deps)
    if total == 0:
        return

    # Stats counters.
    resolved = 0
    no_license = 0
    errors = 0

    console = Console(stderr=True, force_terminal=None)
    progress = Progress(
        SpinnerColumn(),
        TextColumn('[bold blue]Fetching licenses'),
        BarColumn(bar_width=30),
        MofNCompleteColumn(),
        TextColumn('•'),
        TextColumn('[dim]{task.fields[current]}'),
        TextColumn('•'),
        TimeElapsedColumn(),
        console=console,
        transient=True,
        disable=not sys.stderr.isatty(),
    )

    with progress:
        task = progress.add_task(
            'Fetching',
            total=total,
            current='starting…',
        )

        for dep_name in sorted_deps:
            progress.update(task, current=dep_name)

            url = f'https://pypi.org/pypi/{dep_name}/json'
            try:
                resp = httpx.get(url, timeout=10, follow_redirects=True)
                if resp.status_code != 200:
                    errors += 1
                    progress.advance(task)
                    continue
                data = resp.json()
            except Exception:  # noqa: BLE001, S112
                errors += 1
                progress.advance(task)
                continue

            result = extract_license_from_pypi_json(data.get('info', {}), dep_name)
            if result.value:
                pkg_raw_licenses[dep_name] = result.value
                if pkg_license_sources is not None:
                    pkg_license_sources[dep_name] = result.source or 'PyPI registry'
                resolved += 1
            else:
                no_license += 1

            progress.advance(task)

    # Print summary line.
    parts: list[str] = [f'[bold]License lookup:[/] {total} packages queried']
    if resolved:
        parts.append(f'[green]{resolved} resolved[/]')
    if no_license:
        parts.append(f'[yellow]{no_license} no license[/]')
    if errors:
        parts.append(f'[red]{errors} errors[/]')
    console.print(' • '.join(parts), highlight=False)


def _check_license_compatibility(
    packages: list[Package],
    result: PreflightResult,
    *,
    project_license: str = '',
    user_toml: Path | None = None,
    exemptions: LicenseExemptions | None = None,
    color: bool | None = None,
    workspace_root: Path | None = None,
    ecosystem: str = 'python',
) -> None:
    """Check that dependency licenses are compatible with the project license.

    For each publishable package:
        1. Detect the package's own license (or use override).
        2. Detect each dependency's license (including transitive deps
           resolved from ``uv.lock`` when *workspace_root* is provided).
        3. Parse as SPDX expression and evaluate compatibility.
        4. Skip exempt packages and globally allowed licenses.

    Builds a :class:`LicenseTree` that can be retrieved from
    ``result.context['license_tree']`` for display purposes.

    If *project_license* is not provided, the license of the first
    publishable package is used as the project license.

    Args:
        packages: All workspace packages.
        result: Accumulator for check outcomes.
        project_license: Override for the project's SPDX license ID.
        user_toml: Optional user-provided TOML with additional
            license data / compatibility rules.
        exemptions: Optional exemption configuration for commercial
            licenses, allow-lists, and per-package overrides.
        color: Whether to use colored output. ``None`` means auto-detect.
        workspace_root: Path to the workspace root. When provided,
            ``uv.lock`` is parsed to resolve transitive dependencies
            (dependencies of dependencies) for license checking.
        ecosystem: Ecosystem identifier (e.g. ``'python'``, ``'js'``)
            used to generate registry URLs for dependency nodes.
    """
    check_name = 'license_compatibility'
    ex = exemptions or LicenseExemptions()

    # Load graph and resolver once.
    try:
        graph = LicenseGraph.load(user_toml=user_toml)
    except Exception as exc:  # noqa: BLE001
        result.add_warning(
            check_name,
            f'Failed to load license graph: {exc}',
            hint='Check your license TOML configuration files.',
        )
        return

    resolver = LicenseResolver(graph)

    # Determine the project license.
    if not project_license:
        for pkg in packages:
            if not pkg.is_publishable:
                continue
            detected = detect_license(pkg)
            if detected.found:
                resolved = resolver.resolve(detected.value)
                if resolved.resolved:
                    project_license = resolved.spdx_id
                    break

    if not project_license:
        result.add_warning(
            check_name,
            'Could not determine project license.',
            hint=('Set project.license in your root manifest or pass --project-license to override.'),
        )
        return

    # Resolve the project license itself.
    proj_resolved = resolver.resolve(project_license)
    if not proj_resolved.resolved:
        result.add_warning(
            check_name,
            f'Unknown project license: {project_license!r}',
            hint='Use a valid SPDX identifier for the project license.',
        )
        return

    proj_spdx = proj_resolved.spdx_id

    # Build a map of package name → raw license string for all packages.
    # Overrides take priority over auto-detection.
    # Also track how each license was detected (for diagnostics).
    pkg_raw_licenses: dict[str, str] = {}
    pkg_license_sources: dict[str, str] = {}
    unresolved: list[str] = []
    for pkg in packages:
        if pkg.name in ex.license_overrides:
            pkg_raw_licenses[pkg.name] = ex.license_overrides[pkg.name]
            pkg_license_sources[pkg.name] = 'releasekit.toml override'
            continue
        detected = detect_license(pkg)
        if detected.found:
            pkg_raw_licenses[pkg.name] = detected.value
            pkg_license_sources[pkg.name] = detected.source or 'local detection'

    # ── Transitive dependency resolution via lockfile ──────────
    # Parse uv.lock to discover deps-of-deps.
    lock_graph = None
    transitive_external: set[str] = set()
    if workspace_root is not None:
        lock_path = workspace_root / 'uv.lock'
        lock_graph = parse_uv_lock(lock_path)
        if lock_graph.entries:
            publishable_names = {pkg.name for pkg in packages if pkg.is_publishable}
            transitive_external = all_transitive_external_deps(
                lock_graph,
                publishable_names,
            )

    # ── Apply overrides to external deps ─────────────────────────
    # Overrides take priority over registry lookup — useful when
    # upstream metadata is wrong (e.g. bare "Apache" instead of
    # "Apache-2.0").
    for dep_name, spdx_override in ex.license_overrides.items():
        if dep_name not in pkg_raw_licenses:
            pkg_raw_licenses[dep_name] = spdx_override
            pkg_license_sources[dep_name] = 'releasekit.toml override'

    # ── Registry lookup fallback for external deps ───────────────
    # Collect external dep names that have no local license.
    # Include both direct external deps AND transitive deps from lockfile.
    missing_external: set[str] = set()
    for pkg in packages:
        if not pkg.is_publishable:
            continue
        for dep_name in pkg.external_deps:
            if dep_name not in pkg_raw_licenses and dep_name not in ex.exempt_packages:
                missing_external.add(dep_name)

    # Add transitive deps that aren't already known.
    for dep_name in transitive_external:
        if dep_name not in pkg_raw_licenses and dep_name not in ex.exempt_packages:
            missing_external.add(dep_name)

    if missing_external:
        # Log how many were already resolved locally before hitting the network.
        local_count = len(pkg_raw_licenses)
        override_count = sum(1 for s in pkg_license_sources.values() if s == 'releasekit.toml override')
        detect_count = local_count - override_count
        logger.info(
            'license_resolution',
            local=local_count,
            overrides=override_count,
            detected=detect_count,
            fetching=len(missing_external),
        )
        _resolve_external_licenses(missing_external, pkg_raw_licenses, pkg_license_sources)

    # ── Build per-package dep sets (direct + transitive) ──────────
    # For each publishable package, compute the full set of deps to check.
    # This includes direct deps plus transitive deps from the lockfile.
    internal_names = {pkg.name for pkg in packages}

    def _all_deps_for(pkg: Package) -> list[str]:
        """Return direct deps + transitive external deps for *pkg*."""
        direct = pkg.internal_deps + pkg.external_deps
        if lock_graph is None or not lock_graph.entries:
            return direct
        # Get transitive external deps from lockfile.
        transitive = _transitive_deps(lock_graph, pkg.name)
        # Merge: direct deps first, then transitive deps not already listed.
        direct_set = set(direct)
        extra = sorted(transitive - direct_set - internal_names)
        return direct + extra

    # ── Build the license tree ────────────────────────────────────
    ltree = LicenseTree(project_license=proj_spdx)

    # ── Phase 1: Deny-list check ──────────────────────────────────
    # Runs before compatibility. Even if the graph says "compatible",
    # a denied license is a hard failure unless exempted.
    denied: list[str] = []
    denied_contexts: list[str | SourceContext] = []

    if ex.deny_licenses:
        for pkg in packages:
            if not pkg.is_publishable:
                continue
            for dep_name in _all_deps_for(pkg):
                if dep_name in ex.exempt_packages:
                    continue
                raw = pkg_raw_licenses.get(dep_name)
                if raw is None:
                    continue

                all_ids = _resolve_all_ids(raw, resolver)

                # Exceptions: workspace-wide, then per-project.
                pkg_exceptions = ex.project_exceptions.get(
                    dep_name,
                    frozenset(),
                )
                effective_deny = ex.deny_licenses - ex.workspace_exceptions - pkg_exceptions
                blocked_ids = all_ids & effective_deny

                if blocked_ids:
                    blocked_str = ', '.join(sorted(blocked_ids))
                    denied.append(f'{pkg.name} → {dep_name} (blocked: {blocked_str})')
                    denied_contexts.append(
                        _make_source_context(
                            pkg.manifest_path,
                            dep_name,
                            f'denied: {blocked_str}',
                        )
                    )

    if denied:
        result.add_failure(
            check_name,
            f'Denied license(s): {"; ".join(denied)}',
            hint=(
                'These licenses are blocked by corporate policy '
                '(deny_licenses in [license] config). '
                'Remove the dependency, add a project_exception or '
                'workspace_exception, or request a policy change.'
            ),
            context=denied_contexts,
        )
        return

    # ── Phase 2: Compatibility check ─────────────────────────────
    violations: list[str] = []
    violation_contexts: list[str | SourceContext] = []

    for pkg in packages:
        if not pkg.is_publishable:
            continue

        # Resolve this package's own license for the tree.
        pkg_own_raw = pkg_raw_licenses.get(pkg.name, '')
        pkg_own_resolved = resolver.resolve(pkg_own_raw) if pkg_own_raw else None
        pkg_own_spdx = pkg_own_resolved.spdx_id if (pkg_own_resolved and pkg_own_resolved.resolved) else proj_spdx

        ptree = PackageTree(
            name=pkg.name,
            license=pkg_own_spdx,
            manifest_path=str(pkg.manifest_path),
        )

        for dep_name in _all_deps_for(pkg):
            # Skip exempt packages.
            if dep_name in ex.exempt_packages:
                ptree.deps.append(
                    DepNode(
                        name=dep_name,
                        license='(exempt)',
                        status=DepStatus.EXEMPT,
                    )
                )
                continue

            raw = pkg_raw_licenses.get(dep_name)
            dep_url = registry_url_for(dep_name, ecosystem)
            dep_source = pkg_license_sources.get(dep_name, '')
            if raw is None:
                ptree.deps.append(
                    DepNode(
                        name=dep_name,
                        status=DepStatus.NO_LICENSE,
                        registry_url=dep_url,
                    )
                )
                continue

            # Check the global allow-list first (single resolved ID).
            resolved = resolver.resolve(raw)
            dep_label = resolved.spdx_id if resolved.resolved else raw

            if resolved.resolved and resolved.spdx_id in ex.allow_licenses:
                ptree.deps.append(
                    DepNode(
                        name=dep_name,
                        license=dep_label,
                        status=DepStatus.ALLOWED,
                        source=dep_source,
                    )
                )
                continue

            # Full SPDX expression evaluation (handles OR, AND, WITH, +).
            if _is_expression_compatible(raw, proj_spdx, graph, resolver, ex.allow_licenses):
                ptree.deps.append(
                    DepNode(
                        name=dep_name,
                        license=dep_label,
                        status=DepStatus.OK,
                        source=dep_source,
                    )
                )
            else:
                ptree.deps.append(
                    DepNode(
                        name=dep_name,
                        license=dep_label,
                        status=DepStatus.INCOMPATIBLE,
                        detail=f'cannot be used in {proj_spdx} project',
                        registry_url=dep_url,
                        source=dep_source,
                    )
                )
                violations.append(f'{pkg.name} ({proj_spdx}) → {dep_name} ({dep_label})')
                violation_contexts.append(
                    _make_source_context(
                        pkg.manifest_path,
                        dep_name,
                        f'incompatible: {dep_label}',
                    )
                )
                if not resolved.resolved:
                    unresolved.append(f'{dep_name} ({raw!r})')

        ltree.packages.append(ptree)

    # Store the tree in result context for display.
    use_color = should_use_color(force=color)
    tree_text = format_license_tree(ltree, color=use_color)
    result.context.setdefault('license_tree', [tree_text])
    # Store the raw tree object for re-rendering in other formats.
    result.context.setdefault('license_tree_obj', cast(Sequence[str | SourceContext], [ltree]))

    if violations:
        result.add_failure(
            check_name,
            f'License incompatibility: {"; ".join(violations)}',
            hint=(
                f'Project license is {proj_spdx}. The listed dependencies '
                f'have incompatible licenses. Either change the dependency, '
                f'add it to exempt_packages in [license] config, '
                f'or adjust the project license.'
            ),
            context=violation_contexts,
        )
    elif unresolved:
        result.add_warning(
            check_name,
            f'Could not resolve licenses for: {", ".join(unresolved)}',
            hint='Add SPDX license identifiers to these packages.',
        )
    else:
        result.add_pass(check_name)
