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

"""Tests for _create_backends() dispatch and registry_url wiring in cli.py.

Verifies that the correct PackageManager and Registry backend types are
instantiated for each tool/ecosystem, and that registry_url overrides
the default base URL when set.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from releasekit.backends.pm import (
    CargoBackend,
    DartBackend,
    GoBackend,
    MavenBackend,
    PnpmBackend,
    UvBackend,
)
from releasekit.backends.registry import (
    CratesIoRegistry,
    GoProxyCheck,
    MavenCentralRegistry,
    NpmRegistry,
    PubDevRegistry,
    PyPIBackend,
)
from releasekit.cli import _create_backends
from releasekit.config import CONFIG_FILENAME, VALID_WORKSPACE_KEYS, ReleaseConfig, WorkspaceConfig, load_config


def _config(forge: str = 'none') -> ReleaseConfig:
    """Minimal ReleaseConfig for testing."""
    return ReleaseConfig(forge=forge)


# ── Tool → Backend Dispatch ──────────────────────────────────────────


class TestCreateBackendsDispatch:
    """_create_backends selects the right PM + Registry for each tool."""

    def test_default_is_uv_pypi(self, tmp_path: Path) -> None:
        """No ws_config → defaults to UvBackend + PyPIBackend."""
        _vcs, pm, _forge, registry = _create_backends(tmp_path, _config())
        assert isinstance(pm, UvBackend)
        assert isinstance(registry, PyPIBackend)

    def test_uv_tool(self, tmp_path: Path) -> None:
        """tool='uv' → UvBackend + PyPIBackend."""
        ws = WorkspaceConfig(tool='uv')
        _vcs, pm, _forge, registry = _create_backends(tmp_path, _config(), ws_config=ws)
        assert isinstance(pm, UvBackend)
        assert isinstance(registry, PyPIBackend)

    def test_pnpm_tool(self, tmp_path: Path) -> None:
        """tool='pnpm' → PnpmBackend + NpmRegistry."""
        ws = WorkspaceConfig(tool='pnpm')
        _vcs, pm, _forge, registry = _create_backends(tmp_path, _config(), ws_config=ws)
        assert isinstance(pm, PnpmBackend)
        assert isinstance(registry, NpmRegistry)

    def test_go_tool(self, tmp_path: Path) -> None:
        """tool='go' → GoBackend + GoProxyCheck."""
        ws = WorkspaceConfig(tool='go')
        _vcs, pm, _forge, registry = _create_backends(tmp_path, _config(), ws_config=ws)
        assert isinstance(pm, GoBackend)
        assert isinstance(registry, GoProxyCheck)

    def test_pub_tool(self, tmp_path: Path) -> None:
        """tool='pub' → DartBackend + PubDevRegistry."""
        ws = WorkspaceConfig(tool='pub')
        _vcs, pm, _forge, registry = _create_backends(tmp_path, _config(), ws_config=ws)
        assert isinstance(pm, DartBackend)
        assert isinstance(registry, PubDevRegistry)

    def test_gradle_tool(self, tmp_path: Path) -> None:
        """tool='gradle' → MavenBackend + MavenCentralRegistry."""
        ws = WorkspaceConfig(tool='gradle')
        _vcs, pm, _forge, registry = _create_backends(tmp_path, _config(), ws_config=ws)
        assert isinstance(pm, MavenBackend)
        assert isinstance(registry, MavenCentralRegistry)

    def test_maven_tool(self, tmp_path: Path) -> None:
        """tool='maven' → MavenBackend + MavenCentralRegistry."""
        ws = WorkspaceConfig(tool='maven')
        _vcs, pm, _forge, registry = _create_backends(tmp_path, _config(), ws_config=ws)
        assert isinstance(pm, MavenBackend)
        assert isinstance(registry, MavenCentralRegistry)

    def test_cargo_tool(self, tmp_path: Path) -> None:
        """tool='cargo' → CargoBackend + CratesIoRegistry."""
        ws = WorkspaceConfig(tool='cargo')
        _vcs, pm, _forge, registry = _create_backends(tmp_path, _config(), ws_config=ws)
        assert isinstance(pm, CargoBackend)
        assert isinstance(registry, CratesIoRegistry)


# ── registry_url Override ────────────────────────────────────────────


class TestRegistryUrlOverride:
    """registry_url on WorkspaceConfig overrides the default base URL."""

    def test_pypi_registry_url(self, tmp_path: Path) -> None:
        """PyPIBackend uses custom base_url when registry_url is set."""
        ws = WorkspaceConfig(tool='uv', registry_url='https://test.pypi.org')
        _vcs, _pm, _forge, registry = _create_backends(tmp_path, _config(), ws_config=ws)
        assert isinstance(registry, PyPIBackend)
        assert registry._base_url == 'https://test.pypi.org'

    def test_pypi_default_url(self, tmp_path: Path) -> None:
        """PyPIBackend uses production URL when registry_url is empty."""
        ws = WorkspaceConfig(tool='uv')
        _vcs, _pm, _forge, registry = _create_backends(tmp_path, _config(), ws_config=ws)
        assert isinstance(registry, PyPIBackend)
        assert registry._base_url == 'https://pypi.org'

    def test_npm_registry_url(self, tmp_path: Path) -> None:
        """NpmRegistry uses custom base_url when registry_url is set."""
        ws = WorkspaceConfig(tool='pnpm', registry_url='http://localhost:4873')
        _vcs, _pm, _forge, registry = _create_backends(tmp_path, _config(), ws_config=ws)
        assert isinstance(registry, NpmRegistry)
        assert registry._base_url == 'http://localhost:4873'

    def test_go_proxy_registry_url(self, tmp_path: Path) -> None:
        """GoProxyCheck uses custom base_url when registry_url is set."""
        ws = WorkspaceConfig(tool='go', registry_url='http://localhost:3000')
        _vcs, _pm, _forge, registry = _create_backends(tmp_path, _config(), ws_config=ws)
        assert isinstance(registry, GoProxyCheck)
        assert registry._base_url == 'http://localhost:3000'

    def test_pubdev_registry_url(self, tmp_path: Path) -> None:
        """PubDevRegistry uses custom base_url when registry_url is set."""
        ws = WorkspaceConfig(tool='pub', registry_url='http://localhost:8080')
        _vcs, _pm, _forge, registry = _create_backends(tmp_path, _config(), ws_config=ws)
        assert isinstance(registry, PubDevRegistry)
        assert registry._base_url == 'http://localhost:8080'

    def test_maven_registry_url(self, tmp_path: Path) -> None:
        """MavenCentralRegistry uses custom base_url when registry_url is set."""
        ws = WorkspaceConfig(tool='gradle', registry_url='http://localhost:8081')
        _vcs, _pm, _forge, registry = _create_backends(tmp_path, _config(), ws_config=ws)
        assert isinstance(registry, MavenCentralRegistry)
        assert registry._base_url == 'http://localhost:8081'

    def test_crates_io_registry_url(self, tmp_path: Path) -> None:
        """CratesIoRegistry uses custom base_url when registry_url is set."""
        ws = WorkspaceConfig(tool='cargo', registry_url='http://localhost:3000')
        _vcs, _pm, _forge, registry = _create_backends(tmp_path, _config(), ws_config=ws)
        assert isinstance(registry, CratesIoRegistry)
        assert registry._base_url == 'http://localhost:3000'


# ── Test Registry Constants ──────────────────────────────────────────


class TestRegistryConstants:
    """Each registry backend exposes DEFAULT_BASE_URL and TEST_BASE_URL."""

    @pytest.mark.parametrize(
        'cls,expected_default',
        [
            (PyPIBackend, 'https://pypi.org'),
            (NpmRegistry, 'https://registry.npmjs.org'),
            (GoProxyCheck, 'https://proxy.golang.org'),
            (PubDevRegistry, 'https://pub.dev'),
            (MavenCentralRegistry, 'https://search.maven.org'),
            (CratesIoRegistry, 'https://crates.io'),
        ],
    )
    def test_default_base_url(self, cls: type, expected_default: str) -> None:
        """DEFAULT_BASE_URL matches the production registry."""
        assert cls.DEFAULT_BASE_URL == expected_default  # ty: ignore[unresolved-attribute]

    @pytest.mark.parametrize(
        'cls',
        [
            PyPIBackend,
            NpmRegistry,
            GoProxyCheck,
            PubDevRegistry,
            MavenCentralRegistry,
            CratesIoRegistry,
        ],
    )
    def test_test_base_url_exists(self, cls: type) -> None:
        """TEST_BASE_URL is defined and non-empty."""
        assert hasattr(cls, 'TEST_BASE_URL')
        assert cls.TEST_BASE_URL


# ── Config registry_url Field ────────────────────────────────────────


class TestConfigRegistryUrl:
    """WorkspaceConfig.registry_url is accepted in config loading."""

    def test_registry_url_in_valid_keys(self) -> None:
        """registry_url is in VALID_WORKSPACE_KEYS."""
        assert 'registry_url' in VALID_WORKSPACE_KEYS

    def test_workspace_config_default(self) -> None:
        """WorkspaceConfig.registry_url defaults to empty string."""
        ws = WorkspaceConfig()
        assert ws.registry_url == ''

    def test_workspace_config_set(self) -> None:
        """WorkspaceConfig.registry_url can be set."""
        ws = WorkspaceConfig(registry_url='https://test.pypi.org')
        assert ws.registry_url == 'https://test.pypi.org'

    def test_registry_url_roundtrip(self, tmp_path: Path) -> None:
        """registry_url survives TOML write → load round-trip."""
        toml_content = """\
forge = "none"

[workspace.py]
ecosystem = "python"
root = "."
registry_url = "https://test.pypi.org"
"""
        (tmp_path / CONFIG_FILENAME).write_text(toml_content)
        config = load_config(tmp_path)
        assert config.workspaces['py'].registry_url == 'https://test.pypi.org'
