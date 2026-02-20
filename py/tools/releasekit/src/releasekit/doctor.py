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

"""Release state consistency checker (``releasekit doctor``).

Diagnoses inconsistent state between the workspace, git tags, and the
platform release. Useful after initial adoption or when things look off.

Checks::

    1. Config validity        → releasekit.toml parses without errors
    2. Tag/version alignment  → each package's current version has a tag
    3. Orphaned tags          → tags that don't match any known package
    4. VCS state              → clean worktree, not shallow
    5. Forge connectivity     → platform forge (e.g. GitHub) is reachable
    6. Default branch         → HEAD is on the configured default branch

Each check produces a :class:`DiagnosticResult` (pass / warn / fail).
"""

from __future__ import annotations

import dataclasses
from enum import Enum
from typing import TYPE_CHECKING

from releasekit.logging import get_logger
from releasekit.tags import format_tag

if TYPE_CHECKING:
    from releasekit.backends.forge import Forge
    from releasekit.backends.vcs import VCS
    from releasekit.config import ReleaseConfig, WorkspaceConfig
    from releasekit.workspace import Package

logger = get_logger(__name__)


class Severity(Enum):
    """Diagnostic severity level."""

    PASS = 'pass'
    WARN = 'warn'
    FAIL = 'fail'


@dataclasses.dataclass
class DiagnosticResult:
    """Result of a single diagnostic check."""

    name: str
    severity: Severity
    message: str
    hint: str = ''


@dataclasses.dataclass
class DoctorReport:
    """Aggregated results from all diagnostic checks."""

    results: list[DiagnosticResult] = dataclasses.field(default_factory=list)

    def add(self, name: str, severity: Severity, message: str, hint: str = '') -> None:
        """Add a diagnostic result."""
        self.results.append(DiagnosticResult(name=name, severity=severity, message=message, hint=hint))

    @property
    def passed(self) -> list[DiagnosticResult]:
        """Return all passing results."""
        return [r for r in self.results if r.severity == Severity.PASS]

    @property
    def warnings(self) -> list[DiagnosticResult]:
        """Return all warning results."""
        return [r for r in self.results if r.severity == Severity.WARN]

    @property
    def failures(self) -> list[DiagnosticResult]:
        """Return all failing results."""
        return [r for r in self.results if r.severity == Severity.FAIL]

    @property
    def ok(self) -> bool:
        """Return True if there are no failures."""
        return not self.failures


async def _check_config(
    config: ReleaseConfig,
    ws_config: WorkspaceConfig,
    report: DoctorReport,
) -> None:
    """Check that the config is valid and complete."""
    if not ws_config.label:
        report.add('config', Severity.FAIL, 'No workspace label configured.')
        return
    if not ws_config.ecosystem:
        report.add('config', Severity.FAIL, f'Workspace "{ws_config.label}" has no ecosystem.')
        return
    if not ws_config.tag_format:
        report.add('config', Severity.WARN, 'No tag_format configured; using default.')
    else:
        report.add(
            'config',
            Severity.PASS,
            f'Config OK (workspace={ws_config.label}, ecosystem={ws_config.ecosystem}).',
        )


async def _check_tag_alignment(
    packages: list[Package],
    vcs: VCS,
    ws_config: WorkspaceConfig,
    report: DoctorReport,
) -> None:
    """Check that each package's current version has a matching git tag."""
    missing: list[str] = []
    found: list[str] = []

    for pkg in packages:
        tag = format_tag(ws_config.tag_format, name=pkg.name, version=pkg.version, label=ws_config.label)
        if await vcs.tag_exists(tag):
            found.append(tag)
        else:
            missing.append(f'{pkg.name}@{pkg.version} (expected tag: {tag})')

    if missing:
        report.add(
            'tag_alignment',
            Severity.WARN,
            f'{len(missing)} package(s) missing tags: {", ".join(missing[:5])}'
            + (f' (+{len(missing) - 5} more)' if len(missing) > 5 else ''),
            hint='Run "releasekit prepare" to create tags, or set bootstrap_sha for mid-stream adoption.',
        )
    else:
        report.add('tag_alignment', Severity.PASS, f'All {len(found)} package tags present.')


