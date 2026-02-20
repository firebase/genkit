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

"""Optional changeset file support (hybrid with conventional commits).

Reads ``.changeset/*.md`` files in the Changesets format and converts
them to bump instructions that can be merged with conventional-commit
bumps. This allows teams to use explicit changeset files for intentional
version bumps while still supporting automatic conventional-commit
detection.

Key Concepts (ELI5)::

    ┌─────────────────────────┬─────────────────────────────────────────────┐
    │ Concept                 │ Plain-English                               │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ Changeset file          │ A markdown file in ``.changeset/`` that     │
    │                         │ declares which packages get bumped and by   │
    │                         │ how much (major/minor/patch).               │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ Hybrid mode             │ Changeset bumps are merged with             │
    │                         │ conventional-commit bumps. The higher bump  │
    │                         │ wins for each package.                      │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ Consume                 │ After a release, consumed changeset files   │
    │                         │ are deleted so they don't apply again.      │
    └─────────────────────────┴─────────────────────────────────────────────┘

Changeset file format::

    ---
    "genkit": minor
    "genkit-plugin-firebase": patch
    ---

    Add streaming support to the genkit core library.

Usage::

    from releasekit.changesets import (
        read_changesets,
        merge_changeset_bumps,
        consume_changesets,
    )

    changesets = read_changesets(Path('.changeset'))
    merged = merge_changeset_bumps(commit_bumps, changesets)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from releasekit.commit_parsing import BumpType, max_bump
from releasekit.logging import get_logger

logger = get_logger(__name__)

# Regex for parsing changeset frontmatter lines: "package-name": bump_level
_FRONTMATTER_LINE_RE = re.compile(r'^["\']?(?P<name>[^"\']+)["\']?\s*:\s*(?P<bump>major|minor|patch)\s*$')

# Map string bump levels to BumpType.
_BUMP_MAP: dict[str, BumpType] = {
    'major': BumpType.MAJOR,
    'minor': BumpType.MINOR,
    'patch': BumpType.PATCH,
}


@dataclass(frozen=True)
class Changeset:
    """A single parsed changeset file.

    Attributes:
        path: Path to the ``.changeset/*.md`` file.
        bumps: Mapping of package name → bump level.
        summary: Human-readable summary from the changeset body.
    """

    path: Path
    bumps: dict[str, BumpType] = field(default_factory=dict)
    summary: str = ''


def _parse_changeset(path: Path) -> Changeset | None:
    """Parse a single changeset markdown file.

    Expected format::

        ---
        "package-a": minor
        "package-b": patch
        ---

        Description of the change.

    Args:
        path: Path to the changeset file.

    Returns:
        Parsed :class:`Changeset`, or ``None`` if the file is invalid.
    """
    try:
        text = path.read_text(encoding='utf-8')
    except OSError as exc:
        logger.warning('changeset_read_error', path=str(path), error=str(exc))
        return None

    lines = text.strip().split('\n')

    # Find frontmatter delimiters.
    if not lines or lines[0].strip() != '---':
        logger.debug('changeset_no_frontmatter', path=str(path))
        return None

    end_idx = -1
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == '---':
            end_idx = i
            break

    if end_idx < 0:
        logger.debug('changeset_unclosed_frontmatter', path=str(path))
        return None

    # Parse frontmatter lines.
    bumps: dict[str, BumpType] = {}
    for line in lines[1:end_idx]:
        stripped = line.strip()
        if not stripped:
            continue
        m = _FRONTMATTER_LINE_RE.match(stripped)
        if m:
            name = m.group('name')
            bump_str = m.group('bump')
            bumps[name] = _BUMP_MAP[bump_str]
        else:
            logger.warning('changeset_invalid_line', path=str(path), line=stripped)

    # Extract summary (everything after the closing ---).
    summary_lines = lines[end_idx + 1 :]
    summary = '\n'.join(summary_lines).strip()

    if not bumps:
        logger.debug('changeset_empty', path=str(path))
        return None

    return Changeset(path=path, bumps=bumps, summary=summary)


def read_changesets(changeset_dir: Path) -> list[Changeset]:
    """Read all changeset files from the ``.changeset/`` directory.

    Ignores non-markdown files and the ``config.json`` file.

    Args:
        changeset_dir: Path to the ``.changeset/`` directory.

    Returns:
        List of parsed :class:`Changeset` objects.
    """
    if not changeset_dir.is_dir():
        logger.debug('changeset_dir_not_found', path=str(changeset_dir))
        return []

    changesets: list[Changeset] = []
    for path in sorted(changeset_dir.glob('*.md')):
        if path.name.startswith('.') or path.name == 'README.md':
            continue

        cs = _parse_changeset(path)
        if cs is not None:
            changesets.append(cs)
            logger.info(
                'changeset_read',
                path=str(path),
                packages=len(cs.bumps),
            )

    logger.info('changesets_total', count=len(changesets))
    return changesets


def merge_changeset_bumps(
    commit_bumps: dict[str, BumpType],
    changesets: list[Changeset],
) -> dict[str, BumpType]:
    """Merge changeset bumps with conventional-commit bumps.

    For each package, the higher bump level wins. This allows changeset
    files to override or supplement commit-based bumps.

    Args:
        commit_bumps: Package → bump from conventional commits.
        changesets: Parsed changeset files.

    Returns:
        Merged package → bump mapping.
    """
    merged = dict(commit_bumps)

    for cs in changesets:
        for name, bump in cs.bumps.items():
            existing = merged.get(name, BumpType.NONE)
            winner = max_bump(existing, bump)
            if winner != existing:
                logger.info(
                    'changeset_bump_override',
                    package=name,
                    from_bump=existing.value,
                    to_bump=winner.value,
                    changeset=str(cs.path.name),
                )
            merged[name] = winner

    return merged


def changeset_summaries(changesets: list[Changeset]) -> dict[str, list[str]]:
    """Extract per-package summaries from changesets for changelog use.

    Args:
        changesets: Parsed changeset files.

    Returns:
        Mapping of package name → list of summary strings.
    """
    result: dict[str, list[str]] = {}
    for cs in changesets:
        if not cs.summary:
            continue
        for name in cs.bumps:
            result.setdefault(name, []).append(cs.summary)
    return result


def consume_changesets(
    changesets: list[Changeset],
    *,
    dry_run: bool = False,
) -> list[Path]:
    """Delete consumed changeset files after a release.

    Args:
        changesets: Changeset files to consume.
        dry_run: If True, log what would be deleted without deleting.

    Returns:
        List of paths that were (or would be) deleted.
    """
    deleted: list[Path] = []
    for cs in changesets:
        if dry_run:
            logger.info('changeset_consume_dry_run', path=str(cs.path))
            deleted.append(cs.path)
            continue

        try:
            cs.path.unlink()
            deleted.append(cs.path)
            logger.info('changeset_consumed', path=str(cs.path))
        except OSError as exc:
            logger.warning('changeset_consume_error', path=str(cs.path), error=str(exc))

    return deleted


__all__ = [
    'Changeset',
    'changeset_summaries',
    'consume_changesets',
    'merge_changeset_bumps',
    'read_changesets',
]
