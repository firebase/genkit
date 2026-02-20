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

"""Tests for Rust/Cargo ecosystem backends (CargoWorkspace, CargoBackend, CratesIoRegistry).

Verifies that:

- CargoWorkspace discovers crates from Cargo.toml workspace members.
- CargoWorkspace classifies internal vs external dependencies.
- CargoWorkspace handles workspace version inheritance.
- CargoWorkspace rewrites versions in Cargo.toml.
- CargoWorkspace rewrites dependency versions.
- CargoBackend conforms to the PackageManager protocol.
- CratesIoRegistry conforms to the Registry protocol.
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import httpx
import pytest
from releasekit.backends.pm import PackageManager
from releasekit.backends.pm.cargo import CargoBackend
from releasekit.backends.registry import Registry
from releasekit.backends.registry.crates_io import CratesIoRegistry
from releasekit.backends.workspace import Workspace
from releasekit.backends.workspace.cargo import CargoWorkspace

# Helpers


def _create_cargo_workspace(root: Path, members: list[str], ws_version: str | None = None) -> None:
    """Create a root Cargo.toml with [workspace]."""
    root.mkdir(parents=True, exist_ok=True)
    members_str = ', '.join(f'"{m}"' for m in members)
    ws_pkg = ''
    if ws_version:
        ws_pkg = f'\n[workspace.package]\nversion = "{ws_version}"\n'
    (root / 'Cargo.toml').write_text(
        f'[workspace]\nmembers = [{members_str}]\n{ws_pkg}',
        encoding='utf-8',
    )


def _create_crate(
    root: Path,
    subdir: str,
    name: str,
    version: str = '1.0.0',
    deps: dict[str, str] | None = None,
    publish: bool = True,
    workspace_version: bool = False,
) -> Path:
    """Create a crate's Cargo.toml and return its directory."""
    crate_dir = root / subdir
    crate_dir.mkdir(parents=True, exist_ok=True)
    ver_line = 'version.workspace = true' if workspace_version else f'version = "{version}"'
    pub_line = '' if publish else 'publish = false'
    deps_section = ''
    if deps:
        dep_lines = '\n'.join(f'{d} = "{v}"' for d, v in deps.items())
        deps_section = f'\n[dependencies]\n{dep_lines}\n'
    (crate_dir / 'Cargo.toml').write_text(
        f'[package]\nname = "{name}"\n{ver_line}\nedition = "2021"\n{pub_line}\n{deps_section}',
        encoding='utf-8',
    )
    return crate_dir


# Protocol conformance


class TestCargoProtocolConformance:
    """Cargo backends implement their respective protocols."""

    def test_workspace_protocol(self) -> None:
        """CargoWorkspace satisfies the Workspace protocol."""
        ws = CargoWorkspace(Path('.'))
        assert isinstance(ws, Workspace)

    def test_pm_protocol(self) -> None:
        """CargoBackend satisfies the PackageManager protocol."""
        pm = CargoBackend(Path('.'))
        assert isinstance(pm, PackageManager)

    def test_registry_protocol(self) -> None:
        """CratesIoRegistry satisfies the Registry protocol."""
        reg = CratesIoRegistry()
        assert isinstance(reg, Registry)


# CargoWorkspace.discover()


