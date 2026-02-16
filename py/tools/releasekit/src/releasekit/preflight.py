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
import shutil
import threading
import warnings
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import tomlkit

from releasekit.backends._run import CommandResult, run_command
from releasekit.backends.forge import Forge
from releasekit.backends.pm import PackageManager
from releasekit.backends.registry import Registry
from releasekit.backends.validation.oidc import validate_oidc_environment
from releasekit.backends.vcs import VCS
from releasekit.compliance import ComplianceStatus, evaluate_compliance
from releasekit.errors import E, ReleaseKitError, ReleaseKitWarning
from releasekit.graph import DependencyGraph, detect_cycles
from releasekit.logging import get_logger
from releasekit.osv import OSVSeverity, check_osv_vulnerabilities
from releasekit.provenance import BuildContext, SLSABuildLevel, is_ci
from releasekit.sbom import _make_purl
from releasekit.scorecard import run_scorecard_checks
from releasekit.versions import PackageVersion
from releasekit.workspace import Package

logger = get_logger(__name__)


@dataclass(frozen=True)
class SourceContext:
    """Source location with optional line number and snippet.

    Used by health checks to point the user at the exact file and line
    that caused a warning or failure.  The CLI renderer reads these to
    produce Rust-style diagnostic output with source excerpts.

    Attributes:
        path: Absolute or relative path to the file.
        line: 1-based line number of the offending line (0 = unknown).
        key: The TOML key or search term that was matched.
        label: Short annotation shown next to the line (e.g. ``'missing here'``).
    """

    path: str
    line: int = 0
    key: str = ''
    label: str = ''

    def __str__(self) -> str:
        """Format as ``path:line`` when line is known, else just ``path``."""
        if self.line:
            return f'{self.path}:{self.line}'
        return self.path


