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

"""Go-specific workspace check backend (``GoCheckBackend``)."""

from __future__ import annotations

import re

from releasekit.checks._base import BaseCheckBackend
from releasekit.checks._go_fixers import (
    fix_build_system,
    fix_duplicate_dependencies,
)
from releasekit.logging import get_logger
from releasekit.preflight import PreflightResult, SourceContext, run_check, run_version_consistency_check
from releasekit.workspace import Package

logger = get_logger(__name__)

# SemVer pattern for Go modules (v-prefixed).
_GO_SEMVER_RE = re.compile(r'^v?\d+\.\d+\.\d+(-[\w.]+)?$')

# Go module path pattern.
_GO_MODULE_RE = re.compile(r'^[a-z][a-z0-9./_-]+$')


def _go_mod(pkg: Package) -> str:
    """Return the go.mod path string for a package."""
    return str(pkg.path / 'go.mod')


def _find_go_mod_line(text: str, directive: str) -> int:
    """Find the 1-based line number of a go.mod directive.

    Searches for lines starting with ``directive `` (e.g. ``module ``,
    ``go ``).  Returns 0 if not found.
    """
    target = f'{directive} '
    for i, line in enumerate(text.splitlines(), 1):
        if line.startswith(target):
            return i
    return 0


class GoCheckBackend(BaseCheckBackend):
    """Go-specific workspace checks.

    Checks for:
    - ``go.mod`` presence (build system)
    - ``go.sum`` presence (lockfile)
    - Module path naming conventions
    - Version field presence
    - SemVer compliance (Go modules require vX.Y.Z)
    - Self-dependencies
    - Duplicate dependencies
    - Version consistency across modules

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

    def _manifest_path(self, pkg: Package) -> str:
        """Return the go.mod path string for a package."""
        return _go_mod(pkg)

    def check_build_system(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that each module has a go.mod file."""
        run_check(
            result,
            'build_system',
            packages,
            lambda pkg: [(pkg.name, str(pkg.path))] if not (pkg.path / 'go.mod').is_file() else [],
            message='Missing go.mod',
            hint='Run `go mod init` to create go.mod.',
        )

    def check_dependency_resolution(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that go.sum exists alongside go.mod."""
        run_check(
            result,
            'go_sum_present',
            packages,
            lambda pkg: (
                [(pkg.name, _go_mod(pkg))]
                if (pkg.path / 'go.mod').is_file() and not (pkg.path / 'go.sum').is_file()
                else []
            ),
            message='Missing go.sum',
            hint='Run `go mod tidy` to generate go.sum.',
            severity='warning',
        )

    def check_naming_convention(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that module paths follow Go naming conventions."""

        def _probe(pkg: Package) -> list[tuple[str, str | SourceContext]]:
            if _GO_MODULE_RE.match(pkg.name):
                return []
            go_mod_path = pkg.path / 'go.mod'
            try:
                text = go_mod_path.read_text(encoding='utf-8')
                line = _find_go_mod_line(text, 'module')
            except Exception:
                line = 0
            return [
                (
                    pkg.name,
                    SourceContext(
                        path=str(go_mod_path),
                        line=line,
                        key='module',
                        label=f'non-standard: {pkg.name!r}',
                    ),
                )
            ]

        run_check(
            result,
            'naming_convention',
            packages,
            _probe,
            message='Non-standard module paths',
            hint='Go module paths should be lowercase with / separators.',
            severity='warning',
        )

    def check_version_field(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that all modules declare a version."""
        run_check(
            result,
            'version_field',
            packages,
            lambda pkg: [(pkg.name, _go_mod(pkg))] if not pkg.version or pkg.version == '0.0.0' else [],
            message='Missing version',
            hint='Go module versions are set via git tags (e.g. v1.2.3).',
            severity='warning',
        )

    def check_version_pep440(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that versions are valid Go SemVer (vX.Y.Z)."""

        def _probe(pkg: Package) -> list[tuple[str, str | SourceContext]]:
            if not pkg.version or pkg.version == '0.0.0' or _GO_SEMVER_RE.match(pkg.version):
                return []
            go_mod_path = pkg.path / 'go.mod'
            try:
                text = go_mod_path.read_text(encoding='utf-8')
                line = _find_go_mod_line(text, 'module')
            except Exception:
                line = 0
            return [
                (
                    f'{pkg.name}=={pkg.version}',
                    SourceContext(
                        path=str(go_mod_path),
                        line=line,
                        key='module',
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
            hint='Go modules require SemVer tags (e.g. v1.2.3).',
            severity='warning',
        )

    def check_version_consistency(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that all modules share the same version."""
        run_version_consistency_check(
            result,
            'version_consistency',
            packages,
            core_package=self._core_package,
            manifest_path_fn=_go_mod,
            hint_template='All modules should use version {version}.',
            filter_fn=lambda pkg: bool(pkg.version),
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
        """Run all Go-specific auto-fixers."""
        changes: list[str] = []
        changes.extend(fix_build_system(packages, dry_run=dry_run))
        changes.extend(fix_duplicate_dependencies(packages, dry_run=dry_run))
        return changes


__all__ = [
    'GoCheckBackend',
]