class TestCargoWorkspaceDiscover:
    """CargoWorkspace.discover() finds and classifies Rust crates."""

    @pytest.mark.asyncio
    async def test_basic_discovery(self, tmp_path: Path) -> None:
        """Crates listed in workspace members are discovered."""
        _create_cargo_workspace(tmp_path, ['core', 'utils'])
        _create_crate(tmp_path, 'core', 'my-core', '1.0.0')
        _create_crate(tmp_path, 'utils', 'my-utils', '1.0.0')
        ws = CargoWorkspace(tmp_path)
        pkgs = await ws.discover()
        assert len(pkgs) == 2
        names = [p.name for p in pkgs]
        assert 'my-core' in names
        assert 'my-utils' in names

    @pytest.mark.asyncio
    async def test_version_parsed(self, tmp_path: Path) -> None:
        """Version is parsed from Cargo.toml."""
        _create_cargo_workspace(tmp_path, ['core'])
        _create_crate(tmp_path, 'core', 'my-core', '3.5.0')
        ws = CargoWorkspace(tmp_path)
        pkgs = await ws.discover()
        assert pkgs[0].version == '3.5.0'

    @pytest.mark.asyncio
    async def test_workspace_version_inheritance(self, tmp_path: Path) -> None:
        """Crates with version.workspace = true inherit workspace version."""
        _create_cargo_workspace(tmp_path, ['core'], ws_version='2.0.0')
        _create_crate(tmp_path, 'core', 'my-core', workspace_version=True)
        ws = CargoWorkspace(tmp_path)
        pkgs = await ws.discover()
        assert pkgs[0].version == '2.0.0'

    @pytest.mark.asyncio
    async def test_internal_deps(self, tmp_path: Path) -> None:
        """Dependencies on workspace crates are classified as internal."""
        _create_cargo_workspace(tmp_path, ['core', 'app'])
        _create_crate(tmp_path, 'core', 'my-core')
        _create_crate(tmp_path, 'app', 'my-app', deps={'my-core': '1.0.0'})
        ws = CargoWorkspace(tmp_path)
        pkgs = await ws.discover()
        app = next(p for p in pkgs if p.name == 'my-app')
        assert 'my-core' in app.internal_deps

    @pytest.mark.asyncio
    async def test_external_deps(self, tmp_path: Path) -> None:
        """Dependencies not in workspace are classified as external."""
        _create_cargo_workspace(tmp_path, ['core'])
        _create_crate(tmp_path, 'core', 'my-core', deps={'serde': '1.0.200'})
        ws = CargoWorkspace(tmp_path)
        pkgs = await ws.discover()
        assert 'serde' in pkgs[0].external_deps

    @pytest.mark.asyncio
    async def test_unpublishable_crate(self, tmp_path: Path) -> None:
        """Crates with publish = false are not publishable."""
        _create_cargo_workspace(tmp_path, ['internal'])
        _create_crate(tmp_path, 'internal', 'internal-tool', publish=False)
        ws = CargoWorkspace(tmp_path)
        pkgs = await ws.discover()
        assert pkgs[0].is_publishable is False

    @pytest.mark.asyncio
    async def test_exclude_patterns(self, tmp_path: Path) -> None:
        """Exclude patterns filter crates by name."""
        _create_cargo_workspace(tmp_path, ['core', 'examples'])
        _create_crate(tmp_path, 'core', 'my-core')
        _create_crate(tmp_path, 'examples', 'my-examples')
        ws = CargoWorkspace(tmp_path)
        pkgs = await ws.discover(exclude_patterns=['my-examples'])
        names = [p.name for p in pkgs]
        assert 'my-examples' not in names
        assert 'my-core' in names

    @pytest.mark.asyncio
    async def test_glob_members(self, tmp_path: Path) -> None:
        """Glob patterns in members are expanded."""
        _create_cargo_workspace(tmp_path, ['crates/*'])
        _create_crate(tmp_path, 'crates/alpha', 'alpha')
        _create_crate(tmp_path, 'crates/beta', 'beta')
        ws = CargoWorkspace(tmp_path)
        pkgs = await ws.discover()
        assert len(pkgs) == 2
        names = [p.name for p in pkgs]
        assert 'alpha' in names
        assert 'beta' in names

    @pytest.mark.asyncio
    async def test_missing_cargo_toml(self, tmp_path: Path) -> None:
        """Missing Cargo.toml returns empty list."""
        ws = CargoWorkspace(tmp_path)
        pkgs = await ws.discover()
        assert pkgs == []

    @pytest.mark.asyncio
    async def test_not_a_workspace(self, tmp_path: Path) -> None:
        """Cargo.toml without [workspace] returns empty list."""
        tmp_path.mkdir(parents=True, exist_ok=True)  # noqa: ASYNC240
        (tmp_path / 'Cargo.toml').write_text(  # noqa: ASYNC240
            '[package]\nname = "standalone"\nversion = "1.0.0"\n',
            encoding='utf-8',
        )
        ws = CargoWorkspace(tmp_path)
        pkgs = await ws.discover()
        assert pkgs == []

    @pytest.mark.asyncio
    async def test_manifest_path(self, tmp_path: Path) -> None:
        """Package manifest_path points to Cargo.toml."""
        _create_cargo_workspace(tmp_path, ['core'])
        _create_crate(tmp_path, 'core', 'my-core')
        ws = CargoWorkspace(tmp_path)
        pkgs = await ws.discover()
        assert pkgs[0].manifest_path.name == 'Cargo.toml'

    @pytest.mark.asyncio
    async def test_sorted_by_name(self, tmp_path: Path) -> None:
        """Packages are sorted by name."""
        _create_cargo_workspace(tmp_path, ['zeta', 'alpha'])
        _create_crate(tmp_path, 'zeta', 'zeta-crate')
        _create_crate(tmp_path, 'alpha', 'alpha-crate')
        ws = CargoWorkspace(tmp_path)
        pkgs = await ws.discover()
        assert pkgs[0].name == 'alpha-crate'
        assert pkgs[1].name == 'zeta-crate'


