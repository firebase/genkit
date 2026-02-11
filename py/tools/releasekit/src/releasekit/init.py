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

Auto-detects workspace structure, generates ``[tool.releasekit]``
configuration in ``pyproject.toml``, and updates ``.gitignore``.
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
    [tool.releasekit]          (if TTY)
         │                         │
         ▼                         ▼
    Write pyproject.toml       Prompt: apply? [Y/n]
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
    """Auto-detect release groups from package naming conventions.

    Groups are detected by:
    - ``core``: Packages matching the workspace name (e.g., ``genkit``)
    - ``plugins``: Packages with ``-plugin-`` in the name
    - ``samples``: Packages in ``samples/`` directories

    Args:
        packages: Discovered workspace packages.

    Returns:
        A dict mapping group name to a list of glob patterns.
    """
    groups: dict[str, list[str]] = {}
    plugin_names: list[str] = []
    sample_names: list[str] = []
    core_names: list[str] = []

    for pkg in packages:
        if '-plugin-' in pkg.name:
            plugin_names.append(pkg.name)
        elif 'sample' in str(pkg.path).lower() or 'sample' in pkg.name:
            sample_names.append(pkg.name)
        else:
            core_names.append(pkg.name)

    if core_names:
        groups['core'] = core_names

    # If all plugins share a prefix, use a glob pattern.
    if plugin_names:
        prefixes = {n.rsplit('-', 1)[0] + '-*' for n in plugin_names if '-' in n}
        if len(prefixes) == 1:
            groups['plugins'] = [prefixes.pop()]
        else:
            groups['plugins'] = sorted(plugin_names)

    if sample_names:
        groups['samples'] = sorted(sample_names)

    return groups


def generate_config_toml(
    groups: dict[str, list[str]],
    *,
    exclude: list[str] | None = None,
    tag_format: str = '{name}-v{version}',
    umbrella_tag: str = 'v{version}',
) -> str:
    """Generate a ``[tool.releasekit]`` TOML fragment.

    Args:
        groups: Package groups from :func:`detect_groups`.
        exclude: Glob patterns for packages to exclude.
        tag_format: Per-package tag format.
        umbrella_tag: Umbrella tag format.

    Returns:
        A TOML string suitable for insertion into ``pyproject.toml``.
    """
    doc = tomlkit.document()
    table = tomlkit.table()

    table.add('tag_format', tag_format)
    table.add('umbrella_tag', umbrella_tag)

    if exclude:
        table.add('exclude', exclude)

    if groups:
        groups_table = tomlkit.table()
        for group_name, patterns in sorted(groups.items()):
            groups_table.add(group_name, patterns)
        table.add('groups', groups_table)

    table.add('changelog', True)
    table.add('smoke_test', True)

    doc.add('tool', tomlkit.table())
    tool_dict = dict(doc['tool'])  # type: ignore[arg-type]
    tool_dict['releasekit'] = table
    doc['tool'] = tool_dict

    return tomlkit.dumps(doc)


def _has_releasekit_config(pyproject_path: Path) -> bool:
    """Return True if pyproject.toml already has [tool.releasekit]."""
    if not pyproject_path.exists():
        return False
    content = pyproject_path.read_text(encoding='utf-8')
    doc = tomlkit.parse(content)
    tool = doc.get('tool')
    if not isinstance(tool, dict):
        return False
    return 'releasekit' in tool


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
    3. Generates ``[tool.releasekit]`` TOML
    4. Updates ``pyproject.toml`` (if not dry-run)
    5. Updates ``.gitignore`` (if not dry-run)

    Args:
        workspace_root: Path to the workspace root.
        dry_run: Preview changes without writing files.
        force: Overwrite existing ``[tool.releasekit]`` section.

    Returns:
        The generated TOML fragment (for display/preview).
    """
    pyproject_path = workspace_root / 'pyproject.toml'

    if _has_releasekit_config(pyproject_path) and not force:
        logger.info(
            '[tool.releasekit] already exists in %s (use --force to overwrite)',
            pyproject_path,
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

    toml_fragment = generate_config_toml(groups, exclude=exclude or None)

    if dry_run:
        return toml_fragment

    # Write to pyproject.toml.
    _update_pyproject(pyproject_path, groups, exclude)
    logger.info('Updated %s', pyproject_path)

    # Update .gitignore.
    _update_gitignore(workspace_root / '.gitignore')
    logger.info('Updated %s', workspace_root / '.gitignore')

    return toml_fragment


def _update_pyproject(
    pyproject_path: Path,
    groups: dict[str, list[str]],
    exclude: list[str],
) -> None:
    """Add [tool.releasekit] to an existing pyproject.toml."""
    content = pyproject_path.read_text(encoding='utf-8')
    doc = tomlkit.parse(content)

    if 'tool' not in doc:
        doc.add('tool', tomlkit.table())

    tool = doc['tool']
    if not isinstance(tool, dict):
        return

    rk_table = tomlkit.table()
    rk_table.add('tag_format', '{name}-v{version}')
    rk_table.add('umbrella_tag', 'v{version}')

    if exclude:
        rk_table.add('exclude', exclude)

    if groups:
        groups_table = tomlkit.table()
        for group_name, patterns in sorted(groups.items()):
            groups_table.add(group_name, patterns)
        rk_table.add('groups', groups_table)

    rk_table.add('changelog', True)
    rk_table.add('smoke_test', True)

    tool_dict = dict(tool)
    tool_dict['releasekit'] = rk_table
    doc['tool'] = tool_dict

    pyproject_path.write_text(tomlkit.dumps(doc), encoding='utf-8')


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
        console.print('\n[bold]Generated [tool.releasekit] configuration:[/bold]\n')
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
