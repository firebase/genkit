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

"""Dart/Flutter-specific auto-fixer functions for ``pubspec.yaml`` files."""

from __future__ import annotations

from releasekit.logging import get_logger
from releasekit.workspace import Package

logger = get_logger(__name__)


def fix_publish_to_consistency(
    packages: list[Package],
    *,
    dry_run: bool = False,
) -> list[str]:
    """Add ``publish_to: none`` to non-publishable packages missing it.

    Args:
        packages: All discovered workspace packages.
        dry_run: If ``True``, report what would change without writing.

    Returns:
        List of human-readable descriptions of changes made.
    """
    changes: list[str] = []

    for pkg in packages:
        if pkg.is_publishable:
            continue
        pubspec = pkg.path / 'pubspec.yaml'
        if not pubspec.is_file():
            continue
        try:
            text = pubspec.read_text(encoding='utf-8')
        except OSError:
            continue

        has_publish_none = 'publish_to: none' in text or "publish_to: 'none'" in text
        if has_publish_none:
            continue

        # Insert publish_to: none after the name: line.
        lines = text.splitlines(keepends=True)
        new_lines: list[str] = []
        inserted = False
        for line in lines:
            new_lines.append(line)
            if not inserted and line.strip().startswith('name:'):
                new_lines.append('publish_to: none\n')
                inserted = True

        if not inserted:
            # Fallback: prepend.
            new_lines.insert(0, 'publish_to: none\n')

        action = f'{pkg.name}: added publish_to: none'
        changes.append(action)
        if not dry_run:
            pubspec.write_text(''.join(new_lines), encoding='utf-8')
            logger.warning('fix_dart_publish_to', action=action, path=str(pubspec))
        else:
            logger.info('fix_dart_publish_to_dry_run', action=action, path=str(pubspec))

    return changes


def fix_duplicate_dependencies(
    packages: list[Package],
    *,
    dry_run: bool = False,
) -> list[str]:
    """Remove duplicate dependency entries from ``pubspec.yaml``.

    This is a best-effort fixer that detects and removes duplicate
    keys within ``dependencies:`` and ``dev_dependencies:`` blocks.

    Args:
        packages: All discovered workspace packages.
        dry_run: If ``True``, report what would change without writing.

    Returns:
        List of human-readable descriptions of changes made.
    """
    changes: list[str] = []

    for pkg in packages:
        # Use the all_deps field to detect duplicates.
        seen: set[str] = set()
        has_dupes = False
        for dep in pkg.all_deps:
            if dep in seen:
                has_dupes = True
                break
            seen.add(dep)

        if not has_dupes:
            continue

        pubspec = pkg.path / 'pubspec.yaml'
        if not pubspec.is_file():
            continue
        try:
            text = pubspec.read_text(encoding='utf-8')
        except OSError:
            continue

        lines = text.splitlines(keepends=True)
        new_lines: list[str] = []
        in_deps_block = False
        deps_indent = 0
        seen_in_block: set[str] = set()
        removed: list[str] = []

        for line in lines:
            stripped = line.strip()

            # Detect start of dependencies/dev_dependencies block.
            if stripped in ('dependencies:', 'dev_dependencies:'):
                in_deps_block = True
                deps_indent = len(line) - len(line.lstrip())
                seen_in_block = set()
                new_lines.append(line)
                continue

            # Detect end of block (line at same or lower indent, non-empty).
            if in_deps_block and stripped and not stripped.startswith('#'):
                line_indent = len(line) - len(line.lstrip())
                if line_indent <= deps_indent and ':' in stripped:
                    in_deps_block = False
                    seen_in_block = set()

            if in_deps_block and stripped and not stripped.startswith('#'):
                dep_name = stripped.split(':')[0].strip()
                if dep_name in seen_in_block:
                    removed.append(dep_name)
                    continue
                seen_in_block.add(dep_name)

            new_lines.append(line)

        if removed:
            new_text = ''.join(new_lines)
            action = f'{pkg.name}: removed duplicate deps: {", ".join(removed)}'
            changes.append(action)
            if not dry_run:
                pubspec.write_text(new_text, encoding='utf-8')
                logger.warning('fix_dart_duplicate_deps', action=action, path=str(pubspec))
            else:
                logger.info('fix_dart_duplicate_deps_dry_run', action=action, path=str(pubspec))

    return changes


def fix_metadata_completeness(
    packages: list[Package],
    *,
    dry_run: bool = False,
) -> list[str]:
    """Add missing required fields to ``pubspec.yaml``.

    Adds stub ``description``, ``repository``, and ``environment``
    fields when they are absent from publishable packages.

    Args:
        packages: All discovered workspace packages.
        dry_run: If ``True``, report what would change without writing.

    Returns:
        List of human-readable descriptions of changes made.
    """
    changes: list[str] = []

    for pkg in packages:
        if not pkg.is_publishable:
            continue
        pubspec = pkg.path / 'pubspec.yaml'
        if not pubspec.is_file():
            continue
        try:
            text = pubspec.read_text(encoding='utf-8')
        except OSError:
            continue

        additions: list[str] = []
        if 'description:' not in text:
            additions.append("description: 'TODO: Add package description'")
        if 'repository:' not in text:
            additions.append("repository: 'TODO: Add repository URL'")
        if 'environment:' not in text:
            additions.append("environment:\n  sdk: '>=3.0.0 <4.0.0'")

        if not additions:
            continue

        new_text = text.rstrip('\n') + '\n' + '\n'.join(additions) + '\n'
        added_fields = [a.split(':')[0] for a in additions]
        action = f'{pkg.name}: added {", ".join(added_fields)} to pubspec.yaml'
        changes.append(action)
        if not dry_run:
            pubspec.write_text(new_text, encoding='utf-8')
            logger.warning('fix_dart_metadata', action=action, path=str(pubspec))
        else:
            logger.info('fix_dart_metadata_dry_run', action=action, path=str(pubspec))

    return changes


__all__ = [
    'fix_duplicate_dependencies',
    'fix_metadata_completeness',
    'fix_publish_to_consistency',
]