async def _check_orphaned_tags(
    packages: list[Package],
    vcs: VCS,
    ws_config: WorkspaceConfig,
    report: DoctorReport,
) -> None:
    """Check for tags that match the tag format but don't correspond to any known package version."""
    # Build set of expected tags.
    expected_tags: set[str] = set()
    for pkg in packages:
        expected_tags.add(format_tag(ws_config.tag_format, name=pkg.name, version=pkg.version, label=ws_config.label))

    # List all tags matching a loose pattern.
    try:
        all_tags = await vcs.list_tags()
    except (AttributeError, NotImplementedError):
        report.add('orphaned_tags', Severity.WARN, 'VCS backend does not support list_tags; skipping orphan check.')
        return

    # Filter to tags that look like they belong to this workspace.
    # Use the label as a heuristic if present.
    label = ws_config.label
    workspace_tags = [t for t in all_tags if label and label in t] if label else all_tags

    orphaned = [t for t in workspace_tags if t not in expected_tags]
    if orphaned:
        report.add(
            'orphaned_tags',
            Severity.WARN,
            f'{len(orphaned)} tag(s) not matching current package versions: {", ".join(orphaned[:5])}'
            + (f' (+{len(orphaned) - 5} more)' if len(orphaned) > 5 else ''),
            hint='These may be from previous releases. Use "releasekit rollback <tag>" to clean up.',
        )
    else:
        report.add('orphaned_tags', Severity.PASS, 'No orphaned tags found.')


async def _check_vcs_state(
    vcs: VCS,
    report: DoctorReport,
) -> None:
    """Check VCS state: clean worktree, not shallow."""
    # Clean worktree.
    try:
        await vcs.diff_files(since_tag=None)
        # diff_files with no since_tag returns uncommitted changes on some backends.
        # Use a more reliable check: check if worktree is clean.
        result = await vcs.is_clean()
        if result:
            report.add('worktree', Severity.PASS, 'Working tree is clean.')
        else:
            report.add(
                'worktree',
                Severity.WARN,
                'Working tree has uncommitted changes.',
                hint='Commit or stash changes before releasing.',
            )
    except (AttributeError, NotImplementedError):
        # Fallback: just report we couldn't check.
        report.add('worktree', Severity.WARN, 'Could not verify worktree state.')

    # Shallow clone.
    try:
        is_shallow = await vcs.is_shallow()
        if is_shallow:
            report.add(
                'shallow_clone',
                Severity.WARN,
                'Repository is a shallow clone; git log may be incomplete.',
                hint='Run "git fetch --unshallow" for complete history.',
            )
        else:
            report.add('shallow_clone', Severity.PASS, 'Full clone detected.')
    except (AttributeError, NotImplementedError):
        pass


async def _check_forge(
    forge: Forge | None,
    report: DoctorReport,
) -> None:
    """Check forge connectivity."""
    if forge is None:
        report.add(
            'forge',
            Severity.WARN,
            'No forge backend configured.',
            hint='Set forge = "github" in releasekit.toml for platform releases.',
        )
        return

    try:
        available = await forge.is_available()
        if available:
            report.add('forge', Severity.PASS, 'Forge backend is available.')
        else:
            report.add(
                'forge',
                Severity.WARN,
                'Forge backend not available.',
                hint='Check that the forge CLI tool is installed and authenticated.',
            )
    except Exception as exc:
        report.add('forge', Severity.WARN, f'Forge check failed: {exc}')


async def _check_default_branch(
    vcs: VCS,
    config: ReleaseConfig,
    report: DoctorReport,
) -> None:
    """Check that HEAD is on the default branch."""
    try:
        current = await vcs.current_branch()
        default = config.default_branch or 'main'
        if current == default:
            report.add('default_branch', Severity.PASS, f'On default branch ({default}).')
        else:
            report.add(
                'default_branch',
                Severity.WARN,
                f'Not on default branch: current={current}, expected={default}.',
                hint='Releases should be cut from the default branch.',
            )
    except (AttributeError, NotImplementedError):
        pass


async def run_doctor(
    *,
    packages: list[Package],
    vcs: VCS,
    forge: Forge | None,
    config: ReleaseConfig,
    ws_config: WorkspaceConfig,
) -> DoctorReport:
    """Run all diagnostic checks and return a report.

    Args:
        packages: Discovered workspace packages.
        vcs: VCS backend.
        forge: Optional forge backend.
        config: Global release config.
        ws_config: Per-workspace config.

    Returns:
        A :class:`DoctorReport` with all diagnostic results.
    """
    report = DoctorReport()

    await _check_config(config, ws_config, report)
    await _check_tag_alignment(packages, vcs, ws_config, report)
    await _check_orphaned_tags(packages, vcs, ws_config, report)
    await _check_vcs_state(vcs, report)
    await _check_forge(forge, report)
    await _check_default_branch(vcs, config, report)

    return report


__all__ = [
    'DiagnosticResult',
    'DoctorReport',
    'Severity',
    'run_doctor',
]
