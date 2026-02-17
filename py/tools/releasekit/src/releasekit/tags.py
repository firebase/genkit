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

r"""Git tag creation and platform release management for publish pipelines.

Creates per-package tags and an umbrella release tag after a successful
publish run. Supports two modes:

- **Local mode** (default): Creates tags and pushes them after all
  packages are published. Optionally creates a platform release if
  the forge backend is available.

- **CI mode** (``--publish-from=ci``): Creates a *draft* platform release
  with the release manifest as an asset. A downstream CI workflow
  downloads the manifest, publishes packages, then promotes the
  draft to published.

Key Concepts (ELI5)::

    ┌─────────────────────────┬─────────────────────────────────────────────┐
    │ Concept                 │ Plain-English                               │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ Per-package tag         │ One tag per published package, e.g.         │
    │                         │ ``genkit-v0.5.0``.                          │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ Umbrella tag            │ One tag for the entire release, e.g.        │
    │                         │ ``v0.5.0``.                                 │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ TagResult               │ Collects created/skipped/failed tags.       │
    └─────────────────────────┴─────────────────────────────────────────────┘

Tag creation flow::

    publish_workspace completes
         │
         ▼
    create_tags(manifest, vcs, forge, config)
         │
         ├── for each bumped package:
         │     ├── format tag: tag_format.format(name=..., version=...)
         │     ├── tag_exists? → skip (log warning)
         │     └── vcs.tag(tag_name, message=...)
         │
         ├── umbrella tag:
         │     ├── format: umbrella_tag.format(version=...)
         │     ├── tag_exists? → skip (log warning)
         │     └── vcs.tag(tag_name, message=...)
         │
         ├── vcs.push(tags=True) — push all tags at once
         │
         └── forge available?
               ├── yes → create_release(umbrella_tag, body=notes, draft=ci_mode)
               └── no  → log info, skip (graceful degradation)

Dual-mode release creation::

    Local mode (publish_from=local):
       1. Tags created AFTER all packages published
       2. Push tags
       3. Create platform release (published, not draft)

    CI mode (publish_from=ci):
       1. Tags created BEFORE publishing (version job)
       2. Draft platform release with manifest.json asset
       3. CI workflow downloads manifest, publishes, promotes

Usage::

    from releasekit.tags import create_tags

    result = create_tags(
        manifest=manifest,
        vcs=git_backend,
        forge=forge_backend,
        tag_format='{name}-v{version}',
        umbrella_tag_format='v{version}',
        release_body='## Changes\\n...',
        publish_from='local',
        dry_run=False,
    )
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from pathlib import Path

from releasekit.backends.forge import Forge
from releasekit.backends.vcs import VCS
from releasekit.logging import get_logger
from releasekit.versions import ReleaseManifest, resolve_umbrella_version

logger = get_logger(__name__)

# Semver-ish pattern: digits.digits.digits with optional pre-release/build.
_SEMVER_RE = re.compile(r'(\d+\.\d+\.\d+(?:[-+].+)?)')

# Characters and patterns forbidden in git ref names (see git-check-ref-format).
_INVALID_TAG_PATTERNS: list[tuple[str, str]] = [
    ('//', 'contains consecutive slashes'),
    ('..', 'contains ..'),
    (' ', 'contains space'),
    ('~', 'contains ~'),
    ('^', 'contains ^'),
    (':', 'contains :'),
    ('\\', 'contains a backslash'),
    ('@{', 'contains an invalid sequence "@{"'),
    ('/.', 'contains an invalid sequence "/.", path component starts with dot'),
]


def validate_tag_name(tag: str) -> str | None:
    """Validate that a tag name is a valid git ref.

    Returns ``None`` if valid, or an error description if invalid.
    This catches common format-string bugs (e.g. empty ``{label}``
    producing a leading ``/``) before any git operations happen.

    Args:
        tag: The tag name to validate.

    Returns:
        ``None`` if the tag is valid, otherwise a human-readable
        error message explaining why it is invalid.
    """
    if not tag:
        return 'tag name is empty'
    if tag == '@':
        return 'tag name cannot be "@"'
    if tag.startswith('.'):
        return f'starts with . (got {tag!r})'
    if tag.startswith('/'):
        return f'starts with / (got {tag!r}) — likely a missing {{label}} value'
    if tag.endswith('/'):
        return f'ends with / (got {tag!r})'
    if tag.endswith('.'):
        return f'ends with . (got {tag!r})'
    if tag.endswith('.lock'):
        return f'ends with .lock (got {tag!r})'
    for pattern, desc in _INVALID_TAG_PATTERNS:
        if pattern in tag:
            return f'{desc} (got {tag!r})'
    return None


@dataclass(frozen=True)
class TagResult:
    """Result of a tag creation run.

    Attributes:
        created: Tag names that were successfully created.
        skipped: Tag names that already existed (not overwritten).
        failed: Mapping of tag name to error message for failures.
        pushed: Whether tags were pushed to the remote.
        release_url: URL of the platform release, if created.
    """

    created: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)
    pushed: bool = False
    release_url: str = ''

    @property
    def ok(self) -> bool:
        """Return True if no tag operations failed."""
        return not self.failed


def format_tag(
    tag_format: str,
    *,
    name: str = '',
    version: str = '',
    label: str = '',
) -> str:
    """Format a tag string from a template.

    Args:
        tag_format: Format string with ``{name}``, ``{version}``, and
            ``{label}`` placeholders.  ``{label}`` is the workspace
            label (e.g. ``py``, ``js``) and is useful in monorepos
            where multiple ecosystems share a single repository.
        name: Package name (for per-package tags).
        version: Version string.
        label: Workspace label.

    Returns:
        The formatted tag string.

    Examples::

        >>> format_tag('{name}-v{version}', name='genkit', version='0.5.0')
        'genkit-v0.5.0'
        >>> format_tag('{name}@{version}', name='@genkit-ai/core', version='1.2.3')
        '@genkit-ai/core@1.2.3'
    """
    return tag_format.format(name=name, version=version, label=label)


def parse_tag(
    tag: str,
    tag_format: str = '{name}-v{version}',
) -> tuple[str, str] | None:
    """Reverse-parse a tag string into (name, version).

    Handles both simple formats (``genkit-v0.5.0``) and scoped npm
    formats (``@genkit-ai/core@1.2.3``).

    The function converts the ``tag_format`` into a regex by replacing
    ``{name}`` and ``{version}`` with capture groups, then matches
    against the tag string.

    Args:
        tag: The tag string to parse.
        tag_format: The format template used to create the tag.

    Returns:
        A ``(name, version)`` tuple, or ``None`` if the tag does not
        match the format.

    Examples::

        >>> parse_tag('genkit-v0.5.0', '{name}-v{version}')
        ('genkit', '0.5.0')
        >>> parse_tag('@genkit-ai/core@1.2.3', '{name}@{version}')
        ('@genkit-ai/core', '1.2.3')
        >>> parse_tag('v0.5.0', '{name}-v{version}') is None
        True
    """
    # Build a regex from the format string.
    # Escape everything except our placeholders.
    escaped = re.escape(tag_format)
    # Replace escaped placeholders with capture groups.
    # {version} matches semver; {name} matches everything else greedily.
    pattern = escaped.replace(r'\{version\}', r'(' + _SEMVER_RE.pattern + r')')
    pattern = pattern.replace(r'\{name\}', r'(.+?)')
    pattern = pattern.replace(r'\{label\}', r'(?:.+?)')
    pattern = f'^{pattern}$'

    m = re.match(pattern, tag)
    if m is None:
        return None

    groups = m.groups()
    # The regex produces: (name_group, version_outer, version_inner) or
    # just (version_outer, version_inner) if no {name} placeholder.
    # We need to figure out which groups are name vs version.
    if '{name}' in tag_format:
        # First group is name, second is version (outer capture).
        return (groups[0], groups[1])
    # No name in format — return empty name.
    return ('', groups[0])


async def create_tags(
    *,
    manifest: ReleaseManifest,
    vcs: VCS,
    forge: Forge | None = None,
    tag_format: str = '{name}-v{version}',
    secondary_tag_format: str = '',
    umbrella_tag_format: str = 'v{version}',
    core_package: str = '',
    label: str = '',
    release_body: str = '',
    release_title: str | None = None,
    manifest_path: Path | None = None,
    provenance_path: Path | None = None,
    publish_from: str = 'local',
    prerelease: bool = False,
    dry_run: bool = False,
) -> TagResult:
    """Create per-package tags, an umbrella tag, and optionally a platform release.

    Per-package tags use ``tag_format`` (e.g. ``genkit-v0.5.0``).
    If ``secondary_tag_format`` is set, a second tag is also created
    per package (e.g. ``@genkit-ai/core@1.2.3`` for npm-style scoped tags).
    The umbrella tag uses ``umbrella_tag_format`` (e.g. ``v0.5.0``).

    If a tag already exists, it is skipped with a warning (not
    overwritten). This makes the function idempotent for resume
    scenarios.

    If ``forge`` is provided and available, a platform release is created:

    - **Local mode**: Published release with ``release_body``.
    - **CI mode**: Draft release with ``manifest_path`` as an asset.

    Args:
        manifest: Release manifest with per-package version records.
        vcs: VCS backend for tag operations.
        forge: Optional forge backend for platform releases. If ``None``
            or ``forge.is_available()`` returns ``False``, release
            creation is silently skipped.
        tag_format: Per-package tag format string.
        secondary_tag_format: Optional second per-package tag format.
            Useful for dual-tagging (e.g. ``{name}-v{version}`` and
            ``{name}@{version}`` simultaneously). Empty string to disable.
        umbrella_tag_format: Umbrella tag format string.
        core_package: Name of the core package whose version determines
            the umbrella tag. Falls back to the first bumped package.
        label: Workspace label for the ``{label}`` placeholder.
        release_body: Markdown body for the platform release.
        release_title: Release title. Defaults to the umbrella tag.
        manifest_path: Path to the manifest JSON file. Attached as a
            release asset in CI mode.
        provenance_path: Path to the SLSA provenance file
            (``.intoto.jsonl``). Attached as a release asset if present.
        publish_from: ``"local"`` or ``"ci"``. Controls whether the
            release is published or draft.
        prerelease: Whether to mark the release as a prerelease.
        dry_run: Preview mode — log actions without executing.

    Returns:
        A :class:`TagResult` with created/skipped/failed tags and
        optional release URL.
    """
    result = TagResult()
    bumped = manifest.bumped

    if not bumped:
        logger.info('tags_skip_no_bumped', reason='No packages were bumped')
        return result

    umbrella_version = resolve_umbrella_version(bumped, core_package=core_package)
    umbrella_tag = format_tag(umbrella_tag_format, version=umbrella_version, label=label)

    # ── Build a tag plan: generate all tag names once, validate, then create. ──
    # Each entry is (tag_name, message, package_name, is_secondary).
    tag_plan: list[tuple[str, str, str, bool]] = []
    for pkg in bumped:
        primary = format_tag(tag_format, name=pkg.name, version=pkg.new_version, label=label)
        msg = f'Release {pkg.name} v{pkg.new_version}'
        tag_plan.append((primary, msg, pkg.name, False))

        if secondary_tag_format:
            sec = format_tag(secondary_tag_format, name=pkg.name, version=pkg.new_version, label=label)
            if sec != primary:  # Avoid duplicate if formats resolve identically.
                tag_plan.append((sec, msg, pkg.name, True))

    # ── Fail-fast: validate all planned tag names before creating any. ──
    # This prevents the bug where silently-malformed tags (e.g. /genkit-v0.6.0
    # from an empty {label}) are created locally, "pushed" without error, but
    # never actually reach the remote because git rejects invalid ref names.
    all_planned = [umbrella_tag] + [t[0] for t in tag_plan]
    validation_errors: list[str] = []
    for planned in all_planned:
        err = validate_tag_name(planned)
        if err is not None:
            validation_errors.append(f'{planned}: {err}')

    if validation_errors:
        msg = f'{len(validation_errors)} invalid tag name(s):\n' + '\n'.join(f'  - {e}' for e in validation_errors)
        logger.error('tag_validation_failed', errors=validation_errors)
        raise ValueError(msg)

    # ── Create tags from the plan. ──
    for tag_name, tag_message, package_name, is_secondary in tag_plan:
        if await vcs.tag_exists(tag_name):
            result.skipped.append(tag_name)
            event = 'secondary_tag_exists_skip' if is_secondary else 'tag_exists_skip'
            logger.warning(event, tag=tag_name, package=package_name)
        else:
            try:
                await vcs.tag(tag_name, message=tag_message, dry_run=dry_run)
                result.created.append(tag_name)
                event = 'secondary_tag_created' if is_secondary else 'tag_created'
                logger.info(event, tag=tag_name, package=package_name)
            except Exception as exc:
                result.failed[tag_name] = str(exc)
                event = 'secondary_tag_create_failed' if is_secondary else 'tag_create_failed'
                logger.error(event, tag=tag_name, package=package_name, error=str(exc))

    umbrella_message = f'Release v{umbrella_version} ({len(bumped)} packages)'

    if await vcs.tag_exists(umbrella_tag):
        result.skipped.append(umbrella_tag)
        logger.warning('umbrella_tag_exists_skip', tag=umbrella_tag)
    else:
        try:
            await vcs.tag(umbrella_tag, message=umbrella_message, dry_run=dry_run)
            result.created.append(umbrella_tag)
            logger.info(
                'umbrella_tag_created',
                tag=umbrella_tag,
                version=umbrella_version,
                packages=len(bumped),
            )
        except Exception as exc:
            result.failed[umbrella_tag] = str(exc)
            logger.error(
                'umbrella_tag_create_failed',
                tag=umbrella_tag,
                error=str(exc),
            )

    if result.created and not result.failed:
        push_result = await vcs.push(tags=True, dry_run=dry_run)
        if not push_result.ok:
            raise RuntimeError(f'Failed to push tags to remote: {push_result.stderr.strip()}')
        # Mutate the frozen dataclass via object.__setattr__ for
        # the pushed flag — TagResult is frozen for safety but we
        # need to set this after the push succeeds.
        object.__setattr__(result, 'pushed', True)
        logger.info(
            'tags_pushed',
            count=len(result.created),
            tags=result.created,
        )

    await _create_release_if_available(
        forge=forge,
        umbrella_tag=umbrella_tag,
        umbrella_version=umbrella_version,
        bumped_count=len(bumped),
        release_body=release_body,
        release_title=release_title,
        manifest_path=manifest_path,
        provenance_path=provenance_path,
        publish_from=publish_from,
        prerelease=prerelease,
        dry_run=dry_run,
        result=result,
    )

    logger.info(
        'tags_summary',
        created=len(result.created),
        skipped=len(result.skipped),
        failed=len(result.failed),
        pushed=result.pushed,
        release_url=result.release_url or '(none)',
    )

    return result


async def _create_release_if_available(
    *,
    forge: Forge | None,
    umbrella_tag: str,
    umbrella_version: str,
    bumped_count: int,
    release_body: str,
    release_title: str | None,
    manifest_path: Path | None,
    provenance_path: Path | None = None,
    publish_from: str,
    prerelease: bool,
    dry_run: bool,
    result: TagResult,
) -> None:
    """Create a platform release if the forge is available.

    Separated from :func:`create_tags` for testability and clarity.

    In local mode, creates a published release.
    In CI mode, creates a draft release with the manifest as an asset.

    Args:
        forge: Forge backend (may be None).
        umbrella_tag: The umbrella tag for the release.
        umbrella_version: Version string for the title.
        bumped_count: Number of bumped packages (for title).
        release_body: Markdown body.
        release_title: Optional custom title.
        manifest_path: Path to manifest JSON (CI asset).
        provenance_path: Path to SLSA provenance file (release asset).
        publish_from: ``"local"`` or ``"ci"``.
        prerelease: Mark as prerelease.
        dry_run: Preview mode.
        result: TagResult to update with the release URL.
    """
    if forge is None:
        logger.info('release_skip_no_forge', reason='No forge backend provided')
        return

    if not await forge.is_available():
        logger.info(
            'release_skip_forge_unavailable',
            reason='Forge CLI not installed or not authenticated. Skipping release creation.',
            hint='Install and authenticate: gh auth login',
        )
        return

    is_ci = publish_from == 'ci'
    title = release_title or f'v{umbrella_version} ({bumped_count} packages)'

    # In CI mode, attach the manifest as a release asset.
    assets: list[Path] = []
    if is_ci and manifest_path is not None and await asyncio.to_thread(manifest_path.exists):
        assets.append(manifest_path)

    # Attach SLSA provenance file as a release asset (all modes).
    if provenance_path is not None and await asyncio.to_thread(provenance_path.exists):
        assets.append(provenance_path)
        logger.info('provenance_asset_attached', path=str(provenance_path))

    try:
        await forge.create_release(
            tag=umbrella_tag,
            title=title,
            body=release_body,
            draft=is_ci,
            prerelease=prerelease,
            assets=assets if assets else None,
            dry_run=dry_run,
        )
        # Construct a plausible URL for logging.
        release_url = f'(draft release for {umbrella_tag})' if is_ci else f'(release {umbrella_tag})'
        object.__setattr__(result, 'release_url', release_url)
        logger.info(
            'release_created',
            tag=umbrella_tag,
            draft=is_ci,
            prerelease=prerelease,
            assets=len(assets),
        )
    except Exception as exc:
        # Release creation failure is non-fatal — tags are already
        # pushed, so the release can be created manually.
        logger.error(
            'release_create_failed',
            tag=umbrella_tag,
            error=str(exc),
            hint='Create manually: gh release create <tag> --title <title>',
        )


async def delete_tags(
    *,
    manifest: ReleaseManifest,
    vcs: VCS,
    forge: Forge | None = None,
    tag_format: str = '{name}-v{version}',
    umbrella_tag_format: str = 'v{version}',
    label: str = '',
    remote: bool = True,
    dry_run: bool = False,
) -> TagResult:
    """Delete per-package tags and the umbrella tag (rollback).

    Used for rollback scenarios when a release needs to be undone.
    Deletes tags locally and optionally from the remote. Also deletes
    the associated platform release if the forge is available.

    Args:
        manifest: Release manifest with per-package version records.
        vcs: VCS backend for tag deletion.
        forge: Optional forge backend for release deletion.
        tag_format: Per-package tag format string.
        umbrella_tag_format: Umbrella tag format string.
        label: Workspace label for the ``{label}`` placeholder.
        remote: Also delete from the remote.
        dry_run: Preview mode — log actions without executing.

    Returns:
        A :class:`TagResult` where ``created`` contains deleted tags
        and ``skipped`` contains tags that didn't exist.
    """
    result = TagResult()
    bumped = manifest.bumped

    if not bumped:
        logger.info('delete_tags_skip_no_bumped')
        return result

    umbrella_version = bumped[0].new_version
    umbrella_tag = format_tag(umbrella_tag_format, version=umbrella_version, label=label)

    for pkg in bumped:
        tag_name = format_tag(tag_format, name=pkg.name, version=pkg.new_version, label=label)

        if not await vcs.tag_exists(tag_name):
            result.skipped.append(tag_name)
            logger.debug('delete_tag_not_found', tag=tag_name)
            continue

        try:
            await vcs.delete_tag(tag_name, remote=remote, dry_run=dry_run)
            result.created.append(tag_name)
            logger.info('tag_deleted', tag=tag_name, remote=remote)
        except Exception as exc:
            result.failed[tag_name] = str(exc)
            logger.error('tag_delete_failed', tag=tag_name, error=str(exc))

    if await vcs.tag_exists(umbrella_tag):
        try:
            await vcs.delete_tag(umbrella_tag, remote=remote, dry_run=dry_run)
            result.created.append(umbrella_tag)
            logger.info('umbrella_tag_deleted', tag=umbrella_tag, remote=remote)
        except Exception as exc:
            result.failed[umbrella_tag] = str(exc)
            logger.error('umbrella_tag_delete_failed', tag=umbrella_tag, error=str(exc))
    else:
        result.skipped.append(umbrella_tag)

    if forge is not None and await forge.is_available():
        try:
            await forge.delete_release(umbrella_tag, dry_run=dry_run)
            logger.info('release_deleted', tag=umbrella_tag)
        except Exception as exc:
            logger.warning(
                'release_delete_failed',
                tag=umbrella_tag,
                error=str(exc),
            )

    return result


__all__ = [
    'TagResult',
    'create_tags',
    'delete_tags',
    'format_tag',
    'parse_tag',
    'validate_tag_name',
]
