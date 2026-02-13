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

"""Preflight safety checks before publishing.

Validates that the workspace is in a correct state before starting a
release. All backends are injected via dependency injection, making
this module testable with fake backends.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                               │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Preflight checks    │ Like a pilot's checklist before takeoff.      │
    │                     │ If anything fails, we don't take off.         │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Fail-fast           │ Stop at the first blocker. Don't waste time   │
    │                     │ checking everything if one thing is broken.   │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ DI (Dependency      │ Each backend (git, uv, gh, PyPI) is passed   │
    │  Injection)         │ as an argument. Tests can swap in fakes.     │
    └─────────────────────┴────────────────────────────────────────────────┘

Check order::

    1. Lock acquisition         → prevents concurrent releases
    2. Clean working tree       → no uncommitted changes
    3. Lock file check          → uv.lock is up to date
    4. Shallow clone detection  → warn if git history is truncated
    5. Cycle detection          → ensures publishable order
    6. Forge availability       → warn if `gh` CLI is not available
    7. Version conflict check   → none of the computed versions already
                                  exist on the registry

Usage::

    from releasekit.preflight import run_preflight

    # All backends injected:
    await run_preflight(
        vcs=git_backend,
        pm=uv_backend,
        forge=github_backend,
        registry=pypi_backend,
        packages=all_packages,
        graph=dep_graph,
        versions=version_list,
        workspace_root=Path('.'),
    )
"""

from __future__ import annotations

import asyncio
import os
import shutil
import warnings
from pathlib import Path

import tomlkit

from releasekit.backends._run import CommandResult, run_command
from releasekit.backends.forge import Forge
from releasekit.backends.pm import PackageManager
from releasekit.backends.registry import Registry
from releasekit.backends.vcs import VCS
from releasekit.errors import E, ReleaseKitError, ReleaseKitWarning
from releasekit.graph import DependencyGraph, detect_cycles
from releasekit.logging import get_logger
from releasekit.versions import PackageVersion
from releasekit.workspace import Package

logger = get_logger(__name__)


class PreflightResult:
    """Collects preflight check results.

    Attributes:
        passed: List of check names that passed.
        warnings: List of check names that produced warnings.
        failed: List of check names that failed.
        errors: Dict mapping failed check name to error message.
        warning_messages: Dict mapping warning check name to message.
    """

    def __init__(self) -> None:
        """Initialize with empty result lists."""
        self.passed: list[str] = []
        self.warnings: list[str] = []
        self.failed: list[str] = []
        self.errors: dict[str, str] = {}
        self.warning_messages: dict[str, str] = {}
        self.hints: dict[str, str] = {}

    def add_pass(self, name: str) -> None:
        """Record a passing check."""
        self.passed.append(name)
        logger.info('preflight_pass', check=name)

    def add_warning(self, name: str, message: str, *, hint: str = '') -> None:
        """Record a warning (non-blocking)."""
        self.warnings.append(name)
        self.warning_messages[name] = message
        if hint:
            self.hints[name] = hint
        logger.warning('preflight_warning', check=name, message=message)

    def add_failure(self, name: str, message: str, *, hint: str = '') -> None:
        """Record a failure (blocking)."""
        self.failed.append(name)
        self.errors[name] = message
        if hint:
            self.hints[name] = hint
        logger.error('preflight_fail', check=name, message=message)

    @property
    def ok(self) -> bool:
        """Return True if no checks failed."""
        return len(self.failed) == 0

    def summary(self) -> str:
        """Return a human-readable summary."""
        total = len(self.passed) + len(self.warnings) + len(self.failed)
        parts = [f'{total} checks:']
        if self.passed:
            parts.append(f'{len(self.passed)} passed')
        if self.warnings:
            parts.append(f'{len(self.warnings)} warnings')
        if self.failed:
            parts.append(f'{len(self.failed)} failed')
        return ', '.join(parts)