def find_key_line(content: str, key: str, *, section: str = '') -> int:
    """Find the 1-based line number of a TOML key in file content.

    Searches for ``key = `` or ``[section]`` patterns.  Returns 0 if
    not found.  This is a simple string-search fallback because
    ``tomlkit`` does not expose line numbers.

    Args:
        content: The full file content.
        key: The TOML key to search for (e.g. ``'name'``,
            ``'build-system'``).
        section: If provided, search for ``[section]`` header instead
            of a key assignment.

    Returns:
        1-based line number, or 0 if not found.
    """
    if section:
        target = f'[{section}]'
        for i, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            if stripped == target or stripped.startswith(target + ' '):
                return i
        return 0

    target = f'{key} ='
    target_no_space = f'{key}='
    for i, line in enumerate(content.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith(target) or stripped.startswith(target_no_space):
            return i
    return 0


def read_source_snippet(
    path: str | Path,
    line: int,
    *,
    context_lines: int = 2,
) -> list[tuple[int, str]]:
    """Read a few lines around ``line`` from a file.

    Returns a list of ``(line_number, line_text)`` tuples.  Returns an
    empty list if the file cannot be read or ``line`` is 0.

    Args:
        path: Path to the source file.
        line: 1-based centre line.
        context_lines: Number of lines to show above and below.

    Returns:
        List of ``(lineno, text)`` pairs.
    """
    if line <= 0:
        return []
    try:
        all_lines = Path(path).read_text(encoding='utf-8').splitlines()
    except Exception:
        return []
    start = max(0, line - 1 - context_lines)
    end = min(len(all_lines), line + context_lines)
    return [(i + 1, all_lines[i]) for i in range(start, end)]


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
        self._lock = threading.Lock()
        self.passed: list[str] = []
        self.warnings: list[str] = []
        self.failed: list[str] = []
        self.errors: dict[str, str] = {}
        self.warning_messages: dict[str, str] = {}
        self.hints: dict[str, str] = {}
        self.context: dict[str, Sequence[str | SourceContext]] = {}

    def add_pass(self, name: str) -> None:
        """Record a passing check."""
        with self._lock:
            self.passed.append(name)
        logger.info('preflight_pass', check=name)

    def add_warning(
        self,
        name: str,
        message: str,
        *,
        hint: str = '',
        context: Sequence[str | SourceContext] | None = None,
    ) -> None:
        """Record a warning (non-blocking).

        Args:
            name: Check identifier.
            message: Human-readable description of the issue.
            hint: Actionable suggestion for fixing the issue.
            context: File location annotations — plain path strings or
                :class:`SourceContext` instances with line numbers.
        """
        with self._lock:
            self.warnings.append(name)
            self.warning_messages[name] = message
            if hint:
                self.hints[name] = hint
            if context:
                self.context[name] = context
        logger.warning('preflight_warning', check=name, message=message)

    def add_failure(
        self,
        name: str,
        message: str,
        *,
        hint: str = '',
        context: Sequence[str | SourceContext] | None = None,
    ) -> None:
        """Record a failure (blocking).

        Args:
            name: Check identifier.
            message: Human-readable description of the issue.
            hint: Actionable suggestion for fixing the issue.
            context: File location annotations — plain path strings or
                :class:`SourceContext` instances with line numbers.
        """
        with self._lock:
            self.failed.append(name)
            self.errors[name] = message
            if hint:
                self.hints[name] = hint
            if context:
                self.context[name] = context
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


def run_check(
    result: PreflightResult,
    check_name: str,
    packages: Sequence[Package],
    probe: Callable[[Package], Sequence[tuple[str, str | SourceContext]]],
    *,
    message: str,
    hint: str,
    severity: Literal['warning', 'failure'] = 'failure',
    joiner: str = ', ',
) -> None:
    """Run a per-package probe and record the outcome.

    This eliminates the boilerplate that every check method repeats:
    initialise two lists, loop over packages, collect issues and
    locations, then call ``add_warning`` / ``add_failure`` or
    ``add_pass``.

    Args:
        result: Accumulator for check outcomes.
        check_name: Identifier for this check (e.g. ``'build_system'``).
        packages: Packages to inspect.
        probe: Called once per package.  Returns a (possibly empty)
            sequence of ``(issue_description, location)`` tuples.
            The location can be a plain path string or a
            :class:`SourceContext` with line-level detail.
            Return an empty sequence to signal "no issues for this
            package".
        message: Prefix placed before the joined issue descriptions,
            e.g. ``'Missing go.mod'``.  The final message is
            ``f'{message}: {joiner.join(issues)}'``.
        hint: Actionable fix suggestion.
        severity: ``'failure'`` (default, blocks release) or
            ``'warning'`` (informational).
        joiner: String used to join issue descriptions (default ``', '``).
    """
    issues: list[str] = []
    locations: list[str | SourceContext] = []
    for pkg in packages:
        for desc, loc in probe(pkg):
            issues.append(desc)
            locations.append(loc)

    if issues:
        text = f'{message}: {joiner.join(issues)}'
        if severity == 'failure':
            result.add_failure(check_name, text, hint=hint, context=locations)
        else:
            result.add_warning(check_name, text, hint=hint, context=locations)
    else:
        result.add_pass(check_name)


def run_version_consistency_check(
    result: PreflightResult,
    check_name: str,
    packages: Sequence[Package],
    *,
    core_package: str,
    manifest_path_fn: Callable[[Package], str],
    hint_template: str = 'All packages should use version {version}.',
    filter_fn: Callable[[Package], bool] | None = None,
) -> None:
    """Check that all packages share the same version as the core package.

    This is the second most common pattern across check backends.

    Args:
        result: Accumulator for check outcomes.
        check_name: Identifier for this check.
        packages: Packages to inspect.
        core_package: Name of the core/reference package.
        manifest_path_fn: Given a package, return the path string to
            use as context (e.g. ``lambda p: str(p.path / 'go.mod')``).
        hint_template: Format string with ``{version}`` placeholder.
        filter_fn: Optional predicate to restrict which packages are
            compared.  Receives each non-core package; return ``True``
            to include it in the comparison.
    """
    if not core_package:
        result.add_pass(check_name)
        return

    core_pkg = next((p for p in packages if p.name == core_package), None)
    if core_pkg is None:
        result.add_warning(
            check_name,
            f'Core package "{core_package}" not found.',
            hint=f'Ensure a package named "{core_package}" exists in the workspace.',
        )
        return

    core_version = core_pkg.version
    mismatches: list[str] = []
    locations: list[str] = []
    for pkg in packages:
        if pkg.name == core_package:
            continue
        if filter_fn is not None and not filter_fn(pkg):
            continue
        if pkg.version != core_version:
            mismatches.append(f'{pkg.name}=={pkg.version} (expected {core_version})')
            locations.append(manifest_path_fn(pkg))

    if mismatches:
        result.add_failure(
            check_name,
            f'Version mismatch: {", ".join(mismatches)}',
            hint=hint_template.format(version=core_version),
            context=locations,
        )
    else:
        result.add_pass(check_name)


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
    """Check OIDC trusted publishing configuration.

    In CI, missing OIDC credentials are a **failure** because provenance
    cannot be signed (SLSA Build L2 is impossible). Locally, it is a
    warning since API-token publishing is still valid.

    See: https://docs.pypi.org/trusted-publishers/

    Args:
        forge: Code forge backend (None if unavailable).
        result: Accumulator for check outcomes.
    """
    check_name = 'trusted_publisher'

    oidc_result = validate_oidc_environment()
    if oidc_result.ok:
        result.add_pass(check_name)
        return

    # In CI, missing OIDC is a failure — provenance cannot be signed.
    if is_ci():
        result.add_failure(
            check_name,
            f'CI environment missing OIDC credentials: {oidc_result.message}',
            hint=(
                'Configure OIDC trusted publishing for your CI platform. '
                'GitHub Actions: add "id-token: write" permission. '
                'GitLab CI: ensure CI_JOB_JWT_V2 is available. '
                'To override, set sign_provenance = false in releasekit.toml.'
            ),
        )
    else:
        result.add_warning(
            check_name,
            oidc_result.message,
            hint=oidc_result.hint,
        )


def _check_source_integrity(
    result: PreflightResult,
) -> None:
    """Check that source integrity metadata is available.

    SLSA provenance requires a source commit digest and ref to
    establish what source was built. Missing values degrade the
    provenance quality.

    Args:
        result: Accumulator for check outcomes.
    """
    check_name = 'source_integrity'

    ctx = BuildContext.from_env()

    issues: list[str] = []
    if not ctx.source_digest:
        issues.append('source commit SHA not detected (GitHub: GITHUB_SHA, GitLab: CI_COMMIT_SHA)')
    if not ctx.source_ref:
        issues.append('source ref not detected (GitHub: GITHUB_REF, GitLab: CI_COMMIT_REF_NAME)')
    if not ctx.source_repo:
        issues.append('source repository not detected (GitHub: GITHUB_REPOSITORY, GitLab: CI_PROJECT_URL)')

    if issues:
        if is_ci():
            result.add_failure(
                check_name,
                f'Source integrity metadata missing: {"; ".join(issues)}',
                hint=(
                    'Ensure your CI workflow exposes source metadata '
                    'environment variables. These are required for '
                    'SLSA provenance generation.'
                ),
            )
        else:
            result.add_warning(
                check_name,
                f'Source integrity metadata unavailable (local build): {"; ".join(issues)}',
                hint='This is expected for local builds. Provenance will have limited source information.',
            )
    else:
        result.add_pass(check_name)


def _check_build_as_code(
    result: PreflightResult,
) -> None:
    """Check that the build is defined in version control (build-as-code).

    SLSA Build L3 requires that the build configuration is defined in
    the source repository, not by user parameters. This check verifies
    that the build entry point (workflow file) is known.

    Args:
        result: Accumulator for check outcomes.
    """
    check_name = 'build_as_code'

    if not is_ci():
        result.add_pass(check_name)
        return

    ctx = BuildContext.from_env()
    if ctx.source_entry_point:
        result.add_pass(check_name)
    else:
        result.add_warning(
            check_name,
            'Build entry point (workflow file) not detected. SLSA Build L3 requires build-as-code.',
            hint=('GitHub Actions: ensure GITHUB_WORKFLOW_REF is set. GitLab CI: ensure CI_CONFIG_PATH is set.'),
        )


def _check_slsa_level(
    result: PreflightResult,
) -> None:
    """Report the achievable SLSA Build level for this environment.

    This is an informational check that always passes but emits
    warnings when the environment cannot achieve L2 or L3.

    Args:
        result: Accumulator for check outcomes.
    """
    check_name = 'slsa_build_level'

    if not is_ci():
        result.add_warning(
            check_name,
            'Local build: SLSA Build L1 only (provenance exists but is not signed).',
            hint='Run in CI with OIDC credentials for SLSA Build L2+.',
        )
        return

    ctx = BuildContext.from_env()
    level = ctx.slsa_build_level

    if level >= SLSABuildLevel.L3:
        result.add_pass(check_name)
    elif level >= SLSABuildLevel.L2:
        result.add_warning(
            check_name,
            f'SLSA Build L{int(level)}: signed provenance, but build isolation '
            f'not verified (L3 requires github-hosted runners or equivalent).',
            hint=(
                'Use github-hosted runners (not self-hosted) for SLSA Build L3. '
                f'Current runner environment: {ctx.runner_environment!r}.'
            ),
        )
    else:
        result.add_warning(
            check_name,
            f'SLSA Build L{int(level)}: provenance will not be signed.',
            hint='Configure OIDC credentials for SLSA Build L2+.',
        )


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
        if cmd_result.return_code == 0:
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


def _check_scorecard(
    result: PreflightResult,
    *,
    workspace_root: Path,
) -> None:
    """Run OpenSSF Scorecard-aligned security checks.

    These are local file-existence and configuration-pattern checks
    that verify the repository follows security best practices.
    Failures produce warnings (not blocking) since they are hygiene
    checks, not correctness checks.

    Args:
        result: Accumulator for check outcomes.
        workspace_root: Path to the workspace root.
    """
    scorecard_results = run_scorecard_checks(workspace_root)
    failed = [r for r in scorecard_results if not r.passed]

    if failed:
        messages = [f'{r.check}: {r.message}' for r in failed]
        hints = [r.hint for r in failed if r.hint]
        result.add_warning(
            'scorecard',
            f'{len(failed)} Scorecard check(s) failed: {"; ".join(messages)}',
            hint=hints[0] if hints else '',
        )
    else:
        result.add_pass('scorecard')


async def _check_osv(
    result: PreflightResult,
    *,
    packages: list[Package],
    ecosystem: str = 'python',
    severity_threshold: str = 'HIGH',
) -> None:
    """Check for known vulnerabilities via the OSV.dev API.

    Queries OSV with package purls for vulnerabilities at or above
    the configured severity threshold.
    Failures produce warnings in local builds and failures in CI.

    Args:
        result: Accumulator for check outcomes.
        packages: Workspace packages to check.
        ecosystem: Package ecosystem for purl generation.
        severity_threshold: Minimum severity to report (CRITICAL,
            HIGH, MEDIUM, LOW). Default: HIGH.
    """
    try:
        threshold = OSVSeverity[severity_threshold.upper()]
    except KeyError:
        threshold = OSVSeverity.HIGH

    purls = [_make_purl(pkg.name, pkg.version, ecosystem) for pkg in packages if pkg.version]
    if not purls:
        result.add_pass('osv_vulnerabilities')
        return

    vulns = await check_osv_vulnerabilities(
        purls,
        severity_threshold=threshold,
    )

    if vulns:
        vuln_strs = [f'{v.purl}: {v.id} ({v.severity.name})' for v in vulns[:5]]
        message = f'{len(vulns)} HIGH+ vulnerability(ies): {"; ".join(vuln_strs)}'
        if is_ci():
            result.add_failure(
                'osv_vulnerabilities',
                message,
                hint='Review vulnerabilities at https://osv.dev and update affected dependencies.',
            )
        else:
            result.add_warning(
                'osv_vulnerabilities',
                message,
                hint='Review vulnerabilities at https://osv.dev and update affected dependencies.',
            )
    else:
        result.add_pass('osv_vulnerabilities')


def _check_security_insights(
    result: PreflightResult,
    *,
    workspace_root: Path,
) -> None:
    """Check that SECURITY-INSIGHTS.yml exists at the repo root.

    The OpenSSF Security Insights specification recommends a single
    ``SECURITY-INSIGHTS.yml`` per repository.  This check warns when
    the file is missing so maintainers can generate it with
    ``releasekit init --security-insights``.

    Args:
        result: Accumulator for check outcomes.
        workspace_root: Path to the workspace root.
    """
    check_name = 'security_insights'
    candidates = [
        workspace_root / 'SECURITY-INSIGHTS.yml',
        workspace_root / 'SECURITY_INSIGHTS.yml',
        workspace_root / '.github' / 'SECURITY-INSIGHTS.yml',
    ]
    for path in candidates:
        if path.is_file():
            result.add_pass(check_name)
            return
    result.add_warning(
        check_name,
        'No SECURITY-INSIGHTS.yml found.',
        hint="Generate one with 'releasekit init --security-insights'.",
    )


def _check_compliance(
    result: PreflightResult,
    *,
    workspace_root: Path,
) -> None:
    """Run OSPS Baseline compliance evaluation and report gaps.

    Evaluates the repository against OpenSSF OSPS Baseline controls
    and reports any gaps as warnings.  This is informational — gaps
    do not block the release.

    Args:
        result: Accumulator for check outcomes.
        workspace_root: Path to the workspace root.
    """
    check_name = 'compliance'
    try:
        controls = evaluate_compliance(workspace_root)
        gaps = [c for c in controls if c.status == ComplianceStatus.GAP]
        if gaps:
            gap_strs = [f'{c.id} ({c.control})' for c in gaps[:5]]
            suffix = f' and {len(gaps) - 5} more' if len(gaps) > 5 else ''
            result.add_warning(
                check_name,
                f'{len(gaps)} OSPS Baseline gap(s): {"; ".join(gap_strs)}{suffix}',
                hint="Run 'releasekit compliance' for the full report.",
            )
        else:
            result.add_pass(check_name)
    except Exception as exc:
        result.add_warning(
            check_name,
            f'Compliance evaluation failed: {exc}',
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
    osv_severity_threshold: str = 'HIGH',
    skip_checks: list[str] | None = None,
) -> PreflightResult:
    """Run all preflight checks.

    All backends are injected via parameters (dependency injection),
    making this function testable with fake backends.

    Checks are split into **universal** (always run) and
    **ecosystem-specific** (gated by ``ecosystem`` parameter):

    Universal checks:
        clean_worktree, lock_file, shallow_clone, cycle_detection,
        forge_available, dist_clean, trusted_publisher,
        source_integrity, build_as_code, slsa_build_level,
        version_conflicts, security_insights, compliance.

    Security checks (safe-by-default):
        trusted_publisher — **fails in CI** when OIDC is missing
            (provenance cannot be signed). Warns locally.
        source_integrity — **fails in CI** when source commit SHA,
            ref, or repo URL is missing. Warns locally.
        build_as_code — warns in CI when the build entry point
            (workflow file) is not detected (L3 degradation).
        slsa_build_level — informational: reports the achievable
            SLSA Build level and warns when below L3.
        security_insights — warns when ``SECURITY-INSIGHTS.yml``
            is missing from the repository root.
        compliance — warns when OSPS Baseline gaps are detected.

    Python-specific checks (``ecosystem='python'``):
        metadata_validation — validates pyproject.toml required fields.
        pip_audit — runs ``pip-audit`` for known vulnerabilities.
            Auto-enabled in CI, or when ``run_audit=True``.
        osv_vulnerabilities — queries OSV.dev for known vulns.
            Auto-enabled in CI, or when ``run_audit=True``.

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
            Auto-enabled in CI environments.
        osv_severity_threshold: Minimum OSV severity level to report.
            One of ``CRITICAL``, ``HIGH``, ``MEDIUM``, ``LOW``.
        skip_checks: List of check names to skip. Skipped checks
            are recorded as passed without running. Use this to
            suppress checks that are not applicable to a workspace.

    Returns:
        A :class:`PreflightResult` with all check outcomes.

    Raises:
        ReleaseKitError: On the first blocking failure (dirty worktree).
    """
    result = PreflightResult()
    _skip = frozenset(skip_checks or ())

    def _skipped(name: str) -> bool:
        """Return True and record a pass if the check should be skipped."""
        if name in _skip:
            result.add_pass(name)
            logger.info('preflight_skipped', check=name)
            return True
        return False

    if not _skipped('clean_worktree'):
        await _check_clean_worktree(vcs, result, dry_run=dry_run)
        if not result.ok:
            raise ReleaseKitError(
                E.PREFLIGHT_DIRTY_WORKTREE,
                result.errors.get('clean_worktree', 'Working tree is dirty.'),
                hint='Commit or stash your changes before publishing.',
            )

    if not _skipped('lock_file'):
        await _check_lock_file(pm, result, workspace_root=workspace_root, dry_run=dry_run)
    if not _skipped('shallow_clone'):
        await _check_shallow_clone(vcs, result)
    if not _skipped('cycle_detection'):
        await _check_cycles(graph, result)
    if not _skipped('forge_available'):
        await _check_forge(forge, result)
    if not _skipped('dist_clean'):
        _check_dist_artifacts(packages, result)
    if not _skipped('trusted_publisher'):
        _check_trusted_publisher(forge, result)
    if not _skipped('source_integrity'):
        _check_source_integrity(result)
    if not _skipped('build_as_code'):
        _check_build_as_code(result)
    if not _skipped('slsa_build_level'):
        _check_slsa_level(result)

    if not skip_version_check and not _skipped('version_conflicts'):
        await _check_version_conflicts(registry, versions, result)

    if not _skipped('scorecard'):
        _check_scorecard(result, workspace_root=workspace_root)
    if not _skipped('security_insights'):
        _check_security_insights(result, workspace_root=workspace_root)
    if not _skipped('compliance'):
        _check_compliance(result, workspace_root=workspace_root)

    if ecosystem == 'python':
        if not _skipped('metadata_validation'):
            _check_metadata_validation(packages, result)

        # Auto-enable vulnerability scanning in CI, or when explicitly requested.
        should_audit = run_audit or is_ci()
        if should_audit:
            if not _skipped('pip_audit'):
                await _check_pip_audit(result, workspace_root=workspace_root)
            if not _skipped('osv_vulnerabilities'):
                await _check_osv(
                    result,
                    packages=packages,
                    ecosystem=ecosystem,
                    severity_threshold=osv_severity_threshold,
                )

    logger.info('preflight_complete', summary=result.summary())
    return result


__all__ = [
    'PreflightResult',
    'SourceContext',
    'find_key_line',
    'read_source_snippet',
    'run_preflight',
]
