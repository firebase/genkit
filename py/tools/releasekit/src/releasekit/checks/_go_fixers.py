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

"""Go-specific auto-fixer functions for ``go.mod`` files."""

from __future__ import annotations

from releasekit.logging import get_logger
from releasekit.workspace import Package

logger = get_logger(__name__)


def fix_duplicate_dependencies(
    packages: list[Package],
    *,
    dry_run: bool = False,
) -> list[str]:
    """Remove duplicate ``require`` directives from ``go.mod``.

    Scans each package's ``go.mod`` for duplicate module paths in
    ``require`` blocks and removes the later occurrences.

    Args:
        packages: All discovered workspace packages.
        dry_run: If ``True``, report what would change without writing.

    Returns:
        List of human-readable descriptions of changes made.
    """
    changes: list[str] = []

    for pkg in packages:
        go_mod = pkg.path / 'go.mod'
        if not go_mod.is_file():
            continue
        try:
            text = go_mod.read_text(encoding='utf-8')
        except OSError:
            continue

        lines = text.splitlines(keepends=True)
        seen: set[str] = set()
        new_lines: list[str] = []
        removed: list[str] = []
        in_require = False

        for line in lines:
            stripped = line.strip()

            if stripped == 'require (' or stripped.startswith('require ('):
                in_require = True
                new_lines.append(line)
                continue
            if in_require and stripped == ')':
                in_require = False
                new_lines.append(line)
                continue

            if in_require and stripped and not stripped.startswith('//'):
                # Lines inside require block look like: module/path v1.2.3
                parts = stripped.split()
                if parts:
                    mod_path = parts[0]
                    if mod_path in seen:
                        removed.append(mod_path)
                        continue
                    seen.add(mod_path)

            new_lines.append(line)

        if removed:
            new_text = ''.join(new_lines)
            action = f'{pkg.name}: removed duplicate require directives: {", ".join(removed)}'
            changes.append(action)
            if not dry_run:
                go_mod.write_text(new_text, encoding='utf-8')
                logger.warning('fix_go_duplicate_deps', action=action, path=str(go_mod))
            else:
                logger.info('fix_go_duplicate_deps_dry_run', action=action, path=str(go_mod))

    return changes


def fix_build_system(
    packages: list[Package],
    *,
    dry_run: bool = False,
) -> list[str]:
    """Create a minimal ``go.mod`` for packages missing one.

    The generated ``go.mod`` uses the package name as the module path
    and defaults to ``go 1.21``.

    Args:
        packages: All discovered workspace packages.
        dry_run: If ``True``, report what would change without writing.

    Returns:
        List of human-readable descriptions of changes made.
    """
    changes: list[str] = []

    for pkg in packages:
        go_mod = pkg.path / 'go.mod'
        if go_mod.is_file():
            continue

        content = f'module {pkg.name}\n\ngo 1.21\n'
        action = f'{pkg.name}: created go.mod'
        changes.append(action)
        if not dry_run:
            go_mod.write_text(content, encoding='utf-8')
            logger.warning('fix_go_build_system', action=action, path=str(go_mod))
        else:
            logger.info('fix_go_build_system_dry_run', action=action, path=str(go_mod))

    return changes


__all__ = [
    'fix_build_system',
    'fix_duplicate_dependencies',
]
