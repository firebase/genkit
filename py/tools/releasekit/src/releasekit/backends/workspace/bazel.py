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

"""Bazel workspace backend for releasekit.

The :class:`BazelWorkspace` implements the
:class:`~releasekit.backends.workspace.Workspace` protocol by parsing
``MODULE.bazel`` and ``BUILD`` / ``BUILD.bazel`` files.

Bazel workspace layout (Bzlmod)::

    repo/
    ├── MODULE.bazel          ← root module (version, deps)
    ├── MODULE.bazel.lock     ← lockfile
    ├── core/
    │   ├── BUILD.bazel       ← package: java_library, java_export, etc.
    │   └── src/...
    ├── plugins/
    │   ├── google/
    │   │   ├── BUILD.bazel
    │   │   └── src/...
    │   └── vertex/
    │       ├── BUILD.bazel
    │       └── src/...
    └── samples/
        └── ...

Legacy WORKSPACE layout::

    repo/
    ├── WORKSPACE             ← root (external deps)
    ├── BUILD.bazel           ← root package
    ├── core/
    │   └── BUILD.bazel
    └── ...

Version handling:

    Bazel stores versions in:
    - ``MODULE.bazel``: ``module(name = "...", version = "x.y.z")``
    - ``version.bzl``: ``VERSION = "x.y.z"``
    - Build rules: ``version = "x.y.z"`` attribute

    The ``rewrite_version`` method handles ``MODULE.bazel`` and
    ``version.bzl`` formats. For build rule attributes, the workspace
    backend rewrites the version in the BUILD file directly.
"""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path

from releasekit._types import DetectedLicense
from releasekit.backends.workspace._io import read_file, write_file
from releasekit.backends.workspace._types import Package
from releasekit.logging import get_logger

log = get_logger('releasekit.backends.workspace.bazel')

# Regex to parse module() call in MODULE.bazel.
_MODULE_NAME_RE = re.compile(
    r'module\s*\(\s*name\s*=\s*"([^"]+)"',
    re.MULTILINE,
)
_MODULE_VERSION_RE = re.compile(
    r'(module\s*\(\s*(?:[^)]*?,\s*)?version\s*=\s*")([^"]+)(")',
    re.MULTILINE | re.DOTALL,
)

# Regex to parse version.bzl: VERSION = "x.y.z"
_VERSION_BZL_RE = re.compile(
    r'^(VERSION\s*=\s*["\'])([^"\']+)(["\'])',
    re.MULTILINE,
)

# Regex to parse bazel_dep() calls in MODULE.bazel.
_BAZEL_DEP_RE = re.compile(
    r'bazel_dep\s*\(\s*name\s*=\s*"([^"]+)"\s*,\s*version\s*=\s*"([^"]+)"',
    re.MULTILINE,
)

# Regex to find BUILD/BUILD.bazel files with publishable targets.
# Matches: java_export, kt_jvm_export, npm_package, py_wheel,
# dart_pub_publish, oci_push, publish_binary.
_PUBLISH_RULE_RE = re.compile(
    r'(?:java_export|kt_jvm_export|npm_package|py_wheel'
    r'|dart_pub_publish|oci_push|publish_binary)\s*\(',
    re.MULTILINE,
)

# Regex to extract name = "..." from a BUILD rule.
_BUILD_NAME_RE = re.compile(r'name\s*=\s*"([^"]+)"')

# Regex to extract version = "..." from a BUILD rule.
_BUILD_VERSION_RE = re.compile(
    r'(version\s*=\s*")([^"]+)(")',
)


def _find_build_files(root: Path) -> list[Path]:
    """Find all BUILD and BUILD.bazel files under root (non-recursive in each dir)."""
    results: list[Path] = []
    for build_file in sorted(root.rglob('BUILD.bazel')):
        results.append(build_file)
    for build_file in sorted(root.rglob('BUILD')):
        # Skip if BUILD.bazel already found in same directory.
        if (build_file.parent / 'BUILD.bazel') not in results:
            results.append(build_file)
    return sorted(results)


