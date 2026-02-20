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

"""Tests for the Workspace protocol and UvWorkspace implementation.

Verifies that UvWorkspace correctly:

- Discovers packages in a uv workspace.
- Classifies dependencies as internal (workspace-sourced) or external.
- Rewrites versions in pyproject.toml files.
- Rewrites dependency version constraints.
- Conforms to the Workspace protocol.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from releasekit.backends.workspace import Package, UvWorkspace, Workspace
from releasekit.errors import ReleaseKitError

# Helpers


def _write_root(
    root: Path,
    members: str = '"packages/*"',
    exclude: str = '',
    sources: str = '',
) -> None:
    """Write a root pyproject.toml for a uv workspace."""
    exclude_line = f'exclude = [{exclude}]' if exclude else ''
    sources_section = f'\n[tool.uv.sources]\n{sources}\n' if sources else ''
    (root / 'pyproject.toml').write_text(
        f'[project]\nname = "workspace"\n\n'
        f'[tool.uv.workspace]\nmembers = [{members}]\n{exclude_line}\n'
        f'{sources_section}'
    )


def _write_package(
    root: Path,
    subdir: str,
    name: str,
    version: str = '0.1.0',
    deps: str = '',
    classifiers: str = '',
) -> Path:
    """Write a package's pyproject.toml and return its directory."""
    pkg_dir = root / subdir
    pkg_dir.mkdir(parents=True, exist_ok=True)
    dep_line = f'dependencies = [{deps}]' if deps else ''
    cls_line = f'classifiers = [{classifiers}]' if classifiers else ''
    (pkg_dir / 'pyproject.toml').write_text(
        f'[project]\nname = "{name}"\nversion = "{version}"\n{dep_line}\n{cls_line}\n'
    )
    return pkg_dir


# Protocol conformance


class TestWorkspaceProtocolConformance:
    """UvWorkspace implements the Workspace protocol."""

    def test_is_runtime_checkable(self) -> None:
        """UvWorkspace satisfies the Workspace protocol at runtime."""
        ws = UvWorkspace(Path('.'))
        assert isinstance(ws, Workspace), 'UvWorkspace should be a Workspace'


# Discovery


