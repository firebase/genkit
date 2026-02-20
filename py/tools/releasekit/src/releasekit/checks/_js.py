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

"""JavaScript/TypeScript-specific workspace check backend (``JsCheckBackend``)."""

from __future__ import annotations

import json
import re

from releasekit.checks._base import BaseCheckBackend
from releasekit.checks._js_fixers import (
    fix_duplicate_dependencies,
    fix_metadata_completeness,
    fix_private_field_consistency,
)
from releasekit.logging import get_logger
from releasekit.preflight import PreflightResult, SourceContext, run_check
from releasekit.workspace import Package

logger = get_logger(__name__)

# SemVer pattern for npm packages.
_SEMVER_RE = re.compile(r'^\d+\.\d+\.\d+(-[\w.]+)?$')

# npm scoped package pattern: @scope/name.
_SCOPED_RE = re.compile(r'^@[\w-]+/[\w.-]+$')

# npm package name pattern (unscoped).
_NPM_NAME_RE = re.compile(r'^[a-z][\w.-]*$')


def _read_package_json(pkg: Package) -> dict[str, object] | None:
    """Read and parse package.json for a package."""
    pj = pkg.path / 'package.json'
    if not pj.is_file():
        return None
    try:
        return json.loads(pj.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return None


def _pkg_json(pkg: Package) -> str:
    """Return the package.json path string for a package."""
    return str(pkg.path / 'package.json')


def _find_json_key_line(text: str, key: str) -> int:
    """Find the 1-based line number of a JSON key in file content.

    Searches for ``"key":`` patterns.  Returns 0 if not found.
    """
    target = f'"{key}"'
    for i, line in enumerate(text.splitlines(), 1):
        if target in line and ':' in line[line.index(target) :]:
            return i
    return 0


class JsCheckBackend(BaseCheckBackend):
    """JavaScript/TypeScript-specific workspace checks.

    Checks for:
    - ``package.json`` presence (build system)
    - TypeScript ``d.ts`` type declarations (type markers)
    - npm naming conventions (``@scope/name``)
    - Version field presence
    - SemVer compliance
    - Metadata completeness (name, version, description, license, repository)
    - Self-dependencies
    - Duplicate dependencies
    - Version consistency across packages
    - ``private: true`` consistency with publish config

    Args:
        core_package: Name of the core package for version consistency.
        plugin_prefix: Expected prefix (e.g. ``@genkit/``).
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
        """Return the package.json path string for a package."""
        return _pkg_json(pkg)

    def check_build_system(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that each package has a package.json."""
        run_check(
            result,
            'build_system',
            packages,
            lambda pkg: [(pkg.name, str(pkg.path))] if not (pkg.path / 'package.json').is_file() else [],
            message='Missing package.json',
            hint='Run `npm init` or `pnpm init` to create package.json.',
        )

    def check_type_markers(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that TypeScript packages have ``types`` field in package.json."""

        def _probe(pkg: Package) -> list[tuple[str, str | SourceContext]]:
            if not pkg.is_publishable:
                return []
            pj = _read_package_json(pkg)
            if pj is None:
                return []
            if 'types' not in pj and 'typings' not in pj:
                if (pkg.path / 'tsconfig.json').is_file():
                    pj_path = pkg.path / 'package.json'
                    try:
                        text = pj_path.read_text(encoding='utf-8')
                        line = _find_json_key_line(text, 'name') or 1
                    except Exception:
                        line = 1
                    return [
                        (
                            pkg.name,
                            SourceContext(
                                path=str(pj_path),
                                line=line,
                                key='types',
                                label='types field missing',
                            ),
                        )
                    ]
            return []

        run_check(
            result,
            'type_declarations',
            packages,
            _probe,
            message='Missing types field',
            hint='Add "types" field to package.json for TypeScript packages.',
            severity='warning',
        )

    def check_naming_convention(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that package names follow npm naming conventions."""

        def _probe(pkg: Package) -> list[tuple[str, str | SourceContext]]:
            if _SCOPED_RE.match(pkg.name) or _NPM_NAME_RE.match(pkg.name):
                return []
            pj_path = pkg.path / 'package.json'
            try:
                text = pj_path.read_text(encoding='utf-8')
                line = _find_json_key_line(text, 'name')
            except Exception:
                line = 0
            return [
                (
                    pkg.name,
                    SourceContext(
                        path=str(pj_path),
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
            hint='npm names should be lowercase. Scoped: @scope/name. Unscoped: name.',
            severity='warning',
        )

    def check_metadata_completeness(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that package.json has required fields for npm."""

        def _probe(pkg: Package) -> list[tuple[str, str | SourceContext]]:
            if not pkg.is_publishable:
                return []
            pj = _read_package_json(pkg)
            if pj is None:
                return []
            missing: list[str] = []
            for field in ('name', 'version', 'description', 'license', 'repository'):
                if field not in pj or not pj[field]:
                    missing.append(field)
            if missing:
                pj_path = pkg.path / 'package.json'
                try:
                    text = pj_path.read_text(encoding='utf-8')
                    line = _find_json_key_line(text, 'name') or 1
                except Exception:
                    line = 1
                return [
                    (
                        f'{pkg.name}: missing {", ".join(missing)}',
                        SourceContext(
                            path=str(pj_path),
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
            hint='npm requires name, version, description, license, repository.',
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
            pj_path = pkg.path / 'package.json'
            try:
                text = pj_path.read_text(encoding='utf-8')
                line = _find_json_key_line(text, 'version')
            except Exception:
                line = 0
            return [
                (
                    f'{pkg.name}=={pkg.version}',
                    SourceContext(
                        path=str(pj_path),
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
            hint='npm packages must use SemVer (e.g. 1.2.3).',
            severity='warning',
        )

    def check_publish_classifier_consistency(
        self,
        packages: list[Package],
        result: PreflightResult,
        exclude_publish: list[str] | None = None,
    ) -> None:
        """Check that ``private: true`` is consistent with publish config."""

        def _probe(pkg: Package) -> list[tuple[str, str | SourceContext]]:
            pj = _read_package_json(pkg)
            if pj is None:
                return []
            is_private = pj.get('private', False) is True
            pj_path = pkg.path / 'package.json'
            try:
                text = pj_path.read_text(encoding='utf-8')
                line = _find_json_key_line(text, 'private') or _find_json_key_line(text, 'name') or 1
            except Exception:
                line = 1
            if pkg.is_publishable and is_private:
                return [
                    (
                        f'{pkg.name}: publishable but private:true',
                        SourceContext(
                            path=str(pj_path),
                            line=line,
                            key='private',
                            label='private:true but publishable',
                        ),
                    )
                ]
            if not pkg.is_publishable and not is_private:
                return [
                    (
                        f'{pkg.name}: excluded but missing private:true',
                        SourceContext(
                            path=str(pj_path),
                            line=line,
                            key='private',
                            label='missing private:true',
                        ),
                    )
                ]
            return []

        run_check(
            result,
            'private_field_consistency',
            packages,
            _probe,
            message='Private field mismatch',
            hint='Set "private": true for non-publishable packages.',
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
        """Run all JavaScript-specific auto-fixers."""
        changes: list[str] = []
        changes.extend(fix_private_field_consistency(packages, dry_run=dry_run))
        changes.extend(fix_metadata_completeness(packages, dry_run=dry_run))
        changes.extend(fix_duplicate_dependencies(packages, dry_run=dry_run))
        return changes


__all__ = [
    'JsCheckBackend',
]
