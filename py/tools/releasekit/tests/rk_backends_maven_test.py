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

"""Tests for Java/Maven ecosystem backends (MavenWorkspace, MavenBackend, MavenCentralRegistry).

Verifies that:

- MavenWorkspace discovers modules from pom.xml (Maven) and settings.gradle (Gradle).
- MavenWorkspace classifies internal vs external dependencies.
- MavenWorkspace rewrites versions in pom.xml and build.gradle.
- MavenBackend conforms to the PackageManager protocol.
- MavenCentralRegistry conforms to the Registry protocol.
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
from releasekit.backends.pm.maven import MavenBackend
from releasekit.backends.registry import Registry
from releasekit.backends.registry.maven_central import MavenCentralRegistry
from releasekit.backends.workspace import Workspace
from releasekit.backends.workspace.maven import MavenWorkspace

# Helpers — Maven

_POM_TEMPLATE = """\
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>{group_id}</groupId>
    <artifactId>{artifact_id}</artifactId>
    <version>{version}</version>
    {modules_block}
    {deps_block}
</project>
"""


def _create_parent_pom(root: Path, group_id: str, modules: list[str]) -> None:
    """Create a parent pom.xml with <modules>."""
    root.mkdir(parents=True, exist_ok=True)
    modules_xml = '<modules>\n' + '\n'.join(f'        <module>{m}</module>' for m in modules) + '\n    </modules>'
    (root / 'pom.xml').write_text(
        _POM_TEMPLATE.format(
            group_id=group_id,
            artifact_id='parent',
            version='1.0.0',
            modules_block=modules_xml,
            deps_block='',
        ),
        encoding='utf-8',
    )


def _create_module_pom(
    root: Path,
    subdir: str,
    group_id: str,
    artifact_id: str,
    version: str = '1.0.0',
    deps: list[str] | None = None,
) -> Path:
    """Create a module pom.xml."""
    mod_dir = root / subdir
    mod_dir.mkdir(parents=True, exist_ok=True)
    deps_xml = ''
    if deps:
        dep_entries = '\n'.join(f'        <dependency><artifactId>{d}</artifactId></dependency>' for d in deps)
        deps_xml = f'<dependencies>\n{dep_entries}\n    </dependencies>'
    (mod_dir / 'pom.xml').write_text(
        _POM_TEMPLATE.format(
            group_id=group_id,
            artifact_id=artifact_id,
            version=version,
            modules_block='',
            deps_block=deps_xml,
        ),
        encoding='utf-8',
    )
    return mod_dir


# Helpers — Gradle


def _create_settings_gradle(root: Path, includes: list[str]) -> None:
    """Create a settings.gradle with include directives."""
    root.mkdir(parents=True, exist_ok=True)
    lines = [f"include ':{inc}'" for inc in includes]
    (root / 'settings.gradle').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def _create_gradle_project(
    root: Path,
    subdir: str,
    version: str = '1.0.0',
) -> Path:
    """Create a build.gradle for a subproject."""
    proj_dir = root / subdir
    proj_dir.mkdir(parents=True, exist_ok=True)
    (proj_dir / 'build.gradle').write_text(
        f"group = 'com.example'\nversion = '{version}'\n",
        encoding='utf-8',
    )
    return proj_dir


# Protocol conformance


class TestMavenProtocolConformance:
    """Maven/Java backends implement their respective protocols."""

    def test_workspace_protocol(self) -> None:
        """MavenWorkspace satisfies the Workspace protocol."""
        ws = MavenWorkspace(Path('.'))
        assert isinstance(ws, Workspace)

    def test_pm_protocol(self) -> None:
        """MavenBackend satisfies the PackageManager protocol."""
        pm = MavenBackend(Path('.'))
        assert isinstance(pm, PackageManager)

    def test_registry_protocol(self) -> None:
        """MavenCentralRegistry satisfies the Registry protocol."""
        reg = MavenCentralRegistry()
        assert isinstance(reg, Registry)


# MavenWorkspace.discover() — Maven


class TestMavenWorkspaceDiscoverMaven:
    """MavenWorkspace.discover() finds Maven modules from pom.xml."""

    @pytest.mark.asyncio
    async def test_basic_discovery(self, tmp_path: Path) -> None:
        """Modules listed in parent POM are discovered."""
        _create_parent_pom(tmp_path, 'com.example', ['core', 'utils'])
        _create_module_pom(tmp_path, 'core', 'com.example', 'core', '1.0.0')
        _create_module_pom(tmp_path, 'utils', 'com.example', 'utils', '1.0.0')
        ws = MavenWorkspace(tmp_path)
        pkgs = await ws.discover()
        assert len(pkgs) == 2
        names = [p.name for p in pkgs]
        assert 'core' in names
        assert 'utils' in names

    @pytest.mark.asyncio
    async def test_internal_deps(self, tmp_path: Path) -> None:
        """Dependencies on workspace modules are classified as internal."""
        _create_parent_pom(tmp_path, 'com.example', ['core', 'app'])
        _create_module_pom(tmp_path, 'core', 'com.example', 'core')
        _create_module_pom(tmp_path, 'app', 'com.example', 'app', deps=['core'])
        ws = MavenWorkspace(tmp_path)
        pkgs = await ws.discover()
        app = next(p for p in pkgs if p.name == 'app')
        assert 'core' in app.internal_deps

    @pytest.mark.asyncio
    async def test_external_deps(self, tmp_path: Path) -> None:
        """Dependencies not in workspace are classified as external."""
        _create_parent_pom(tmp_path, 'com.example', ['core'])
        _create_module_pom(tmp_path, 'core', 'com.example', 'core', deps=['guava'])
        ws = MavenWorkspace(tmp_path)
        pkgs = await ws.discover()
        assert 'guava' in pkgs[0].external_deps

    @pytest.mark.asyncio
    async def test_exclude_patterns(self, tmp_path: Path) -> None:
        """Exclude patterns filter modules by artifactId."""
        _create_parent_pom(tmp_path, 'com.example', ['core', 'samples'])
        _create_module_pom(tmp_path, 'core', 'com.example', 'core')
        _create_module_pom(tmp_path, 'samples', 'com.example', 'samples')
        ws = MavenWorkspace(tmp_path)
        pkgs = await ws.discover(exclude_patterns=['samples'])
        names = [p.name for p in pkgs]
        assert 'samples' not in names

    @pytest.mark.asyncio
    async def test_missing_pom(self, tmp_path: Path) -> None:
        """Missing pom.xml returns empty list."""
        ws = MavenWorkspace(tmp_path)
        pkgs = await ws.discover()
        assert pkgs == []

    @pytest.mark.asyncio
    async def test_manifest_path(self, tmp_path: Path) -> None:
        """Package manifest_path points to pom.xml."""
        _create_parent_pom(tmp_path, 'com.example', ['core'])
        _create_module_pom(tmp_path, 'core', 'com.example', 'core')
        ws = MavenWorkspace(tmp_path)
        pkgs = await ws.discover()
        assert pkgs[0].manifest_path.name == 'pom.xml'


# MavenWorkspace.discover() — Gradle


class TestMavenWorkspaceDiscoverGradle:
    """MavenWorkspace.discover() finds Gradle subprojects from settings.gradle."""

    @pytest.mark.asyncio
    async def test_basic_gradle_discovery(self, tmp_path: Path) -> None:
        """Subprojects listed in settings.gradle are discovered."""
        _create_settings_gradle(tmp_path, ['core', 'utils'])
        _create_gradle_project(tmp_path, 'core', '1.0.0')
        _create_gradle_project(tmp_path, 'utils', '2.0.0')
        ws = MavenWorkspace(tmp_path)
        pkgs = await ws.discover()
        assert len(pkgs) == 2
        names = [p.name for p in pkgs]
        assert 'core' in names
        assert 'utils' in names

    @pytest.mark.asyncio
    async def test_gradle_version_parsed(self, tmp_path: Path) -> None:
        """Version is parsed from build.gradle."""
        _create_settings_gradle(tmp_path, ['core'])
        _create_gradle_project(tmp_path, 'core', '3.5.0')
        ws = MavenWorkspace(tmp_path)
        pkgs = await ws.discover()
        assert pkgs[0].version == '3.5.0'

    @pytest.mark.asyncio
    async def test_gradle_exclude_patterns(self, tmp_path: Path) -> None:
        """Exclude patterns filter Gradle subprojects."""
        _create_settings_gradle(tmp_path, ['core', 'sample'])
        _create_gradle_project(tmp_path, 'core')
        _create_gradle_project(tmp_path, 'sample')
        ws = MavenWorkspace(tmp_path)
        pkgs = await ws.discover(exclude_patterns=['sample'])
        names = [p.name for p in pkgs]
        assert 'sample' not in names

    @pytest.mark.asyncio
    async def test_missing_settings_gradle(self, tmp_path: Path) -> None:
        """Missing settings.gradle with no pom.xml returns empty list."""
        ws = MavenWorkspace(tmp_path)
        pkgs = await ws.discover()
        assert pkgs == []


# MavenWorkspace.rewrite_version()


class TestMavenWorkspaceRewriteVersion:
    """MavenWorkspace.rewrite_version() edits pom.xml and build.gradle."""

    @pytest.mark.asyncio
    async def test_rewrite_pom_version(self, tmp_path: Path) -> None:
        """Version is rewritten in pom.xml."""
        mod_dir = _create_module_pom(tmp_path, 'core', 'com.example', 'core', '1.0.0')
        ws = MavenWorkspace(tmp_path)
        old = await ws.rewrite_version(mod_dir / 'pom.xml', '2.0.0')
        assert old == '1.0.0'
        text = (mod_dir / 'pom.xml').read_text()
        assert '<version>2.0.0</version>' in text

    @pytest.mark.asyncio
    async def test_rewrite_gradle_version(self, tmp_path: Path) -> None:
        """Version is rewritten in build.gradle."""
        proj_dir = _create_gradle_project(tmp_path, 'core', '1.0.0')
        ws = MavenWorkspace(tmp_path)
        old = await ws.rewrite_version(proj_dir / 'build.gradle', '2.0.0')
        assert old == '1.0.0'
        text = (proj_dir / 'build.gradle').read_text()
        assert "'2.0.0'" in text


# MavenWorkspace.rewrite_dependency_version()


class TestMavenWorkspaceRewriteDependencyVersion:
    """MavenWorkspace.rewrite_dependency_version() edits dep constraints."""

    @pytest.mark.asyncio
    async def test_rewrite_pom_dep(self, tmp_path: Path) -> None:
        """Dependency version is updated in pom.xml."""
        mod_dir = tmp_path / 'app'
        mod_dir.mkdir(parents=True)
        (mod_dir / 'pom.xml').write_text(
            '<?xml version="1.0"?>\n<project>\n'
            '  <dependencies>\n'
            '    <dependency>\n'
            '      <artifactId>core</artifactId>\n'
            '      <version>1.0.0</version>\n'
            '    </dependency>\n'
            '  </dependencies>\n'
            '</project>\n',
            encoding='utf-8',
        )
        ws = MavenWorkspace(tmp_path)
        await ws.rewrite_dependency_version(mod_dir / 'pom.xml', 'core', '2.0.0')
        text = (mod_dir / 'pom.xml').read_text()
        assert '2.0.0' in text

    @pytest.mark.asyncio
    async def test_no_match_is_noop(self, tmp_path: Path) -> None:
        """Non-matching dep name is a no-op."""
        mod_dir = _create_module_pom(tmp_path, 'core', 'com.example', 'core', deps=['guava'])
        ws = MavenWorkspace(tmp_path)
        await ws.rewrite_dependency_version(mod_dir / 'pom.xml', 'nonexistent', '1.0.0')


# MavenCentralRegistry


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


def _maven_transport(body: str, status: int = 200) -> Any:  # noqa: ANN401
    """Create a transport that always returns the given response for solrsearch URLs."""

    def handler(request: httpx.Request) -> httpx.Response:
        """Handler."""
        url = str(request.url)
        if 'solrsearch/select' in url:
            return httpx.Response(status, text=body)
        return httpx.Response(404, text='Not found')

    return handler


class TestMavenCentralRegistry:
    """Tests for MavenCentralRegistry backend."""

    @pytest.mark.asyncio()
    async def test_check_published_exists(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns True when artifact version exists on Maven Central."""
        reg = MavenCentralRegistry(base_url='https://search.test')
        body = json.dumps({'response': {'numFound': 1}})
        monkeypatch.setattr(
            'releasekit.backends.registry.maven_central.http_client',
            _make_client_cm(_maven_transport(body)),
        )
        assert await reg.check_published('com.example:core', '1.0.0') is True

    @pytest.mark.asyncio()
    async def test_check_published_not_exists(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns False when artifact version is not on Maven Central."""
        reg = MavenCentralRegistry(base_url='https://search.test')
        body = json.dumps({'response': {'numFound': 0}})
        monkeypatch.setattr(
            'releasekit.backends.registry.maven_central.http_client',
            _make_client_cm(_maven_transport(body)),
        )
        assert await reg.check_published('com.example:core', '9.9.9') is False

    @pytest.mark.asyncio()
    async def test_project_exists(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns True when artifact exists on Maven Central."""
        reg = MavenCentralRegistry(base_url='https://search.test')
        body = json.dumps({'response': {'numFound': 1}})
        monkeypatch.setattr(
            'releasekit.backends.registry.maven_central.http_client',
            _make_client_cm(_maven_transport(body)),
        )
        assert await reg.project_exists('com.example:core') is True

    @pytest.mark.asyncio()
    async def test_project_not_exists(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns False when artifact does not exist on Maven Central."""
        reg = MavenCentralRegistry(base_url='https://search.test')
        body = json.dumps({'response': {'numFound': 0}})
        monkeypatch.setattr(
            'releasekit.backends.registry.maven_central.http_client',
            _make_client_cm(_maven_transport(body)),
        )
        assert await reg.project_exists('com.example:nonexistent') is False

    @pytest.mark.asyncio()
    async def test_latest_version(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns latest version from Maven Central."""
        reg = MavenCentralRegistry(base_url='https://search.test')
        body = json.dumps({'response': {'docs': [{'v': '2.1.0'}]}})
        monkeypatch.setattr(
            'releasekit.backends.registry.maven_central.http_client',
            _make_client_cm(_maven_transport(body)),
        )
        assert await reg.latest_version('com.example:core') == '2.1.0'

    @pytest.mark.asyncio()
    async def test_latest_version_not_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns None when artifact is not on Maven Central."""
        reg = MavenCentralRegistry(base_url='https://search.test')
        monkeypatch.setattr(
            'releasekit.backends.registry.maven_central.http_client',
            _make_client_cm(_maven_transport('', status=404)),
        )
        assert await reg.latest_version('com.example:nonexistent') is None

    @pytest.mark.asyncio()
    async def test_verify_checksum_noop(self) -> None:
        """Checksum verification returns all files as missing."""
        reg = MavenCentralRegistry()
        result = await reg.verify_checksum('com.example:core', '1.0.0', {'file.jar': 'abc'})
        assert 'file.jar' in result.missing