class TestUvWorkspaceDiscover:
    """UvWorkspace.discover() finds and classifies packages."""

    @pytest.mark.asyncio
    async def test_basic_discovery(self, tmp_path: Path) -> None:
        """Packages in member dirs are discovered."""
        _write_root(tmp_path)
        _write_package(tmp_path, 'packages/core', 'my-pkg', '1.0.0')
        ws = UvWorkspace(tmp_path)
        pkgs = await ws.discover()
        assert len(pkgs) == 1
        assert pkgs[0].name == 'my-pkg'
        assert pkgs[0].version == '1.0.0'

    @pytest.mark.asyncio
    async def test_internal_dep_with_workspace_source(self, tmp_path: Path) -> None:
        """Deps with workspace=true source are classified as internal."""
        _write_root(tmp_path, sources='genkit = { workspace = true }')
        _write_package(tmp_path, 'packages/core', 'genkit', '0.5.0')
        _write_package(
            tmp_path,
            'packages/plugin',
            'genkit-plugin-foo',
            '0.5.0',
            deps='"genkit>=0.5.0"',
        )
        ws = UvWorkspace(tmp_path)
        pkgs = await ws.discover()
        plugin = next(p for p in pkgs if p.name == 'genkit-plugin-foo')
        assert plugin.internal_deps == ['genkit']

    @pytest.mark.asyncio
    async def test_pinned_dep_is_external(self, tmp_path: Path) -> None:
        """Workspace members without workspace=true source are external."""
        _write_root(tmp_path)
        _write_package(tmp_path, 'packages/core', 'genkit', '1.0.0')
        _write_package(
            tmp_path,
            'packages/app',
            'app-legacy',
            '0.1.0',
            deps='"genkit==1.0.0"',
        )
        ws = UvWorkspace(tmp_path)
        pkgs = await ws.discover()
        app = next(p for p in pkgs if p.name == 'app-legacy')
        assert app.internal_deps == []
        assert 'genkit' in app.external_deps

    @pytest.mark.asyncio
    async def test_mixed_deps(self, tmp_path: Path) -> None:
        """Both internal and external deps are classified correctly."""
        _write_root(tmp_path, sources='core = { workspace = true }')
        _write_package(tmp_path, 'packages/core', 'core')
        _write_package(
            tmp_path,
            'packages/app',
            'app',
            deps='"core", "httpx>=0.27"',
        )
        ws = UvWorkspace(tmp_path)
        pkgs = await ws.discover()
        app = next(p for p in pkgs if p.name == 'app')
        assert app.internal_deps == ['core']
        assert app.external_deps == ['httpx']

    @pytest.mark.asyncio
    async def test_external_dep(self, tmp_path: Path) -> None:
        """Non-workspace deps are external."""
        _write_root(tmp_path)
        _write_package(tmp_path, 'packages/core', 'my-pkg', deps='"requests>=2.28.0"')
        ws = UvWorkspace(tmp_path)
        pkgs = await ws.discover()
        assert pkgs[0].external_deps == ['requests']

    @pytest.mark.asyncio
    async def test_exclude_patterns(self, tmp_path: Path) -> None:
        """Exclude patterns filter by package name."""
        _write_root(tmp_path)
        _write_package(tmp_path, 'packages/core', 'core')
        _write_package(tmp_path, 'packages/sample', 'sample-demo')
        ws = UvWorkspace(tmp_path)
        pkgs = await ws.discover(exclude_patterns=['sample-*'])
        names = [p.name for p in pkgs]
        assert 'sample-demo' not in names

    @pytest.mark.asyncio
    async def test_workspace_exclude(self, tmp_path: Path) -> None:
        """Packages matching workspace exclude globs are excluded."""
        _write_root(tmp_path, '"packages/*"', '"packages/test"')
        _write_package(tmp_path, 'packages/real', 'real-pkg')
        _write_package(tmp_path, 'packages/test', 'test-pkg')
        ws = UvWorkspace(tmp_path)
        pkgs = await ws.discover()
        names = [p.name for p in pkgs]
        assert 'test-pkg' not in names

    @pytest.mark.asyncio
    async def test_name_normalization(self, tmp_path: Path) -> None:
        """Package names are normalized per PEP 503."""
        _write_root(tmp_path)
        _write_package(tmp_path, 'packages/my_pkg', 'my_pkg')
        ws = UvWorkspace(tmp_path)
        pkgs = await ws.discover()
        assert pkgs[0].name == 'my-pkg'

    @pytest.mark.asyncio
    async def test_dep_normalization(self, tmp_path: Path) -> None:
        """Dependency names are normalized for matching."""
        _write_root(tmp_path, sources='my_core = { workspace = true }')
        _write_package(tmp_path, 'packages/core', 'my_core')
        _write_package(
            tmp_path,
            'packages/app',
            'my-app',
            deps='"my_core>=1.0"',
        )
        ws = UvWorkspace(tmp_path)
        pkgs = await ws.discover()
        app = next(p for p in pkgs if p.name == 'my-app')
        assert app.internal_deps == ['my-core']

    @pytest.mark.asyncio
    async def test_manifest_path(self, tmp_path: Path) -> None:
        """Package manifest_path points to pyproject.toml."""
        _write_root(tmp_path)
        _write_package(tmp_path, 'packages/core', 'core')
        ws = UvWorkspace(tmp_path)
        pkgs = await ws.discover()
        assert pkgs[0].manifest_path.name == 'pyproject.toml'


# Error handling


class TestUvWorkspaceErrors:
    """UvWorkspace raises clear errors on invalid workspaces."""

    @pytest.mark.asyncio
    async def test_missing_pyproject(self, tmp_path: Path) -> None:
        """Missing root pyproject.toml raises error."""
        ws = UvWorkspace(tmp_path)
        with pytest.raises(ReleaseKitError) as exc_info:
            await ws.discover()
        assert 'RK-WORKSPACE-NOT-FOUND' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_no_members(self, tmp_path: Path) -> None:
        """Empty members list raises error."""
        _write_root(tmp_path, members='')
        ws = UvWorkspace(tmp_path)
        with pytest.raises(ReleaseKitError) as exc_info:
            await ws.discover()
        assert 'RK-WORKSPACE-NO-MEMBERS' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_duplicate_package_name(self, tmp_path: Path) -> None:
        """Duplicate package names raise error."""
        _write_root(tmp_path, members='"a", "b"')
        _write_package(tmp_path, 'a', 'dup-pkg', '1.0.0')
        _write_package(tmp_path, 'b', 'dup-pkg', '2.0.0')
        ws = UvWorkspace(tmp_path)
        with pytest.raises(ReleaseKitError) as exc_info:
            await ws.discover()
        assert 'RK-WORKSPACE-DUPLICATE-PACKAGE' in str(exc_info.value)