async def _check_clean_worktree(
    vcs: VCS,
    result: PreflightResult,
    *,
    dry_run: bool = False,
) -> None:
    """Check that the working tree has no uncommitted changes."""
    check_name = 'clean_worktree'
    if await vcs.is_clean(dry_run=dry_run):
        result.add_pass(check_name)
    else:
        result.add_failure(
            check_name,
            'Working tree has uncommitted changes.',
        )


async def _check_lock_file(
    pm: PackageManager,
    result: PreflightResult,
    *,
    workspace_root: Path,
    dry_run: bool = False,
) -> None:
    """Check that uv.lock is up to date."""
    check_name = 'lock_file'
    try:
        await pm.lock(check_only=True, cwd=workspace_root, dry_run=dry_run)
        result.add_pass(check_name)
    except Exception:
        result.add_failure(
            check_name,
            "Lock file is out of date. Run 'uv lock' to update.",
        )


async def _check_shallow_clone(
    vcs: VCS,
    result: PreflightResult,
) -> None:
    """Warn if the repository is a shallow clone."""
    check_name = 'shallow_clone'
    if await vcs.is_shallow():
        result.add_warning(
            check_name,
            'Repository is a shallow clone; git log may be incomplete.',
        )
        warnings.warn(
            ReleaseKitWarning(
                E.PREFLIGHT_SHALLOW_CLONE,
                'Repository is a shallow clone; git log data may be incomplete.',
                hint="Run 'git fetch --unshallow' to fetch full history.",
            ),
            stacklevel=2,
        )
    else:
        result.add_pass(check_name)


async def _check_cycles(
    graph: DependencyGraph,
    result: PreflightResult,
) -> None:
    """Check for circular dependencies in the graph."""
    check_name = 'cycle_detection'
    cycles = detect_cycles(graph)
    if cycles:
        cycle_strs = [' → '.join(c) for c in cycles]
        result.add_failure(
            check_name,
            f'Circular dependencies detected: {"; ".join(cycle_strs)}',
        )
    else:
        result.add_pass(check_name)


async def _check_forge(
    forge: Forge | None,
    result: PreflightResult,
) -> None:
    """Warn if the forge CLI is not available."""
    check_name = 'forge_available'
    if forge is None:
        result.add_warning(check_name, 'No forge backend configured.')
        return

    if await forge.is_available():
        result.add_pass(check_name)
    else:
        result.add_warning(
            check_name,
            'Forge CLI not installed or not authenticated. Platform releases will be skipped.',
        )


async def _check_version_conflicts(
    registry: Registry,
    versions: list[PackageVersion],
    result: PreflightResult,
) -> None:
    """Check that none of the target versions already exist on the registry."""
    check_name = 'version_conflicts'
    conflicts: list[str] = []

    for v in versions:
        if v.skipped:
            continue
        if await registry.check_published(v.name, v.new_version):
            conflicts.append(f'{v.name}=={v.new_version}')

    if conflicts:
        result.add_failure(
            check_name,
            f'Versions already on registry: {", ".join(conflicts)}',
        )
    else:
        result.add_pass(check_name)


def _check_dist_artifacts(
    packages: list[Package],
    result: PreflightResult,
) -> None:
    """Check for stale dist/ directories that could interfere with publishing.

    If a package has a non-empty ``dist/`` directory from a previous build,
    ``uv publish`` might upload old artifacts by mistake. This is a
    blocking check because the consequences are severe (publishing
    wrong versions).

    Args:
        packages: All workspace packages.
        result: Accumulator for check outcomes.
    """
    check_name = 'dist_clean'
    stale: list[str] = []
    for pkg in packages:
        dist_dir = pkg.path / 'dist'
        if dist_dir.is_dir() and any(dist_dir.iterdir()):
            stale.append(pkg.name)

    if stale:
        result.add_failure(
            check_name,
            f'Stale dist/ directories: {", ".join(stale)}',
        )
        logger.warning(
            'stale_dist_detected',
            packages=stale,
            hint='Run `rm -rf */dist` or use `releasekit clean` before publishing.',
        )
    else:
        result.add_pass(check_name)


