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

"""Dart/Flutter package manager backend for releasekit.

The :class:`DartBackend` implements the
:class:`~releasekit.backends.pm.PackageManager` protocol via the
``dart`` CLI (``dart pub publish``, ``dart pub get``, etc.).

All methods are async — blocking subprocess calls are dispatched to
``asyncio.to_thread()`` to avoid blocking the event loop.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from releasekit.backends._run import CommandResult, run_command
from releasekit.logging import get_logger

log = get_logger('releasekit.backends.pm.dart')


class DartBackend:
    """Dart :class:`~releasekit.backends.pm.PackageManager` implementation.

    Uses ``dart pub`` for package operations. Also supports Flutter
    packages via the same ``dart pub`` interface.

    Args:
        workspace_root: Path to the Dart workspace root.
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
        """Dart packages don't have a separate build step for publishing.

        Runs ``dart pub get`` to ensure dependencies are resolved, which
        is the closest equivalent to a pre-publish build step.
        """
        cmd = ['dart', 'pub', 'get']

        log.info('build', package=package_dir.name)
        return await asyncio.to_thread(
            run_command,
            cmd,
            cwd=package_dir,
            dry_run=dry_run,
        )

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
        """Publish a Dart package using ``dart pub publish``.

        Args:
            dist_dir: Path to the package directory (contains ``pubspec.yaml``).
            check_url: Ignored (pub.dev has no check URL).
            registry_url: Custom pub server URL (``--server``).
            dist_tag: Ignored (pub.dev has no dist-tag concept).
            publish_branch: Ignored.
            provenance: Ignored.
            dry_run: If True, uses ``--dry-run`` flag.
        """
        cmd = ['dart', 'pub', 'publish', '--force']
        if dry_run:
            cmd.append('--dry-run')
        if registry_url:
            cmd.extend(['--server', registry_url])

        log.info('publish', package=dist_dir.name, dry_run=dry_run)
        return await asyncio.to_thread(
            run_command,
            cmd,
            cwd=dist_dir,
            dry_run=dry_run,
        )

    async def lock(
        self,
        *,
        check_only: bool = False,
        upgrade_package: str | None = None,
        cwd: Path | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """Run ``dart pub get`` or ``dart pub upgrade`` to resolve deps."""
        work_dir = cwd or self._root
        if upgrade_package:
            cmd = ['dart', 'pub', 'upgrade', upgrade_package]
        elif check_only:
            # dart pub get with --dry-run to check if deps are resolved.
            cmd = ['dart', 'pub', 'get', '--dry-run']
        else:
            cmd = ['dart', 'pub', 'get']

        log.info('lock', check_only=check_only, cwd=str(work_dir))
        return await asyncio.to_thread(
            run_command,
            cmd,
            cwd=work_dir,
            dry_run=dry_run,
        )

    async def version_bump(
        self,
        package_dir: Path,
        new_version: str,
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Bump version in ``pubspec.yaml``.

        Dart doesn't have a built-in version bump command, so this
        rewrites the ``version:`` field in ``pubspec.yaml`` directly.
        The actual rewrite is handled by the workspace backend; this
        method just validates the version is set.
        """
        log.info(
            'version_bump',
            package=package_dir.name,
            version=new_version,
        )
        # The workspace backend handles pubspec.yaml rewriting.
        # This is a validation-only step.
        return CommandResult(
            command=['dart', 'version-bump', new_version],
            return_code=0,
            stdout=f'Version {new_version} will be set in pubspec.yaml.',
            stderr='',
            duration=0.0,
            dry_run=dry_run,
        )

    async def resolve_check(
        self,
        package_name: str,
        version: str,
        *,
        registry_url: str | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """Verify a Dart package is available via ``dart pub cache add``."""
        cmd = ['dart', 'pub', 'cache', 'add', package_name, '--version', version]

        log.info('resolve_check', package=package_name, version=version)
        return await asyncio.to_thread(
            run_command,
            cmd,
            cwd=self._root,
            dry_run=dry_run,
        )

    async def smoke_test(
        self,
        package_name: str,
        version: str,
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Smoke-test a Dart package by adding it as a dependency."""
        cmd = ['dart', 'pub', 'cache', 'add', package_name, '--version', version]

        log.info('smoke_test', package=package_name, version=version)
        return await asyncio.to_thread(
            run_command,
            cmd,
            cwd=self._root,
            dry_run=dry_run,
        )


__all__ = [
    'DartBackend',
]
