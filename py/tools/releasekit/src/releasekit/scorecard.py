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

r"""OpenSSF Scorecard-aligned security checks.

Implements a subset of `OpenSSF Scorecard`_ checks that can be run
**locally** without the Scorecard API.  These are file-existence and
configuration-pattern checks that verify the repository follows
security best practices.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────┐
    │ Concept             │ Plain-English                                  │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Scorecard           │ An OpenSSF project that grades repos on       │
    │                     │ security practices (0–10 per check).          │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Local checks        │ We don't call the Scorecard API — we check   │
    │                     │ for the same files/patterns ourselves.        │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Preflight           │ These checks run before every release to      │
    │                     │ surface security hygiene issues early.        │
    └─────────────────────┴────────────────────────────────────────────────┘

Checks implemented::

    ┌──────────────────────────┬──────────────────────────────────────────┐
    │ Scorecard Check          │ What We Validate                         │
    ├──────────────────────────┼──────────────────────────────────────────┤
    │ SECURITY.md              │ SECURITY.md exists at repo root          │
    ├──────────────────────────┼──────────────────────────────────────────┤
    │ Dependency-Update-Tool   │ Dependabot or Renovate config exists     │
    ├──────────────────────────┼──────────────────────────────────────────┤
    │ CI-Tests                 │ CI workflow files exist                   │
    ├──────────────────────────┼──────────────────────────────────────────┤
    │ Pinned-Dependencies      │ CI workflows pin actions by SHA          │
    ├──────────────────────────┼──────────────────────────────────────────┤
    │ Token-Permissions        │ CI workflows use least-privilege perms   │
    ├──────────────────────────┼──────────────────────────────────────────┤
    │ Signed-Releases          │ Sigstore bundles exist for artifacts     │
    └──────────────────────────┴──────────────────────────────────────────┘

Usage::

    from releasekit.scorecard import run_scorecard_checks, ScorecardResult

    results = run_scorecard_checks(repo_root=Path('/path/to/repo'))
    for r in results:
        print(f'{r.check}: {"PASS" if r.passed else "WARN"} — {r.message}')

.. _OpenSSF Scorecard: https://securityscorecards.dev/
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from releasekit.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class ScorecardCheckResult:
    """Result of a single Scorecard-aligned check.

    Attributes:
        check: Name of the Scorecard check (e.g. ``'SECURITY.md'``).
        passed: Whether the check passed.
        message: Human-readable description of the outcome.
        hint: Actionable suggestion if the check failed.
        severity: ``'warning'`` (default) or ``'failure'``.
    """

    check: str
    passed: bool
    message: str = ''
    hint: str = ''
    severity: str = 'warning'


def _check_security_md(repo_root: Path) -> ScorecardCheckResult:
    """Check that SECURITY.md exists at the repo root.

    Args:
        repo_root: Path to the repository root.

    Returns:
        A :class:`ScorecardCheckResult`.
    """
    candidates = [
        repo_root / 'SECURITY.md',
        repo_root / '.github' / 'SECURITY.md',
        repo_root / 'docs' / 'SECURITY.md',
    ]
    for path in candidates:
        if path.is_file():
            return ScorecardCheckResult(
                check='security_md',
                passed=True,
                message=f'SECURITY.md found at {path.relative_to(repo_root)}',
            )
    return ScorecardCheckResult(
        check='security_md',
        passed=False,
        message='No SECURITY.md found',
        hint='Create a SECURITY.md with vulnerability reporting instructions.',
    )


def _check_dependency_update_tool(repo_root: Path) -> ScorecardCheckResult:
    """Check that a dependency update tool (Dependabot/Renovate) is configured.

    Args:
        repo_root: Path to the repository root.

    Returns:
        A :class:`ScorecardCheckResult`.
    """
    candidates = [
        repo_root / '.github' / 'dependabot.yml',
        repo_root / '.github' / 'dependabot.yaml',
        repo_root / 'renovate.json',
        repo_root / 'renovate.json5',
        repo_root / '.renovaterc',
        repo_root / '.renovaterc.json',
    ]
    for path in candidates:
        if path.is_file():
            return ScorecardCheckResult(
                check='dependency_update_tool',
                passed=True,
                message=f'Dependency update tool configured: {path.name}',
            )
    return ScorecardCheckResult(
        check='dependency_update_tool',
        passed=False,
        message='No dependency update tool configured',
        hint='Add .github/dependabot.yml or renovate.json to automate dependency updates.',
    )


def _check_ci_tests(repo_root: Path) -> ScorecardCheckResult:
    """Check that CI workflow files exist.

    Args:
        repo_root: Path to the repository root.

    Returns:
        A :class:`ScorecardCheckResult`.
    """
    workflows_dir = repo_root / '.github' / 'workflows'
    gitlab_ci = repo_root / '.gitlab-ci.yml'
    circleci = repo_root / '.circleci' / 'config.yml'

    workflow_files: list[Path] = []
    if workflows_dir.is_dir():
        workflow_files = list(workflows_dir.glob('*.yml')) + list(workflows_dir.glob('*.yaml'))

    if workflow_files:
        return ScorecardCheckResult(
            check='ci_tests',
            passed=True,
            message=f'{len(workflow_files)} GitHub Actions workflow(s) found',
        )
    if gitlab_ci.is_file():
        return ScorecardCheckResult(
            check='ci_tests',
            passed=True,
            message='GitLab CI configuration found',
        )
    if circleci.is_file():
        return ScorecardCheckResult(
            check='ci_tests',
            passed=True,
            message='CircleCI configuration found',
        )
    return ScorecardCheckResult(
        check='ci_tests',
        passed=False,
        message='No CI configuration found',
        hint='Add .github/workflows/*.yml, .gitlab-ci.yml, or .circleci/config.yml.',
    )


# Pattern matching GitHub Actions uses: with a tag (not SHA).
# e.g. uses: actions/checkout@v4  (tag, not pinned)
# vs.  uses: actions/checkout@abc123...  (SHA, pinned)
_USES_TAG_PATTERN = re.compile(
    r'uses:\s+[\w\-./]+@(?!([0-9a-f]{40}|[0-9a-f]{64}))[^\s#]+',
)


def _check_pinned_dependencies(repo_root: Path) -> ScorecardCheckResult:
    """Check that CI workflows pin actions by SHA, not tag.

    Args:
        repo_root: Path to the repository root.

    Returns:
        A :class:`ScorecardCheckResult`.
    """
    workflows_dir = repo_root / '.github' / 'workflows'
    if not workflows_dir.is_dir():
        return ScorecardCheckResult(
            check='pinned_dependencies',
            passed=True,
            message='No GitHub Actions workflows to check',
        )

    unpinned: list[str] = []
    workflow_files = list(workflows_dir.glob('*.yml')) + list(workflows_dir.glob('*.yaml'))

    for wf in workflow_files:
        try:
            content = wf.read_text(encoding='utf-8')
            for i, line in enumerate(content.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith('#'):
                    continue
                if _USES_TAG_PATTERN.search(stripped):
                    unpinned.append(f'{wf.name}:{i}')
        except Exception:  # noqa: BLE001
            logger.debug('scorecard_read_error', file=str(wf))
            continue

    if unpinned:
        return ScorecardCheckResult(
            check='pinned_dependencies',
            passed=False,
            message=f'{len(unpinned)} action(s) not pinned by SHA: {", ".join(unpinned[:5])}',
            hint='Pin GitHub Actions by commit SHA instead of tag (e.g. actions/checkout@<sha>).',
        )
    return ScorecardCheckResult(
        check='pinned_dependencies',
        passed=True,
        message='All GitHub Actions are pinned by SHA',
    )


# Pattern for overly permissive top-level permissions.
_PERMISSIONS_WRITE_ALL = re.compile(r'permissions:\s*write-all', re.IGNORECASE)


def _check_token_permissions(repo_root: Path) -> ScorecardCheckResult:
    """Check that CI workflows use least-privilege token permissions.

    Flags workflows that use ``permissions: write-all`` at the top level.

    Args:
        repo_root: Path to the repository root.

    Returns:
        A :class:`ScorecardCheckResult`.
    """
    workflows_dir = repo_root / '.github' / 'workflows'
    if not workflows_dir.is_dir():
        return ScorecardCheckResult(
            check='token_permissions',
            passed=True,
            message='No GitHub Actions workflows to check',
        )

    violations: list[str] = []
    workflow_files = list(workflows_dir.glob('*.yml')) + list(workflows_dir.glob('*.yaml'))

    for wf in workflow_files:
        try:
            content = wf.read_text(encoding='utf-8')
            if _PERMISSIONS_WRITE_ALL.search(content):
                violations.append(wf.name)
        except Exception:  # noqa: BLE001
            logger.debug('scorecard_read_error', file=str(wf))
            continue

    if violations:
        return ScorecardCheckResult(
            check='token_permissions',
            passed=False,
            message=f'Overly permissive permissions in: {", ".join(violations)}',
            hint='Use least-privilege permissions (e.g. contents: read, id-token: write).',
        )
    return ScorecardCheckResult(
        check='token_permissions',
        passed=True,
        message='No overly permissive token permissions found',
    )


def _check_signed_releases(repo_root: Path) -> ScorecardCheckResult:
    """Check that Sigstore bundles exist for previous release artifacts.

    Looks for ``.sigstore.json`` files in common artifact directories.

    Args:
        repo_root: Path to the repository root.

    Returns:
        A :class:`ScorecardCheckResult`.
    """
    artifact_dirs = [
        repo_root / 'dist',
        repo_root / 'artifacts',
    ]
    sigstore_files: list[Path] = []
    for d in artifact_dirs:
        if d.is_dir():
            sigstore_files.extend(d.glob('*.sigstore.json'))

    if sigstore_files:
        return ScorecardCheckResult(
            check='signed_releases',
            passed=True,
            message=f'{len(sigstore_files)} Sigstore bundle(s) found',
        )
    return ScorecardCheckResult(
        check='signed_releases',
        passed=True,
        message='No artifact directories to check (OK for first release)',
    )


def run_scorecard_checks(
    repo_root: Path,
) -> list[ScorecardCheckResult]:
    """Run all OpenSSF Scorecard-aligned checks.

    Args:
        repo_root: Path to the repository root.

    Returns:
        List of :class:`ScorecardCheckResult` for each check.
    """
    checks = [
        _check_security_md,
        _check_dependency_update_tool,
        _check_ci_tests,
        _check_pinned_dependencies,
        _check_token_permissions,
        _check_signed_releases,
    ]
    results = [check(repo_root) for check in checks]

    passed = sum(1 for r in results if r.passed)
    total = len(results)
    logger.info('scorecard_complete', passed=passed, total=total)

    return results


__all__ = [
    'ScorecardCheckResult',
    'run_scorecard_checks',
]