def _check_trusted_publisher(
    forge: Forge | None,
    result: PreflightResult,
) -> None:
    """Warn if OIDC trusted publishing is not configured.

    Trusted publishing (PyPI's OIDC integration) is the recommended
    authentication method for CI. This check warns when publishing
    locally without it — not blocking, since local publishing with
    API tokens is still valid.

    See: https://docs.pypi.org/trusted-publishers/

    Args:
        forge: Code forge backend (None if unavailable).
        result: Accumulator for check outcomes.
    """
    check_name = 'trusted_publisher'

    # OIDC token presence is the signal that trusted publishing is active.
    # Different CI platforms set different env vars for OIDC:
    #   GitHub Actions: ACTIONS_ID_TOKEN_REQUEST_URL
    #   GitLab CI:      CI_JOB_JWT / CI_JOB_JWT_V2
    #   CircleCI:       CIRCLE_OIDC_TOKEN_V2
    has_oidc = bool(
        os.environ.get('ACTIONS_ID_TOKEN_REQUEST_URL')
        or os.environ.get('CI_JOB_JWT_V2')
        or os.environ.get('CI_JOB_JWT')
        or os.environ.get('CIRCLE_OIDC_TOKEN_V2')
    )
    is_ci = bool(os.environ.get('CI'))

    if is_ci and not has_oidc:
        result.add_warning(
            check_name,
            'Publishing from CI without OIDC trusted publisher. '
            'Consider configuring trusted publishing for better security.',
        )
    else:
        result.add_pass(check_name)


async def _check_pip_audit(
    result: PreflightResult,
    *,
    workspace_root: Path,
) -> None:
    """Run ``pip-audit`` to check for known vulnerabilities.

    This is a Python-specific advisory check. It only runs if ``pip-audit``
    is installed. Failures produce a warning (not blocking) because
    vulnerability databases may flag false positives or transitive deps
    the user can't easily fix.

    This check does NOT apply to JavaScript, Go, Rust, or other ecosystems.
    Each ecosystem should provide its own equivalent (e.g. ``npm audit``,
    ``cargo audit``, ``govulncheck``).

    Args:
        result: Accumulator for check outcomes.
        workspace_root: Path to the workspace root.
    """
    check_name = 'pip_audit'

    if not shutil.which('pip-audit'):
        result.add_warning(
            check_name,
            "'pip-audit' not installed. Skipping vulnerability scan. Install with: pip install pip-audit",
        )
        return

    try:
        cmd_result: CommandResult = await asyncio.to_thread(
            run_command,
            ['pip-audit', '--strict', '--progress-spinner=off'],
            cwd=workspace_root,
        )
        if cmd_result.returncode == 0:
            result.add_pass(check_name)
        else:
            result.add_warning(
                check_name,
                f'pip-audit found vulnerabilities: {cmd_result.stderr or cmd_result.stdout}',
            )
    except Exception as exc:
        result.add_warning(
            check_name,
            f'pip-audit failed to run: {exc}',
        )


