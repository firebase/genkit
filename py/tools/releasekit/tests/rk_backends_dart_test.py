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

"""Tests for Dart ecosystem backends (DartWorkspace, DartBackend, PubDevRegistry).

Verifies that:

- DartWorkspace discovers packages from melos.yaml and pubspec.yaml files.
- DartWorkspace classifies internal vs external dependencies.
- DartWorkspace rewrites versions in pubspec.yaml.
- DartWorkspace rewrites dependency versions.
- DartBackend conforms to the PackageManager protocol.
- PubDevRegistry conforms to the Registry protocol.
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
from releasekit.backends.pm.dart import DartBackend
from releasekit.backends.registry import Registry
from releasekit.backends.registry.pubdev import PubDevRegistry
from releasekit.backends.workspace import Workspace
from releasekit.backends.workspace.dart import DartWorkspace

# Helpers


def _create_melos(root: Path, patterns: list[str]) -> None:
    """Create a melos.yaml with the given package patterns."""
    items = '\n'.join(f'  - {p}' for p in patterns)
    (root / 'melos.yaml').write_text(
        f'name: workspace\n\npackages:\n{items}\n',
        encoding='utf-8',
    )


def _create_pubspec(
    directory: Path,
    name: str,
    version: str = '1.0.0',
    deps: dict[str, str] | None = None,
    dev_deps: dict[str, str] | None = None,
    private: bool = False,
) -> Path:
    """Create a pubspec.yaml and return the directory."""
    directory.mkdir(parents=True, exist_ok=True)
    lines = [f'name: {name}', f'version: {version}']
    if private:
        lines.append('publish_to: none')
    if deps:
        lines.append('dependencies:')
        for dep_name, dep_ver in deps.items():
            lines.append(f'  {dep_name}: {dep_ver}')
    if dev_deps:
        lines.append('dev_dependencies:')
        for dep_name, dep_ver in dev_deps.items():
            lines.append(f'  {dep_name}: {dep_ver}')
    (directory / 'pubspec.yaml').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return directory


# Protocol conformance


class TestDartProtocolConformance:
    """Dart backends implement their respective protocols."""

    def test_workspace_protocol(self) -> None:
        """DartWorkspace satisfies the Workspace protocol."""
        ws = DartWorkspace(Path('.'))
        assert isinstance(ws, Workspace)

    def test_pm_protocol(self) -> None:
        """DartBackend satisfies the PackageManager protocol."""
        pm = DartBackend(Path('.'))
        assert isinstance(pm, PackageManager)

    def test_registry_protocol(self) -> None:
        """PubDevRegistry satisfies the Registry protocol."""
        reg = PubDevRegistry()
        assert isinstance(reg, Registry)


# DartWorkspace.discover()


class TestDartWorkspaceDiscover:
    """DartWorkspace.discover() finds and classifies Dart packages."""

    @pytest.mark.asyncio
    async def test_melos_discovery(self, tmp_path: Path) -> None:
        """Packages matching melos.yaml globs are discovered."""
        _create_melos(tmp_path, ['packages/*'])
        _create_pubspec(tmp_path / 'packages' / 'genkit', 'genkit', '0.5.0')
        ws = DartWorkspace(tmp_path)
        pkgs = await ws.discover()
        assert len(pkgs) == 1
        assert pkgs[0].name == 'genkit'
        assert pkgs[0].version == '0.5.0'

    @pytest.mark.asyncio
    async def test_fallback_subdir_scan(self, tmp_path: Path) -> None:
        """Without melos.yaml, scans subdirectories for pubspec.yaml."""
        _create_pubspec(tmp_path / 'core', 'my_core', '1.0.0')
        _create_pubspec(tmp_path / 'utils', 'my_utils', '1.0.0')
        ws = DartWorkspace(tmp_path)
        pkgs = await ws.discover()
        names = [p.name for p in pkgs]
        assert 'my_core' in names
        assert 'my_utils' in names

    @pytest.mark.asyncio
    async def test_root_pubspec_included(self, tmp_path: Path) -> None:
        """Root pubspec.yaml is included in discovery."""
        _create_pubspec(tmp_path, 'root_pkg', '1.0.0')
        ws = DartWorkspace(tmp_path)
        pkgs = await ws.discover()
        assert any(p.name == 'root_pkg' for p in pkgs)

    @pytest.mark.asyncio
    async def test_internal_deps(self, tmp_path: Path) -> None:
        """Dependencies on workspace packages are classified as internal."""
        _create_melos(tmp_path, ['packages/*'])
        _create_pubspec(tmp_path / 'packages' / 'core', 'core', '1.0.0')
        _create_pubspec(
            tmp_path / 'packages' / 'plugin',
            'plugin',
            '1.0.0',
            deps={'core': '^1.0.0'},
        )
        ws = DartWorkspace(tmp_path)
        pkgs = await ws.discover()
        plugin = next(p for p in pkgs if p.name == 'plugin')
        assert 'core' in plugin.internal_deps

    @pytest.mark.asyncio
    async def test_external_deps(self, tmp_path: Path) -> None:
        """Dependencies not in workspace are classified as external."""
        _create_melos(tmp_path, ['packages/*'])
        _create_pubspec(
            tmp_path / 'packages' / 'core',
            'core',
            '1.0.0',
            deps={'http': '^1.0.0'},
        )
        ws = DartWorkspace(tmp_path)
        pkgs = await ws.discover()
        assert 'http' in pkgs[0].external_deps

    @pytest.mark.asyncio
    async def test_private_package(self, tmp_path: Path) -> None:
        """Packages with publish_to: none are not publishable."""
        _create_melos(tmp_path, ['packages/*'])
        _create_pubspec(tmp_path / 'packages' / 'internal', 'internal', private=True)
        ws = DartWorkspace(tmp_path)
        pkgs = await ws.discover()
        assert pkgs[0].is_publishable is False

    @pytest.mark.asyncio
    async def test_exclude_patterns(self, tmp_path: Path) -> None:
        """Exclude patterns filter packages by name."""
        _create_melos(tmp_path, ['packages/*'])
        _create_pubspec(tmp_path / 'packages' / 'core', 'core')
        _create_pubspec(tmp_path / 'packages' / 'example', 'example_app')
        ws = DartWorkspace(tmp_path)
        pkgs = await ws.discover(exclude_patterns=['example_*'])
        names = [p.name for p in pkgs]
        assert 'example_app' not in names
        assert 'core' in names

    @pytest.mark.asyncio
    async def test_manifest_path(self, tmp_path: Path) -> None:
        """Package manifest_path points to pubspec.yaml."""
        _create_pubspec(tmp_path / 'core', 'core')
        ws = DartWorkspace(tmp_path)
        pkgs = await ws.discover()
        assert pkgs[0].manifest_path.name == 'pubspec.yaml'


# DartWorkspace.rewrite_version()


class TestDartWorkspaceRewriteVersion:
    """DartWorkspace.rewrite_version() edits pubspec.yaml."""

    @pytest.mark.asyncio
    async def test_rewrite_version(self, tmp_path: Path) -> None:
        """Version is rewritten and old version returned."""
        pkg_dir = _create_pubspec(tmp_path / 'core', 'core', '1.0.0')
        ws = DartWorkspace(tmp_path)
        old = await ws.rewrite_version(pkg_dir / 'pubspec.yaml', '2.0.0')
        assert old == '1.0.0'
        text = (pkg_dir / 'pubspec.yaml').read_text()
        assert 'version: 2.0.0' in text


# DartWorkspace.rewrite_dependency_version()


class TestDartWorkspaceRewriteDependencyVersion:
    """DartWorkspace.rewrite_dependency_version() edits dep constraints."""

    @pytest.mark.asyncio
    async def test_rewrite_dep_version(self, tmp_path: Path) -> None:
        """Dependency version is updated in pubspec.yaml."""
        pkg_dir = _create_pubspec(
            tmp_path / 'plugin',
            'plugin',
            deps={'core': '^1.0.0'},
        )
        ws = DartWorkspace(tmp_path)
        await ws.rewrite_dependency_version(pkg_dir / 'pubspec.yaml', 'core', '2.0.0')
        text = (pkg_dir / 'pubspec.yaml').read_text()
        assert '^2.0.0' in text

    @pytest.mark.asyncio
    async def test_no_match_is_noop(self, tmp_path: Path) -> None:
        """Non-matching dep name is a no-op."""
        pkg_dir = _create_pubspec(
            tmp_path / 'core',
            'core',
            deps={'http': '^1.0.0'},
        )
        ws = DartWorkspace(tmp_path)
        await ws.rewrite_dependency_version(pkg_dir / 'pubspec.yaml', 'nonexistent', '1.0.0')


# PubDevRegistry


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


class TestPubDevRegistry:
    """Tests for PubDevRegistry backend."""

    @pytest.mark.asyncio()
    async def test_check_published_exists(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns True when package version exists on pub.dev."""
        reg = PubDevRegistry(base_url='https://pub.test')
        body = json.dumps({'version': '1.0.0'})
        transport = _mock_transport({'/api/packages/genkit/versions/1.0.0': (200, body)})
        monkeypatch.setattr('releasekit.backends.registry.pubdev.http_client', _make_client_cm(transport))
        assert await reg.check_published('genkit', '1.0.0') is True

    @pytest.mark.asyncio()
    async def test_check_published_not_exists(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns False when package version is not on pub.dev."""
        reg = PubDevRegistry(base_url='https://pub.test')
        transport = _mock_transport({})
        monkeypatch.setattr('releasekit.backends.registry.pubdev.http_client', _make_client_cm(transport))
        assert await reg.check_published('genkit', '9.9.9') is False

    @pytest.mark.asyncio()
    async def test_project_exists(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns True when package exists on pub.dev."""
        reg = PubDevRegistry(base_url='https://pub.test')
        transport = _mock_transport({'/api/packages/genkit': (200, '{}')})
        monkeypatch.setattr('releasekit.backends.registry.pubdev.http_client', _make_client_cm(transport))
        assert await reg.project_exists('genkit') is True

    @pytest.mark.asyncio()
    async def test_latest_version(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns latest version from pub.dev."""
        reg = PubDevRegistry(base_url='https://pub.test')
        body = json.dumps({'latest': {'version': '2.0.0'}})
        transport = _mock_transport({'/api/packages/genkit': (200, body)})
        monkeypatch.setattr('releasekit.backends.registry.pubdev.http_client', _make_client_cm(transport))
        assert await reg.latest_version('genkit') == '2.0.0'

    @pytest.mark.asyncio()
    async def test_latest_version_not_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns None when package is not on pub.dev."""
        reg = PubDevRegistry(base_url='https://pub.test')
        transport = _mock_transport({})
        monkeypatch.setattr('releasekit.backends.registry.pubdev.http_client', _make_client_cm(transport))
        assert await reg.latest_version('nonexistent') is None

    @pytest.mark.asyncio()
    async def test_verify_checksum_noop(self) -> None:
        """Checksum verification returns all files as missing."""
        reg = PubDevRegistry()
        result = await reg.verify_checksum('genkit', '1.0.0', {'file.tar.gz': 'abc'})
        assert 'file.tar.gz' in result.missing
