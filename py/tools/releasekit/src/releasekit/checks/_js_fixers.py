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

"""JavaScript/TypeScript-specific auto-fixer functions for ``package.json`` files."""

from __future__ import annotations

import json
from typing import cast

from releasekit.logging import get_logger
from releasekit.workspace import Package

logger = get_logger(__name__)


def _read_package_json(pkg: Package) -> tuple[dict[str, object] | None, str]:
    """Read and parse package.json, returning (data, raw_text)."""
    pj = pkg.path / 'package.json'
    if not pj.is_file():
        return None, ''
    try:
        text = pj.read_text(encoding='utf-8')
        return json.loads(text), text
    except (json.JSONDecodeError, OSError):
        return None, ''


def _write_package_json(pkg: Package, data: dict[str, object]) -> None:
    """Write package.json with 2-space indent and trailing newline."""
    pj = pkg.path / 'package.json'
    pj.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def fix_private_field_consistency(
    packages: list[Package],
    *,
    dry_run: bool = False,
) -> list[str]:
    """Add ``"private": true`` to non-publishable packages missing it.

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
        data, _ = _read_package_json(pkg)
        if data is None:
            continue
        if data.get('private', False) is True:
            continue

        data['private'] = True
        action = f'{pkg.name}: added "private": true to package.json'
        changes.append(action)
        if not dry_run:
            _write_package_json(pkg, data)
            logger.warning('fix_js_private_field', action=action, path=str(pkg.path / 'package.json'))
        else:
            logger.info('fix_js_private_field_dry_run', action=action, path=str(pkg.path / 'package.json'))

    return changes


def fix_metadata_completeness(
    packages: list[Package],
    *,
    dry_run: bool = False,
) -> list[str]:
    """Add missing required fields to ``package.json``.

    Adds stub ``description``, ``license``, and ``repository`` fields
    when they are absent from publishable packages.

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
        data, _ = _read_package_json(pkg)
        if data is None:
            continue

        added: list[str] = []
        if not data.get('description'):
            data['description'] = 'TODO: Add package description'
            added.append('description')
        if not data.get('license'):
            data['license'] = 'Apache-2.0'
            added.append('license')
        if not data.get('repository'):
            data['repository'] = {'type': 'git', 'url': 'TODO: Add repository URL'}
            added.append('repository')

        if not added:
            continue

        action = f'{pkg.name}: added {", ".join(added)} to package.json'
        changes.append(action)
        if not dry_run:
            _write_package_json(pkg, data)
            logger.warning('fix_js_metadata', action=action, path=str(pkg.path / 'package.json'))
        else:
            logger.info('fix_js_metadata_dry_run', action=action, path=str(pkg.path / 'package.json'))

    return changes


def fix_duplicate_dependencies(
    packages: list[Package],
    *,
    dry_run: bool = False,
) -> list[str]:
    """Remove duplicate dependency entries from ``package.json``.

    Checks ``dependencies``, ``devDependencies``, and
    ``peerDependencies`` for duplicate keys. Since JSON objects
    cannot have duplicate keys (later values win), this fixer
    detects when the same package appears in multiple dep sections
    and removes it from ``devDependencies`` if also in
    ``dependencies``.

    Args:
        packages: All discovered workspace packages.
        dry_run: If ``True``, report what would change without writing.

    Returns:
        List of human-readable descriptions of changes made.
    """
    changes: list[str] = []

    for pkg in packages:
        data, _ = _read_package_json(pkg)
        if data is None:
            continue

        raw_deps = data.get('dependencies', {})
        raw_dev = data.get('devDependencies', {})
        if not isinstance(raw_deps, dict) or not isinstance(raw_dev, dict):
            continue
        deps = cast(dict[str, object], raw_deps)
        dev_deps = cast(dict[str, object], raw_dev)

        # Remove from devDependencies if already in dependencies.
        overlap = set(deps.keys()) & set(dev_deps.keys())
        if not overlap:
            continue

        for dep_name in overlap:
            del dev_deps[dep_name]

        action = f'{pkg.name}: removed {", ".join(sorted(overlap))} from devDependencies (already in dependencies)'
        changes.append(action)
        if not dry_run:
            _write_package_json(pkg, data)
            logger.warning('fix_js_duplicate_deps', action=action, path=str(pkg.path / 'package.json'))
        else:
            logger.info('fix_js_duplicate_deps_dry_run', action=action, path=str(pkg.path / 'package.json'))

    return changes


__all__ = [
    'fix_duplicate_dependencies',
    'fix_metadata_completeness',
    'fix_private_field_consistency',
]
