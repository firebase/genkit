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

"""Structured changelog generation from Conventional Commits.

Generates a markdown changelog grouped by commit type (Breaking Changes,
Features, Bug Fixes, etc.). Commit data is read from git log via the
VCS backend. Supports both per-package and umbrella changelogs, with
prerelease-to-release rollup.

Key Concepts (ELI5)::

    ┌─────────────────────────┬─────────────────────────────────────────────┐
    │ Concept                 │ Plain-English                               │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ ChangelogEntry          │ One parsed commit: type, scope, description │
    │                         │ and optional PR reference.                  │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ ChangelogSection        │ A group of entries under one heading, e.g.  │
    │                         │ "Features" or "Bug Fixes".                  │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ Changelog               │ All sections for one version/release.       │
    └─────────────────────────┴─────────────────────────────────────────────┘

Changelog generation flow::

    vcs.log(since_tag=last_tag, paths=[pkg.path])
         │
         ▼
    parse_conventional_commit(message, sha)
         │
         ▼
    group by commit type → ChangelogSection
         │
         ▼
    render_changelog(sections) → markdown string

Usage::

    from releasekit.changelog import generate_changelog

    md = generate_changelog(
        vcs=git_backend,
        version='0.5.0',
        since_tag='v0.4.0',
    )
    print(md)
    # ## 0.5.0
    #
    # ### Breaking Changes
    # - **auth**: Remove deprecated OAuth1 support (abc123)
    #
    # ### Features
    # - **streaming**: Add real-time event streaming (def456)
    #
    # ### Bug Fixes
    # - Fix race condition in publisher (789abc)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from releasekit.backends.vcs import VCS
from releasekit.logging import get_logger
from releasekit.versioning import ConventionalCommit, parse_conventional_commit

logger = get_logger(__name__)


# Maps commit type to section heading (display order matters).
_SECTION_ORDER: list[tuple[str, str]] = [
    ('breaking', 'Breaking Changes'),
    ('feat', 'Features'),
    ('fix', 'Bug Fixes'),
    ('perf', 'Performance'),
    ('refactor', 'Refactoring'),
    ('docs', 'Documentation'),
    ('test', 'Tests'),
    ('ci', 'CI/CD'),
    ('build', 'Build'),
    ('chore', 'Chores'),
    ('style', 'Style'),
    ('revert', 'Reverts'),
]

# Heading lookup (type → display name).
_TYPE_HEADINGS: dict[str, str] = dict(_SECTION_ORDER)

# Types to exclude from changelogs by default (too noisy).
_DEFAULT_EXCLUDE_TYPES: frozenset[str] = frozenset({
    'chore',
    'style',
    'ci',
    'build',
    'test',
})

# Regex to extract PR references like (#1234) from commit messages.
_PR_REF_PATTERN: re.Pattern[str] = re.compile(r'\(#(\d+)\)')


@dataclass(frozen=True)
class ChangelogEntry:
    """A single changelog entry from one commit.

    Attributes:
        type: Commit type (e.g. ``"feat"``, ``"fix"``).
        scope: Optional scope (e.g. ``"auth"``).
        description: Commit description.
        sha: Short commit SHA (first 7 characters).
        pr_number: PR number extracted from description, if any.
        breaking: Whether this is a breaking change.
    """

    type: str
    description: str
    sha: str = ''
    scope: str = ''
    pr_number: str = ''
    breaking: bool = False


@dataclass
class ChangelogSection:
    """A group of changelog entries under one heading.

    Attributes:
        heading: Section heading (e.g. ``"Features"``).
        entries: Entries in this section, in commit order.
    """

    heading: str
    entries: list[ChangelogEntry] = field(default_factory=list)


@dataclass
class Changelog:
    """Complete changelog for one version.

    Attributes:
        version: Version string (e.g. ``"0.5.0"``).
        sections: Sections grouped by commit type.
        date: Optional date string (ISO 8601).
    """

    version: str
    sections: list[ChangelogSection] = field(default_factory=list)
    date: str = ''


def _commit_to_entry(cc: ConventionalCommit) -> ChangelogEntry:
    """Convert a parsed Conventional Commit to a ChangelogEntry."""
    short_sha = cc.sha[:7] if cc.sha else ''

    # Extract PR reference from description.
    pr_match = _PR_REF_PATTERN.search(cc.description)
    pr_number = pr_match.group(1) if pr_match else ''

    # Clean description: remove trailing PR reference for cleaner display.
    description = cc.description
    if pr_match:
        description = description[: pr_match.start()].rstrip()

    return ChangelogEntry(
        type=cc.type,
        description=description,
        sha=short_sha,
        scope=cc.scope,
        pr_number=pr_number,
        breaking=cc.breaking,
    )


def _group_entries(
    entries: list[ChangelogEntry],
) -> list[ChangelogSection]:
    """Group entries by commit type into ordered sections.

    Returns sections in the canonical order defined by
    ``_SECTION_ORDER``. Empty sections are omitted.
    """
    # Bucket entries by type (breaking changes get their own bucket).
    buckets: dict[str, list[ChangelogEntry]] = {}
    for entry in entries:
        key = 'breaking' if entry.breaking else entry.type
        buckets.setdefault(key, []).append(entry)

    # Build sections in display order.
    sections: list[ChangelogSection] = []
    for type_key, heading in _SECTION_ORDER:
        bucket = buckets.pop(type_key, [])
        if bucket:
            sections.append(ChangelogSection(heading=heading, entries=bucket))

    # Catch any types not in the predefined order.
    for type_key, bucket in sorted(buckets.items()):
        if bucket:
            heading = type_key.capitalize()
            sections.append(ChangelogSection(heading=heading, entries=bucket))

    return sections


def _render_entry(entry: ChangelogEntry) -> str:
    """Render a single entry as a markdown bullet point.

    Format: ``- **scope**: description (sha) (#pr)``
    """
    parts: list[str] = ['- ']

    if entry.scope:
        parts.append(f'**{entry.scope}**: ')

    parts.append(entry.description)

    refs: list[str] = []
    if entry.sha:
        refs.append(entry.sha)
    if entry.pr_number:
        refs.append(f'#{entry.pr_number}')

    if refs:
        parts.append(f' ({", ".join(refs)})')

    return ''.join(parts)


def render_changelog(changelog: Changelog) -> str:
    """Render a Changelog as a markdown string.

    Args:
        changelog: The changelog to render.

    Returns:
        A markdown string with version heading, sections, and entries.
    """
    lines: list[str] = []

    # Version heading.
    heading = f'## {changelog.version}'
    if changelog.date:
        heading += f' ({changelog.date})'
    lines.append(heading)
    lines.append('')

    for section in changelog.sections:
        lines.append(f'### {section.heading}')
        lines.append('')
        for entry in section.entries:
            lines.append(_render_entry(entry))
        lines.append('')

    return '\n'.join(lines).rstrip() + '\n'


async def generate_changelog(
    *,
    vcs: VCS,
    version: str,
    since_tag: str | None = None,
    paths: list[str] | None = None,
    exclude_types: frozenset[str] | None = None,
    date: str = '',
    log_format: str = '%H %s',
) -> Changelog:
    """Generate a structured changelog from git history.

    Reads the git log since ``since_tag``, parses Conventional Commits,
    groups them by type, and returns a :class:`Changelog`.

    Args:
        vcs: VCS backend for git operations.
        version: Version string for the changelog heading.
        since_tag: Only include commits after this tag. If ``None``,
            includes all history.
        paths: Limit commits to changes in these paths.
        exclude_types: Commit types to exclude. Defaults to
            ``_DEFAULT_EXCLUDE_TYPES`` (chore, style, ci, build, test).
        date: Optional date string for the heading.
        log_format: Git log format. Must produce ``SHA subject`` lines.

    Returns:
        A :class:`Changelog` with grouped sections.
    """
    if exclude_types is None:
        exclude_types = _DEFAULT_EXCLUDE_TYPES

    log_lines = await vcs.log(since_tag=since_tag, paths=paths, format=log_format)
    logger.info(
        'changelog_commits_found',
        count=len(log_lines),
        since_tag=since_tag or '(all)',
        paths=paths or '(all)',
    )

    entries: list[ChangelogEntry] = []
    for line in log_lines:
        # Format: "SHA subject" — split on first space.
        parts = line.split(' ', 1)
        if len(parts) < 2:
            continue
        sha, message = parts

        cc = parse_conventional_commit(message, sha=sha)
        if cc is None:
            # Non-conventional commit — skip.
            continue

        if cc.type in exclude_types and not cc.breaking:
            # Excluded type (unless it's breaking — breaking always shows).
            continue

        entries.append(_commit_to_entry(cc))

    sections = _group_entries(entries)

    logger.info(
        'changelog_generated',
        version=version,
        sections=len(sections),
        entries=len(entries),
    )

    return Changelog(version=version, sections=sections, date=date)


async def generate_umbrella_changelog(
    *,
    vcs: VCS,
    version: str,
    since_tag: str | None = None,
    exclude_types: frozenset[str] | None = None,
    date: str = '',
) -> Changelog:
    """Generate an umbrella changelog for the entire workspace.

    Unlike :func:`generate_changelog`, this does not filter by path —
    it includes all commits since ``since_tag``.

    Args:
        vcs: VCS backend.
        version: Version string for the heading.
        since_tag: Only include commits after this tag.
        exclude_types: Types to exclude.
        date: Optional date string.

    Returns:
        A :class:`Changelog` covering the whole workspace.
    """
    return await generate_changelog(
        vcs=vcs,
        version=version,
        since_tag=since_tag,
        paths=None,
        exclude_types=exclude_types,
        date=date,
    )


__all__ = [
    'Changelog',
    'ChangelogEntry',
    'ChangelogSection',
    'generate_changelog',
    'generate_umbrella_changelog',
    'render_changelog',
]
