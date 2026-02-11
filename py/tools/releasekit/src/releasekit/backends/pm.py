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

"""PackageManager protocol and uv backend for releasekit.

The :class:`PackageManager` protocol defines the interface for build,
publish, lock, and verification operations. The default implementation,
:class:`UvBackend`, delegates to ``uv`` via :func:`run_command`.

Key design decisions (from roadmap D-2, D-3, D-7, D-9):

- ``build()`` uses ``--no-sources`` (D-3) to verify packages build
  without workspace source overrides.
- ``publish()`` uses ``--check-url`` (D-7) for native retry handling.
- ``lock()`` supports ``--upgrade-package`` (D-2) for lock file freshness.
- ``resolve_check()`` uses ``uv pip install --dry-run`` (D-9) for
  consistency with the uv toolchain.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from releasekit.backends._run import CommandResult, run_command
from releasekit.logging import get_logger

log = get_logger('releasekit.backends.pm')


@runtime_checkable
class PackageManager(Protocol):
    """Protocol for package build and publish operations.

    All methods accept ``dry_run`` to support preview mode.
    """

    def build(
        self,
        package_dir: Path,
        *,
        output_dir: Path | None = None,
        no_sources: bool = True,
        dry_run: bool = False,
    ) -> CommandResult:
        """Build a distribution (sdist + wheel) for a package.

        Args:
            package_dir: Path to the package directory containing pyproject.toml.
            output_dir: Directory to place built distributions.
            no_sources: Use ``--no-sources`` to verify builds without workspace
                source overrides (D-3).
            dry_run: Log the command without executing.
        """
        ...

    def publish(
        self,
        dist_dir: Path,
        *,
        check_url: str | None = None,
        index_url: str | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """Publish distributions to a package index.

        Args:
            dist_dir: Directory containing .tar.gz and .whl files.
            check_url: URL to check for existing versions (D-7).
            index_url: Custom index URL (e.g., Test PyPI).
            dry_run: Log the command without executing.
        """
        ...

    def lock(
        self,
        *,
        check_only: bool = False,
        upgrade_package: str | None = None,
        cwd: Path | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """Update or verify the lock file.

        Args:
            check_only: Only verify the lock file is up-to-date (exit 1 if not).
            upgrade_package: Upgrade a specific package in the lock file (D-2).
            cwd: Working directory (defaults to workspace root).
            dry_run: Log the command without executing.
        """
        ...

    def version_bump(
        self,
        package_dir: Path,
        new_version: str,
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Bump the version of a package via ``uv version``.

        Args:
            package_dir: Path to the package directory.
            new_version: New version string (PEP 440).
            dry_run: Log the command without executing.
        """
        ...

    def resolve_check(
        self,
        package_name: str,
        version: str,
        *,
        index_url: str | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """Verify a published package can be resolved by pip (D-9).

        Args:
            package_name: Name of the package on PyPI.
            version: Expected version.
            index_url: Custom index URL.
            dry_run: Log the command without executing.
        """
        ...

    def smoke_test(
        self,
        package_name: str,
        version: str,
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Smoke-test a published package by importing it.

        Args:
            package_name: Package name to test.
            version: Version to install.
            dry_run: Log the command without executing.
        """
        ...


class UvBackend:
    """Default :class:`PackageManager` implementation using ``uv``.

    Args:
        workspace_root: Path to the workspace root (contains ``pyproject.toml``
            with ``[tool.uv.workspace]``).
    """

    def __init__(self, workspace_root: Path) -> None:
        """Initialize with the workspace root path."""
        self._root = workspace_root

    def build(
        self,
        package_dir: Path,
        *,
        output_dir: Path | None = None,
        no_sources: bool = True,
        dry_run: bool = False,
    ) -> CommandResult:
        """Build a package distribution using ``uv build``."""
        cmd = ['uv', 'build']
        if no_sources:
            cmd.append('--no-sources')
        if output_dir:
            cmd.extend(['--out-dir', str(output_dir)])
        cmd.append(str(package_dir))

        log.info('build', package=package_dir.name, no_sources=no_sources)
        return run_command(cmd, cwd=self._root, dry_run=dry_run)

    def publish(
        self,
        dist_dir: Path,
        *,
        check_url: str | None = None,
        index_url: str | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """Publish distributions using ``uv publish``."""
        cmd = ['uv', 'publish']
        if check_url:
            cmd.extend(['--check-url', check_url])
        if index_url:
            cmd.extend(['--index-url', index_url])
        cmd.append(str(dist_dir))

        log.info('publish', dist_dir=str(dist_dir))
        return run_command(cmd, cwd=self._root, dry_run=dry_run)

    def lock(
        self,
        *,
        check_only: bool = False,
        upgrade_package: str | None = None,
        cwd: Path | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """Update or verify the lock file using ``uv lock``."""
        cmd = ['uv', 'lock']
        if check_only:
            cmd.append('--check')
        if upgrade_package:
            cmd.extend(['--upgrade-package', upgrade_package])

        effective_cwd = cwd or self._root
        log.info('lock', check_only=check_only, upgrade_package=upgrade_package)
        return run_command(cmd, cwd=effective_cwd, dry_run=dry_run)

    def version_bump(
        self,
        package_dir: Path,
        new_version: str,
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Set a package version using ``uv version``."""
        cmd = ['uv', 'version', '--frozen', new_version]

        log.info('version_bump', package=package_dir.name, version=new_version)
        return run_command(cmd, cwd=package_dir, dry_run=dry_run)

    def resolve_check(
        self,
        package_name: str,
        version: str,
        *,
        index_url: str | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """Verify a published package resolves using ``uv pip install --dry-run``."""
        cmd = ['uv', 'pip', 'install', '--dry-run', f'{package_name}=={version}']
        if index_url:
            cmd.extend(['--index-url', index_url])

        log.info('resolve_check', package=package_name, version=version)
        return run_command(cmd, cwd=self._root, dry_run=dry_run)

    def smoke_test(
        self,
        package_name: str,
        version: str,
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Smoke-test a published package via ``uv run --with``."""
        import_name = package_name.replace('-', '_')
        cmd = [
            'uv',
            'run',
            '--no-project',
            '--with',
            f'{package_name}=={version}',
            'python',
            '-c',
            f'import {import_name}; print({import_name}.__version__)',
        ]

        log.info('smoke_test', package=package_name, version=version)
        return run_command(cmd, cwd=self._root, dry_run=dry_run)


__all__ = [
    'PackageManager',
    'UvBackend',
]
