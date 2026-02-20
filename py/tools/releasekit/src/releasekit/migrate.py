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

r"""Migration from alternative release tools to releasekit.

Provides a ``MigrationSource`` protocol and concrete implementations
for converting configuration from alternative release tools into
``releasekit.toml`` format.  Also contains tag classification utilities
reused by :mod:`releasekit.init` for bootstrap SHA detection.

Key Concepts (ELI5)::

    ┌─────────────────────────┬─────────────────────────────────────────────┐
    │ Concept                 │ Plain-English                               │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ MigrationSource         │ Protocol for reading config from an         │
    │                         │ alternative tool and converting it.         │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ ReleasePleaseSource     │ Reads .release-please-manifest.json and     │
    │                         │ release-please-config.json.                │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ ClassifiedTag           │ A git tag matched to a workspace and        │
    │                         │ optionally a package, with its version      │
    │                         │ and commit SHA resolved.                    │
    └─────────────────────────┴─────────────────────────────────────────────┘

Migration flow::

    releasekit migrate --from release-please [--dry-run]
         │
         ├── source.detect(root)       → True if config files found
         ├── source.convert(root)      → releasekit.toml TOML string
         └── write releasekit.toml     → (or print if --dry-run)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import tomlkit

from releasekit.backends.vcs import VCS
from releasekit.config import CONFIG_FILENAME, WorkspaceConfig
from releasekit.logging import get_logger
from releasekit.tags import parse_tag

logger = get_logger(__name__)

# Regex for a valid semver version (simplified — major.minor.patch with
# optional pre-release).
_SEMVER_CMP_RE = re.compile(
    r'^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)'
    r'(?:-(?P<pre>[a-zA-Z0-9.]+))?$',
)


def _semver_sort_key(version: str) -> tuple[int, int, int, bool, str]:
    """Return a sort key for semver comparison.

    Pre-release versions sort *before* their release counterpart
    (e.g. ``1.0.0-rc.1 < 1.0.0``).

    Args:
        version: A semver version string.

    Returns:
        A tuple suitable for ``sorted()`` / ``max()`` comparison.
    """
    m = _SEMVER_CMP_RE.match(version)
    if m is None:
        return (0, 0, 0, False, version)
    pre = m.group('pre') or ''
    # No pre-release → sorts after any pre-release at the same version.
    return (
        int(m.group('major')),
        int(m.group('minor')),
        int(m.group('patch')),
        pre == '',  # True (1) for release, False (0) for pre-release
        pre,
    )


@dataclass
class ClassifiedTag:
    """A git tag classified against a workspace configuration.

    Attributes:
        tag: The raw git tag string (e.g. ``"genkit@0.5.0"``).
        workspace_label: The workspace label it matched (e.g. ``"py"``).
        package_name: Package name if it's a per-package tag, or empty
            string if it's an umbrella tag.
        version: The parsed version string.
        commit_sha: The commit SHA the tag points to.
        is_umbrella: ``True`` if this matched the umbrella tag format.
    """

    tag: str
    workspace_label: str
    package_name: str = ''
    version: str = ''
    commit_sha: str = ''
    is_umbrella: bool = False


@dataclass
class MigrationReport:
    """Result of a migration scan.

    Attributes:
        classified: Tags successfully matched to a workspace.
        unclassified: Tags that could not be matched to any workspace.
        latest_per_workspace: The latest classified tag per workspace label.
        bootstrap_shas: The ``bootstrap_sha`` value to write per workspace.
        written: Whether ``releasekit.toml`` was actually modified.
    """

    classified: list[ClassifiedTag] = field(default_factory=list)
    unclassified: list[str] = field(default_factory=list)
    latest_per_workspace: dict[str, ClassifiedTag] = field(default_factory=dict)
    bootstrap_shas: dict[str, str] = field(default_factory=dict)
    written: bool = False


def classify_tags(
    tags: list[str],
    workspaces: dict[str, WorkspaceConfig],
) -> tuple[list[ClassifiedTag], list[str]]:
    """Classify git tags against workspace configurations.

    For each tag, tries to match it against the ``tag_format`` and
    ``umbrella_tag`` of every workspace. The first match wins.

    Args:
        tags: Raw git tag strings.
        workspaces: Workspace configs keyed by label.

    Returns:
        A tuple of (classified_tags, unclassified_tags).
    """
    classified: list[ClassifiedTag] = []
    unclassified: list[str] = []

    for tag in tags:
        matched = False
        for label, ws in workspaces.items():
            # Try per-package tag format.
            parsed = parse_tag(tag, ws.tag_format)
            if parsed is not None:
                name, version = parsed
                classified.append(
                    ClassifiedTag(
                        tag=tag,
                        workspace_label=label,
                        package_name=name,
                        version=version,
                        is_umbrella=False,
                    )
                )
                matched = True
                break

            # Try umbrella tag format.
            parsed = parse_tag(tag, ws.umbrella_tag)
            if parsed is not None:
                _name, version = parsed
                classified.append(
                    ClassifiedTag(
                        tag=tag,
                        workspace_label=label,
                        package_name='',
                        version=version,
                        is_umbrella=True,
                    )
                )
                matched = True
                break

            # Try secondary tag format if configured.
            if ws.secondary_tag_format:
                parsed = parse_tag(tag, ws.secondary_tag_format)
                if parsed is not None:
                    name, version = parsed
                    classified.append(
                        ClassifiedTag(
                            tag=tag,
                            workspace_label=label,
                            package_name=name,
                            version=version,
                            is_umbrella=False,
                        )
                    )
                    matched = True
                    break

        if not matched:
            unclassified.append(tag)

    return classified, unclassified


def pick_latest(
    classified: list[ClassifiedTag],
) -> dict[str, ClassifiedTag]:
    """Pick the latest tag per workspace by semver.

    Args:
        classified: All classified tags.

    Returns:
        Dict mapping workspace label to the highest-version tag.
    """
    latest: dict[str, ClassifiedTag] = {}
    for ct in classified:
        key = ct.workspace_label
        if key not in latest or _semver_sort_key(ct.version) > _semver_sort_key(latest[key].version):
            latest[key] = ct
    return latest


async def resolve_commit_shas(
    classified: list[ClassifiedTag],
    vcs: VCS,
) -> None:
    """Resolve the commit SHA for each classified tag (in-place).

    Args:
        classified: Tags to resolve. Each tag's ``commit_sha`` is
            updated in place.
        vcs: VCS backend for resolving tags to commits.
    """
    for ct in classified:
        if not ct.commit_sha:
            ct.commit_sha = await vcs.tag_commit_sha(ct.tag)


def write_bootstrap_sha(
    config_path: Path,
    workspace_label: str,
    bootstrap_sha: str,
) -> None:
    """Write ``bootstrap_sha`` into a ``releasekit.toml`` file.

    Uses tomlkit for comment-preserving edits.

    Args:
        config_path: Path to ``releasekit.toml``.
        workspace_label: The workspace section to update.
        bootstrap_sha: The SHA to write.
    """
    text = config_path.read_text(encoding='utf-8')
    doc = tomlkit.parse(text)

    ws_table = doc.get('workspace')
    if ws_table is None:
        ws_table = tomlkit.table()
        doc['workspace'] = ws_table

    section = ws_table.get(workspace_label)
    if section is None:
        section = tomlkit.table()
        ws_table[workspace_label] = section

    section['bootstrap_sha'] = bootstrap_sha
    config_path.write_text(tomlkit.dumps(doc), encoding='utf-8')


# MigrationSource protocol + implementations


@runtime_checkable
class MigrationSource(Protocol):
    """Protocol for reading config from an alternative release tool.

    Each implementation knows how to detect and convert one tool's
    configuration into ``releasekit.toml`` format.
    """

    @property
    def name(self) -> str:
        """Human-readable name of the source tool."""
        ...  # pragma: no cover

    def detect(self, root: Path) -> bool:
        """Return True if this tool's config files exist at ``root``."""
        ...  # pragma: no cover

    def convert(self, root: Path) -> str:
        """Read the tool's config and return a ``releasekit.toml`` string."""
        ...  # pragma: no cover


