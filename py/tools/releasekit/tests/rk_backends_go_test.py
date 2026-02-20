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

"""Tests for Go ecosystem backends (GoWorkspace, GoBackend, GoProxyCheck).

Verifies that:

- GoWorkspace discovers modules from go.work and go.mod files.
- GoWorkspace classifies internal vs external dependencies.
- GoWorkspace rewrite_version is a no-op (returns Go toolchain version).
- GoWorkspace rewrite_dependency_version updates require directives.
- GoBackend conforms to the PackageManager protocol.
- GoProxyCheck conforms to the Registry protocol.
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
from releasekit.backends.pm.go import GoBackend
from releasekit.backends.registry import Registry
from releasekit.backends.registry.goproxy import GoProxyCheck
from releasekit.backends.workspace import Workspace
from releasekit.backends.workspace.go import GoWorkspace

# Helpers


def _create_go_workspace(root: Path, modules: list[str]) -> None:
    """Create a go.work file with the given module directories."""
    use_block = '\n'.join(f'\t./{m}' for m in modules)
    (root / 'go.work').write_text(
        f'go 1.24\n\nuse (\n{use_block}\n)\n',
        encoding='utf-8',
    )


def _create_go_module(
    root: Path,
    subdir: str,
    module_path: str,
    go_version: str = '1.24',
    requires: list[str] | None = None,
) -> Path:
    """Create a go.mod file for a module."""
    mod_dir = root / subdir
    mod_dir.mkdir(parents=True, exist_ok=True)
    req_lines = ''
    if requires:
        req_block = '\n'.join(f'\t{r} v0.1.0' for r in requires)
        req_lines = f'\nrequire (\n{req_block}\n)\n'
    (mod_dir / 'go.mod').write_text(
        f'module {module_path}\n\ngo {go_version}\n{req_lines}',
        encoding='utf-8',
    )
    return mod_dir


# Protocol conformance


class TestGoProtocolConformance:
    """Go backends implement their respective protocols."""

    def test_workspace_protocol(self) -> None:
        """GoWorkspace satisfies the Workspace protocol."""
        ws = GoWorkspace(Path('.'))
        assert isinstance(ws, Workspace)

    def test_pm_protocol(self) -> None:
        """GoBackend satisfies the PackageManager protocol."""
        pm = GoBackend(Path('.'))
        assert isinstance(pm, PackageManager)

    def test_registry_protocol(self) -> None:
        """GoProxyCheck satisfies the Registry protocol."""
        reg = GoProxyCheck()
        assert isinstance(reg, Registry)


# GoWorkspace.discover()


class TestGoWorkspaceDiscover:
    """GoWorkspace.discover() finds and classifies Go modules."""

    @pytest.mark.asyncio
    async def test_basic_discovery(self, tmp_path: Path) -> None:
        """Modules listed in go.work are discovered."""
        _create_go_module(tmp_path, 'genkit', 'github.com/firebase/genkit/go/genkit')
        _create_go_workspace(tmp_path, ['genkit'])
        ws = GoWorkspace(tmp_path)
        pkgs = await ws.discover()
        assert len(pkgs) == 1
        assert pkgs[0].name == 'genkit'
        assert pkgs[0].version == '1.24'
        assert pkgs[0].is_publishable is True

    @pytest.mark.asyncio
    async def test_multiple_modules(self, tmp_path: Path) -> None:
        """Multiple modules are discovered and sorted."""
        _create_go_module(tmp_path, 'genkit', 'github.com/firebase/genkit/go/genkit')
        _create_go_module(tmp_path, 'plugins/googleai', 'github.com/firebase/genkit/go/plugins/googleai')
        _create_go_workspace(tmp_path, ['genkit', 'plugins/googleai'])
        ws = GoWorkspace(tmp_path)
        pkgs = await ws.discover()
        assert len(pkgs) == 2
        assert pkgs[0].name == 'genkit'
        assert pkgs[1].name == 'googleai'

    @pytest.mark.asyncio
    async def test_internal_deps(self, tmp_path: Path) -> None:
        """Dependencies on workspace modules are classified as internal."""
        _create_go_module(tmp_path, 'genkit', 'github.com/firebase/genkit/go/genkit')
        _create_go_module(
            tmp_path,
            'plugins/googleai',
            'github.com/firebase/genkit/go/plugins/googleai',
            requires=['github.com/firebase/genkit/go/genkit'],
        )
        _create_go_workspace(tmp_path, ['genkit', 'plugins/googleai'])
        ws = GoWorkspace(tmp_path)
        pkgs = await ws.discover()
        plugin = next(p for p in pkgs if p.name == 'googleai')
        assert len(plugin.internal_deps) == 1

    @pytest.mark.asyncio
    async def test_external_deps(self, tmp_path: Path) -> None:
        """Dependencies not in workspace are classified as external."""
        _create_go_module(
            tmp_path,
            'genkit',
            'github.com/firebase/genkit/go/genkit',
            requires=['golang.org/x/net'],
        )
        _create_go_workspace(tmp_path, ['genkit'])
        ws = GoWorkspace(tmp_path)
        pkgs = await ws.discover()
        assert 'golang.org/x/net' in pkgs[0].external_deps

    @pytest.mark.asyncio
    async def test_exclude_patterns(self, tmp_path: Path) -> None:
        """Exclude patterns filter modules by short name."""
        _create_go_module(tmp_path, 'genkit', 'github.com/firebase/genkit/go/genkit')
        _create_go_module(tmp_path, 'samples', 'github.com/firebase/genkit/go/samples')
        _create_go_workspace(tmp_path, ['genkit', 'samples'])
        ws = GoWorkspace(tmp_path)
        pkgs = await ws.discover(exclude_patterns=['samples'])
        names = [p.name for p in pkgs]
        assert 'samples' not in names
        assert 'genkit' in names

    @pytest.mark.asyncio
    async def test_missing_go_work_and_go_mod(self, tmp_path: Path) -> None:
        """Missing both go.work and go.mod returns empty list."""
        ws = GoWorkspace(tmp_path)
        pkgs = await ws.discover()
        assert pkgs == []

    @pytest.mark.asyncio
    async def test_single_module_go_mod(self, tmp_path: Path) -> None:
        """Standalone go.mod (no go.work) discovers the root module."""
        _create_go_module(tmp_path, '.', 'github.com/firebase/genkit/go')
        ws = GoWorkspace(tmp_path)
        pkgs = await ws.discover()
        assert len(pkgs) == 1
        assert pkgs[0].name == 'go'
        assert pkgs[0].is_publishable is True

    @pytest.mark.asyncio
    async def test_single_module_with_sub_modules(self, tmp_path: Path) -> None:
        """Standalone go.mod discovers root + nested sub-modules."""
        _create_go_module(tmp_path, '.', 'github.com/firebase/genkit/go')
        _create_go_module(
            tmp_path,
            'samples/mcp-demo',
            'github.com/firebase/genkit/go/samples/mcp-demo',
        )
        ws = GoWorkspace(tmp_path)
        pkgs = await ws.discover()
        names = sorted(p.name for p in pkgs)
        assert names == ['go', 'mcp-demo']

    @pytest.mark.asyncio
    async def test_single_module_sub_module_deps(self, tmp_path: Path) -> None:
        """Sub-module depending on root is classified as internal dep."""
        _create_go_module(tmp_path, '.', 'github.com/firebase/genkit/go')
        _create_go_module(
            tmp_path,
            'samples/demo',
            'github.com/firebase/genkit/go/samples/demo',
            requires=['github.com/firebase/genkit/go'],
        )
        ws = GoWorkspace(tmp_path)
        pkgs = await ws.discover()
        demo = next(p for p in pkgs if p.name == 'demo')
        assert len(demo.internal_deps) == 1

    @pytest.mark.asyncio
    async def test_single_module_exclude_patterns(self, tmp_path: Path) -> None:
        """Exclude patterns work with single-module discovery."""
        _create_go_module(tmp_path, '.', 'github.com/firebase/genkit/go')
        _create_go_module(
            tmp_path,
            'samples/demo',
            'github.com/firebase/genkit/go/samples/demo',
        )
        ws = GoWorkspace(tmp_path)
        pkgs = await ws.discover(exclude_patterns=['demo'])
        names = [p.name for p in pkgs]
        assert 'demo' not in names
        assert 'go' in names

    @pytest.mark.asyncio
    async def test_manifest_path(self, tmp_path: Path) -> None:
        """Package manifest_path points to go.mod."""
        _create_go_module(tmp_path, 'genkit', 'github.com/firebase/genkit/go/genkit')
        _create_go_workspace(tmp_path, ['genkit'])
        ws = GoWorkspace(tmp_path)
        pkgs = await ws.discover()
        assert pkgs[0].manifest_path.name == 'go.mod'


# GoWorkspace.rewrite_version()


class TestGoWorkspaceRewriteVersion:
    """GoWorkspace.rewrite_version() is a no-op for Go modules."""

    @pytest.mark.asyncio
    async def test_returns_go_version(self, tmp_path: Path) -> None:
        """Returns the Go toolchain version from go.mod."""
        mod_dir = _create_go_module(tmp_path, 'genkit', 'github.com/firebase/genkit/go/genkit', '1.24')
        ws = GoWorkspace(tmp_path)
        old = await ws.rewrite_version(mod_dir / 'go.mod', '2.0.0')
        assert old == '1.24'


# GoWorkspace.rewrite_dependency_version()


class TestGoWorkspaceRewriteDependencyVersion:
    """GoWorkspace.rewrite_dependency_version() updates require directives."""

    @pytest.mark.asyncio
    async def test_rewrites_dep(self, tmp_path: Path) -> None:
        """Dependency version is updated in go.mod."""
        mod_dir = _create_go_module(
            tmp_path,
            'plugin',
            'github.com/firebase/genkit/go/plugin',
            requires=['github.com/firebase/genkit/go/genkit'],
        )
        ws = GoWorkspace(tmp_path)
        await ws.rewrite_dependency_version(
            mod_dir / 'go.mod',
            'github.com/firebase/genkit/go/genkit',
            '1.0.0',
        )
        text = (mod_dir / 'go.mod').read_text()
        assert 'v1.0.0' in text

    @pytest.mark.asyncio
    async def test_no_match_is_noop(self, tmp_path: Path) -> None:
        """Non-matching dep name is a no-op."""
        mod_dir = _create_go_module(
            tmp_path,
            'genkit',
            'github.com/firebase/genkit/go/genkit',
            requires=['golang.org/x/net'],
        )
        ws = GoWorkspace(tmp_path)
        await ws.rewrite_dependency_version(
            mod_dir / 'go.mod',
            'nonexistent/dep',
            '1.0.0',
        )


# GoProxyCheck (registry)


def _mock_transport(responses: dict[str, tuple[int, str]]) -> Any:  # noqa: ANN401
    """Create a mock transport that returns canned responses by URL suffix."""

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


class TestGoProxyCheck:
    """Tests for GoProxyCheck registry backend."""

    @pytest.mark.asyncio()
    async def test_check_published_exists(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns True when module version exists on proxy."""
        reg = GoProxyCheck(base_url='https://proxy.test')
        transport = _mock_transport({'/go/genkit/@v/v1.0.0.info': (200, '{}')})
        monkeypatch.setattr('releasekit.backends.registry.goproxy.http_client', _make_client_cm(transport))
        assert await reg.check_published('go/genkit', '1.0.0') is True

    @pytest.mark.asyncio()
    async def test_check_published_not_exists(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns False when module version is not on proxy."""
        reg = GoProxyCheck(base_url='https://proxy.test')
        transport = _mock_transport({})
        monkeypatch.setattr('releasekit.backends.registry.goproxy.http_client', _make_client_cm(transport))
        assert await reg.check_published('go/genkit', '9.9.9') is False

    @pytest.mark.asyncio()
    async def test_project_exists(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns True when module has versions on proxy."""
        reg = GoProxyCheck(base_url='https://proxy.test')
        transport = _mock_transport({'/go/genkit/@v/list': (200, 'v1.0.0\nv1.1.0\n')})
        monkeypatch.setattr('releasekit.backends.registry.goproxy.http_client', _make_client_cm(transport))
        assert await reg.project_exists('go/genkit') is True

    @pytest.mark.asyncio()
    async def test_latest_version(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns latest version from proxy."""
        reg = GoProxyCheck(base_url='https://proxy.test')
        body = json.dumps({'Version': 'v1.2.3'})
        transport = _mock_transport({'/go/genkit/@latest': (200, body)})
        monkeypatch.setattr('releasekit.backends.registry.goproxy.http_client', _make_client_cm(transport))
        assert await reg.latest_version('go/genkit') == '1.2.3'

    @pytest.mark.asyncio()
    async def test_latest_version_not_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns None when module is not on proxy."""
        reg = GoProxyCheck(base_url='https://proxy.test')
        transport = _mock_transport({})
        monkeypatch.setattr('releasekit.backends.registry.goproxy.http_client', _make_client_cm(transport))
        assert await reg.latest_version('nonexistent') is None

    @pytest.mark.asyncio()
    async def test_verify_checksum_noop(self) -> None:
        """Checksum verification returns all files as missing (not checked)."""
        reg = GoProxyCheck()
        result = await reg.verify_checksum('go/genkit', '1.0.0', {'file.tar.gz': 'abc'})
        assert 'file.tar.gz' in result.missing