def _check_metadata_validation(
    packages: list[Package],
    result: PreflightResult,
) -> None:
    """Validate that publishable packages have required pyproject.toml metadata.

    Checks for critical fields that PyPI requires for a successful upload:
    ``description``, ``license``, ``requires-python``, and ``authors``.
    Missing fields produce warnings (not blocking) so the user can fix them
    before the actual publish step fails.

    This is a Python-specific check. Other ecosystems (npm, cargo, Go)
    have different required metadata fields and should implement their own
    validation.

    Args:
        packages: All workspace packages.
        result: Accumulator for check outcomes.
    """
    check_name = 'metadata_validation'
    issues: list[str] = []
    required_fields = ('description', 'license', 'requires-python')

    for pkg in packages:
        if not pkg.is_publishable:
            continue
        pyproject = pkg.manifest_path
        if not pyproject.is_file():
            continue

        try:
            content = pyproject.read_text(encoding='utf-8')
            data = tomlkit.loads(content)
            project = data.get('project', {})

            missing = [f for f in required_fields if not project.get(f)]
            if not project.get('authors'):
                missing.append('authors')

            if missing:
                issues.append(f'{pkg.name}: missing {", ".join(missing)}')
        except Exception as exc:
            issues.append(f'{pkg.name}: failed to parse pyproject.toml: {exc}')

    if issues:
        result.add_warning(
            check_name,
            f'Metadata issues: {"; ".join(issues)}',
        )
    else:
        result.add_pass(check_name)


async def run_preflight(
    *,
    vcs: VCS,
    pm: PackageManager,
    forge: Forge | None,
    registry: Registry,
    packages: list[Package],
    graph: DependencyGraph,
    versions: list[PackageVersion],
    workspace_root: Path,
    dry_run: bool = False,
    skip_version_check: bool = False,
    ecosystem: str = 'python',
    run_audit: bool = False,
) -> PreflightResult:
    """Run all preflight checks.

    All backends are injected via parameters (dependency injection),
    making this function testable with fake backends.

    Checks are split into **universal** (always run) and
    **ecosystem-specific** (gated by ``ecosystem`` parameter):

    Universal checks:
        clean_worktree, lock_file, shallow_clone, cycle_detection,
        forge_available, dist_clean, trusted_publisher, version_conflicts.

    Python-specific checks (``ecosystem='python'``):
        metadata_validation — validates pyproject.toml required fields.
        pip_audit — runs ``pip-audit`` for known vulnerabilities (advisory).
            Only runs when ``run_audit=True`` since it requires network
            access and ``pip-audit`` to be installed.

    Args:
        vcs: Version control backend.
        pm: Package manager backend.
        forge: Code forge backend (optional; ``None`` to skip).
        registry: Package registry backend.
        packages: All workspace packages (for dist artifact checks).
        graph: Workspace dependency graph.
        versions: Computed version bumps.
        workspace_root: Path to the workspace root.
        dry_run: Pass through to backends.
        skip_version_check: Skip registry version conflict check
            (useful for ``--force`` mode).
        ecosystem: The workspace ecosystem type. Currently only
            ``'python'`` triggers ecosystem-specific checks.
            Future values: ``'node'``, ``'rust'``, ``'go'``.
        run_audit: Whether to run vulnerability scanning (e.g.
            ``pip-audit``). Defaults to ``False`` because it
            requires network access and an external tool.

    Returns:
        A :class:`PreflightResult` with all check outcomes.

    Raises:
        ReleaseKitError: On the first blocking failure (dirty worktree).
    """
    result = PreflightResult()

    await _check_clean_worktree(vcs, result, dry_run=dry_run)
    if not result.ok:
        raise ReleaseKitError(
            E.PREFLIGHT_DIRTY_WORKTREE,
            result.errors.get('clean_worktree', 'Working tree is dirty.'),
            hint='Commit or stash your changes before publishing.',
        )

    await _check_lock_file(pm, result, workspace_root=workspace_root, dry_run=dry_run)
    await _check_shallow_clone(vcs, result)
    await _check_cycles(graph, result)
    await _check_forge(forge, result)
    _check_dist_artifacts(packages, result)
    _check_trusted_publisher(forge, result)

    if not skip_version_check:
        await _check_version_conflicts(registry, versions, result)

    if ecosystem == 'python':
        _check_metadata_validation(packages, result)
        if run_audit:
            await _check_pip_audit(result, workspace_root=workspace_root)

    logger.info('preflight_complete', summary=result.summary())
    return result


__all__ = [
    'PreflightResult',
    'run_preflight',
]
