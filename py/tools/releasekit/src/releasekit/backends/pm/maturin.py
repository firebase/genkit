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

"""Maturin package manager backend for releasekit.

The :class:`MaturinBackend` implements the
:class:`~releasekit.backends.pm.PackageManager` protocol for Python
packages that use `maturin <https://www.maturin.rs/>`_ as their build
backend (i.e. Rust+Python hybrid packages via PyO3).

Maturin handles:

- **Building**: ``maturin build --release`` produces platform-specific
  wheels containing compiled Rust extensions.
- **Publishing**: ``uv publish`` uploads the built wheels to PyPI
  (maturin itself delegates to twine/uv for upload).
- **Locking**: ``uv lock`` manages the Python-side lockfile.

Typical project layout::

    my-package/
    ├── pyproject.toml     ← build-backend = "maturin"
    ├── Cargo.toml         ← Rust crate metadata
    ├── src/
    │   ├── lib.rs         ← Rust source (PyO3 bindings)
    │   └── my_package/
    │       ├── __init__.py
    │       └── _native.pyi
    └── tests/
        └── test_basic.py

All methods are async — blocking subprocess calls are dispatched to
``asyncio.to_thread()`` to avoid blocking the event loop.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from releasekit.backends._run import CommandResult, run_command
from releasekit.logging import get_logger

log = get_logger('releasekit.backends.pm.maturin')


class MaturinBackend:
    """Maturin :class:`~releasekit.backends.pm.PackageManager` implementation.

    Uses ``maturin build`` for building platform wheels and ``uv publish``
    for uploading to PyPI. Version bumps and lockfile management are
    handled via ``uv`` since the Python-side metadata lives in
    ``pyproject.toml``.

    Args:
        workspace_root: Path to the workspace root (contains the root
            ``pyproject.toml`` with ``[tool.uv.workspace]``).
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
        """Build a maturin package using ``maturin build --release``.

        Produces platform-specific wheels containing compiled Rust
        extensions linked to the Python module.

        Args:
            package_dir: Path to the package directory containing both
                ``pyproject.toml`` (with ``build-backend = "maturin"``)
                and ``Cargo.toml``.
            output_dir: Directory to place built wheels. Defaults to
                ``target/wheels/`` within the package directory.
            no_sources: Unused for maturin (kept for protocol compat).
            dry_run: Log the command without executing.
        """
        cmd = ['maturin', 'build', '--release']

        if output_dir:
            cmd.extend(['--out', str(output_dir)])

        # Build an sdist alongside the wheel for source distribution.
        cmd.append('--sdist')

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
        """Publish built wheels using ``uv publish``.

        Maturin builds produce wheels in the output directory. We use
        ``uv publish`` to upload them to PyPI (same as the uv backend).

        Args:
            dist_dir: Directory containing built ``.whl`` and ``.tar.gz``
                files from ``maturin build``.
            check_url: Index URL to check for existing files (skips
                duplicates).
            registry_url: Upload endpoint URL. Mapped to
                ``uv publish --publish-url``.
            dist_tag: Ignored (npm-only, accepted for protocol compat).
            publish_branch: Ignored (npm-only, accepted for protocol compat).
            provenance: Ignored (npm-only, accepted for protocol compat).
            dry_run: Perform a dry run without uploading.
        """
        cmd = ['uv', 'publish']
        if check_url:
            cmd.extend(['--check-url', check_url])
        if registry_url:
            cmd.extend(['--publish-url', registry_url])
        cmd.append(str(dist_dir))

        log.info('publish', dist_dir=str(dist_dir))
        return await asyncio.to_thread(
            run_command,
            cmd,
            cwd=self._root,
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
        """Update or verify the lock file using ``uv lock``.

        Maturin packages still use ``uv lock`` for Python-side
        dependency management.

        Args:
            check_only: Only verify the lock file is up-to-date.
            upgrade_package: Upgrade a specific package in the lock file.
            cwd: Working directory override.
            dry_run: Log the command without executing.
        """
        cmd = ['uv', 'lock']
        if check_only:
            cmd.append('--check')
        if upgrade_package:
            cmd.extend(['--upgrade-package', upgrade_package])

        effective_cwd = cwd or self._root
        log.info('lock', check_only=check_only, upgrade_package=upgrade_package)
        return await asyncio.to_thread(
            run_command,
            cmd,
            cwd=effective_cwd,
            dry_run=dry_run,
        )

    async def version_bump(
        self,
        package_dir: Path,
        new_version: str,
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Bump the version in both ``pyproject.toml`` and ``Cargo.toml``.

        Uses ``uv version`` for the Python-side version. The Rust-side
        ``Cargo.toml`` version is handled by the workspace backend's
        ``rewrite_version`` method (or ``cargo set-version`` if
        ``cargo-edit`` is installed).

        Args:
            package_dir: Path to the package directory.
            new_version: New version string (PEP 440).
            dry_run: Log the command without executing.
        """
        cmd = ['uv', 'version', '--frozen', new_version]

        log.info(
            'version_bump',
            package=package_dir.name,
            version=new_version,
        )
        return await asyncio.to_thread(
            run_command,
            cmd,
            cwd=package_dir,
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
        """Verify a published package resolves using ``uv pip install --dry-run``."""
        cmd = ['uv', 'pip', 'install', '--dry-run', f'{package_name}=={version}']
        if registry_url:
            cmd.extend(['--default-index', registry_url])

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
        """Smoke-test a published maturin package via ``uv run --with``.

        Verifies the native extension loads correctly by importing the
        package and printing its version.
        """
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
        return await asyncio.to_thread(
            run_command,
            cmd,
            cwd=self._root,
            dry_run=dry_run,
        )


__all__ = [
    'MaturinBackend',
]