# CargoWorkspace.rewrite_version()


class TestCargoWorkspaceRewriteVersion:
    """CargoWorkspace.rewrite_version() edits Cargo.toml."""

    @pytest.mark.asyncio
    async def test_rewrite_direct_version(self, tmp_path: Path) -> None:
        """Version is rewritten in crate Cargo.toml."""
        _create_cargo_workspace(tmp_path, ['core'])
        crate_dir = _create_crate(tmp_path, 'core', 'my-core', '1.0.0')
        ws = CargoWorkspace(tmp_path)
        old = await ws.rewrite_version(crate_dir / 'Cargo.toml', '2.0.0')
        assert old == '1.0.0'
        text = (crate_dir / 'Cargo.toml').read_text()
        assert 'version = "2.0.0"' in text

    @pytest.mark.asyncio
    async def test_rewrite_workspace_inherited_version(self, tmp_path: Path) -> None:
        """Workspace-inherited version rewrites the root Cargo.toml."""
        _create_cargo_workspace(tmp_path, ['core'], ws_version='1.0.0')
        crate_dir = _create_crate(tmp_path, 'core', 'my-core', workspace_version=True)
        ws = CargoWorkspace(tmp_path)
        old = await ws.rewrite_version(crate_dir / 'Cargo.toml', '2.0.0')
        assert old == '1.0.0'
        root_text = (tmp_path / 'Cargo.toml').read_text()
        assert '"2.0.0"' in root_text


# CargoWorkspace.rewrite_dependency_version()


class TestCargoWorkspaceRewriteDependencyVersion:
    """CargoWorkspace.rewrite_dependency_version() edits dep constraints."""

    @pytest.mark.asyncio
    async def test_rewrite_simple_dep(self, tmp_path: Path) -> None:
        """Simple string dependency version is updated."""
        _create_cargo_workspace(tmp_path, ['app'])
        crate_dir = _create_crate(tmp_path, 'app', 'my-app', deps={'serde': '1.0.0'})
        ws = CargoWorkspace(tmp_path)
        await ws.rewrite_dependency_version(crate_dir / 'Cargo.toml', 'serde', '2.0.0')
        text = (crate_dir / 'Cargo.toml').read_text()
        assert '"2.0.0"' in text

    @pytest.mark.asyncio
    async def test_no_match_is_noop(self, tmp_path: Path) -> None:
        """Non-matching dep name is a no-op."""
        _create_cargo_workspace(tmp_path, ['core'])
        crate_dir = _create_crate(tmp_path, 'core', 'my-core', deps={'serde': '1.0.0'})
        ws = CargoWorkspace(tmp_path)
        await ws.rewrite_dependency_version(crate_dir / 'Cargo.toml', 'nonexistent', '1.0.0')


# CratesIoRegistry


def _mock_transport(responses: dict[str, tuple[int, str]]) -> Any:  # noqa: ANN401
    """Create a mock transport."""

    def handler(request: httpx.Request) -> httpx.Response:
        """Handler."""
        url = str(request.url)
        for suffix, (status, body) in responses.items():
            if url.endswith(suffix):
                return httpx.Response(status, text=body)
        return httpx.Response(404, text='Not found')

    return handler


def _make_client_cm(transport: Any) -> Any:  # noqa: ANN401
    """Create a context manager that yields an httpx.AsyncClient with mock transport."""

    @asynccontextmanager
    async def _client_cm(**kw: Any) -> AsyncGenerator[httpx.AsyncClient]:  # noqa: ANN401
        """Client cm."""
        async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
            yield client

    return _client_cm


