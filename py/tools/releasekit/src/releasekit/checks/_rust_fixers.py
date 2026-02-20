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

"""Rust/Cargo-specific auto-fixer functions for ``Cargo.toml`` files."""

from __future__ import annotations

import re

from releasekit.logging import get_logger
from releasekit.workspace import Package

logger = get_logger(__name__)


def fix_metadata_completeness(
    packages: list[Package],
    *,
    dry_run: bool = False,
) -> list[str]:
    """Add missing required fields to ``Cargo.toml``.

    Adds stub ``description``, ``license``, and ``repository`` fields
    to the ``[package]`` section when they are absent from publishable
    crates.

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
        cargo_toml = pkg.path / 'Cargo.toml'
        if not cargo_toml.is_file():
            continue
        try:
            text = cargo_toml.read_text(encoding='utf-8')
        except OSError:
            continue

        additions: list[str] = []
        if 'description =' not in text and 'description=' not in text:
            additions.append('description = "TODO: Add crate description"')
        if 'license =' not in text and 'license=' not in text:
            additions.append('license = "Apache-2.0"')
        if 'repository =' not in text and 'repository=' not in text:
            additions.append('repository = "TODO: Add repository URL"')

        if not additions:
            continue

        # Insert after [package] section header.
        lines = text.splitlines(keepends=True)
        new_lines: list[str] = []
        inserted = False
        for line in lines:
            new_lines.append(line)
            if not inserted and line.strip() == '[package]':
                for addition in additions:
                    new_lines.append(addition + '\n')
                inserted = True

        if not inserted:
            # Fallback: append to end.
            for addition in additions:
                new_lines.append(addition + '\n')

        added_fields = [a.split(' =')[0].split('=')[0].strip() for a in additions]
        action = f'{pkg.name}: added {", ".join(added_fields)} to Cargo.toml'
        changes.append(action)
        if not dry_run:
            cargo_toml.write_text(''.join(new_lines), encoding='utf-8')
            logger.warning('fix_rust_metadata', action=action, path=str(cargo_toml))
        else:
            logger.info('fix_rust_metadata_dry_run', action=action, path=str(cargo_toml))

    return changes


def fix_wildcard_dependencies(
    packages: list[Package],
    *,
    dry_run: bool = False,
) -> list[str]:
    r"""Replace wildcard (``*``) dependency versions with ``>=0``.

    Finds lines matching ``= "*"`` and replaces them with ``= ">=0"``.

    Args:
        packages: All discovered workspace packages.
        dry_run: If ``True``, report what would change without writing.

    Returns:
        List of human-readable descriptions of changes made.
    """
    changes: list[str] = []

    for pkg in packages:
        cargo_toml = pkg.path / 'Cargo.toml'
        if not cargo_toml.is_file():
            continue
        try:
            text = cargo_toml.read_text(encoding='utf-8')
        except OSError:
            continue

        new_text, count = re.subn(r'=\s*"\*"', '= ">=0"', text)
        if count == 0:
            continue

        action = f'{pkg.name}: replaced {count} wildcard dep version(s) with ">=0"'
        changes.append(action)
        if not dry_run:
            cargo_toml.write_text(new_text, encoding='utf-8')
            logger.warning('fix_rust_wildcard_deps', action=action, path=str(cargo_toml))
        else:
            logger.info('fix_rust_wildcard_deps_dry_run', action=action, path=str(cargo_toml))

    return changes


def fix_duplicate_dependencies(
    packages: list[Package],
    *,
    dry_run: bool = False,
) -> list[str]:
    """Remove duplicate dependency entries from ``Cargo.toml``.

    Scans ``[dependencies]``, ``[dev-dependencies]``, and
    ``[build-dependencies]`` sections for duplicate crate names
    and removes later occurrences.

    Args:
        packages: All discovered workspace packages.
        dry_run: If ``True``, report what would change without writing.

    Returns:
        List of human-readable descriptions of changes made.
    """
    changes: list[str] = []
    _dep_section_re = re.compile(r'^\[((?:dev-|build-)?dependencies)\]')

    for pkg in packages:
        cargo_toml = pkg.path / 'Cargo.toml'
        if not cargo_toml.is_file():
            continue
        try:
            text = cargo_toml.read_text(encoding='utf-8')
        except OSError:
            continue

        lines = text.splitlines(keepends=True)
        new_lines: list[str] = []
        in_dep_section = False
        seen_in_section: set[str] = set()
        removed: list[str] = []

        for line in lines:
            stripped = line.strip()

            # Detect section headers.
            if stripped.startswith('['):
                in_dep_section = bool(_dep_section_re.match(stripped))
                seen_in_section = set()
                new_lines.append(line)
                continue

            if in_dep_section and stripped and not stripped.startswith('#'):
                # Lines look like: crate_name = "version" or crate_name = { ... }
                dep_name = stripped.split('=')[0].strip() if '=' in stripped else ''
                if dep_name:
                    if dep_name in seen_in_section:
                        removed.append(dep_name)
                        continue
                    seen_in_section.add(dep_name)

            new_lines.append(line)

        if removed:
            new_text = ''.join(new_lines)
            action = f'{pkg.name}: removed duplicate deps: {", ".join(removed)}'
            changes.append(action)
            if not dry_run:
                cargo_toml.write_text(new_text, encoding='utf-8')
                logger.warning('fix_rust_duplicate_deps', action=action, path=str(cargo_toml))
            else:
                logger.info('fix_rust_duplicate_deps_dry_run', action=action, path=str(cargo_toml))

    return changes


__all__ = [
    'fix_duplicate_dependencies',
    'fix_metadata_completeness',
    'fix_wildcard_dependencies',
]
