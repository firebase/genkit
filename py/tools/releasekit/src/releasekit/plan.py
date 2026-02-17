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

"""Execution plan for release publishing.

Builds a table of per-package publish actions (version bump, skip,
exclude) with status emoji and reason. Output as a Rich table (TTY),
JSON, or CSV. Shared between the ``plan`` and ``publish`` subcommands.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                               │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ ExecutionPlan       │ A checklist of what will happen to each       │
    │                     │ package: publish, skip, or exclude.           │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ PlanEntry           │ One row in the checklist: package name,       │
    │                     │ current version, next version, and why.       │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Format              │ How to display: table (human), JSON (CI),     │
    │                     │ or CSV (spreadsheet).                         │
    └─────────────────────┴────────────────────────────────────────────────┘

Usage::

    from releasekit.plan import ExecutionPlan, PlanEntry, PlanStatus

    plan = ExecutionPlan(
        entries=[
            PlanEntry(
                name='genkit',
                level=0,
                current_version='0.4.0',
                next_version='0.5.0',
                status=PlanStatus.INCLUDED,
                bump='minor',
                reason='feat: add streaming',
            ),
        ]
    )

    # Rich table (default for TTY)
    print(plan.format_table())

    # JSON (for CI pipelines)
    print(plan.format_json())

    # CSV (for spreadsheets)
    print(plan.format_csv())
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict, dataclass, field
from enum import Enum

from releasekit.logging import get_logger
from releasekit.versions import PackageVersion
from releasekit.workspace import Package

logger = get_logger(__name__)


class PlanStatus(str, Enum):
    """Status of a package in the execution plan.

    Determines whether a package will be published and why.
    """

    INCLUDED = 'included'
    SKIPPED = 'skipped'
    EXCLUDED = 'excluded'
    PUBLISH_EXCLUDED = 'publish_excluded'
    ALREADY_PUBLISHED = 'already_published'
    DEPENDENCY_ONLY = 'dependency_only'


# Emoji map for terminal display.
_STATUS_EMOJI: dict[PlanStatus, str] = {
    PlanStatus.INCLUDED: '📦',
    PlanStatus.SKIPPED: '⏭️',
    PlanStatus.EXCLUDED: '🚫',
    PlanStatus.PUBLISH_EXCLUDED: '🔒',
    PlanStatus.ALREADY_PUBLISHED: '✅',
    PlanStatus.DEPENDENCY_ONLY: '🔗',
}

# Derived status sets for filtering.
# Packages whose version will be bumped (regardless of publish outcome).
BUMPED_STATUSES: frozenset[PlanStatus] = frozenset({
    PlanStatus.INCLUDED,
    PlanStatus.PUBLISH_EXCLUDED,
    PlanStatus.ALREADY_PUBLISHED,
})

# Packages that will actually be published to a registry.
PUBLISHABLE_STATUSES: frozenset[PlanStatus] = frozenset({
    PlanStatus.INCLUDED,
})


@dataclass(frozen=True)
class PlanEntry:
    """One row in the execution plan.

    Attributes:
        name: Package name.
        level: Topological level (0 = no internal deps).
        current_version: Current version in pyproject.toml.
        next_version: Computed next version (same as current if skipped).
        status: Whether the package will be published.
        bump: Bump type applied (``"minor"``, ``"patch"``, etc.).
        reason: Human-readable reason for the status.
        order: Publish order within the level (0-based).
    """

    name: str
    level: int = 0
    current_version: str = ''
    next_version: str = ''
    status: PlanStatus = PlanStatus.INCLUDED
    bump: str = 'none'
    reason: str = ''
    order: int = 0


@dataclass
class ExecutionPlan:
    """Complete publish plan for all workspace packages.

    Attributes:
        entries: Per-package plan entries, ordered by level then name.
        git_sha: HEAD SHA when the plan was computed.
    """

    entries: list[PlanEntry] = field(default_factory=list)
    git_sha: str = ''
    umbrella_version: str = ''

    @property
    def included(self) -> list[PlanEntry]:
        """Return entries that will be published."""
        return [e for e in self.entries if e.status == PlanStatus.INCLUDED]

    @property
    def skipped(self) -> list[PlanEntry]:
        """Return entries that will be skipped."""
        return [e for e in self.entries if e.status in {PlanStatus.SKIPPED, PlanStatus.ALREADY_PUBLISHED}]

    def filter_by_status(self, statuses: set[PlanStatus]) -> ExecutionPlan:
        """Return a new plan containing only entries with the given statuses.

        Args:
            statuses: Set of :class:`PlanStatus` values to keep.

        Returns:
            A new :class:`ExecutionPlan` with filtered entries.
        """
        return ExecutionPlan(
            entries=[e for e in self.entries if e.status in statuses],
            git_sha=self.git_sha,
            umbrella_version=self.umbrella_version,
        )

    def summary(self) -> dict[str, int]:
        """Return a summary count by status."""
        counts: dict[str, int] = {}
        for entry in self.entries:
            counts[entry.status.value] = counts.get(entry.status.value, 0) + 1
        return counts

    def format_table(self) -> str:
        """Format the plan as a human-readable table with emoji.

        Returns:
            A formatted table string.
        """
        if not self.entries:
            return 'No packages in the execution plan.'

        # Calculate column widths.
        headers = ['', 'Level', 'Package', 'Current', 'Next', 'Bump', 'Status', 'Reason']
        rows: list[list[str]] = []

        for entry in self.entries:
            emoji = _STATUS_EMOJI.get(entry.status, '❓')
            rows.append([
                emoji,
                str(entry.level),
                entry.name,
                entry.current_version,
                entry.next_version or '—',
                entry.bump,
                entry.status.value,
                entry.reason,
            ])

        # Calculate column widths.
        widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                # Emoji characters may have display width 2, but we use
                # a fixed 2-char column for the emoji.
                widths[i] = max(widths[i], len(cell))

        # Build the table.
        lines: list[str] = []
        fmt = '  '.join(f'{{:<{w}}}' for w in widths)
        lines.append(fmt.format(*headers))
        lines.append(fmt.format(*('─' * w for w in widths)))
        for row in rows:
            lines.append(fmt.format(*row))

        # Append summary.
        summary = self.summary()
        summary_parts = [f'{count} {status}' for status, count in sorted(summary.items())]
        lines.append('')
        if self.umbrella_version:
            lines.append(f'Umbrella version: {self.umbrella_version}')
        lines.append(f'Total: {len(self.entries)} packages ({", ".join(summary_parts)})')

        return '\n'.join(lines)

    def format_ascii_flow(self) -> str:
        """Format the plan as an ASCII flow diagram showing publish order.

        Groups packages by topological level with box-drawing characters
        and arrows showing the publish sequence.

        Returns:
            An ASCII art string showing the publish flow.
        """
        if not self.entries:
            return 'No packages in the execution plan.'

        included = [e for e in self.entries if e.status == PlanStatus.INCLUDED]
        if not included:
            return 'No packages to publish.'

        # Group by level.
        levels: dict[int, list[PlanEntry]] = {}
        for entry in included:
            levels.setdefault(entry.level, []).append(entry)

        # Compute box width from longest package line.
        max_line_len = 0
        for level_entries in levels.values():
            for e in level_entries:
                line = f'  {e.name} {e.current_version} -> {e.next_version} ({e.bump})'
                max_line_len = max(max_line_len, len(line))
        width = max(50, max_line_len + 4)

        lines: list[str] = []
        sorted_levels = sorted(levels.keys())

        for i, level_idx in enumerate(sorted_levels):
            level_entries = levels[level_idx]

            if i == 0:
                lines.append(f'┌{"─" * width}┐')
            else:
                # Arrow between levels.
                arrow_pad = (width - 1) // 2
                lines.append(f'│{" " * width}│')
                lines.append(f'│{" " * arrow_pad}│{" " * (width - arrow_pad - 1)}│')
                lines.append(f'│{" " * arrow_pad}▼{" " * (width - arrow_pad - 1)}│')
                lines.append(f'├{"─" * width}┤')

            header = f'│ Level {level_idx} (parallel)'
            lines.append(f'{header}{" " * (width - len(header) + 1)}│')

            for e in level_entries:
                emoji = _STATUS_EMOJI.get(e.status, '❓')
                content = f'│   {emoji} {e.name} {e.current_version} → {e.next_version} ({e.bump})'
                lines.append(f'{content}{" " * (width - len(content) + 1)}│')

        lines.append(f'└{"─" * width}┘')

        # Summary line.
        total = len(included)
        level_count = len(sorted_levels)
        if self.umbrella_version:
            lines.append(f'\nUmbrella version: {self.umbrella_version}')
        lines.append(f'\n{total} package(s) across {level_count} level(s)')

        return '\n'.join(lines)

    def format_json(self) -> str:
        """Format the plan as machine-readable JSON.

        Returns:
            A JSON string.
        """
        data = {
            'git_sha': self.git_sha,
            'umbrella_version': self.umbrella_version,
            'summary': self.summary(),
            'entries': [asdict(e) for e in self.entries],
        }
        return json.dumps(data, indent=2)

    def format_csv(self) -> str:
        """Format the plan as CSV.

        Returns:
            A CSV string.
        """
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['level', 'order', 'name', 'current_version', 'next_version', 'bump', 'status', 'reason'])
        for entry in self.entries:
            writer.writerow([
                entry.level,
                entry.order,
                entry.name,
                entry.current_version,
                entry.next_version,
                entry.bump,
                entry.status.value,
                entry.reason,
            ])
        return output.getvalue()


def build_plan(
    versions: list[PackageVersion],
    levels: list[list[Package]],
    *,
    exclude_names: list[str] | None = None,
    exclude_publish_names: set[str] | None = None,
    already_published: set[str] | None = None,
    git_sha: str = '',
    umbrella_version: str = '',
) -> ExecutionPlan:
    """Build an execution plan from version computation results.

    Args:
        versions: List of :class:`~releasekit.versions.PackageVersion` records.
        levels: Topological levels from :func:`~releasekit.graph.topo_sort`.
        exclude_names: Package names to mark as excluded from discovery.
        exclude_publish_names: Package names excluded from publishing
            (bumped but not published).
        already_published: Package names already published on the registry.
        git_sha: Current HEAD SHA.
        umbrella_version: Resolved umbrella version for the release.

    Returns:
        An :class:`ExecutionPlan` with entries for all packages.
    """
    excludes = set(exclude_names or [])
    publish_excludes = exclude_publish_names or set()
    published = already_published or set()

    # Build a name→PackageVersion lookup.
    version_map: dict[str, PackageVersion] = {}
    for v in versions:
        version_map[v.name] = v

    # Build a name→level lookup.
    level_map: dict[str, int] = {}
    for level_idx, level in enumerate(levels):
        for pkg in level:
            level_map[pkg.name] = level_idx

    entries: list[PlanEntry] = []
    order_per_level: dict[int, int] = {}

    for v in versions:
        level = level_map.get(v.name, 0)
        order = order_per_level.get(level, 0)
        order_per_level[level] = order + 1

        if v.name in excludes:
            status = PlanStatus.EXCLUDED
            reason = 'excluded by configuration'
        elif v.name in published:
            status = PlanStatus.ALREADY_PUBLISHED
            reason = f'{v.new_version} already on registry'
        elif v.skipped:
            status = PlanStatus.SKIPPED
            reason = v.reason or 'no changes since last tag'
        elif v.name in publish_excludes:
            status = PlanStatus.PUBLISH_EXCLUDED
            reason = 'bumped but excluded from publishing'
        else:
            status = PlanStatus.INCLUDED
            reason = v.reason

        entries.append(
            PlanEntry(
                name=v.name,
                level=level,
                current_version=v.old_version,
                next_version=v.new_version,
                status=status,
                bump=v.bump,
                reason=reason,
                order=order,
            )
        )

    # Sort by level, then name for stable output.
    entries.sort(key=lambda e: (e.level, e.name))

    plan = ExecutionPlan(entries=entries, git_sha=git_sha, umbrella_version=umbrella_version)
    logger.info('plan_built', total=len(entries), **plan.summary())
    return plan


__all__ = [
    'BUMPED_STATUSES',
    'ExecutionPlan',
    'PUBLISHABLE_STATUSES',
    'PlanEntry',
    'PlanStatus',
    'build_plan',
]