class TestCratesIoRegistry:
    """Tests for CratesIoRegistry backend."""

    @pytest.mark.asyncio()
    async def test_check_published_exists(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns True when crate version exists on crates.io."""
        reg = CratesIoRegistry(base_url='https://crates.test')
        transport = _mock_transport({'/api/v1/crates/serde/1.0.200': (200, '{}')})
        monkeypatch.setattr('releasekit.backends.registry.crates_io.http_client', _make_client_cm(transport))
        assert await reg.check_published('serde', '1.0.200') is True

    @pytest.mark.asyncio()
    async def test_check_published_not_exists(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns False when crate version is not on crates.io."""
        reg = CratesIoRegistry(base_url='https://crates.test')
        transport = _mock_transport({})
        monkeypatch.setattr('releasekit.backends.registry.crates_io.http_client', _make_client_cm(transport))
        assert await reg.check_published('serde', '99.99.99') is False

    @pytest.mark.asyncio()
    async def test_project_exists(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns True when crate exists on crates.io."""
        reg = CratesIoRegistry(base_url='https://crates.test')
        transport = _mock_transport({'/api/v1/crates/serde': (200, '{}')})
        monkeypatch.setattr('releasekit.backends.registry.crates_io.http_client', _make_client_cm(transport))
        assert await reg.project_exists('serde') is True

    @pytest.mark.asyncio()
    async def test_project_not_exists(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns False when crate does not exist on crates.io."""
        reg = CratesIoRegistry(base_url='https://crates.test')
        transport = _mock_transport({})
        monkeypatch.setattr('releasekit.backends.registry.crates_io.http_client', _make_client_cm(transport))
        assert await reg.project_exists('nonexistent-crate-xyz') is False

    @pytest.mark.asyncio()
    async def test_latest_version(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns latest stable version from crates.io."""
        reg = CratesIoRegistry(base_url='https://crates.test')
        body = json.dumps({'crate': {'max_stable_version': '1.0.200', 'newest_version': '1.0.201-beta'}})
        transport = _mock_transport({'/api/v1/crates/serde': (200, body)})
        monkeypatch.setattr('releasekit.backends.registry.crates_io.http_client', _make_client_cm(transport))
        assert await reg.latest_version('serde') == '1.0.200'

    @pytest.mark.asyncio()
    async def test_latest_version_fallback_newest(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Falls back to newest_version when max_stable_version is absent."""
        reg = CratesIoRegistry(base_url='https://crates.test')
        body = json.dumps({'crate': {'newest_version': '0.1.0-alpha'}})
        transport = _mock_transport({'/api/v1/crates/new-crate': (200, body)})
        monkeypatch.setattr('releasekit.backends.registry.crates_io.http_client', _make_client_cm(transport))
        assert await reg.latest_version('new-crate') == '0.1.0-alpha'

    @pytest.mark.asyncio()
    async def test_latest_version_not_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns None when crate is not on crates.io."""
        reg = CratesIoRegistry(base_url='https://crates.test')
        transport = _mock_transport({})
        monkeypatch.setattr('releasekit.backends.registry.crates_io.http_client', _make_client_cm(transport))
        assert await reg.latest_version('nonexistent') is None

    @pytest.mark.asyncio()
    async def test_verify_checksum_noop(self) -> None:
        """Checksum verification returns all files as missing."""
        reg = CratesIoRegistry()
        result = await reg.verify_checksum('serde', '1.0.0', {'serde-1.0.0.crate': 'abc'})
        assert 'serde-1.0.0.crate' in result.missing

    @pytest.mark.asyncio()
    async def test_poll_immediately_available(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Poll returns True when version is immediately available."""
        reg = CratesIoRegistry(base_url='https://crates.test')
        transport = _mock_transport({'/api/v1/crates/serde/1.0.0': (200, '{}')})
        monkeypatch.setattr('releasekit.backends.registry.crates_io.http_client', _make_client_cm(transport))
        result = await reg.poll_available('serde', '1.0.0', timeout=10.0, interval=1.0)
        assert result is True
