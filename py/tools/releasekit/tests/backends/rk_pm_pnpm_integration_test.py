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

"""Integration tests for PnpmBackend against real pnpm/npm commands.

These tests create real Node.js projects in temp directories and exercise
the ``pnpm pack``, ``pnpm install``, and ``npm version`` commands that
PnpmBackend constructs.

The tests do NOT publish to any registry — only local operations.
"""

from __future__ import annotations

import json
import shutil
import textwrap
from pathlib import Path

import pytest
from releasekit.backends.pm.pnpm import PnpmBackend
from releasekit.logging import configure_logging

configure_logging(quiet=True)

_pnpm_missing = shutil.which('pnpm') is None
_npm_missing = shutil.which('npm') is None


def _init_pnpm_package(tmp_path: Path) -> Path:
    """Create a minimal npm package suitable for ``pnpm pack``.

    Returns the package directory.
    """
    pkg = tmp_path / 'test-pkg'
    pkg.mkdir()
    (pkg / 'package.json').write_text(
        json.dumps(
            {
                'name': 'test-pkg',
                'version': '0.1.0',
                'main': 'index.js',
            },
            indent=2,
        )
        + '\n'
    )
    (pkg / 'index.js').write_text('module.exports = {};\n')
    return pkg


def _init_pnpm_workspace(tmp_path: Path) -> Path:
    """Create a minimal pnpm workspace with one member package.

    Returns the workspace root.
    """
    root = tmp_path / 'workspace'
    root.mkdir()
    (root / 'package.json').write_text(
        json.dumps(
            {
                'name': 'test-workspace',
                'version': '0.0.0',
                'private': True,
            },
            indent=2,
        )
        + '\n'
    )
    (root / 'pnpm-workspace.yaml').write_text(
        textwrap.dedent("""\
        packages:
          - 'packages/*'
    """)
    )

    pkg = root / 'packages' / 'test-pkg'
    pkg.mkdir(parents=True)
    (pkg / 'package.json').write_text(
        json.dumps(
            {
                'name': 'test-pkg',
                'version': '0.1.0',
                'main': 'index.js',
            },
            indent=2,
        )
        + '\n'
    )
    (pkg / 'index.js').write_text('module.exports = {};\n')
    return root


@pytest.mark.skipif(_pnpm_missing, reason='pnpm not found on PATH. Install pnpm: https://pnpm.io/installation')
class TestPnpmBuild:
    """Test pnpm pack with real packages."""

    @pytest.mark.asyncio
    async def test_pack_produces_tarball(self, tmp_path: Path) -> None:
        """build() should produce a .tgz tarball."""
        pkg = _init_pnpm_package(tmp_path)
        dist = tmp_path / 'dist'
        dist.mkdir()

        backend = PnpmBackend(workspace_root=tmp_path)
        result = await backend.build(pkg, output_dir=dist)
        assert result.ok, f'pnpm pack failed: {result.stderr}'

        tarballs = list(dist.glob('*.tgz'))
        assert len(tarballs) >= 1, f'No tarballs found in {dist}'

    @pytest.mark.asyncio
    async def test_build_dry_run(self, tmp_path: Path) -> None:
        """build(dry_run=True) should not produce files."""
        pkg = _init_pnpm_package(tmp_path)
        dist = tmp_path / 'dist'
        dist.mkdir()

        backend = PnpmBackend(workspace_root=tmp_path)
        result = await backend.build(pkg, output_dir=dist, dry_run=True)
        assert result.ok
        assert result.dry_run
        assert list(dist.iterdir()) == []


@pytest.mark.skipif(_pnpm_missing, reason='pnpm not found on PATH. Install pnpm: https://pnpm.io/installation')
class TestPnpmLock:
    """Test pnpm install --lockfile-only with real workspaces."""

    @pytest.mark.asyncio
    async def test_lock_generates_lockfile(self, tmp_path: Path) -> None:
        """lock() should generate a pnpm-lock.yaml file."""
        root = _init_pnpm_workspace(tmp_path)
        backend = PnpmBackend(workspace_root=root)
        result = await backend.lock()
        assert result.ok, f'pnpm install --lockfile-only failed: {result.stderr}'
        assert (root / 'pnpm-lock.yaml').is_file()

    @pytest.mark.asyncio
    async def test_lock_frozen_passes_after_lock(self, tmp_path: Path) -> None:
        """lock(check_only=True) should pass after a fresh lock."""
        root = _init_pnpm_workspace(tmp_path)
        backend = PnpmBackend(workspace_root=root)

        # First, generate the lockfile.
        result = await backend.lock()
        assert result.ok, f'pnpm install --lockfile-only failed: {result.stderr}'

        # Then verify it.
        check = await backend.lock(check_only=True)
        assert check.ok, f'pnpm install --frozen-lockfile failed: {check.stderr}'

    @pytest.mark.asyncio
    async def test_lock_dry_run(self, tmp_path: Path) -> None:
        """lock(dry_run=True) should not create a lockfile."""
        root = _init_pnpm_workspace(tmp_path)
        backend = PnpmBackend(workspace_root=root)
        result = await backend.lock(dry_run=True)
        assert result.ok
        assert result.dry_run
        assert not (root / 'pnpm-lock.yaml').is_file()


@pytest.mark.skipif(_npm_missing, reason='npm not found on PATH. Install npm (comes with Node.js): https://nodejs.org/')
class TestPnpmVersionBump:
    """Test npm version with real packages."""

    @pytest.mark.asyncio
    async def test_version_bump(self, tmp_path: Path) -> None:
        """version_bump() should update the version in package.json."""
        pkg = _init_pnpm_package(tmp_path)
        backend = PnpmBackend(workspace_root=tmp_path)

        result = await backend.version_bump(pkg, '2.0.0')
        assert result.ok, f'npm version failed: {result.stderr}'

        # Verify the version was updated.
        data = json.loads((pkg / 'package.json').read_text())
        assert data['version'] == '2.0.0'

    @pytest.mark.asyncio
    async def test_version_bump_dry_run(self, tmp_path: Path) -> None:
        """version_bump(dry_run=True) should not change the file."""
        pkg = _init_pnpm_package(tmp_path)
        backend = PnpmBackend(workspace_root=tmp_path)

        result = await backend.version_bump(pkg, '2.0.0', dry_run=True)
        assert result.ok
        assert result.dry_run

        data = json.loads((pkg / 'package.json').read_text())
        assert data['version'] == '0.1.0'
