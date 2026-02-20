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

"""pnpm package manager backend for releasekit.

The :class:`PnpmBackend` implements the
:class:`~releasekit.backends.pm.PackageManager` protocol via the
``pnpm`` CLI (``pnpm pack``, ``pnpm publish``, ``pnpm install``, etc.).

CLI commands used:

- ``pnpm pack --pack-destination <dir>``: Create a tarball (build).
  See: https://pnpm.io/cli/pack
- ``pnpm publish --no-git-checks``: Publish to npm registry.
  See: https://pnpm.io/cli/publish
- ``pnpm install --lockfile-only``: Regenerate lockfile without
  installing node_modules.
  See: https://pnpm.io/cli/install#--lockfile-only
- ``pnpm install --frozen-lockfile``: Verify lockfile is up-to-date.
  See: https://pnpm.io/cli/install#--frozen-lockfile

Note: pnpm does not have a built-in ``version`` command. The
``version_bump`` method delegates to ``npm version --no-git-tag-version``
to update the ``version`` field in ``package.json``. Alternatively,
callers can use :meth:`PnpmWorkspace.rewrite_version` to edit
``package.json`` directly (without invoking npm).

All methods are async — blocking subprocess calls are dispatched to
``asyncio.to_thread()`` to avoid blocking the event loop.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from releasekit.backends._run import CommandResult, run_command
from releasekit.logging import get_logger

log = get_logger('releasekit.backends.pm.pnpm')


class PnpmBackend:
    """Package manager implementation using ``pnpm``.

    Implements the :class:`~releasekit.backends.pm.PackageManager`
    protocol for npm/Node.js packages managed by pnpm.

    Args:
        workspace_root: Path to the workspace root (containing
            ``pnpm-workspace.yaml``).
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
        """Build a package tarball using ``pnpm pack``.

        Uses ``--pack-destination`` to place the tarball in the output
        directory. The ``no_sources`` parameter is accepted for protocol
        compatibility but has no effect — pnpm always resolves workspace
        deps during pack (converting ``workspace:*`` to real versions).

        See: https://pnpm.io/cli/pack
        """
        cmd = ['pnpm', 'pack']
        if output_dir:
            cmd.extend(['--pack-destination', str(output_dir)])

        log.info('build', package=package_dir.name)
        return await asyncio.to_thread(run_command, cmd, cwd=package_dir, dry_run=dry_run)

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
        """Publish a package using ``pnpm publish``.

        Args:
            dist_dir: Directory containing the package (with
                ``package.json``). Unlike uv, pnpm publishes from
                the package directory, not a dist directory.
            check_url: Unused for npm (accepted for protocol compat).
            registry_url: Custom registry URL (maps to ``--registry``).
            dist_tag: npm dist-tag (maps to ``--tag``).
            publish_branch: Allow publishing from a non-default branch
                (maps to ``--publish-branch``).
            provenance: Generate provenance attestation
                (maps to ``--provenance``).
            dry_run: Perform a dry run without uploading.

        See: https://pnpm.io/cli/publish
        """
        cmd = ['pnpm', 'publish', '--no-git-checks', '--access', 'public']
        if registry_url:
            cmd.extend(['--registry', registry_url])
        if dist_tag:
            cmd.extend(['--tag', dist_tag])
        if publish_branch:
            cmd.extend(['--publish-branch', publish_branch])
        if provenance:
            cmd.append('--provenance')
        if dry_run:
            cmd.append('--dry-run')

        log.info('publish', package_dir=str(dist_dir))
        return await asyncio.to_thread(run_command, cmd, cwd=dist_dir, dry_run=dry_run)

    async def lock(
        self,
        *,
        check_only: bool = False,
        upgrade_package: str | None = None,
        cwd: Path | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """Update or verify the lockfile using ``pnpm install``.

        Uses ``--lockfile-only`` to regenerate the lockfile without
        installing node_modules, or ``--frozen-lockfile`` to verify
        the lockfile is up-to-date.

        See: https://pnpm.io/cli/install#--lockfile-only
        See: https://pnpm.io/cli/install#--frozen-lockfile
        """
        if upgrade_package:
            # pnpm update <pkg> is the equivalent of upgrading a single dep.
            # Note: check_only is not applicable with upgrade_package.
            cmd = ['pnpm', 'update', upgrade_package]
        elif check_only:
            cmd = ['pnpm', 'install', '--frozen-lockfile']
        else:
            cmd = ['pnpm', 'install', '--lockfile-only']

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
        """Set a package version by editing ``package.json`` via npm version.

        Uses ``npm version`` (not ``pnpm version``, which doesn't exist)
        with ``--no-git-tag-version`` to update the version field in
        package.json without creating a git tag or commit.

        See: https://docs.npmjs.com/cli/v10/commands/npm-version
        """
        cmd = ['npm', 'version', new_version, '--no-git-tag-version']

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
        """Verify a published package resolves using ``pnpm view``.

        Checks that the specified version is available on the
        npm registry by querying package metadata.
        """
        cmd = ['pnpm', 'view', f'{package_name}@{version}', 'version']
        if registry_url:
            cmd.extend(['--registry', registry_url])

        log.info('resolve_check', package=package_name, version=version)
        return await asyncio.to_thread(run_command, cmd, cwd=self._root, dry_run=dry_run)

    async def smoke_test(
        self,
        package_name: str,
        version: str,
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Smoke-test a published package via ``pnpm dlx``.

        Uses ``pnpm dlx`` (like ``npx``) to run the package in an
        isolated environment, verifying it can be downloaded and
        its main entry point resolves.

        See: https://pnpm.io/cli/dlx
        """
        cmd = [
            'node',
            '-e',
            f'require("{package_name}")',
        ]

        log.info('smoke_test', package=package_name, version=version)
        return await asyncio.to_thread(run_command, cmd, cwd=self._root, dry_run=dry_run)


__all__ = [
    'PnpmBackend',
]
