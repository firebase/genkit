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

"""Integration tests for UvBackend against real uv commands.

These tests create real Python projects in temp directories and exercise
the ``uv build``, ``uv lock``, and ``uv version`` commands that
UvBackend constructs.

The tests do NOT publish to any registry — only local operations.
"""

from __future__ import annotations

import shutil
import textwrap
from pathlib import Path

import pytest
from releasekit.backends.pm.uv import UvBackend
from releasekit.logging import configure_logging

configure_logging(quiet=True)

pytestmark = pytest.mark.skipif(
    shutil.which('uv') is None,
    reason='uv not found on PATH. Install uv: https://docs.astral.sh/uv/',
)

_MINIMAL_PYPROJECT = textwrap.dedent("""\
    [project]
    name = "test-pkg"
    version = "0.1.0"
    requires-python = ">=3.10"

    [build-system]
    requires = ["setuptools>=68.0"]
    build-backend = "setuptools.build_meta"

    [tool.setuptools.packages.find]
    where = ["src"]
""")


def _init_uv_project(tmp_path: Path) -> Path:
    """Create a minimal Python package suitable for ``uv build``.

    Returns the package directory.
    """
    pkg = tmp_path / 'test-pkg'
    pkg.mkdir()
    (pkg / 'pyproject.toml').write_text(_MINIMAL_PYPROJECT)
    src = pkg / 'src' / 'test_pkg'
    src.mkdir(parents=True)
    (src / '__init__.py').write_text('__version__ = "0.1.0"\n')
    return pkg


def _init_uv_workspace(tmp_path: Path) -> Path:
    """Create a minimal uv workspace with one member package.

    Returns the workspace root.
    """
    root = tmp_path / 'workspace'
    root.mkdir()
    (root / 'pyproject.toml').write_text(
        textwrap.dedent("""\
        [project]
        name = "test-workspace"
        version = "0.0.0"
        requires-python = ">=3.10"

        [tool.uv.workspace]
        members = ["packages/*"]
    """)
    )

    pkg = root / 'packages' / 'test-pkg'
    pkg.mkdir(parents=True)
    (pkg / 'pyproject.toml').write_text(_MINIMAL_PYPROJECT)
    src = pkg / 'src' / 'test_pkg'
    src.mkdir(parents=True)
    (src / '__init__.py').write_text('__version__ = "0.1.0"\n')
    return root


class TestUvBuild:
    """Test uv build with real packages."""

    @pytest.mark.asyncio
    async def test_build_produces_dist(self, tmp_path: Path) -> None:
        """build() should produce .whl and .tar.gz files."""
        pkg = _init_uv_project(tmp_path)
        dist = tmp_path / 'dist'
        dist.mkdir()

        backend = UvBackend(workspace_root=tmp_path)
        result = await backend.build(pkg, output_dir=dist, no_sources=False)
        assert result.ok, f'uv build failed: {result.stderr}'

        files = list(dist.iterdir())
        extensions = {f.suffix for f in files}
        assert '.whl' in extensions or '.gz' in extensions, f'No dist files: {files}'

    @pytest.mark.asyncio
    async def test_build_dry_run(self, tmp_path: Path) -> None:
        """build(dry_run=True) should not produce files."""
        pkg = _init_uv_project(tmp_path)
        dist = tmp_path / 'dist'
        dist.mkdir()

        backend = UvBackend(workspace_root=tmp_path)
        result = await backend.build(pkg, output_dir=dist, dry_run=True)
        assert result.ok
        assert result.dry_run
        assert list(dist.iterdir()) == []


class TestUvLock:
    """Test uv lock with real workspaces."""

    @pytest.mark.asyncio
    async def test_lock_generates_lockfile(self, tmp_path: Path) -> None:
        """lock() should generate a uv.lock file."""
        root = _init_uv_workspace(tmp_path)
        backend = UvBackend(workspace_root=root)
        result = await backend.lock()
        assert result.ok, f'uv lock failed: {result.stderr}'
        assert (root / 'uv.lock').is_file()

    @pytest.mark.asyncio
    async def test_lock_check_passes_after_lock(self, tmp_path: Path) -> None:
        """lock(check_only=True) should pass after a fresh lock."""
        root = _init_uv_workspace(tmp_path)
        backend = UvBackend(workspace_root=root)

        # First, generate the lockfile.
        result = await backend.lock()
        assert result.ok, f'uv lock failed: {result.stderr}'

        # Then verify it.
        check = await backend.lock(check_only=True)
        assert check.ok, f'uv lock --check failed: {check.stderr}'

    @pytest.mark.asyncio
    async def test_lock_dry_run(self, tmp_path: Path) -> None:
        """lock(dry_run=True) should not create a lockfile."""
        root = _init_uv_workspace(tmp_path)
        backend = UvBackend(workspace_root=root)
        result = await backend.lock(dry_run=True)
        assert result.ok
        assert result.dry_run
        assert not (root / 'uv.lock').is_file()


class TestUvVersionBump:
    """Test uv version with real packages."""

    @pytest.mark.asyncio
    async def test_version_bump(self, tmp_path: Path) -> None:
        """version_bump() should update the version in pyproject.toml."""
        pkg = _init_uv_project(tmp_path)
        backend = UvBackend(workspace_root=tmp_path)

        result = await backend.version_bump(pkg, '2.0.0')
        assert result.ok, f'uv version failed: {result.stderr}'

        # Verify the version was updated.
        content = (pkg / 'pyproject.toml').read_text()
        assert '2.0.0' in content

    @pytest.mark.asyncio
    async def test_version_bump_dry_run(self, tmp_path: Path) -> None:
        """version_bump(dry_run=True) should not change the file."""
        pkg = _init_uv_project(tmp_path)
        backend = UvBackend(workspace_root=tmp_path)

        result = await backend.version_bump(pkg, '2.0.0', dry_run=True)
        assert result.ok
        assert result.dry_run

        content = (pkg / 'pyproject.toml').read_text()
        assert '0.1.0' in content
        assert '2.0.0' not in content
