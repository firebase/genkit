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

"""Maven/Gradle workspace backend for releasekit.

The :class:`MavenWorkspace` implements the
:class:`~releasekit.backends.workspace.Workspace` protocol by parsing
``pom.xml`` (Maven) or ``settings.gradle`` / ``build.gradle`` (Gradle)
files.

Maven multi-module layout (directory name is arbitrary)::

    java/
    ├── pom.xml              ← parent POM (lists <modules>)
    ├── core/
    │   └── pom.xml          ← module: com.example:core
    ├── plugins/
    │   ├── google/
    │   │   └── pom.xml      ← module: com.example:plugin-google
    │   └── vertex/
    │       └── pom.xml      ← module: com.example:plugin-vertex
    └── samples/
        └── ...

Gradle multi-project layout (directory name is arbitrary)::

    java/
    ├── settings.gradle      ← root (lists include ':core', ':plugins:google')
    ├── build.gradle          ← root build file
    ├── core/
    │   └── build.gradle     ← subproject
    └── plugins/
        ├── google/
        │   └── build.gradle
        └── vertex/
            └── build.gradle

Version handling:

    Maven stores versions in ``pom.xml`` under ``<version>``.
    Gradle stores versions in ``build.gradle`` or ``gradle.properties``.
    The ``rewrite_version`` method handles both formats.
"""

from __future__ import annotations

import fnmatch
import re
import xml.etree.ElementTree as ET  # noqa: N817, S405
from pathlib import Path

import tomlkit
import tomlkit.exceptions
import tomlkit.items

from releasekit.backends.workspace._io import read_file, write_file
from releasekit.backends.workspace._types import Package
from releasekit.logging import get_logger

log = get_logger('releasekit.backends.workspace.maven')

# Maven POM namespace.
_POM_NS = '{http://maven.apache.org/POM/4.0.0}'

# Regex to parse Gradle version from build.gradle or gradle.properties.
_GRADLE_VERSION_RE = re.compile(r"""^version\s*=\s*['"]?([^'"\s]+)['"]?""", re.MULTILINE)

# Regex to parse Gradle group from build.gradle.
_GRADLE_GROUP_RE = re.compile(r"""^group\s*=\s*['"]?([^'"\s]+)['"]?""", re.MULTILINE)

# Regex to parse VERSION_NAME from gradle.properties.
# Matches: VERSION_NAME=1.2.3  or  VERSION_NAME = 1.2.3
_GRADLE_PROPS_VERSION_RE = re.compile(
    r'^(?!\s*#)VERSION_NAME\s*=\s*(.+?)\s*$',
    re.MULTILINE,
)

# Regex to extract project paths from settings.gradle / settings.gradle.kts.
# Matches ':project' strings in any include variant:
#   Groovy:     include ':core', ':plugins:google'
#   Kotlin DSL: include(":core", ":plugins:google")
# In settings.gradle, ':project' strings only appear in include directives.
_SETTINGS_INCLUDE_RE = re.compile(r"""['"]:([\w:/-]+)['"]""")

# Regex to parse Gradle dependency declarations.
# Matches: implementation 'group:artifact:version'
#          api "group:artifact:version"
#          compileOnly 'group:artifact:version'
_GRADLE_DEP_RE = re.compile(
    r"""(?:implementation|api|compileOnly|runtimeOnly|testImplementation)\s*"""
    r"""['"]([^'"]+:[^'"]+)(?::[\d.]+[-\w.]*)['"]""",
)


def _parse_pom_modules(pom_path: Path) -> list[str]:
    """Parse ``<modules>`` from a Maven parent POM."""
    try:
        tree = ET.parse(pom_path)  # noqa: S314
    except ET.ParseError:
        return []
    root = tree.getroot()
    modules_elem = root.find(f'{_POM_NS}modules')
    if modules_elem is None:
        # Try without namespace.
        modules_elem = root.find('modules')
    if modules_elem is None:
        return []
    return [m.text for m in modules_elem.findall(f'{_POM_NS}module') if m.text] + [
        m.text for m in modules_elem.findall('module') if m.text
    ]


