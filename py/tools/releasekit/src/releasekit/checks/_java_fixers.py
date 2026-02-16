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

"""Java/Kotlin-specific auto-fixer functions for POM and Gradle files."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET  # noqa: N817, S405

from releasekit.logging import get_logger
from releasekit.workspace import Package

logger = get_logger(__name__)

_POM_NS = '{http://maven.apache.org/POM/4.0.0}'


def _pom_find(root: ET.Element, tag: str) -> ET.Element | None:
    """Find a POM element with or without namespace."""
    elem = root.find(f'{_POM_NS}{tag}')
    if elem is None:
        elem = root.find(tag)
    return elem


def fix_placeholder_urls(
    packages: list[Package],
    *,
    dry_run: bool = False,
) -> list[str]:
    """Remove placeholder ``example.com`` URLs from POM ``<url>`` elements.

    Replaces ``<url>`` elements containing ``example.com`` with an
    empty string to signal that the URL needs to be filled in.

    Args:
        packages: All discovered workspace packages.
        dry_run: If ``True``, report what would change without writing.

    Returns:
        List of human-readable descriptions of changes made.
    """
    changes: list[str] = []

    for pkg in packages:
        if not pkg.manifest_path.name.endswith('.xml'):
            continue
        try:
            tree = ET.parse(pkg.manifest_path)  # noqa: S314
        except (ET.ParseError, OSError):
            continue

        root = tree.getroot()
        url_elem = _pom_find(root, 'url')
        if url_elem is None or not url_elem.text:
            continue
        if 'example.com' not in url_elem.text:
            continue

        url_elem.text = ''
        action = f'{pkg.name}: cleared placeholder <url> in pom.xml'
        changes.append(action)
        if not dry_run:
            tree.write(str(pkg.manifest_path), xml_declaration=True, encoding='unicode')
            logger.warning('fix_java_placeholder_url', action=action, path=str(pkg.manifest_path))
        else:
            logger.info('fix_java_placeholder_url_dry_run', action=action, path=str(pkg.manifest_path))

    return changes


def fix_duplicate_dependencies(
    packages: list[Package],
    *,
    dry_run: bool = False,
) -> list[str]:
    """Remove duplicate ``<dependency>`` entries from POM files.

    Detects duplicate dependencies by ``groupId:artifactId`` and
    removes later occurrences.

    Args:
        packages: All discovered workspace packages.
        dry_run: If ``True``, report what would change without writing.

    Returns:
        List of human-readable descriptions of changes made.
    """
    changes: list[str] = []

    for pkg in packages:
        if not pkg.manifest_path.name.endswith('.xml'):
            continue
        try:
            tree = ET.parse(pkg.manifest_path)  # noqa: S314
        except (ET.ParseError, OSError):
            continue

        root = tree.getroot()
        modified = False
        removed: list[str] = []

        for deps_tag in (f'{_POM_NS}dependencies', 'dependencies'):
            deps_elem = root.find(deps_tag)
            if deps_elem is None:
                continue

            seen: set[str] = set()
            to_remove: list[ET.Element] = []
            for dep in list(deps_elem):
                gid = dep.find(f'{_POM_NS}groupId')
                if gid is None:
                    gid = dep.find('groupId')
                aid = dep.find(f'{_POM_NS}artifactId')
                if aid is None:
                    aid = dep.find('artifactId')
                gid_text = gid.text if gid is not None and gid.text else '?'
                aid_text = aid.text if aid is not None and aid.text else '?'
                key = f'{gid_text}:{aid_text}'
                if key in seen:
                    to_remove.append(dep)
                    removed.append(key)
                else:
                    seen.add(key)

            for dep in to_remove:
                deps_elem.remove(dep)
                modified = True

        if modified and removed:
            action = f'{pkg.name}: removed duplicate deps: {", ".join(removed)}'
            changes.append(action)
            if not dry_run:
                tree.write(str(pkg.manifest_path), xml_declaration=True, encoding='unicode')
                logger.warning('fix_java_duplicate_deps', action=action, path=str(pkg.manifest_path))
            else:
                logger.info('fix_java_duplicate_deps_dry_run', action=action, path=str(pkg.manifest_path))

    return changes


def fix_metadata_completeness(
    packages: list[Package],
    *,
    dry_run: bool = False,
) -> list[str]:
    """Add missing ``group`` and ``version`` to ``build.gradle`` files.

    For Gradle projects missing ``group`` or ``version`` declarations,
    appends stub declarations.

    Args:
        packages: All discovered workspace packages.
        dry_run: If ``True``, report what would change without writing.

    Returns:
        List of human-readable descriptions of changes made.
    """
    changes: list[str] = []

    for pkg in packages:
        manifest = pkg.manifest_path
        if not manifest.name.startswith('build.gradle'):
            continue
        try:
            text = manifest.read_text(encoding='utf-8')
        except OSError:
            continue

        additions: list[str] = []
        if not re.search(r'^group\s*=', text, re.MULTILINE):
            additions.append("group = 'TODO'")
        if not re.search(r'^version\s*=', text, re.MULTILINE):
            additions.append("version = '0.0.1'")

        if not additions:
            continue

        new_text = text.rstrip('\n') + '\n' + '\n'.join(additions) + '\n'
        added_fields = [a.split(' =')[0].strip() for a in additions]
        action = f'{pkg.name}: added {", ".join(added_fields)} to {manifest.name}'
        changes.append(action)
        if not dry_run:
            manifest.write_text(new_text, encoding='utf-8')
            logger.warning('fix_java_metadata', action=action, path=str(manifest))
        else:
            logger.info('fix_java_metadata_dry_run', action=action, path=str(manifest))

    return changes


__all__ = [
    'fix_duplicate_dependencies',
    'fix_metadata_completeness',
    'fix_placeholder_urls',
]
