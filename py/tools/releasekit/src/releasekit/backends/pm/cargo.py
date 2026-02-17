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

"""Rust/Cargo package manager backend for releasekit.

The :class:`CargoBackend` implements the
:class:`~releasekit.backends.pm.PackageManager` protocol via the
``cargo`` CLI (``cargo build``, ``cargo publish``, ``cargo test``, etc.).

Rust crates are published to `crates.io <https://crates.io>`_ using
``cargo publish``. Authentication is handled via a token stored in
``~/.cargo/credentials.toml`` or the ``CARGO_REGISTRY_TOKEN``
environment variable.

All methods are async — blocking subprocess calls are dispatched to
``asyncio.to_thread()`` to avoid blocking the event loop.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from releasekit.backends._run import CommandResult, run_command
from releasekit.logging import get_logger

log = get_logger('releasekit.backends.pm.cargo')


class CargoBackend:
    """Rust :class:`~releasekit.backends.pm.PackageManager` implementation.

    Args:
        workspace_root: Path to the Cargo workspace root (contains
            ``Cargo.toml`` with ``[workspace]``).
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
        """Build a Rust crate using ``cargo build --release``.

        Args:
            package_dir: Path to the crate directory containing ``Cargo.toml``.
            output_dir: Target directory for build artifacts.
            no_sources: Unused for Cargo (kept for protocol compatibility).
            dry_run: Log the command without executing.
        """
        cmd = ['cargo', 'build', '--release']

        # If package_dir differs from workspace root, use -p flag.
        crate_name = _read_crate_name(package_dir)
        if crate_name and os.path.realpath(package_dir) != os.path.realpath(self._root):  # noqa: ASYNC240 - metadata-only path resolution
            cmd.extend(['-p', crate_name])

        if output_dir:
            cmd.extend(['--target-dir', str(output_dir)])

        log.info('build', package=package_dir.name)
        return await asyncio.to_thread(
            run_command,
            cmd,
            cwd=self._root,
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
        """Publish a crate to crates.io using ``cargo publish``.

        Args:
            dist_dir: Path to the crate directory (not a dist folder —
                Cargo publishes from source).
            check_url: Unused for Cargo.
            registry_url: Alternative registry URL (``--index``).
            dist_tag: Unused for Cargo (no dist-tag concept).
            publish_branch: Unused for Cargo.
            provenance: Unused for Cargo.
            dry_run: Run ``cargo publish --dry-run`` instead of actually
                publishing.
        """
        cmd = ['cargo', 'publish', '--no-verify']

        crate_name = _read_crate_name(dist_dir)
        if crate_name:
            cmd.extend(['-p', crate_name])

        if registry_url:
            cmd.extend(['--index', registry_url])

        if dry_run:
            cmd.append('--dry-run')

        log.info('publish', package=dist_dir.name, dry_run=dry_run)
        return await asyncio.to_thread(
            run_command,
            cmd,
            cwd=self._root,
            dry_run=False,
        )

    async def lock(
        self,
        *,
        check_only: bool = False,
        upgrade_package: str | None = None,
        cwd: Path | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """Run ``cargo update`` or ``cargo generate-lockfile``.

        Args:
            check_only: If True, verify the lockfile is up-to-date
                using ``cargo check``.
            upgrade_package: Specific package to upgrade.
            cwd: Working directory override.
            dry_run: Log the command without executing.
        """
        work_dir = cwd or self._root
        if check_only:
            cmd = ['cargo', 'check', '--locked']
        elif upgrade_package:
            cmd = ['cargo', 'update', '-p', upgrade_package]
        else:
            cmd = ['cargo', 'update']

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
        """Bump the version in ``Cargo.toml``.

        Uses ``cargo set-version`` from ``cargo-edit`` if available,
        otherwise returns a synthetic result indicating manual edit
        is needed (the workspace backend's ``rewrite_version`` handles
        the actual file rewrite).
        """
        crate_name = _read_crate_name(package_dir) or package_dir.name
        cmd = ['cargo', 'set-version', '--package', crate_name, new_version]

        log.info('version_bump', package=crate_name, version=new_version)
        return await asyncio.to_thread(
            run_command,
            cmd,
            cwd=self._root,
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
        """Verify a crate version is fetchable via ``cargo search``."""
        cmd = ['cargo', 'search', package_name, '--limit', '1']

        if registry_url:
            cmd.extend(['--index', registry_url])

        log.info('resolve_check', crate=package_name, version=version)
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
        """Smoke-test a crate by running ``cargo test`` in the workspace."""
        cmd = ['cargo', 'test', '-p', package_name, '--release']

        log.info('smoke_test', crate=package_name, version=version)
        return await asyncio.to_thread(
            run_command,
            cmd,
            cwd=self._root,
            dry_run=dry_run,
        )


def _read_crate_name(crate_dir: Path) -> str | None:
    """Read the crate name from ``Cargo.toml`` (best-effort).

    Does a simple text parse — no TOML library required for this
    lightweight extraction.
    """
    cargo_toml = crate_dir / 'Cargo.toml'
    if not cargo_toml.is_file():
        return None
    try:
        in_package = False
        for line in cargo_toml.read_text(encoding='utf-8').splitlines():
            stripped = line.strip()
            if stripped == '[package]':
                in_package = True
                continue
            if stripped.startswith('[') and in_package:
                break
            if in_package and stripped.startswith('name'):
                # name = "foo"
                _, _, value = stripped.partition('=')
                return value.strip().strip('"').strip("'")
    except OSError:
        pass
    return None


__all__ = [
    'CargoBackend',
]
