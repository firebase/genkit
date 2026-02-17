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

"""Workspace configuration scaffolding for releasekit.

Auto-detects workspace structure, generates ``releasekit.toml``
configuration, updates ``.gitignore``, and scans existing git tags
to auto-set ``bootstrap_sha`` for mid-stream adoption.
Idempotent — safe to run multiple times.

Architecture::

    discover_packages()            .gitignore
         │                             │
         ▼                             ▼
    Detect groups              Append patterns
    (core, plugins,            (*.bak, .releasekit/)
     samples)
         │
         ▼
    Generate TOML              Show diff
    releasekit.toml            (if TTY)
         │                         │
         ▼                         ▼
    Write releasekit.toml      Prompt: apply? [Y/n]
         │
         ▼
    Scan git tags              Report discrepancies
    (classify, pick latest)    (unclassified, missing)
         │
         ▼
    Write bootstrap_sha
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import tomlkit

try:
    from rich.console import Console
    from rich.syntax import Syntax

    _HAS_RICH = True
except ImportError:
    _HAS_RICH = False

from releasekit.backends.vcs import VCS
from releasekit.config import CONFIG_FILENAME, DEFAULT_TOOLS, ReleaseConfig, WorkspaceConfig
from releasekit.logging import get_logger
from releasekit.migrate import (
    ClassifiedTag,
    classify_tags,
    pick_latest,
    resolve_commit_shas,
    write_bootstrap_sha,
)
from releasekit.workspace import Package, discover_packages

logger = get_logger(__name__)

# Patterns to add to .gitignore.
GITIGNORE_PATTERNS: list[str] = [
    '# releasekit backup files',
    '*.bak',
    '.releasekit/',
]


def detect_groups(packages: list[Package]) -> dict[str, list[str]]:
    """Auto-detect release groups from workspace directory structure.

    Groups are detected by the parent directory name of each package.
    For example, packages under ``packages/`` go into a ``"packages"``
    group, packages under ``plugins/`` go into ``"plugins"``, etc.

    If all packages in a group share a common prefix, a glob pattern
    is used instead of listing every name.

    Args:
        packages: Discovered workspace packages.

    Returns:
        A dict mapping group name to a list of glob patterns.
    """
    by_parent: dict[str, list[str]] = {}

    for pkg in packages:
        parent_name = pkg.path.parent.name
        by_parent.setdefault(parent_name, []).append(pkg.name)

    groups: dict[str, list[str]] = {}
    for parent_name, names in sorted(by_parent.items()):
        if not names:
            continue

        # If all names share a common prefix, use a glob pattern.
        prefixes = {n.rsplit('-', 1)[0] + '-*' for n in names if '-' in n}
        if len(prefixes) == 1 and len(names) > 1:
            groups[parent_name] = [prefixes.pop()]
        else:
            groups[parent_name] = sorted(names)

    return groups


def generate_config_toml(
    groups: dict[str, list[str]],
    *,
    workspace_label: str = 'py',
    ecosystem: str = 'python',
    exclude: list[str] | None = None,
    tag_format: str = '{name}-v{version}',
    umbrella_tag: str = 'v{version}',
) -> str:
    """Generate a ``releasekit.toml`` config file.

    Produces a config with global settings at the top level and
    per-workspace settings under ``[workspace.<label>]``.

    Args:
        groups: Package groups from :func:`detect_groups`.
        workspace_label: User-chosen label for the workspace section.
        ecosystem: Ecosystem identifier (e.g. ``"python"``, ``"js"``).
        exclude: Glob patterns for packages to exclude.
        tag_format: Per-package tag format.
        umbrella_tag: Umbrella tag format.

    Returns:
        A TOML string for ``releasekit.toml``.
    """
    doc = tomlkit.document()

    # Global settings.
    doc.add('forge', tomlkit.item('github'))
    doc.add(tomlkit.nl())

    # Workspace section.
    ws_table = tomlkit.table(is_super_table=True)
    ws_inner = tomlkit.table()
    ws_inner.add('ecosystem', tomlkit.item(ecosystem))

    # Only add tool if it differs from the ecosystem default.
    default_tool = DEFAULT_TOOLS.get(ecosystem, '')
    if default_tool:
        ws_inner.comment(f'tool defaults to "{default_tool}" for {ecosystem}')

    ws_inner.add('tag_format', tomlkit.item(tag_format))
    ws_inner.add('umbrella_tag', tomlkit.item(umbrella_tag))

    if exclude:
        ws_inner.add('exclude', tomlkit.item(exclude))

    ws_inner.add('changelog', tomlkit.item(True))
    ws_inner.add('smoke_test', tomlkit.item(True))

    if groups:
        ws_inner.add(tomlkit.nl())
        groups_table = tomlkit.table()
        for group_name, patterns in sorted(groups.items()):
            groups_table.add(group_name, tomlkit.item(patterns))
        ws_inner.add('groups', groups_table)

    ws_table.add(workspace_label, ws_inner)
    doc.add('workspace', ws_table)

    return tomlkit.dumps(doc)


def _detect_ecosystem(workspace_root: Path) -> tuple[str, str]:
    """Detect the ecosystem and suggest a workspace label.

    Checks for common workspace marker files to determine the
    ecosystem. Returns ``(ecosystem, label)`` where label is a
    short name suitable for ``[workspace.<label>]``.

    Falls back to ``("python", "py")`` if nothing is detected.

    Args:
        workspace_root: Path to the workspace root.

    Returns:
        A ``(ecosystem, label)`` tuple.
    """
    # Check for JS/TS workspace markers.
    if (workspace_root / 'pnpm-workspace.yaml').exists() or (workspace_root / 'package.json').exists():
        return ('js', 'js')

    # Check for Rust workspace markers.
    cargo_toml = workspace_root / 'Cargo.toml'
    if cargo_toml.exists():
        try:
            content = cargo_toml.read_text(encoding='utf-8')
            if '[workspace]' in content:
                return ('rust', 'rust')
        except OSError:
            pass

    # Check for Go workspace markers.
    if (workspace_root / 'go.work').exists() or (workspace_root / 'go.mod').exists():
        return ('go', 'go')

    # Check for Clojure workspace markers (before JVM — Clojure is distinct).
    if (workspace_root / 'project.clj').exists() or (workspace_root / 'deps.edn').exists():
        return ('clojure', 'clojure')

    # Check for Kotlin workspace markers (Kotlin DSL + kotlin plugin).
    if (workspace_root / 'settings.gradle.kts').exists() and (workspace_root / 'build.gradle.kts').exists():
        try:
            text = (workspace_root / 'build.gradle.kts').read_text(encoding='utf-8')
            if 'kotlin' in text.lower():
                return ('kotlin', 'kotlin')
        except OSError:
            pass

    # Check for Java/JVM workspace markers.
    if (
        (workspace_root / 'settings.gradle.kts').exists()
        or (workspace_root / 'settings.gradle').exists()
        or (workspace_root / 'build.gradle.kts').exists()
        or (workspace_root / 'build.gradle').exists()
    ):
        return ('java', 'java')
    if (workspace_root / 'pom.xml').exists():
        return ('java', 'java')

    # Check for Dart workspace markers.
    if (workspace_root / 'pubspec.yaml').exists():
        return ('dart', 'dart')

    # Default to Python (uv workspace).
    return ('python', 'py')


def _has_releasekit_config(workspace_root: Path) -> bool:
    """Return True if releasekit.toml already exists."""
    return (workspace_root / CONFIG_FILENAME).exists()


def scaffold_config(
    workspace_root: Path,
    *,
    dry_run: bool = False,
    force: bool = False,
) -> str:
    """Scaffold releasekit configuration for a workspace.

    This is the main entry point for ``releasekit init``. It:

    1. Discovers packages in the workspace
    2. Auto-detects release groups
    3. Generates ``releasekit.toml``
    4. Writes ``releasekit.toml`` (if not dry-run)
    5. Updates ``.gitignore`` (if not dry-run)

    Args:
        workspace_root: Path to the workspace root.
        dry_run: Preview changes without writing files.
        force: Overwrite existing ``releasekit.toml``.

    Returns:
        The generated TOML content (for display/preview).
    """
    if _has_releasekit_config(workspace_root) and not force:
        logger.info(
            '%s already exists in %s (use --force to overwrite)',
            CONFIG_FILENAME,
            workspace_root,
        )
        return ''

    packages = discover_packages(workspace_root)
    groups = detect_groups(packages)

    # Detect common sample patterns for exclusion.
    exclude: list[str] = []
    sample_patterns = [p.name for p in packages if 'sample' in str(p.path).lower()]
    if sample_patterns:
        # If many samples follow a pattern, use a glob.
        prefixes = set()
        for name in sample_patterns:
            parts = name.split('-')
            if len(parts) > 1:
                prefixes.add(parts[0] + '-*')
        if len(prefixes) == 1 and len(sample_patterns) > 2:
            exclude.append(prefixes.pop())

    # Detect ecosystem from workspace structure.
    ecosystem, workspace_label = _detect_ecosystem(workspace_root)

    toml_content = generate_config_toml(
        groups,
        workspace_label=workspace_label,
        ecosystem=ecosystem,
        exclude=exclude or None,
    )

    if dry_run:
        return toml_content

    # Write releasekit.toml.
    config_path = workspace_root / CONFIG_FILENAME
    config_path.write_text(toml_content, encoding='utf-8')
    logger.info('Created %s', config_path)

    # Update .gitignore.
    _update_gitignore(workspace_root / '.gitignore')
    logger.info('Updated %s', workspace_root / '.gitignore')

    return toml_content


def scaffold_multi_config(
    monorepo_root: Path,
    ecosystems: list[tuple[str, str, Path]],
    *,
    dry_run: bool = False,
    force: bool = False,
) -> str:
    """Scaffold releasekit configuration for a multi-ecosystem monorepo.

    Generates a single ``releasekit.toml`` at the monorepo root with
    one ``[workspace.<label>]`` section per detected ecosystem, each
    with its own groups discovered from that ecosystem's packages.

    Args:
        monorepo_root: Path to the monorepo root (where ``.git`` lives).
        ecosystems: List of ``(ecosystem, label, workspace_root)`` tuples.
            For example: ``[("python", "py", Path("/repo/py")),
            ("js", "js", Path("/repo/js"))]``.
        dry_run: Preview changes without writing files.
        force: Overwrite existing ``releasekit.toml``.

    Returns:
        The generated TOML content (for display/preview).
    """
    if _has_releasekit_config(monorepo_root) and not force:
        logger.info(
            '%s already exists in %s (use --force to overwrite)',
            CONFIG_FILENAME,
            monorepo_root,
        )
        return ''

    if not ecosystems:
        logger.warning('No ecosystems detected — cannot scaffold config.')
        return ''

    doc = tomlkit.document()

    # Global settings.
    doc.add('forge', tomlkit.item('github'))
    doc.add(tomlkit.nl())

    # One workspace section per ecosystem.
    ws_super = tomlkit.table(is_super_table=True)

    for ecosystem, label, ws_root in ecosystems:
        ws_inner = tomlkit.table()
        ws_inner.add('ecosystem', tomlkit.item(ecosystem))

        # Compute root relative to monorepo root (omit if same dir).
        try:
            rel_root = ws_root.relative_to(monorepo_root)
            if str(rel_root) != '.':
                ws_inner.add('root', tomlkit.item(str(rel_root)))
        except ValueError:
            ws_inner.add('root', tomlkit.item(str(ws_root)))

        default_tool = DEFAULT_TOOLS.get(ecosystem, '')
        if default_tool:
            ws_inner.comment(f'tool defaults to "{default_tool}" for {ecosystem}')

        ws_inner.add('tag_format', tomlkit.item('{name}-v{version}'))
        ws_inner.add('umbrella_tag', tomlkit.item(f'{label}/v{{version}}'))
        ws_inner.add('changelog', tomlkit.item(True))
        ws_inner.add('smoke_test', tomlkit.item(True))

        # Discover packages and detect groups for this ecosystem.
        try:
            packages = discover_packages(ws_root, ecosystem=ecosystem)
            groups = detect_groups(packages)

            # Detect sample patterns for exclusion.
            exclude: list[str] = []
            sample_patterns = [p.name for p in packages if 'sample' in str(p.path).lower()]
            if sample_patterns:
                prefixes = set()
                for name in sample_patterns:
                    parts = name.split('-')
                    if len(parts) > 1:
                        prefixes.add(parts[0] + '-*')
                if len(prefixes) == 1 and len(sample_patterns) > 2:
                    exclude.append(prefixes.pop())

            if exclude:
                ws_inner.add('exclude', tomlkit.item(exclude))

            if groups:
                ws_inner.add(tomlkit.nl())
                groups_table = tomlkit.table()
                for group_name, patterns in sorted(groups.items()):
                    groups_table.add(group_name, tomlkit.item(patterns))
                ws_inner.add('groups', groups_table)
        except Exception:  # noqa: BLE001
            # Package discovery may fail for ecosystems without backends.
            logger.info(
                'scaffold_discovery_skipped',
                ecosystem=ecosystem,
                label=label,
                message=f'Could not discover packages for {ecosystem} workspace.',
            )

        ws_super.add(label, ws_inner)

    doc.add('workspace', ws_super)

    toml_content = tomlkit.dumps(doc)

    if dry_run:
        return toml_content

    # Write releasekit.toml at monorepo root.
    config_path = monorepo_root / CONFIG_FILENAME
    config_path.write_text(toml_content, encoding='utf-8')
    logger.info('Created %s', config_path)

    # Update .gitignore.
    _update_gitignore(monorepo_root / '.gitignore')
    logger.info('Updated %s', monorepo_root / '.gitignore')

    return toml_content


def _update_gitignore(gitignore_path: Path) -> None:
    """Append releasekit patterns to .gitignore if not already present."""
    existing = ''
    if gitignore_path.exists():
        existing = gitignore_path.read_text(encoding='utf-8')

    lines_to_add: list[str] = []
    for pattern in GITIGNORE_PATTERNS:
        if pattern not in existing:
            lines_to_add.append(pattern)

    if not lines_to_add:
        return

    with gitignore_path.open('a', encoding='utf-8') as f:
        if existing and not existing.endswith('\n'):
            f.write('\n')
        f.write('\n')
        for line in lines_to_add:
            f.write(line + '\n')


@dataclass
class TagScanReport:
    """Result of scanning existing git tags during init.

    Attributes:
        classified: Tags successfully matched to a workspace.
        unclassified: Tags that could not be matched to any workspace.
        latest_per_workspace: The latest classified tag per workspace label.
        bootstrap_shas: The ``bootstrap_sha`` value written per workspace.
        discrepancies: Human-readable discrepancy messages.
        written: Whether ``releasekit.toml`` was modified with bootstrap SHAs.
        tags_created: Bootstrap tags created (tag name list).
        tags_skipped: Bootstrap tags skipped because they already exist.
    """

    classified: list[ClassifiedTag] = field(default_factory=list)
    unclassified: list[str] = field(default_factory=list)
    latest_per_workspace: dict[str, ClassifiedTag] = field(default_factory=dict)
    bootstrap_shas: dict[str, str] = field(default_factory=dict)
    discrepancies: list[str] = field(default_factory=list)
    written: bool = False
    tags_created: list[str] = field(default_factory=list)
    tags_skipped: list[str] = field(default_factory=list)


def _detect_discrepancies(
    classified: list[ClassifiedTag],
    unclassified: list[str],
    latest: dict[str, ClassifiedTag],
) -> list[str]:
    """Detect discrepancies in the tag landscape.

    Checks for:
    - Unclassified tags that don't match any workspace format.
    - Workspaces with only umbrella tags but no per-package tags.
    - Multiple tag formats detected for the same workspace.

    Args:
        classified: Successfully classified tags.
        unclassified: Tags that didn't match any workspace.
        latest: Latest tag per workspace.

    Returns:
        List of human-readable discrepancy messages.
    """
    msgs: list[str] = []

    if unclassified:
        msgs.append(
            f'{len(unclassified)} tag(s) could not be matched to any workspace: '
            + ', '.join(sorted(unclassified)[:10])
            + (' ...' if len(unclassified) > 10 else '')
        )

    # Check for workspaces with only umbrella tags.
    by_workspace: dict[str, list[ClassifiedTag]] = {}
    for ct in classified:
        by_workspace.setdefault(ct.workspace_label, []).append(ct)

    for label, tags in by_workspace.items():
        umbrella_only = all(ct.is_umbrella for ct in tags)
        if umbrella_only and len(tags) > 0:
            msgs.append(
                f'Workspace {label!r}: only umbrella tags found '
                f'(no per-package tags). All packages will use bootstrap_sha.'
            )

        # Check for mixed tag formats (per-package names that differ in pattern).
        per_pkg_tags = [ct for ct in tags if not ct.is_umbrella]
        if per_pkg_tags:
            formats_seen = set()
            for ct in per_pkg_tags:
                # Approximate the format by replacing the version with a placeholder.
                approx = ct.tag.replace(ct.version, '{version}')
                if ct.package_name:
                    approx = approx.replace(ct.package_name, '{name}')
                formats_seen.add(approx)
            if len(formats_seen) > 1:
                msgs.append(f'Workspace {label!r}: multiple tag formats detected: ' + ', '.join(sorted(formats_seen)))

    return msgs


async def create_bootstrap_tags(
    config: ReleaseConfig,
    vcs: VCS,
    *,
    workspace_label: str,
    bootstrap_sha: str,
    dry_run: bool = False,
) -> tuple[list[str], list[str]]:
    """Create per-package tags at the bootstrap SHA.

    Discovers all packages in the workspace and creates tags using
    the workspace's ``tag_format`` for any package that doesn't
    already have a tag. Also creates the umbrella tag if configured
    and missing.

    Args:
        config: The loaded release configuration.
        vcs: VCS backend for tag operations.
        workspace_label: Workspace label (e.g. ``"py"``).
        bootstrap_sha: The commit SHA to tag.
        dry_run: If ``True``, log what would be done without creating tags.

    Returns:
        A ``(created, skipped)`` tuple of tag name lists.
    """
    ws_config: WorkspaceConfig | None = config.workspaces.get(workspace_label)
    if not ws_config:
        return [], []

    # Resolve workspace root.
    config_dir = config.config_path.parent if config.config_path else Path.cwd()
    ws_root = config_dir / ws_config.root if ws_config.root else config_dir

    # Discover packages in this workspace.
    try:
        packages = discover_packages(ws_root, ecosystem=ws_config.ecosystem)
    except Exception:  # noqa: BLE001
        logger.info(
            'bootstrap_tags_discovery_failed',
            workspace=workspace_label,
            message='Could not discover packages — skipping bootstrap tag creation.',
        )
        return [], []

    if not packages:
        logger.info('bootstrap_tags_no_packages', workspace=workspace_label)
        return [], []

    tag_format = ws_config.tag_format
    created: list[str] = []
    skipped: list[str] = []

    for pkg in packages:
        tag_name = tag_format.format(name=pkg.name, version=pkg.version)
        if await vcs.tag_exists(tag_name):
            skipped.append(tag_name)
            continue

        logger.info(
            'bootstrap_tag_create',
            tag=tag_name,
            package=pkg.name,
            version=pkg.version,
            sha=bootstrap_sha[:12],
        )
        result = await vcs.tag(
            tag_name,
            ref=bootstrap_sha,
            message=f'Bootstrap tag for {pkg.name} v{pkg.version}',
            dry_run=dry_run,
        )
        if result.ok or dry_run:
            created.append(tag_name)
        else:
            logger.warning(
                'bootstrap_tag_failed',
                tag=tag_name,
                stderr=result.stderr[:200],
            )

    # Create umbrella tag if configured and missing.
    umbrella_format = ws_config.umbrella_tag
    if umbrella_format and packages:
        # Use the first package's version (all should match in a synchronized workspace).
        umbrella_version = packages[0].version
        umbrella_tag = umbrella_format.format(version=umbrella_version)
        if await vcs.tag_exists(umbrella_tag):
            skipped.append(umbrella_tag)
        else:
            logger.info(
                'bootstrap_tag_create',
                tag=umbrella_tag,
                sha=bootstrap_sha[:12],
            )
            result = await vcs.tag(
                umbrella_tag,
                ref=bootstrap_sha,
                message=f'Bootstrap umbrella tag {umbrella_tag}',
                dry_run=dry_run,
            )
            if result.ok or dry_run:
                created.append(umbrella_tag)

    return created, skipped


async def scan_and_bootstrap(
    config_path: Path,
    config: ReleaseConfig,
    vcs: VCS,
    *,
    dry_run: bool = False,
) -> TagScanReport:
    """Scan existing git tags, write ``bootstrap_sha``, and create bootstrap tags.

    Called after ``scaffold_config()`` to auto-detect the last release
    tag, set ``bootstrap_sha`` so that only new commits are scanned,
    and create per-package tags at the bootstrap commit for packages
    that don't have them yet.

    Gracefully skips when no tags exist.

    Args:
        config_path: Path to ``releasekit.toml``.
        config: The loaded release configuration.
        vcs: VCS backend for tag operations.
        dry_run: If ``True``, compute everything but don't write files.

    Returns:
        A :class:`TagScanReport` with all findings.
    """
    report = TagScanReport()

    workspaces = config.workspaces
    if not workspaces:
        logger.info('init_scan_no_workspaces', message='No workspaces configured, skipping tag scan.')
        return report

    # 1. Scan all tags.
    all_tags = await vcs.list_tags()
    if not all_tags:
        logger.info('init_scan_no_tags', message='No git tags found. Skipping bootstrap.')
        return report

    logger.info('init_scan_tags_found', count=len(all_tags))

    # 2. Classify tags against workspace configs.
    classified, unclassified = classify_tags(all_tags, workspaces)
    report.classified = classified
    report.unclassified = unclassified

    logger.info(
        'init_scan_classified',
        classified=len(classified),
        unclassified=len(unclassified),
    )

    if not classified:
        report.discrepancies.append(f'Found {len(all_tags)} tag(s) but none matched any workspace tag format.')
        return report

    # 3. Resolve commit SHAs.
    await resolve_commit_shas(classified, vcs)

    # 4. Pick latest per workspace.
    report.latest_per_workspace = pick_latest(classified)

    # 5. Compute bootstrap_sha per workspace.
    for label, ct in report.latest_per_workspace.items():
        if ct.commit_sha:
            report.bootstrap_shas[label] = ct.commit_sha
            logger.info(
                'init_scan_latest',
                workspace=label,
                tag=ct.tag,
                version=ct.version,
                sha=ct.commit_sha[:12],
            )

    # 6. Detect discrepancies.
    report.discrepancies = _detect_discrepancies(classified, unclassified, report.latest_per_workspace)

    # 7. Write bootstrap_sha to releasekit.toml.
    config_exists = config_path.exists()  # noqa: ASYNC240
    if not dry_run and report.bootstrap_shas and config_exists:
        for label, sha in report.bootstrap_shas.items():
            write_bootstrap_sha(config_path, label, sha)
        report.written = True
        logger.info('init_scan_written', path=str(config_path))

    # 8. Create bootstrap tags for packages without them.
    for label, sha in report.bootstrap_shas.items():
        created, skipped = await create_bootstrap_tags(
            config,
            vcs,
            workspace_label=label,
            bootstrap_sha=sha,
            dry_run=dry_run,
        )
        report.tags_created.extend(created)
        report.tags_skipped.extend(skipped)

    return report


def print_scaffold_preview(toml_fragment: str) -> None:
    """Print a preview of the generated configuration.

    Uses Rich for colored output if available on a TTY, otherwise
    prints plain text.
    """
    if not toml_fragment:
        return

    if sys.stdout.isatty() and _HAS_RICH:
        console = Console()
        console.print(f'\n[bold]Generated {CONFIG_FILENAME}:[/bold]\n')
        syntax = Syntax(toml_fragment, 'toml', theme='monokai')
        console.print(syntax)
        return

    print(toml_fragment)  # noqa: T201 - CLI output


def print_tag_scan_report(report: TagScanReport) -> None:
    """Print the tag scan results to stdout.

    Shows classified tags, bootstrap SHAs, and any discrepancies.
    """
    if not report.classified and not report.unclassified:
        print('  ℹ️  No git tags found — bootstrap_sha not needed.')  # noqa: T201 - CLI output
        return

    total = len(report.classified) + len(report.unclassified)
    print(f'\n  🔍 Scanned {total} tag(s):')  # noqa: T201 - CLI output
    if report.classified:
        print(f'     {len(report.classified)} matched workspace tag formats')  # noqa: T201 - CLI output
    if report.unclassified:
        print(f'     {len(report.unclassified)} unrecognized')  # noqa: T201 - CLI output

    for label, ct in report.latest_per_workspace.items():
        sha_short = ct.commit_sha[:12] if ct.commit_sha else '(unknown)'
        print(f'     Latest for {label!r}: {ct.tag} → {sha_short}')  # noqa: T201 - CLI output

    if report.bootstrap_shas:
        if report.written:
            for label, sha in report.bootstrap_shas.items():
                print(f'  ✅ bootstrap_sha for {label!r} = "{sha[:12]}..."')  # noqa: T201 - CLI output
        else:
            for label, sha in report.bootstrap_shas.items():
                print(f'  🔶 Would write bootstrap_sha for {label!r} = "{sha[:12]}..."')  # noqa: T201 - CLI output

    if report.discrepancies:
        print('\n  ⚠️  Discrepancies:')  # noqa: T201 - CLI output
        for msg in report.discrepancies:
            print(f'     • {msg}')  # noqa: T201 - CLI output

    # Bootstrap tags.
    if report.tags_created:
        print(f'\n  🏷️  Created {len(report.tags_created)} bootstrap tag(s):')  # noqa: T201 - CLI output
        for tag in report.tags_created:
            print(f'     {tag}')  # noqa: T201 - CLI output
        print('\n  👉 Push tags to remote:  git push origin --tags')  # noqa: T201 - CLI output
    if report.tags_skipped:
        print(f'  ⏭️  Skipped {len(report.tags_skipped)} existing tag(s)')  # noqa: T201 - CLI output


__all__ = [
    'TagScanReport',
    'create_bootstrap_tags',
    'detect_groups',
    'generate_config_toml',
    'print_scaffold_preview',
    'print_tag_scan_report',
    'scan_and_bootstrap',
    'scaffold_config',
]
