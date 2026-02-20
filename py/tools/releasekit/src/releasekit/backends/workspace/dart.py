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

"""Dart workspace backend for releasekit.

The :class:`DartWorkspace` implements the
:class:`~releasekit.backends.workspace.Workspace` protocol by parsing
``pubspec.yaml`` files and Dart/Melos workspace configurations.

Dart workspace layout (directory name is arbitrary; Melos-style)::

    dart/
    ├── melos.yaml           ← workspace root (lists package globs)
    ├── pubspec.yaml         ← root pubspec (optional)
    ├── packages/
    │   ├── genkit/
    │   │   └── pubspec.yaml ← package: genkit
    │   ├── genkit_google/
    │   │   └── pubspec.yaml ← package: genkit_google
    │   └── genkit_vertex/
    │       └── pubspec.yaml ← package: genkit_vertex
    └── examples/
        └── ...

Alternatively, a single-package Dart project has just ``pubspec.yaml``
at the root with no ``melos.yaml``.

Version handling:

    Dart packages store their version in ``pubspec.yaml`` under the
    ``version:`` key. The ``rewrite_version`` method updates this field.
    Dependencies are listed under ``dependencies:`` and
    ``dev_dependencies:`` with version constraints.
"""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path

from releasekit._types import DetectedLicense
from releasekit.backends.workspace._io import read_file, write_file
from releasekit.backends.workspace._types import Package
from releasekit.logging import get_logger

log = get_logger('releasekit.backends.workspace.dart')

# Regex to parse the package name from pubspec.yaml.
_NAME_RE = re.compile(r'^name:\s*(\S+)', re.MULTILINE)

# Regex to parse the version from pubspec.yaml.
_VERSION_RE = re.compile(r'^version:\s*(\S+)', re.MULTILINE)

# Regex to detect publish_to: none (private package).
_PUBLISH_TO_NONE_RE = re.compile(r'^publish_to:\s*["\']?none["\']?', re.MULTILINE)

# Regex to parse dependency names from pubspec.yaml.
_DEP_RE = re.compile(r'^\s{2}(\w[\w_-]*):', re.MULTILINE)


def _parse_melos_packages(melos_path: Path) -> list[str]:
    """Parse package glob patterns from ``melos.yaml``.

    Returns a list of glob patterns like ``['packages/*', 'plugins/*']``.
    """
    if not melos_path.is_file():
        return []
    text = melos_path.read_text(encoding='utf-8')
    # Simple YAML parsing for the packages: list.
    in_packages = False
    patterns: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == 'packages:':
            in_packages = True
            continue
        if in_packages:
            if stripped.startswith('- '):
                patterns.append(stripped[2:].strip())
            elif stripped and not stripped.startswith('#'):
                break
    return patterns


