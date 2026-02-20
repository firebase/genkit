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

"""Dart/Flutter-specific workspace check backend (``DartCheckBackend``)."""

from __future__ import annotations

import re

from releasekit.checks._base import BaseCheckBackend
from releasekit.checks._dart_fixers import (
    fix_duplicate_dependencies,
    fix_metadata_completeness,
    fix_publish_to_consistency,
)
from releasekit.logging import get_logger
from releasekit.preflight import PreflightResult, SourceContext, run_check
from releasekit.workspace import Package

logger = get_logger(__name__)

# SemVer pattern for pub.dev packages.
_SEMVER_RE = re.compile(r'^\d+\.\d+\.\d+(-[\w.]+)?(\+[\w.]+)?$')

# Dart package name pattern: lowercase + underscores.
_DART_NAME_RE = re.compile(r'^[a-z][a-z0-9_]*$')


def _pubspec(pkg: Package) -> str:
    """Return the pubspec.yaml path string for a package."""
    return str(pkg.path / 'pubspec.yaml')


def _find_yaml_key_line(text: str, key: str) -> int:
    """Find the 1-based line number of a top-level YAML key.

    Searches for ``key:`` at the start of a line.  Returns 0 if not found.
    """
    target = f'{key}:'
    for i, line in enumerate(text.splitlines(), 1):
        stripped = line.lstrip()
        if stripped.startswith(target):
            return i
    return 0


class DartCheckBackend(BaseCheckBackend):
    """Dart/Flutter-specific workspace checks.

    Checks for:
    - ``pubspec.yaml`` presence (build system)
    - Package naming conventions (lowercase + underscores)
    - Version field presence
    - SemVer compliance
    - Metadata completeness (name, version, description, environment)
    - Self-dependencies
    - Duplicate dependencies
    - Version consistency across packages

    Args:
        core_package: Name of the core package for version consistency.
        plugin_prefix: Expected prefix for plugin package names.
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

    def _manifest_path(self, pkg: Package) -> str:
        """Return the pubspec.yaml path string for a package."""
        return _pubspec(pkg)

    def check_build_system(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that each package has a pubspec.yaml."""
        run_check(
            result,
            'build_system',
            packages,
            lambda pkg: [(pkg.name, str(pkg.path))] if not (pkg.path / 'pubspec.yaml').is_file() else [],
            message='Missing pubspec.yaml',
            hint='Run `dart create` or `flutter create` to initialize.',
        )

    def check_naming_convention(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that package names follow Dart naming conventions."""

        def _probe(pkg: Package) -> list[tuple[str, str | SourceContext]]:
            if _DART_NAME_RE.match(pkg.name):
                return []
            pubspec_path = pkg.path / 'pubspec.yaml'
            try:
                text = pubspec_path.read_text(encoding='utf-8')
                line = _find_yaml_key_line(text, 'name')
            except Exception:
                line = 0
            return [
                (
                    pkg.name,
                    SourceContext(
                        path=str(pubspec_path),
                        line=line,
                        key='name',
                        label=f'non-standard: {pkg.name!r}',
                    ),
                )
            ]

        run_check(
            result,
            'naming_convention',
            packages,
            _probe,
            message='Non-standard names',
            hint='Dart package names should be lowercase_with_underscores.',
            severity='warning',
        )

    def check_metadata_completeness(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that pubspec.yaml has required fields for pub.dev."""

        def _probe(pkg: Package) -> list[tuple[str, str | SourceContext]]:
            if not pkg.is_publishable:
                return []
            pubspec = pkg.path / 'pubspec.yaml'
            if not pubspec.is_file():
                return []
            try:
                text = pubspec.read_text(encoding='utf-8')
            except OSError:
                return []
            missing: list[str] = []
            for field in ('description', 'repository', 'environment'):
                if f'{field}:' not in text:
                    missing.append(field)
            if missing:
                line = _find_yaml_key_line(text, 'name') or 1
                return [
                    (
                        f'{pkg.name}: missing {", ".join(missing)}',
                        SourceContext(
                            path=str(pubspec),
                            line=line,
                            label=f'missing: {", ".join(missing)}',
                        ),
                    )
                ]
            return []

        run_check(
            result,
            'metadata_completeness',
            packages,
            _probe,
            message='Incomplete metadata',
            hint='pub.dev requires description, repository, and environment in pubspec.yaml.',
            severity='warning',
            joiner='; ',
        )

    def check_version_pep440(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that versions are valid SemVer."""

        def _probe(pkg: Package) -> list[tuple[str, str | SourceContext]]:
            if not pkg.version or pkg.version == '0.0.0' or _SEMVER_RE.match(pkg.version):
                return []
            pubspec_path = pkg.path / 'pubspec.yaml'
            try:
                text = pubspec_path.read_text(encoding='utf-8')
                line = _find_yaml_key_line(text, 'version')
            except Exception:
                line = 0
            return [
                (
                    f'{pkg.name}=={pkg.version}',
                    SourceContext(
                        path=str(pubspec_path),
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
            hint='Dart packages must use SemVer (e.g. 1.2.3).',
            severity='warning',
        )

    def check_publish_classifier_consistency(
        self,
        packages: list[Package],
        result: PreflightResult,
        exclude_publish: list[str] | None = None,
    ) -> None:
        """Check that ``publish_to: none`` is consistent with publish config."""

        def _probe(pkg: Package) -> list[tuple[str, str | SourceContext]]:
            pubspec = pkg.path / 'pubspec.yaml'
            if not pubspec.is_file():
                return []
            try:
                text = pubspec.read_text(encoding='utf-8')
            except OSError:
                return []
            has_publish_none = 'publish_to: none' in text or "publish_to: 'none'" in text
            line = _find_yaml_key_line(text, 'publish_to') or _find_yaml_key_line(text, 'name') or 1
            if pkg.is_publishable and has_publish_none:
                return [
                    (
                        f'{pkg.name}: publishable but publish_to:none',
                        SourceContext(
                            path=str(pubspec),
                            line=line,
                            key='publish_to',
                            label='publish_to:none but publishable',
                        ),
                    )
                ]
            if not pkg.is_publishable and not has_publish_none:
                return [
                    (
                        f'{pkg.name}: excluded but missing publish_to:none',
                        SourceContext(
                            path=str(pubspec),
                            line=line,
                            key='publish_to',
                            label='missing publish_to:none',
                        ),
                    )
                ]
            return []

        run_check(
            result,
            'publish_to_consistency',
            packages,
            _probe,
            message='publish_to mismatch',
            hint='Set publish_to: none for non-publishable packages.',
            severity='warning',
            joiner='; ',
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
        """Run all Dart-specific auto-fixers."""
        changes: list[str] = []
        changes.extend(fix_publish_to_consistency(packages, dry_run=dry_run))
        changes.extend(fix_metadata_completeness(packages, dry_run=dry_run))
        changes.extend(fix_duplicate_dependencies(packages, dry_run=dry_run))
        return changes


__all__ = [
    'DartCheckBackend',
]