def _parse_pom_metadata(pom_path: Path) -> dict[str, str]:
    """Parse groupId, artifactId, and version from a POM file."""
    try:
        tree = ET.parse(pom_path)  # noqa: S314
    except ET.ParseError:
        return {}
    root = tree.getroot()

    def _find(tag: str) -> str:
        elem = root.find(f'{_POM_NS}{tag}')
        if elem is None:
            elem = root.find(tag)
        return elem.text if elem is not None and elem.text else ''

    return {
        'groupId': _find('groupId'),
        'artifactId': _find('artifactId'),
        'version': _find('version'),
    }


def _parse_pom_dependencies(pom_path: Path) -> list[str]:
    """Parse dependency artifactIds from a POM file."""
    try:
        tree = ET.parse(pom_path)  # noqa: S314
    except ET.ParseError:
        return []
    root = tree.getroot()
    deps: list[str] = []
    for deps_elem in [
        root.find(f'{_POM_NS}dependencies'),
        root.find('dependencies'),
    ]:
        if deps_elem is None:
            continue
        for dep in list(deps_elem):
            aid = dep.find(f'{_POM_NS}artifactId')
            if aid is None:
                aid = dep.find('artifactId')
            if aid is not None and aid.text:
                deps.append(aid.text)
    return deps


def _read_gradle_properties_version(props_path: Path) -> str:
    """Read ``VERSION_NAME`` from ``gradle.properties``.

    Returns the version string, or empty string if not found.
    """
    if not props_path.is_file():
        return ''
    text = props_path.read_text(encoding='utf-8')
    m = _GRADLE_PROPS_VERSION_RE.search(text)
    return m.group(1).strip() if m else ''


def _write_gradle_properties_version(props_path: Path, new_version: str) -> str:
    """Rewrite ``VERSION_NAME`` in ``gradle.properties``.

    Returns the old version string.
    """
    text = props_path.read_text(encoding='utf-8')
    m = _GRADLE_PROPS_VERSION_RE.search(text)
    old_version = m.group(1).strip() if m else '0.0.0'
    # Use a capturing-group regex to preserve surrounding content.
    pattern = re.compile(r'^(?!\s*#)(VERSION_NAME\s*=\s*)(.+?)(\s*)$', re.MULTILINE)
    new_text = pattern.sub(rf'\g<1>{new_version}\g<3>', text, count=1)
    if new_text != text:
        props_path.write_text(new_text, encoding='utf-8')
    return old_version


def _read_version_catalog_version(
    catalog_path: Path,
    version_key: str = 'projectVersion',
) -> str:
    """Read a version from ``gradle/libs.versions.toml``.

    Looks for ``key = "x.y.z"`` under the ``[versions]`` section.

    Args:
        catalog_path: Path to ``libs.versions.toml``.
        version_key: Key name under ``[versions]`` (default: ``projectVersion``).

    Returns:
        The version string, or empty string if not found.
    """
    if not catalog_path.is_file():
        return ''
    text = catalog_path.read_text(encoding='utf-8')
    try:
        doc = tomlkit.parse(text)
        version = doc.get('versions', {}).get(version_key)
        return str(version) if version else ''
    except tomlkit.exceptions.TOMLKitError:
        log.warning('version_catalog_parse_failed', path=str(catalog_path))
        return ''


def _write_version_catalog_version(
    catalog_path: Path,
    new_version: str,
    version_key: str = 'projectVersion',
) -> str:
    """Rewrite a version in ``gradle/libs.versions.toml``.

    Uses ``tomlkit`` to parse and rewrite the TOML file, preserving
    formatting and comments.

    Args:
        catalog_path: Path to ``libs.versions.toml``.
        new_version: New version string.
        version_key: Key name under ``[versions]``.

    Returns:
        The old version string.
    """
    text = catalog_path.read_text(encoding='utf-8')
    try:
        doc = tomlkit.parse(text)
    except tomlkit.exceptions.TOMLKitError as e:
        log.warning('version_catalog_parse_failed', path=str(catalog_path), error=str(e))
        return '0.0.0'

    versions_table = doc.get('versions')
    if not isinstance(versions_table, tomlkit.items.Table):
        return '0.0.0'

    old_version = versions_table.get(version_key)
    if old_version is None:
        return '0.0.0'

    old_version_str = str(old_version)
    if old_version_str != new_version:
        versions_table[version_key] = new_version
        catalog_path.write_text(tomlkit.dumps(doc), encoding='utf-8')

    return old_version_str