class DartWorkspace:
    """Dart :class:`~releasekit.backends.workspace.Workspace` implementation.

    Discovers packages via ``melos.yaml`` glob patterns or by scanning
    for ``pubspec.yaml`` files in immediate subdirectories.

    Args:
        workspace_root: Path to the Dart workspace root.
    """

    def __init__(self, workspace_root: Path) -> None:
        """Initialize with the Dart workspace root."""
        self._root = workspace_root.resolve()

    async def discover(
        self,
        *,
        exclude_patterns: list[str] | None = None,
    ) -> list[Package]:
        """Discover all Dart packages in the workspace.

        If ``melos.yaml`` exists, uses its ``packages:`` globs.
        Otherwise, scans for ``pubspec.yaml`` in immediate subdirectories.

        Args:
            exclude_patterns: Glob patterns to exclude packages by name.

        Returns:
            Sorted list of discovered Dart packages.
        """
        melos_path = self._root / 'melos.yaml'
        package_dirs: list[Path] = []

        if melos_path.is_file():
            patterns = _parse_melos_packages(melos_path)
            for pattern in patterns:
                for match in sorted(self._root.glob(pattern)):
                    if match.is_dir() and (match / 'pubspec.yaml').is_file():
                        package_dirs.append(match)
        else:
            # Fallback: scan for pubspec.yaml in subdirectories.
            for child in sorted(self._root.iterdir()):
                if child.is_dir() and (child / 'pubspec.yaml').is_file():
                    package_dirs.append(child)

        # Also check the root itself if it has a pubspec.yaml.
        if (self._root / 'pubspec.yaml').is_file() and self._root not in package_dirs:
            package_dirs.insert(0, self._root)

        # First pass: collect all package names for internal dep classification.
        all_names: set[str] = set()
        for pkg_dir in package_dirs:
            pubspec = pkg_dir / 'pubspec.yaml'
            text = pubspec.read_text(encoding='utf-8')
            m = _NAME_RE.search(text)
            if m:
                all_names.add(m.group(1))

        exclude = exclude_patterns or []
        packages: list[Package] = []

        for pkg_dir in package_dirs:
            pubspec = pkg_dir / 'pubspec.yaml'
            text = pubspec.read_text(encoding='utf-8')

            name_match = _NAME_RE.search(text)
            if not name_match:
                log.debug('no_name', path=str(pubspec))
                continue
            name = name_match.group(1)

            if any(fnmatch.fnmatch(name, pat) for pat in exclude):
                log.debug('excluded', package=name)
                continue

            version_match = _VERSION_RE.search(text)
            version = version_match.group(1) if version_match else '0.0.0'

            is_private = bool(_PUBLISH_TO_NONE_RE.search(text))

            # Parse dependencies.
            deps_section = self._extract_deps_section(text, 'dependencies')
            dev_deps_section = self._extract_deps_section(text, 'dev_dependencies')
            all_dep_names = _DEP_RE.findall(deps_section + '\n' + dev_deps_section)

            internal_deps = [d for d in all_dep_names if d in all_names and d != name]
            external_deps = [d for d in all_dep_names if d not in all_names]

            packages.append(
                Package(
                    name=name,
                    version=version,
                    path=pkg_dir,
                    manifest_path=pubspec,
                    internal_deps=internal_deps,
                    external_deps=external_deps,
                    all_deps=all_dep_names,
                    is_publishable=not is_private,
                )
            )

        packages.sort(key=lambda p: p.name)
        log.info(
            'discovered',
            count=len(packages),
            packages=[p.name for p in packages],
        )
        return packages

    @staticmethod
    def _extract_deps_section(text: str, section_name: str) -> str:
        """Extract a YAML section (dependencies/dev_dependencies) from pubspec."""
        lines = text.splitlines()
        in_section = False
        section_lines: list[str] = []
        for line in lines:
            if line.rstrip() == f'{section_name}:':
                in_section = True
                continue
            if in_section:
                if line and not line[0].isspace() and not line.startswith('#'):
                    break
                section_lines.append(line)
        return '\n'.join(section_lines)

    async def rewrite_version(
        self,
        manifest_path: Path,
        new_version: str,
    ) -> str:
        """Rewrite the ``version:`` field in ``pubspec.yaml``.

        Args:
            manifest_path: Path to ``pubspec.yaml``.
            new_version: New version string.

        Returns:
            The old version string.
        """
        text = await read_file(manifest_path)
        m = _VERSION_RE.search(text)
        old_version = m.group(1) if m else '0.0.0'

        new_text = _VERSION_RE.sub(f'version: {new_version}', text, count=1)
        if new_text != text:
            await write_file(manifest_path, new_text)
            log.info(
                'version_rewritten',
                manifest=str(manifest_path),
                old=old_version,
                new=new_version,
            )
        return old_version

    async def rewrite_dependency_version(
        self,
        manifest_path: Path,
        dep_name: str,
        new_version: str,
    ) -> None:
        """Rewrite a dependency version in ``pubspec.yaml``.

        Updates simple version constraints (e.g. ``^1.0.0``) to use
        the new version with a caret constraint.
        """
        text = await read_file(manifest_path)

        # Match: dep_name: ^X.Y.Z or dep_name: "^X.Y.Z" or dep_name: X.Y.Z
        pattern = re.compile(
            rf'(\s+{re.escape(dep_name)}:\s*)["\']?\^?[\d.]+[-\w.]*["\']?',
        )
        new_text = pattern.sub(rf'\g<1>^{new_version}', text)

        if new_text != text:
            await write_file(manifest_path, new_text)
            log.info(
                'dependency_rewritten',
                manifest=str(manifest_path),
                dep=dep_name,
                version=new_version,
            )
        else:
            log.debug(
                'dependency_not_found',
                manifest=str(manifest_path),
                dep=dep_name,
            )

    async def detect_license(
        self,
        pkg_path: Path,
        pkg_name: str = '',
    ) -> DetectedLicense:
        """Dart ``pubspec.yaml`` has no license field.

        Returns empty so the caller falls back to LICENSE file scanning.
        """
        if not pkg_name:
            pkg_name = pkg_path.name
        return DetectedLicense(value='', source='', package_name=pkg_name)


__all__ = [
    'DartWorkspace',
]