def _parse_module_bazel(module_path: Path) -> dict[str, str]:
    """Parse name and version from MODULE.bazel."""
    if not module_path.is_file():
        return {}
    text = module_path.read_text(encoding='utf-8')
    name_match = _MODULE_NAME_RE.search(text)
    version_match = _MODULE_VERSION_RE.search(text)
    return {
        'name': name_match.group(1) if name_match else '',
        'version': version_match.group(2) if version_match else '0.0.0',
    }


def _parse_build_targets(build_path: Path) -> list[dict[str, str]]:
    """Parse publishable targets from a BUILD file.

    Returns a list of dicts with 'name' and 'version' keys.
    """
    if not build_path.is_file():
        return []
    text = build_path.read_text(encoding='utf-8')

    targets: list[dict[str, str]] = []
    for match in _PUBLISH_RULE_RE.finditer(text):
        # Find the name = "..." within the rule block.
        # Look ahead from the match position to find the closing paren.
        start = match.start()
        depth = 0
        block_end = len(text)
        for i in range(start, len(text)):
            if text[i] == '(':
                depth += 1
            elif text[i] == ')':
                depth -= 1
                if depth == 0:
                    block_end = i
                    break
        block = text[start:block_end]

        name_match = _BUILD_NAME_RE.search(block)
        version_match = _BUILD_VERSION_RE.search(block)
        if name_match:
            targets.append({
                'name': name_match.group(1),
                'version': version_match.group(2) if version_match else '0.0.0',
            })
    return targets


