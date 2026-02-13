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
configuration, and updates ``.gitignore``.
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
"""

from __future__ import annotations

import sys
from pathlib import Path

import tomlkit

try:
    from rich.console import Console
    from rich.syntax import Syntax

    _HAS_RICH = True
except ImportError:
    _HAS_RICH = False

from releasekit.config import CONFIG_FILENAME
from releasekit.logging import get_logger
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
    exclude: list[str] | None = None,
    tag_format: str = '{name}-v{version}',
    umbrella_tag: str = 'v{version}',
) -> str:
    """Generate a ``releasekit.toml`` config file.

    Args:
        groups: Package groups from :func:`detect_groups`.
        exclude: Glob patterns for packages to exclude.
        tag_format: Per-package tag format.
        umbrella_tag: Umbrella tag format.

    Returns:
        A TOML string for ``releasekit.toml``.
    """
    doc = tomlkit.document()

    doc.add('tag_format', tomlkit.item(tag_format))
    doc.add('umbrella_tag', tomlkit.item(umbrella_tag))

    if exclude:
        doc.add('exclude', tomlkit.item(exclude))

    if groups:
        groups_table = tomlkit.table()
        for group_name, patterns in sorted(groups.items()):
            groups_table.add(group_name, tomlkit.item(patterns))
        doc.add('groups', groups_table)

    doc.add('changelog', tomlkit.item(True))
    doc.add('smoke_test', tomlkit.item(True))

    return tomlkit.dumps(doc)


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

    toml_content = generate_config_toml(groups, exclude=exclude or None)

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


__all__ = [
    'detect_groups',
    'generate_config_toml',
    'print_scaffold_preview',
    'scaffold_config',
]
