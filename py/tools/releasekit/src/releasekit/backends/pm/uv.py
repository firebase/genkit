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

"""uv package manager backend for releasekit.

The :class:`UvBackend` implements the
:class:`~releasekit.backends.pm.PackageManager` protocol via the
``uv`` CLI (``uv build``, ``uv publish``, ``uv lock``, etc.).

All methods are async — blocking subprocess calls are dispatched to
``asyncio.to_thread()`` to avoid blocking the event loop.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from releasekit.backends._run import CommandResult, run_command
from releasekit.logging import get_logger

log = get_logger('releasekit.backends.pm.uv')


class UvBackend:
    """Default :class:`~releasekit.backends.pm.PackageManager` implementation using ``uv``.

    Args:
        workspace_root: Path to the workspace root (contains ``pyproject.toml``
            with ``[tool.uv.workspace]``).
    """

    def __init__(self, workspace_root: Path) -> None:
        """Initialize with the workspace root path."""
        self._root = workspace_root

    async def build(
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
        return await asyncio.to_thread(run_command, cmd, cwd=self._root, dry_run=dry_run)

    async def publish(
        self,
        dist_dir: Path,
        *,
        check_url: str | None = None,
        registry_url: str | None = None,
        dist_tag: str | None = None,
        publish_branch: str | None = None,
        provenance: bool = False,
        dry_run: bool = False,
    ) -> CommandResult:
        """Publish distributions using ``uv publish``.

        Args:
            dist_dir: Directory containing built distributions.
            check_url: Index URL to check for existing files (skips duplicates).
            registry_url: Upload endpoint URL. Mapped to ``uv publish --publish-url``
                (``uv publish`` has no ``--index-url`` flag). Defaults to PyPI
                if not specified.
            dist_tag: Ignored (npm-only, accepted for protocol compat).
            publish_branch: Ignored (npm-only, accepted for protocol compat).
            provenance: Ignored (npm-only, accepted for protocol compat).
            dry_run: Perform a dry run without uploading.
        """
        cmd = ['uv', 'publish']
        if check_url:
            cmd.extend(['--check-url', check_url])
        if registry_url:
            # uv publish uses --publish-url (not --index-url) for the
            # upload endpoint.
            cmd.extend(['--publish-url', registry_url])
        cmd.append(str(dist_dir))

        log.info('publish', dist_dir=str(dist_dir))
        return await asyncio.to_thread(run_command, cmd, cwd=self._root, dry_run=dry_run)

    async def lock(
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
        return await asyncio.to_thread(run_command, cmd, cwd=effective_cwd, dry_run=dry_run)

    async def version_bump(
        self,
        package_dir: Path,
        new_version: str,
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Set a package version using ``uv version``."""
        cmd = ['uv', 'version', '--frozen', new_version]

        log.info('version_bump', package=package_dir.name, version=new_version)
        return await asyncio.to_thread(run_command, cmd, cwd=package_dir, dry_run=dry_run)

    async def resolve_check(
        self,
        package_name: str,
        version: str,
        *,
        registry_url: str | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """Verify a published package resolves using ``uv pip install --dry-run``."""
        cmd = ['uv', 'pip', 'install', '--dry-run', f'{package_name}=={version}']
        if registry_url:
            # --index-url is deprecated; use --default-index.
            cmd.extend(['--default-index', registry_url])

        log.info('resolve_check', package=package_name, version=version)
        return await asyncio.to_thread(run_command, cmd, cwd=self._root, dry_run=dry_run)

    async def smoke_test(
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
        return await asyncio.to_thread(run_command, cmd, cwd=self._root, dry_run=dry_run)


__all__ = [
    'UvBackend',
]