class BazelWorkspace:
    """Bazel :class:`~releasekit.backends.workspace.Workspace` implementation.

    Supports both Bzlmod (``MODULE.bazel``) and legacy (``WORKSPACE``)
    layouts. Discovers publishable packages by scanning BUILD files for
    publish-capable rules.

    Args:
        workspace_root: Path to the Bazel workspace root.
    """

    def __init__(self, workspace_root: Path) -> None:
        """Initialize with the Bazel workspace root."""
        self._root = workspace_root.resolve()

    def _is_bzlmod(self) -> bool:
        """Check if the workspace uses Bzlmod (MODULE.bazel)."""
        return (self._root / 'MODULE.bazel').is_file()

    async def discover(
        self,
        *,
        exclude_patterns: list[str] | None = None,
    ) -> list[Package]:
        """Discover all publishable packages in the Bazel workspace.

        Scans BUILD/BUILD.bazel files for publish-capable rules
        (java_export, npm_package, py_wheel, oci_push, etc.).

        Args:
            exclude_patterns: Glob patterns to exclude packages by name.

        Returns:
            Sorted list of discovered packages.
        """
        exclude = exclude_patterns or []
        build_files = _find_build_files(self._root)

        # Get root module metadata for fallback version.
        root_meta = _parse_module_bazel(self._root / 'MODULE.bazel')
        root_version = root_meta.get('version', '0.0.0')

        packages: list[Package] = []
        seen_names: set[str] = set()

        for build_path in build_files:
            targets = _parse_build_targets(build_path)
            if not targets:
                continue

            pkg_dir = build_path.parent
            for target in targets:
                name = target['name']
                version = target['version'] if target['version'] != '0.0.0' else root_version

                if name in seen_names:
                    continue
                if any(fnmatch.fnmatch(name, pat) for pat in exclude):
                    log.debug('excluded', target=name)
                    continue

                seen_names.add(name)
                packages.append(
                    Package(
                        name=name,
                        version=version,
                        path=pkg_dir,
                        manifest_path=build_path,
                        internal_deps=[],
                        external_deps=[],
                        all_deps=[],
                        is_publishable=True,
                    )
                )

        packages.sort(key=lambda p: p.name)
        log.info(
            'discovered_bazel',
            count=len(packages),
            targets=[p.name for p in packages],
        )
        return packages

    async def rewrite_version(
        self,
        manifest_path: Path,
        new_version: str,
    ) -> str:
        """Rewrite the version in a Bazel manifest file.

        Handles three formats:
        1. ``MODULE.bazel``: ``module(name = "...", version = "x.y.z")``
        2. ``version.bzl``: ``VERSION = "x.y.z"``
        3. ``BUILD`` / ``BUILD.bazel``: ``version = "x.y.z"`` attribute

        Args:
            manifest_path: Path to the manifest file.
            new_version: New version string.

        Returns:
            The old version string.
        """
        text = await read_file(manifest_path)

        if manifest_path.name == 'MODULE.bazel':
            return await self._rewrite_module_bazel(manifest_path, text, new_version)
        if manifest_path.name == 'version.bzl':
            return await self._rewrite_version_bzl(manifest_path, text, new_version)
        # BUILD or BUILD.bazel — rewrite version attribute.
        return await self._rewrite_build_version(manifest_path, text, new_version)

    async def rewrite_dependency_version(
        self,
        manifest_path: Path,
        dep_name: str,
        new_version: str,
    ) -> None:
        """Rewrite a dependency's version in a Bazel manifest.

        For ``MODULE.bazel``: rewrites ``bazel_dep(name = "dep", version = "old")``.
        For BUILD files: rewrites ``"group:artifact:old"`` patterns.

        Args:
            manifest_path: Path to the manifest file.
            dep_name: Dependency name to update.
            new_version: New version string.
        """
        text = await read_file(manifest_path)

        if manifest_path.name == 'MODULE.bazel':
            pattern = re.compile(
                rf'(bazel_dep\s*\(\s*name\s*=\s*"{re.escape(dep_name)}"\s*,'
                rf'\s*version\s*=\s*")([^"]+)(")',
                re.MULTILINE,
            )
        else:
            # BUILD file: match "group:artifact:version" patterns.
            pattern = re.compile(
                rf'("{re.escape(dep_name)}:)[\d.]+[-\w.]*(")',
            )

        new_text = pattern.sub(rf'\g<1>{new_version}\g<3>', text)

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

    # Private rewrite helpers

    @staticmethod
    async def _rewrite_module_bazel(
        path: Path,
        text: str,
        new_version: str,
    ) -> str:
        """Rewrite version in MODULE.bazel."""
        m = _MODULE_VERSION_RE.search(text)
        old_version = m.group(2) if m else '0.0.0'
        new_text = _MODULE_VERSION_RE.sub(rf'\g<1>{new_version}\g<3>', text, count=1)
        if new_text != text:
            await write_file(path, new_text)
            log.info(
                'version_rewritten',
                manifest=str(path),
                old=old_version,
                new=new_version,
            )
        return old_version

    @staticmethod
    async def _rewrite_version_bzl(
        path: Path,
        text: str,
        new_version: str,
    ) -> str:
        """Rewrite VERSION in version.bzl."""
        m = _VERSION_BZL_RE.search(text)
        old_version = m.group(2) if m else '0.0.0'
        new_text = _VERSION_BZL_RE.sub(rf'\g<1>{new_version}\g<3>', text, count=1)
        if new_text != text:
            await write_file(path, new_text)
            log.info(
                'version_rewritten',
                manifest=str(path),
                old=old_version,
                new=new_version,
            )
        return old_version

    @staticmethod
    async def _rewrite_build_version(
        path: Path,
        text: str,
        new_version: str,
    ) -> str:
        """Rewrite version attribute in BUILD/BUILD.bazel."""
        m = _BUILD_VERSION_RE.search(text)
        old_version = m.group(2) if m else '0.0.0'
        new_text = _BUILD_VERSION_RE.sub(rf'\g<1>{new_version}\g<3>', text, count=1)
        if new_text != text:
            await write_file(path, new_text)
            log.info(
                'version_rewritten',
                manifest=str(path),
                old=old_version,
                new=new_version,
            )
        return old_version

    async def detect_license(
        self,
        pkg_path: Path,
        pkg_name: str = '',
    ) -> DetectedLicense:
        """Bazel has no standard manifest-level license field.

        Returns empty so the caller falls back to LICENSE file scanning.
        """
        if not pkg_name:
            pkg_name = pkg_path.name
        return DetectedLicense(value='', source='', package_name=pkg_name)


__all__ = [
    'BazelWorkspace',
]