def _parse_gradle_dependencies(build_file: Path) -> list[str]:
    """Parse dependency coordinates from a Gradle build file.

    Returns a list of ``group:artifact`` strings (without version).
    """
    if not build_file.is_file():
        return []
    text = build_file.read_text(encoding='utf-8')
    return _GRADLE_DEP_RE.findall(text)


def _parse_settings_gradle(settings_path: Path) -> list[str]:
    """Parse project includes from ``settings.gradle``."""
    if not settings_path.is_file():
        return []
    text = settings_path.read_text(encoding='utf-8')
    # Match include ':core', ':plugins:google', etc.
    return _SETTINGS_INCLUDE_RE.findall(text)


class MavenWorkspace:
    """Java :class:`~releasekit.backends.workspace.Workspace` implementation.

    Supports both Maven (``pom.xml``) and Gradle (``settings.gradle``)
    multi-module/multi-project layouts.

    Args:
        workspace_root: Path to the Java workspace root.
    """

    def __init__(self, workspace_root: Path) -> None:
        """Initialize with the Java workspace root."""
        self._root = workspace_root.resolve()

    def _is_gradle(self) -> bool:
        """Check if the workspace uses Gradle."""
        return (self._root / 'settings.gradle').is_file() or (self._root / 'settings.gradle.kts').is_file()

    async def discover(
        self,
        *,
        exclude_patterns: list[str] | None = None,
    ) -> list[Package]:
        """Discover all Java modules/subprojects in the workspace.

        For Maven: parses ``<modules>`` from the parent POM.
        For Gradle: parses ``include`` from ``settings.gradle``.

        Args:
            exclude_patterns: Glob patterns to exclude modules by name.

        Returns:
            Sorted list of discovered Java packages.
        """
        if self._is_gradle():
            return await self._discover_gradle(exclude_patterns=exclude_patterns)
        return await self._discover_maven(exclude_patterns=exclude_patterns)

    async def _discover_maven(
        self,
        *,
        exclude_patterns: list[str] | None = None,
    ) -> list[Package]:
        """Discover Maven modules from parent POM."""
        parent_pom = self._root / 'pom.xml'
        if not parent_pom.is_file():
            log.warning('pom_not_found', root=str(self._root))
            return []

        module_names = _parse_pom_modules(parent_pom)

        # Collect all artifact IDs for internal dep classification.
        all_artifacts: dict[str, Path] = {}
        for mod_name in module_names:
            mod_dir = self._root / mod_name
            mod_pom = mod_dir / 'pom.xml'
            if mod_pom.is_file():
                meta = _parse_pom_metadata(mod_pom)
                aid = meta.get('artifactId', mod_name)
                all_artifacts[aid] = mod_dir

        exclude = exclude_patterns or []
        packages: list[Package] = []

        for mod_name in module_names:
            mod_dir = self._root / mod_name
            mod_pom = mod_dir / 'pom.xml'
            if not mod_pom.is_file():
                continue

            meta = _parse_pom_metadata(mod_pom)
            name = meta.get('artifactId', mod_name)
            version = meta.get('version', '0.0.0')

            if any(fnmatch.fnmatch(name, pat) for pat in exclude):
                log.debug('excluded', module=name)
                continue

            dep_names = _parse_pom_dependencies(mod_pom)
            internal_deps = [d for d in dep_names if d in all_artifacts and d != name]
            external_deps = [d for d in dep_names if d not in all_artifacts]

            packages.append(
                Package(
                    name=name,
                    version=version,
                    path=mod_dir,
                    manifest_path=mod_pom,
                    internal_deps=internal_deps,
                    external_deps=external_deps,
                    all_deps=dep_names,
                    is_publishable=True,
                )
            )

        packages.sort(key=lambda p: p.name)
        log.info(
            'discovered_maven',
            count=len(packages),
            modules=[p.name for p in packages],
        )
        return packages

    async def _discover_gradle(
        self,
        *,
        exclude_patterns: list[str] | None = None,
    ) -> list[Package]:
        """Discover Gradle subprojects from settings.gradle."""
        settings = self._root / 'settings.gradle'
        if not settings.is_file():
            settings = self._root / 'settings.gradle.kts'
        if not settings.is_file():
            log.warning('settings_gradle_not_found', root=str(self._root))
            return []

        includes = _parse_settings_gradle(settings)
        exclude = exclude_patterns or []
        packages: list[Package] = []

        # First pass: collect group:artifact identifiers for internal
        # dependency classification.
        all_names: set[str] = set()
        artifact_to_name: dict[str, str] = {}
        for inc in includes:
            name = inc.replace(':', '-').lstrip('-')
            all_names.add(name)
            rel_path = inc.replace(':', '/')
            proj_dir = self._root / rel_path
            build_file = proj_dir / 'build.gradle'
            if not build_file.is_file():
                build_file = proj_dir / 'build.gradle.kts'
            if not build_file.is_file():
                continue
            text = build_file.read_text(encoding='utf-8')
            group_match = _GRADLE_GROUP_RE.search(text)
            if group_match:
                artifact_to_name[f'{group_match.group(1)}:{name}'] = name

        # Second pass: discover packages with dependency classification.
        for inc in includes:
            rel_path = inc.replace(':', '/')
            proj_dir = self._root / rel_path
            name = inc.replace(':', '-').lstrip('-')

            if any(fnmatch.fnmatch(name, pat) for pat in exclude):
                log.debug('excluded', project=name)
                continue

            build_file = proj_dir / 'build.gradle'
            if not build_file.is_file():
                build_file = proj_dir / 'build.gradle.kts'
            if not build_file.is_file():
                continue

            text = build_file.read_text(encoding='utf-8')
            version_match = _GRADLE_VERSION_RE.search(text)
            version = version_match.group(1) if version_match else ''

            # Fall back to gradle.properties VERSION_NAME.
            if not version:
                version = _read_gradle_properties_version(proj_dir / 'gradle.properties')
            # Fall back to root gradle.properties.
            if not version:
                version = _read_gradle_properties_version(self._root / 'gradle.properties')
            # Fall back to version catalog.
            if not version:
                version = _read_version_catalog_version(self._root / 'gradle' / 'libs.versions.toml')
            if not version:
                version = '0.0.0'

            dep_coords = _parse_gradle_dependencies(build_file)
            internal_deps: list[str] = []
            external_deps: list[str] = []
            for coord in dep_coords:
                if coord in artifact_to_name and artifact_to_name[coord] != name:
                    internal_deps.append(artifact_to_name[coord])
                else:
                    external_deps.append(coord)

            packages.append(
                Package(
                    name=name,
                    version=version,
                    path=proj_dir,
                    manifest_path=build_file,
                    internal_deps=internal_deps,
                    external_deps=external_deps,
                    all_deps=dep_coords,
                    is_publishable=True,
                )
            )

        packages.sort(key=lambda p: p.name)
        log.info(
            'discovered_gradle',
            count=len(packages),
            projects=[p.name for p in packages],
        )
        return packages

    async def rewrite_version(
        self,
        manifest_path: Path,
        new_version: str,
    ) -> str:
        """Rewrite the version in a Maven POM or Gradle build file.

        Supported manifest types:

        - ``pom.xml``: rewrites ``<version>`` element.
        - ``build.gradle`` / ``build.gradle.kts``: rewrites ``version = '...'``.
        - ``gradle.properties``: rewrites ``VERSION_NAME=...``.
        - ``libs.versions.toml``: rewrites version key under ``[versions]``.

        Args:
            manifest_path: Path to the manifest file.
            new_version: New version string.

        Returns:
            The old version string.
        """
        if manifest_path.name == 'gradle.properties':
            old = _write_gradle_properties_version(manifest_path, new_version)
            log.info('version_rewritten', manifest=str(manifest_path), old=old, new=new_version)
            return old
        if manifest_path.name == 'libs.versions.toml':
            old = _write_version_catalog_version(manifest_path, new_version)
            log.info('version_rewritten', manifest=str(manifest_path), old=old, new=new_version)
            return old
        if manifest_path.name.startswith('build.gradle'):
            return self._rewrite_gradle_version(manifest_path, new_version)
        return self._rewrite_pom_version(manifest_path, new_version)

    @staticmethod
    def _rewrite_pom_version(pom_path: Path, new_version: str) -> str:
        """Rewrite ``<version>`` in a POM file.

        Uses :mod:`xml.etree.ElementTree` to locate the project-level
        ``<version>`` element, then performs a targeted string
        replacement to preserve the original file formatting.
        """
        text = pom_path.read_text(encoding='utf-8')
        try:
            root = ET.fromstring(text)  # noqa: S314
        except ET.ParseError:
            return '0.0.0'

        # Find the project-level <version> (with or without namespace).
        version_elem = root.find(f'{_POM_NS}version')
        if version_elem is None:
            version_elem = root.find('version')
        if version_elem is None or not version_elem.text:
            return '0.0.0'

        old_version = version_elem.text
        # Targeted replacement of the first occurrence of the old version tag.
        old_tag = f'<version>{old_version}</version>'
        new_tag = f'<version>{new_version}</version>'
        new_text = text.replace(old_tag, new_tag, 1)
        if new_text != text:
            pom_path.write_text(new_text, encoding='utf-8')
            log.info(
                'version_rewritten',
                manifest=str(pom_path),
                old=old_version,
                new=new_version,
            )
        return old_version

    @staticmethod
    def _rewrite_gradle_version(build_file: Path, new_version: str) -> str:
        """Rewrite ``version = '...'`` in a Gradle build file."""
        text = build_file.read_text(encoding='utf-8')
        m = _GRADLE_VERSION_RE.search(text)
        old_version = m.group(1) if m else '0.0.0'
        new_text = _GRADLE_VERSION_RE.sub(f"version = '{new_version}'", text, count=1)
        if new_text != text:
            build_file.write_text(new_text, encoding='utf-8')
            log.info(
                'version_rewritten',
                manifest=str(build_file),
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
        """Rewrite a dependency version in a POM or Gradle build file."""
        text = await read_file(manifest_path)

        if manifest_path.name.startswith('build.gradle'):
            # Gradle: 'group:artifact:version' patterns — regex is
            # unavoidable here since Gradle build files are Groovy/Kotlin.
            pattern = re.compile(
                rf"('{re.escape(dep_name)}:)[\d.]+[-\w.]*(')",
            )
            new_text = pattern.sub(rf'\g<1>{new_version}\g<2>', text)
        else:
            new_text = self._rewrite_pom_dependency(text, dep_name, new_version)

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

    @staticmethod
    def _rewrite_pom_dependency(text: str, dep_name: str, new_version: str) -> str:
        """Rewrite a dependency version in POM XML text.

        Uses :mod:`xml.etree.ElementTree` to locate the ``<dependency>``
        element whose ``<artifactId>`` matches *dep_name*, reads its
        ``<version>`` text, then performs a targeted string replacement
        to preserve the original file formatting.
        """
        try:
            root = ET.fromstring(text)  # noqa: S314
        except ET.ParseError:
            return text

        # Search both namespaced and non-namespaced dependency blocks.
        for deps_tag in (f'{_POM_NS}dependencies', 'dependencies'):
            deps_elem = root.find(deps_tag)
            if deps_elem is None:
                continue
            for dep in list(deps_elem):
                # Find artifactId.
                aid = dep.find(f'{_POM_NS}artifactId')
                if aid is None:
                    aid = dep.find('artifactId')
                if aid is None or aid.text != dep_name:
                    continue
                # Find version.
                ver = dep.find(f'{_POM_NS}version')
                if ver is None:
                    ver = dep.find('version')
                if ver is None or not ver.text:
                    continue
                # Targeted replacement: replace the first occurrence of
                # this specific <artifactId>...<version>old</version>
                # block with the new version.
                old_tag = f'<version>{ver.text}</version>'
                new_tag = f'<version>{new_version}</version>'
                # Find the position of this artifactId in the text and
                # replace the next <version> tag after it.
                aid_pos = text.find(f'<artifactId>{dep_name}</artifactId>')
                if aid_pos == -1:
                    continue
                ver_pos = text.find(old_tag, aid_pos)
                if ver_pos == -1:
                    continue
                return text[:ver_pos] + new_tag + text[ver_pos + len(old_tag) :]

        return text


__all__ = [
    'MavenWorkspace',
]