# Version rewriting


class TestUvWorkspaceRewriteVersion:
    """UvWorkspace.rewrite_version() edits pyproject.toml."""

    @pytest.mark.asyncio
    async def test_rewrite_version(self, tmp_path: Path) -> None:
        """Version is rewritten and old version returned."""
        pkg_dir = _write_package(tmp_path, 'packages/core', 'core', '1.0.0')
        ws = UvWorkspace(tmp_path)
        old = await ws.rewrite_version(pkg_dir / 'pyproject.toml', '2.0.0')
        assert old == '1.0.0'
        # Verify the file was updated.
        text = (pkg_dir / 'pyproject.toml').read_text()
        assert 'version = "2.0.0"' in text

    @pytest.mark.asyncio
    async def test_rewrite_version_missing_key(self, tmp_path: Path) -> None:
        """Missing version key raises error."""
        pkg_dir = tmp_path / 'packages' / 'no-version'
        pkg_dir.mkdir(parents=True)
        (pkg_dir / 'pyproject.toml').write_text('[project]\nname = "no-version"\n')
        ws = UvWorkspace(tmp_path)
        with pytest.raises(ReleaseKitError):
            await ws.rewrite_version(pkg_dir / 'pyproject.toml', '1.0.0')


# Dependency version rewriting


class TestUvWorkspaceRewriteDependencyVersion:
    """UvWorkspace.rewrite_dependency_version() edits dep constraints."""

    @pytest.mark.asyncio
    async def test_rewrite_dep_version(self, tmp_path: Path) -> None:
        """Dependency version is pinned to exact version."""
        pkg_dir = _write_package(tmp_path, 'packages/app', 'app', deps='"core>=1.0.0"')
        ws = UvWorkspace(tmp_path)
        await ws.rewrite_dependency_version(pkg_dir / 'pyproject.toml', 'core', '2.0.0')
        text = (pkg_dir / 'pyproject.toml').read_text()
        assert 'core==2.0.0' in text

    @pytest.mark.asyncio
    async def test_rewrite_dep_no_match(self, tmp_path: Path) -> None:
        """Non-matching dep name is a no-op (no crash)."""
        pkg_dir = _write_package(tmp_path, 'packages/app', 'app', deps='"httpx>=0.27"')
        ws = UvWorkspace(tmp_path)
        # Should not raise.
        await ws.rewrite_dependency_version(pkg_dir / 'pyproject.toml', 'nonexistent', '1.0.0')


# Package dataclass


class TestPackageDataclass:
    """Package dataclass is frozen and has correct defaults."""

    def test_is_frozen(self, tmp_path: Path) -> None:
        """Package instances are immutable."""
        pkg = Package(
            name='test',
            version='1.0.0',
            path=tmp_path,
            manifest_path=tmp_path / 'pyproject.toml',
        )
        with pytest.raises(AttributeError):
            pkg.name = 'oops'  # type: ignore[misc]

    def test_default_publishable(self, tmp_path: Path) -> None:
        """Packages are publishable by default."""
        pkg = Package(
            name='test',
            version='1.0.0',
            path=tmp_path,
            manifest_path=tmp_path / 'pyproject.toml',
        )
        assert pkg.is_publishable is True

    def test_default_deps_empty(self, tmp_path: Path) -> None:
        """Deps default to empty lists."""
        pkg = Package(
            name='test',
            version='1.0.0',
            path=tmp_path,
            manifest_path=tmp_path / 'pyproject.toml',
        )
        assert pkg.internal_deps == []
        assert pkg.external_deps == []
        assert pkg.all_deps == []
