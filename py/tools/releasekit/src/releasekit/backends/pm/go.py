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

"""Go package manager backend for releasekit.

The :class:`GoBackend` implements the
:class:`~releasekit.backends.pm.PackageManager` protocol via the
``go`` CLI (``go build``, ``go test``, ``go mod tidy``, etc.).

Go modules are published by tagging commits in VCS — there is no
separate ``publish`` step. The ``publish`` method is a no-op that
returns a success result with a note that Go uses VCS tags.

All methods are async — blocking subprocess calls are dispatched to
``asyncio.to_thread()`` to avoid blocking the event loop.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from releasekit.backends._run import CommandResult, run_command
from releasekit.logging import get_logger

log = get_logger('releasekit.backends.pm.go')


class GoBackend:
    """Go :class:`~releasekit.backends.pm.PackageManager` implementation.

    Args:
        workspace_root: Path to the Go workspace root (contains ``go.work``).
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
        """Build a Go module using ``go build``."""
        cmd = ['go', 'build', './...']
        env_extra: dict[str, str] = {}
        if output_dir:
            env_extra['GOBIN'] = str(output_dir)

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
        """No-op: Go modules are published via VCS tags.

        Returns a synthetic success result. The actual publishing happens
        when the VCS backend pushes tags — the Go module proxy
        (``proxy.golang.org``) fetches modules from VCS automatically.
        """
        log.info(
            'publish_noop',
            reason='Go modules are published via VCS tags, not a registry upload.',
        )
        return CommandResult(
            command=['go', 'publish', '(noop)'],
            return_code=0,
            stdout='Go modules are published via VCS tags.',
            stderr='',
            duration=0.0,
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
        """Run ``go mod tidy`` to synchronize go.sum."""
        work_dir = cwd or self._root
        if check_only:
            # go mod tidy doesn't have a check-only mode, but we can
            # verify by running tidy and checking for changes.
            cmd = ['go', 'mod', 'tidy']
        elif upgrade_package:
            cmd = ['go', 'get', '-u', upgrade_package]
        else:
            cmd = ['go', 'mod', 'tidy']

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
        """No-op: Go module versions are determined by VCS tags.

        Go modules don't have a version field in ``go.mod`` — the version
        is derived from the git tag. Returns a synthetic success result.
        """
        log.info(
            'version_bump_noop',
            package=package_dir.name,
            version=new_version,
            reason='Go module versions are set by VCS tags.',
        )
        return CommandResult(
            command=['go', 'version-bump', '(noop)'],
            return_code=0,
            stdout=f'Go version {new_version} will be set by VCS tag.',
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
        """Verify a Go module version is fetchable via ``go list``."""
        module_version = f'{package_name}@v{version}'
        cmd = ['go', 'list', '-m', module_version]

        log.info('resolve_check', module=package_name, version=version)
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
        """Smoke-test a Go module by fetching it with ``go get``."""
        module_version = f'{package_name}@v{version}'
        cmd = ['go', 'get', module_version]

        log.info('smoke_test', module=package_name, version=version)
        return await asyncio.to_thread(
            run_command,
            cmd,
            cwd=self._root,
            dry_run=dry_run,
        )


__all__ = [
    'GoBackend',
]