class ReleasePleaseSource:
    """Migration source for release-please.

    Reads:
    - ``.release-please-manifest.json`` — package paths → versions
    - ``release-please-config.json`` — packages config, tag patterns

    Generates a ``releasekit.toml`` with workspace sections, groups,
    and tag format derived from the release-please configuration.
    """

    MANIFEST = '.release-please-manifest.json'
    CONFIG = 'release-please-config.json'

    @property
    def name(self) -> str:
        """Return source name."""
        return 'release-please'

    def detect(self, root: Path) -> bool:
        """Return True if release-please config files exist."""
        return (root / self.MANIFEST).exists() or (root / self.CONFIG).exists()

    def convert(self, root: Path) -> str:
        """Convert release-please config to releasekit.toml."""
        manifest = self._read_json(root / self.MANIFEST)
        config = self._read_json(root / self.CONFIG)

        doc = tomlkit.document()
        doc.add(tomlkit.comment('Migrated from release-please by releasekit migrate'))
        doc.add('forge', tomlkit.item('github'))
        doc.add(tomlkit.nl())

        # Extract packages from config or manifest.
        rp_packages: dict[str, Any] = config.get('packages', {})
        if not rp_packages and manifest:
            rp_packages = {path: {} for path in manifest if path != '.'}

        # Determine tag format from release-please config.
        include_component = config.get('include-component-in-tag', True)
        tag_separator = config.get('tag-separator', '-')
        if include_component:
            tag_format = '{name}' + tag_separator + 'v{version}'
        else:
            tag_format = 'v{version}'

        # Build workspace section.
        ws_table = tomlkit.table(is_super_table=True)
        ws_inner = tomlkit.table()
        ws_inner.add('ecosystem', tomlkit.item('python'))
        ws_inner.add('tag_format', tomlkit.item(tag_format))
        ws_inner.add('umbrella_tag', tomlkit.item('v{version}'))
        ws_inner.add('changelog', tomlkit.item(True))

        # Build groups from package paths.
        if rp_packages:
            groups = self._detect_groups(rp_packages)
            if groups:
                ws_inner.add(tomlkit.nl())
                groups_table = tomlkit.table()
                for group_name, patterns in sorted(groups.items()):
                    groups_table.add(group_name, tomlkit.item(patterns))
                ws_inner.add('groups', groups_table)

        ws_table.add('py', ws_inner)
        doc.add('workspace', ws_table)

        return tomlkit.dumps(doc)

    def _read_json(self, path: Path) -> dict[str, Any]:
        """Read a JSON file, returning empty dict if missing."""
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, OSError):
            logger.warning('migrate_json_read_error', path=str(path))
            return {}

    def _detect_groups(
        self,
        rp_packages: dict[str, Any],
    ) -> dict[str, list[str]]:
        """Detect groups from release-please package paths."""
        by_parent: dict[str, list[str]] = {}
        for pkg_path in rp_packages:
            parts = Path(pkg_path).parts
            if len(parts) >= 2:
                parent = parts[0]
                name = parts[-1]
                by_parent.setdefault(parent, []).append(name)
            elif pkg_path != '.':
                by_parent.setdefault('root', []).append(pkg_path)

        groups: dict[str, list[str]] = {}
        for parent, names in sorted(by_parent.items()):
            if names:
                groups[parent] = sorted(names)
        return groups


