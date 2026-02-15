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

"""Java/Kotlin-specific workspace check backend (``JavaCheckBackend``)."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET  # noqa: N817, S405
from pathlib import Path

from releasekit.checks._base import BaseCheckBackend
from releasekit.checks._java_fixers import (
    fix_duplicate_dependencies,
    fix_metadata_completeness,
    fix_placeholder_urls,
)
from releasekit.logging import get_logger
from releasekit.preflight import PreflightResult, SourceContext, run_check
from releasekit.workspace import Package

logger = get_logger(__name__)

_POM_NS = '{http://maven.apache.org/POM/4.0.0}'

# SemVer pattern (loose): major.minor.patch with optional pre-release.
_SEMVER_RE = re.compile(r'^\d+\.\d+\.\d+(-[\w.]+)?$')

# SNAPSHOT version pattern.
_SNAPSHOT_RE = re.compile(r'-SNAPSHOT$', re.IGNORECASE)

# Maven Central required POM elements (project-level).
_MAVEN_CENTRAL_REQUIRED = ('name', 'description', 'url', 'licenses', 'developers', 'scm')


def _find_xml_tag_line(text: str, tag: str) -> int:
    """Find the 1-based line number of an XML tag in file content.

    Searches for ``<tag>`` or ``<tag `` patterns.  Returns 0 if not found.
    """
    targets = (f'<{tag}>', f'<{tag} ')
    for i, line in enumerate(text.splitlines(), 1):
        for target in targets:
            if target in line:
                return i
    return 0


def _find_gradle_key_line(text: str, key: str) -> int:
    """Find the 1-based line number of a Gradle key assignment.

    Searches for ``key =`` or ``key=`` at the start of a line.
    Returns 0 if not found.
    """
    for i, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith(f'{key} =') or stripped.startswith(f'{key}='):
            return i
    return 0


def _pom_find(root: ET.Element, tag: str) -> ET.Element | None:
    """Find a POM element with or without namespace."""
    elem = root.find(f'{_POM_NS}{tag}')
    if elem is None:
        elem = root.find(tag)
    return elem


def _read_pom(manifest_path: Path) -> ET.Element | None:
    """Parse a POM file, returning the root element or None."""
    if not manifest_path.name.endswith('.xml'):
        return None
    try:
        tree = ET.parse(manifest_path)  # noqa: S314
        return tree.getroot()
    except (ET.ParseError, OSError):
        return None


def _read_gradle(manifest_path: Path) -> str:
    """Read a Gradle build file, returning its text or empty string."""
    if not manifest_path.name.startswith('build.gradle'):
        return ''
    try:
        return manifest_path.read_text(encoding='utf-8')
    except OSError:
        return ''


class JavaCheckBackend(BaseCheckBackend):
    """Java/Kotlin-specific workspace checks.

    Checks for:
    - SNAPSHOT dependencies in release builds
    - Maven Central metadata requirements
    - Version consistency across modules
    - Version field presence
    - Duplicate dependencies
    - Build system presence (pom.xml or build.gradle)
    - SemVer compliance
    - Self-dependencies
    - Metadata completeness (groupId, artifactId, version)

    Args:
        core_package: Name of the core module for version consistency.
        plugin_prefix: Expected prefix for plugin module names.
    """

    def __init__(
        self,
        *,
        core_package: str = '',
        plugin_prefix: str = '',
        **_kwargs: object,
    ) -> None:
        """Initialize with optional project-specific configuration."""
        self._core_package = core_package
        self._plugin_prefix = plugin_prefix

    def check_metadata_completeness(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that POM files have groupId, artifactId, version.

        For Gradle projects, checks that build.gradle has ``group``
        and ``version`` declarations.
        """
        check_name = 'metadata_completeness'
        incomplete: list[str] = []
        locations: list[str | SourceContext] = []

        for pkg in packages:
            root = _read_pom(pkg.manifest_path)
            if root is not None:
                missing: list[str] = []
                for field in ('groupId', 'artifactId', 'version'):
                    elem = _pom_find(root, field)
                    if elem is None or not elem.text:
                        missing.append(field)
                if missing:
                    incomplete.append(f'{pkg.name}: missing {", ".join(missing)}')
                    try:
                        text = pkg.manifest_path.read_text(encoding='utf-8')
                        line = _find_xml_tag_line(text, 'project') or 1
                    except Exception:
                        line = 1
                    locations.append(
                        SourceContext(
                            path=str(pkg.manifest_path),
                            line=line,
                            label=f'missing: {", ".join(missing)}',
                        )
                    )
                continue

            text = _read_gradle(pkg.manifest_path)
            if text:
                missing_g: list[str] = []
                if not re.search(r'^group\s*=', text, re.MULTILINE):
                    missing_g.append('group')
                if not re.search(r'^version\s*=', text, re.MULTILINE):
                    missing_g.append('version')
                if missing_g:
                    incomplete.append(f'{pkg.name}: missing {", ".join(missing_g)}')
                    locations.append(
                        SourceContext(
                            path=str(pkg.manifest_path),
                            line=1,
                            label=f'missing: {", ".join(missing_g)}',
                        )
                    )

        if incomplete:
            result.add_failure(
                check_name,
                f'Incomplete metadata: {"; ".join(incomplete)}',
                hint='Ensure all modules declare groupId/group, artifactId, and version.',
                context=locations,
            )
        else:
            result.add_pass(check_name)

    def check_build_system(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that each module has a pom.xml or build.gradle."""
        run_check(
            result,
            'build_system',
            packages,
            lambda pkg: (
                [(pkg.name, str(pkg.path))]
                if not (pkg.path / 'pom.xml').is_file()
                and not (pkg.path / 'build.gradle').is_file()
                and not (pkg.path / 'build.gradle.kts').is_file()
                else []
            ),
            message='No build file',
            hint='Each module needs pom.xml or build.gradle.',
        )

    def check_version_pep440(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that versions are valid SemVer (Maven convention)."""

        def _probe(pkg: Package) -> list[tuple[str, str | SourceContext]]:
            if not pkg.version or _SEMVER_RE.match(pkg.version):
                return []
            try:
                text = pkg.manifest_path.read_text(encoding='utf-8')
                line = _find_xml_tag_line(text, 'version') or _find_gradle_key_line(text, 'version') or 0
            except Exception:
                line = 0
            return [
                (
                    f'{pkg.name}=={pkg.version}',
                    SourceContext(
                        path=str(pkg.manifest_path),
                        line=line,
                        key='version',
                        label=f'not SemVer: {pkg.version!r}',
                    ),
                )
            ]

        run_check(
            result,
            'version_semver',
            packages,
            _probe,
            message='Non-SemVer versions',
            hint='Maven artifacts should use SemVer (e.g. 1.2.3 or 1.2.3-beta.1).',
            severity='warning',
        )

    def check_dependency_resolution(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check for -SNAPSHOT dependencies (release blocker).

        Release builds must not depend on -SNAPSHOT versions.
        This is the #1 cause of broken Maven releases.
        """
        check_name = 'snapshot_dependencies'
        snapshots: list[str] = []
        locations: list[str | SourceContext] = []
        for pkg in packages:
            root = _read_pom(pkg.manifest_path)
            if root is None:
                continue
            try:
                pom_text = pkg.manifest_path.read_text(encoding='utf-8')
            except Exception:
                pom_text = ''
            for deps_tag in (f'{_POM_NS}dependencies', 'dependencies'):
                deps_elem = root.find(deps_tag)
                if deps_elem is None:
                    continue
                for dep in list(deps_elem):
                    ver_elem = dep.find(f'{_POM_NS}version')
                    if ver_elem is None:
                        ver_elem = dep.find('version')
                    if ver_elem is not None and ver_elem.text and _SNAPSHOT_RE.search(ver_elem.text):
                        aid = dep.find(f'{_POM_NS}artifactId')
                        if aid is None:
                            aid = dep.find('artifactId')
                        dep_name = aid.text if aid is not None and aid.text else '?'
                        snapshots.append(f'{pkg.name} → {dep_name}:{ver_elem.text}')
                        line = _find_xml_tag_line(pom_text, 'dependencies') if pom_text else 0
                        locations.append(
                            SourceContext(
                                path=str(pkg.manifest_path),
                                line=line,
                                label=f'SNAPSHOT: {dep_name}:{ver_elem.text}',
                            )
                        )

        if snapshots:
            result.add_failure(
                check_name,
                f'SNAPSHOT deps: {"; ".join(snapshots)}',
                hint='Replace -SNAPSHOT versions with release versions before publishing.',
                context=locations,
            )
        else:
            result.add_pass(check_name)

    def check_readme_field(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that POM has <description> or Gradle has description."""
        check_name = 'description_field'
        missing_pkgs: list[str] = []
        locations: list[str | SourceContext] = []
        for pkg in packages:
            if not pkg.is_publishable:
                continue
            root = _read_pom(pkg.manifest_path)
            if root is not None:
                desc = _pom_find(root, 'description')
                if desc is None or not desc.text:
                    missing_pkgs.append(pkg.name)
                    try:
                        text = pkg.manifest_path.read_text(encoding='utf-8')
                        line = _find_xml_tag_line(text, 'project') or 1
                    except Exception:
                        line = 1
                    locations.append(
                        SourceContext(
                            path=str(pkg.manifest_path),
                            line=line,
                            label='<description> missing',
                        )
                    )
                continue
            text = _read_gradle(pkg.manifest_path)
            if text and not re.search(r'description\s*=', text):
                missing_pkgs.append(pkg.name)
                locations.append(
                    SourceContext(
                        path=str(pkg.manifest_path),
                        line=1,
                        label='description missing',
                    )
                )

        if missing_pkgs:
            result.add_warning(
                check_name,
                f'Missing description: {", ".join(missing_pkgs)}',
                hint='Add <description> to pom.xml or description to build.gradle.',
                context=locations,
            )
        else:
            result.add_pass(check_name)

    def check_changelog_url(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that POM has <url> and <scm> for Maven Central."""
        check_name = 'maven_central_metadata'
        incomplete: list[str] = []
        locations: list[str | SourceContext] = []
        for pkg in packages:
            if not pkg.is_publishable:
                continue
            root = _read_pom(pkg.manifest_path)
            if root is None:
                continue
            missing_tags: list[str] = []
            for tag in _MAVEN_CENTRAL_REQUIRED:
                if _pom_find(root, tag) is None:
                    missing_tags.append(tag)
            if missing_tags:
                incomplete.append(f'{pkg.name}: missing {", ".join(missing_tags)}')
                try:
                    text = pkg.manifest_path.read_text(encoding='utf-8')
                    line = _find_xml_tag_line(text, 'project') or 1
                except Exception:
                    line = 1
                locations.append(
                    SourceContext(
                        path=str(pkg.manifest_path),
                        line=line,
                        label=f'missing: {", ".join(missing_tags)}',
                    )
                )

        if incomplete:
            result.add_warning(
                check_name,
                f'Maven Central requirements: {"; ".join(incomplete)}',
                hint='Maven Central requires name, description, url, licenses, developers, scm.',
                context=locations,
            )
        else:
            result.add_pass(check_name)

    def check_placeholder_urls(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check for placeholder URLs in POM <url> or <scm>."""
        check_name = 'placeholder_urls'
        placeholders: list[str] = []
        locations: list[str | SourceContext] = []
        for pkg in packages:
            root = _read_pom(pkg.manifest_path)
            if root is None:
                continue
            url_elem = _pom_find(root, 'url')
            if url_elem is not None and url_elem.text:
                if 'example.com' in url_elem.text or not url_elem.text.strip():
                    placeholders.append(f'{pkg.name}: <url>')
                    try:
                        text = pkg.manifest_path.read_text(encoding='utf-8')
                        line = _find_xml_tag_line(text, 'url') or 1
                    except Exception:
                        line = 1
                    locations.append(
                        SourceContext(
                            path=str(pkg.manifest_path),
                            line=line,
                            key='url',
                            label='placeholder URL',
                        )
                    )

        if placeholders:
            result.add_warning(
                check_name,
                f'Placeholder URLs: {", ".join(placeholders)}',
                hint='Replace placeholder URLs with real project URLs.',
                context=locations,
            )
        else:
            result.add_pass(check_name)

    def check_legacy_setup_files(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check for mixed build systems (pom.xml + build.gradle)."""
        run_check(
            result,
            'mixed_build_systems',
            packages,
            lambda pkg: (
                [(pkg.name, str(pkg.path))]
                if (pkg.path / 'pom.xml').is_file()
                and ((pkg.path / 'build.gradle').is_file() or (pkg.path / 'build.gradle.kts').is_file())
                else []
            ),
            message='Both pom.xml and build.gradle',
            hint='Use one build system per module. Remove the unused build file.',
            severity='warning',
        )

    def run_fixes(
        self,
        packages: list[Package],
        *,
        exclude_publish: list[str] | None = None,
        repo_owner: str = '',
        repo_name: str = '',
        namespace_dirs: list[str] | None = None,
        library_dirs: list[str] | None = None,
        plugin_dirs: list[str] | None = None,
        dry_run: bool = False,
    ) -> list[str]:
        """Run all Java-specific auto-fixers."""
        changes: list[str] = []
        changes.extend(fix_placeholder_urls(packages, dry_run=dry_run))
        changes.extend(fix_metadata_completeness(packages, dry_run=dry_run))
        changes.extend(fix_duplicate_dependencies(packages, dry_run=dry_run))
        return changes


__all__ = [
    'JavaCheckBackend',
]
