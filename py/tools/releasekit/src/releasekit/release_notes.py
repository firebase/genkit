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

"""Umbrella release notes generation.

Composes a single release notes document summarizing all packages
bumped in a release. Combines data from multiple sources:

- Changelog entries via :mod:`releasekit.changelog`
- PR data via :meth:`Forge.pr_data` (optional)
- Diff stats via :meth:`VCS.diff_files` (optional)

Key Concepts (ELI5)::

    ┌─────────────────────────┬─────────────────────────────────────────────┐
    │ Concept                 │ Plain-English                               │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ ReleaseNotes            │ The full release document: title, body,     │
    │                         │ and per-package summaries.                  │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ PackageSummary          │ One package's changes: name, old version,   │
    │                         │ new version, and its changelog.             │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ Template rendering      │ Uses Python string.Template for simple      │
    │                         │ variable substitution. No external deps.    │
    └─────────────────────────┴─────────────────────────────────────────────┘

Release notes generation flow::

    ReleaseManifest
         │
         ▼
    For each bumped package:
        generate_changelog(since_tag=last_tag, paths=[pkg.path])
         │
         ▼
    Combine into ReleaseNotes
         │
         ▼
    render_release_notes() → markdown string

Usage::

    from releasekit.release_notes import generate_release_notes

    notes = generate_release_notes(
        manifest=manifest,
        vcs=git_backend,
        tag_format='{name}-v{version}',
    )
    print(notes.render())
"""

from __future__ import annotations

from dataclasses import dataclass, field
from string import Template

from releasekit.backends.vcs import VCS
from releasekit.changelog import (
    Changelog,
    generate_changelog,
    render_changelog,
)
from releasekit.logging import get_logger
from releasekit.tags import format_tag
from releasekit.versions import ReleaseManifest

logger = get_logger(__name__)


@dataclass(frozen=True)
class PackageSummary:
    """Summary of changes for one package in a release.

    Attributes:
        name: Package name.
        old_version: Version before the bump.
        new_version: Version after the bump.
        changelog: Changelog for this package's changes.
    """

    name: str
    old_version: str
    new_version: str
    changelog: Changelog


@dataclass
class ReleaseNotes:
    """Complete release notes for one release.

    Attributes:
        version: Umbrella version string.
        title: Release title.
        summaries: Per-package summaries.
        date: Optional date string.
        preamble: Optional text before the package summaries.
    """

    version: str
    title: str = ''
    summaries: list[PackageSummary] = field(default_factory=list)
    date: str = ''
    preamble: str = ''


_DEFAULT_TEMPLATE = Template("""\
# $title

$preamble

## Packages

$package_sections
""")

_PACKAGE_TEMPLATE = Template("""\
### $name ($old_version → $new_version)

$changelog
""")


def render_release_notes(
    notes: ReleaseNotes,
    *,
    template: Template | None = None,
    package_template: Template | None = None,
) -> str:
    """Render release notes as a markdown string.

    Args:
        notes: The release notes to render.
        template: Optional custom template for the overall document.
        package_template: Optional custom template for each package.

    Returns:
        A markdown string.
    """
    tmpl = template or _DEFAULT_TEMPLATE
    pkg_tmpl = package_template or _PACKAGE_TEMPLATE

    package_sections: list[str] = []
    for summary in notes.summaries:
        changelog_md = render_changelog(summary.changelog).strip()
        section = pkg_tmpl.safe_substitute(
            name=summary.name,
            old_version=summary.old_version,
            new_version=summary.new_version,
            changelog=changelog_md,
        )
        package_sections.append(section.strip())

    title = notes.title or f'Release {notes.version}'
    preamble = notes.preamble or f'{len(notes.summaries)} package(s) updated.'

    result = tmpl.safe_substitute(
        title=title,
        version=notes.version,
        date=notes.date,
        preamble=preamble,
        package_sections='\n\n'.join(package_sections),
    )

    return result.strip() + '\n'


async def generate_release_notes(
    *,
    manifest: ReleaseManifest,
    vcs: VCS,
    tag_format: str = '{name}-v{version}',
    package_paths: dict[str, str] | None = None,
    exclude_types: frozenset[str] | None = None,
    date: str = '',
    title: str = '',
    preamble: str = '',
) -> ReleaseNotes:
    """Generate umbrella release notes from a manifest.

    For each bumped package, generates a per-package changelog by
    reading commits since that package's last tag.

    Args:
        manifest: Release manifest with bumped packages.
        vcs: VCS backend for git operations.
        tag_format: Tag format template.
        package_paths: Optional mapping of package name to directory
            path. If provided, changelogs are scoped to each package's
            directory.
        exclude_types: Commit types to exclude from changelogs.
        date: Optional date string.
        title: Optional release title.
        preamble: Optional preamble text.

    Returns:
        A :class:`ReleaseNotes` with per-package summaries.
    """
    summaries: list[PackageSummary] = []
    paths_map = package_paths or {}

    for pkg in manifest.bumped:
        since_tag = format_tag(tag_format, name=pkg.name, version=pkg.old_version)

        effective_since: str | None = since_tag
        if not await vcs.tag_exists(since_tag):
            logger.info(
                'release_notes_no_previous_tag',
                package=pkg.name,
                tag=since_tag,
            )
            effective_since = None

        pkg_path = paths_map.get(pkg.name)
        changelog = await generate_changelog(
            vcs=vcs,
            version=pkg.new_version,
            since_tag=effective_since,
            paths=[pkg_path] if pkg_path else None,
            exclude_types=exclude_types,
        )

        summaries.append(
            PackageSummary(
                name=pkg.name,
                old_version=pkg.old_version,
                new_version=pkg.new_version,
                changelog=changelog,
            )
        )

    logger.info(
        'release_notes_generated',
        version=manifest.umbrella_tag or 'unknown',
        packages=len(summaries),
    )

    return ReleaseNotes(
        version=manifest.umbrella_tag or 'unknown',
        title=title,
        summaries=summaries,
        date=date,
        preamble=preamble,
    )


__all__ = [
    'PackageSummary',
    'ReleaseNotes',
    'generate_release_notes',
    'render_release_notes',
]