# Registry of known migration sources.
MIGRATION_SOURCES: dict[str, MigrationSource] = {
    'release-please': ReleasePleaseSource(),
}


@dataclass
class ToolMigrationReport:
    """Result of migrating from an alternative release tool.

    Attributes:
        source_name: Name of the source tool.
        detected: Whether the source tool's config was found.
        toml_content: Generated releasekit.toml content.
        written: Whether the file was actually written.
        config_path: Path where config was (or would be) written.
    """

    source_name: str = ''
    detected: bool = False
    toml_content: str = ''
    written: bool = False
    config_path: Path | None = None


def migrate_from_source(
    root: Path,
    source: MigrationSource,
    *,
    dry_run: bool = False,
    force: bool = False,
) -> ToolMigrationReport:
    """Migrate from an alternative release tool to releasekit.

    Args:
        root: Repository root directory.
        source: The migration source to use.
        dry_run: If ``True``, compute everything but don't write files.
        force: If ``True``, overwrite existing ``releasekit.toml``.

    Returns:
        A :class:`ToolMigrationReport` with the results.
    """
    report = ToolMigrationReport(source_name=source.name)
    config_path = root / CONFIG_FILENAME
    report.config_path = config_path

    if not source.detect(root):
        logger.info(
            'migrate_source_not_found',
            source=source.name,
            message=f'No {source.name} configuration found.',
        )
        return report

    report.detected = True
    report.toml_content = source.convert(root)

    if not report.toml_content:
        logger.warning('migrate_empty_conversion', source=source.name)
        return report

    if config_path.exists() and not force:
        logger.info(
            'migrate_config_exists',
            path=str(config_path),
            message=f'{CONFIG_FILENAME} already exists (use --force to overwrite).',
        )
        return report

    if not dry_run:
        config_path.write_text(report.toml_content, encoding='utf-8')
        report.written = True
        logger.info('migrate_written', path=str(config_path), source=source.name)

    return report
