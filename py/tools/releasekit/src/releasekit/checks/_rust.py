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

"""Rust/Cargo-specific workspace check backend (``RustCheckBackend``)."""

from __future__ import annotations

import re

from releasekit.checks._base import BaseCheckBackend
from releasekit.checks._rust_fixers import (
    fix_duplicate_dependencies,
    fix_metadata_completeness,
    fix_wildcard_dependencies,
)
from releasekit.logging import get_logger
from releasekit.preflight import PreflightResult, SourceContext, find_key_line, run_check
from releasekit.workspace import Package

logger = get_logger(__name__)

# SemVer pattern for Cargo crates.
_SEMVER_RE = re.compile(r'^\d+\.\d+\.\d+(-[\w.]+)?$')

# Crate name pattern: lowercase alphanumeric + hyphens/underscores.
_CRATE_NAME_RE = re.compile(r'^[a-z][a-z0-9_-]*$')


def _cargo_toml(pkg: Package) -> str:
    """Return the Cargo.toml path string for a package."""
    return str(pkg.path / 'Cargo.toml')


class RustCheckBackend(BaseCheckBackend):
    """Rust/Cargo-specific workspace checks.

    Checks for:
    - ``Cargo.toml`` presence (build system)
    - ``Cargo.lock`` presence (lockfile)
    - Crate naming conventions
    - Version field presence
    - SemVer compliance
    - Metadata completeness (name, version, edition, description, license)
    - Self-dependencies
    - Duplicate dependencies
    - Version consistency across crates
    - Wildcard dependency versions (``*``)

    Args:
        core_package: Name of the core crate for version consistency.
        plugin_prefix: Expected prefix for plugin crate names.
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
        """Return the Cargo.toml path string for a package."""
        return _cargo_toml(pkg)

    def check_build_system(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that each crate has a Cargo.toml."""
        run_check(
            result,
            'build_system',
            packages,
            lambda pkg: [(pkg.name, str(pkg.path))] if not (pkg.path / 'Cargo.toml').is_file() else [],
            message='Missing Cargo.toml',
            hint='Run `cargo init` to create Cargo.toml.',
        )

    def check_dependency_resolution(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that Cargo.lock exists in the workspace root."""
        check_name = 'cargo_lock_present'
        # Only check the first package's parent for workspace-level lock.
        if packages:
            ws_root = packages[0].path.parent
            # Walk up to find workspace root (where Cargo.lock lives).
            for parent in [packages[0].path, *packages[0].path.parents]:
                if (parent / 'Cargo.lock').is_file():
                    result.add_pass(check_name)
                    return
                if (parent / 'Cargo.toml').is_file():
                    ws_root = parent
            result.add_warning(
                check_name,
                f'Missing Cargo.lock in {ws_root}',
                hint='Run `cargo generate-lockfile` to create Cargo.lock.',
                context=[str(ws_root)],
            )
        else:
            result.add_pass(check_name)

    def check_naming_convention(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that crate names follow Rust naming conventions."""

        def _probe(pkg: Package) -> list[tuple[str, str | SourceContext]]:
            if _CRATE_NAME_RE.match(pkg.name):
                return []
            cargo_path = pkg.path / 'Cargo.toml'
            try:
                content = cargo_path.read_text(encoding='utf-8')
                line = find_key_line(content, 'name')
            except Exception:
                line = 0
            return [
                (
                    pkg.name,
                    SourceContext(
                        path=str(cargo_path),
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
            message='Non-standard crate names',
            hint='Crate names should be lowercase with hyphens or underscores.',
            severity='warning',
        )

    def check_metadata_completeness(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check that Cargo.toml has required fields for crates.io."""

        def _probe(pkg: Package) -> list[tuple[str, str | SourceContext]]:
            if not pkg.is_publishable:
                return []
            cargo_toml = pkg.path / 'Cargo.toml'
            if not cargo_toml.is_file():
                return []
            try:
                text = cargo_toml.read_text(encoding='utf-8')
            except OSError:
                return []
            missing: list[str] = []
            for field in ('description', 'license', 'repository'):
                if f'{field} =' not in text and f'{field}=' not in text:
                    missing.append(field)
            if missing:
                line = find_key_line(text, 'name', section='package') or 1
                return [
                    (
                        f'{pkg.name}: missing {", ".join(missing)}',
                        SourceContext(
                            path=str(cargo_toml),
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
            hint='crates.io requires description, license, and repository in Cargo.toml.',
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
            cargo_path = pkg.path / 'Cargo.toml'
            try:
                content = cargo_path.read_text(encoding='utf-8')
                line = find_key_line(content, 'version')
            except Exception:
                line = 0
            return [
                (
                    f'{pkg.name}=={pkg.version}',
                    SourceContext(
                        path=str(cargo_path),
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
            hint='Cargo crates must use SemVer (e.g. 1.2.3).',
            severity='warning',
        )

    def check_pinned_deps_in_libraries(
        self,
        packages: list[Package],
        result: PreflightResult,
    ) -> None:
        """Check for wildcard (*) dependency versions."""

        def _probe(pkg: Package) -> list[tuple[str, str | SourceContext]]:
            cargo_toml = pkg.path / 'Cargo.toml'
            if not cargo_toml.is_file():
                return []
            try:
                text = cargo_toml.read_text(encoding='utf-8')
            except OSError:
                return []
            match = re.search(r'=\s*"\*"', text)
            if match:
                line = text[: match.start()].count('\n') + 1
                return [
                    (
                        pkg.name,
                        SourceContext(
                            path=str(cargo_toml),
                            line=line,
                            label='wildcard version "*"',
                        ),
                    )
                ]
            return []

        run_check(
            result,
            'wildcard_dependencies',
            packages,
            _probe,
            message='Wildcard deps',
            hint='Avoid version = "*" in dependencies. Use specific version ranges.',
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
        """Run all Rust-specific auto-fixers."""
        changes: list[str] = []
        changes.extend(fix_metadata_completeness(packages, dry_run=dry_run))
        changes.extend(fix_wildcard_dependencies(packages, dry_run=dry_run))
        changes.extend(fix_duplicate_dependencies(packages, dry_run=dry_run))
        return changes


__all__ = [
    'RustCheckBackend',
]
