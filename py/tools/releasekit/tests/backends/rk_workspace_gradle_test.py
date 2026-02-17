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

"""Tests for Gradle-specific features in MavenWorkspace.

Covers:
- ``gradle.properties`` VERSION_NAME version format
- Version catalog (``libs.versions.toml``) version format
- Kotlin DSL ``settings.gradle.kts`` with ``include()`` syntax
- Multi-include parsing: ``include(":a", ":b")``
"""

from __future__ import annotations

from pathlib import Path

import pytest
from releasekit.backends.workspace.maven import (
    MavenWorkspace,
    _parse_settings_gradle,
    _read_gradle_properties_version,
    _read_version_catalog_version,
    _write_gradle_properties_version,
    _write_version_catalog_version,
)
from releasekit.logging import configure_logging

configure_logging(quiet=True)


# gradle.properties helpers


class TestReadGradlePropertiesVersion:
    """Tests for _read_gradle_properties_version()."""

    def test_reads_version_name(self, tmp_path: Path) -> None:
        """Should read VERSION_NAME from gradle.properties."""
        props = tmp_path / 'gradle.properties'
        props.write_text('VERSION_NAME=1.2.3\nGROUP=com.example\n')
        assert _read_gradle_properties_version(props) == '1.2.3'

    def test_reads_version_with_spaces(self, tmp_path: Path) -> None:
        """Should handle spaces around the = sign."""
        props = tmp_path / 'gradle.properties'
        props.write_text('VERSION_NAME = 2.0.0-SNAPSHOT\n')
        assert _read_gradle_properties_version(props) == '2.0.0-SNAPSHOT'

    def test_returns_empty_for_missing_file(self, tmp_path: Path) -> None:
        """Should return empty string for missing file."""
        assert _read_gradle_properties_version(tmp_path / 'gradle.properties') == ''

    def test_returns_empty_when_no_version_name(self, tmp_path: Path) -> None:
        """Should return empty string when VERSION_NAME is absent."""
        props = tmp_path / 'gradle.properties'
        props.write_text('GROUP=com.example\n')
        assert _read_gradle_properties_version(props) == ''

    def test_reads_first_version_name(self, tmp_path: Path) -> None:
        """Should read the first VERSION_NAME if duplicated."""
        props = tmp_path / 'gradle.properties'
        props.write_text('VERSION_NAME=1.0.0\nVERSION_NAME=2.0.0\n')
        assert _read_gradle_properties_version(props) == '1.0.0'


class TestWriteGradlePropertiesVersion:
    """Tests for _write_gradle_properties_version()."""

    def test_rewrites_version(self, tmp_path: Path) -> None:
        """Should rewrite VERSION_NAME and return old version."""
        props = tmp_path / 'gradle.properties'
        props.write_text('VERSION_NAME=1.2.3\nGROUP=com.example\n')
        old = _write_gradle_properties_version(props, '2.0.0')
        assert old == '1.2.3'
        text = props.read_text()
        assert 'VERSION_NAME=2.0.0' in text
        assert '1.2.3' not in text

    def test_preserves_other_properties(self, tmp_path: Path) -> None:
        """Should not modify other properties."""
        props = tmp_path / 'gradle.properties'
        props.write_text('GROUP=com.example\nVERSION_NAME=1.0.0\nPOM_URL=https://example.com\n')
        _write_gradle_properties_version(props, '3.0.0')
        text = props.read_text()
        assert 'GROUP=com.example' in text
        assert 'POM_URL=https://example.com' in text
        assert 'VERSION_NAME=3.0.0' in text

    def test_idempotent(self, tmp_path: Path) -> None:
        """Should be idempotent when called with same version."""
        props = tmp_path / 'gradle.properties'
        props.write_text('VERSION_NAME=1.0.0\n')
        _write_gradle_properties_version(props, '1.0.0')
        assert props.read_text() == 'VERSION_NAME=1.0.0\n'


# Version catalog helpers


class TestReadVersionCatalogVersion:
    """Tests for _read_version_catalog_version()."""

    def test_reads_version_from_catalog(self, tmp_path: Path) -> None:
        """Should read version from [versions] section."""
        catalog = tmp_path / 'libs.versions.toml'
        catalog.write_text(
            '[versions]\n'
            'projectVersion = "1.5.0"\n'
            'kotlin = "1.9.22"\n'
            '\n'
            '[libraries]\n'
            'guava = { module = "com.google.guava:guava", version = "33.0.0-jre" }\n'
        )
        assert _read_version_catalog_version(catalog) == '1.5.0'

    def test_reads_custom_key(self, tmp_path: Path) -> None:
        """Should read a custom version key."""
        catalog = tmp_path / 'libs.versions.toml'
        catalog.write_text('[versions]\nmyVersion = "2.0.0"\n')
        assert _read_version_catalog_version(catalog, version_key='myVersion') == '2.0.0'

    def test_returns_empty_for_missing_file(self, tmp_path: Path) -> None:
        """Should return empty string for missing file."""
        assert _read_version_catalog_version(tmp_path / 'libs.versions.toml') == ''

    def test_returns_empty_when_key_absent(self, tmp_path: Path) -> None:
        """Should return empty string when key is not in [versions]."""
        catalog = tmp_path / 'libs.versions.toml'
        catalog.write_text('[versions]\nkotlin = "1.9.22"\n')
        assert _read_version_catalog_version(catalog) == ''

    def test_returns_empty_when_no_versions_section(self, tmp_path: Path) -> None:
        """Should return empty string when [versions] section is absent."""
        catalog = tmp_path / 'libs.versions.toml'
        catalog.write_text('[libraries]\nguava = "33.0.0-jre"\n')
        assert _read_version_catalog_version(catalog) == ''

    def test_handles_single_quotes(self, tmp_path: Path) -> None:
        """Should handle single-quoted values."""
        catalog = tmp_path / 'libs.versions.toml'
        catalog.write_text("[versions]\nprojectVersion = '3.1.0'\n")
        assert _read_version_catalog_version(catalog) == '3.1.0'


class TestWriteVersionCatalogVersion:
    """Tests for _write_version_catalog_version()."""

    def test_rewrites_version(self, tmp_path: Path) -> None:
        """Should rewrite version and return old version."""
        catalog = tmp_path / 'libs.versions.toml'
        catalog.write_text('[versions]\nprojectVersion = "1.5.0"\nkotlin = "1.9.22"\n')
        old = _write_version_catalog_version(catalog, '2.0.0')
        assert old == '1.5.0'
        text = catalog.read_text()
        assert 'projectVersion = "2.0.0"' in text
        assert 'kotlin = "1.9.22"' in text

    def test_rewrites_custom_key(self, tmp_path: Path) -> None:
        """Should rewrite a custom version key."""
        catalog = tmp_path / 'libs.versions.toml'
        catalog.write_text('[versions]\nmyVersion = "1.0.0"\n')
        old = _write_version_catalog_version(catalog, '2.0.0', version_key='myVersion')
        assert old == '1.0.0'
        assert 'myVersion = "2.0.0"' in catalog.read_text()

    def test_preserves_other_entries(self, tmp_path: Path) -> None:
        """Should not modify other entries."""
        catalog = tmp_path / 'libs.versions.toml'
        catalog.write_text(
            '[versions]\n'
            'projectVersion = "1.0.0"\n'
            'kotlin = "1.9.22"\n'
            '\n'
            '[libraries]\n'
            'guava = { module = "com.google.guava:guava", version = "33.0.0-jre" }\n'
        )
        _write_version_catalog_version(catalog, '3.0.0')
        text = catalog.read_text()
        assert 'kotlin = "1.9.22"' in text
        assert 'guava' in text

    def test_idempotent(self, tmp_path: Path) -> None:
        """Should be idempotent when called with same version."""
        catalog = tmp_path / 'libs.versions.toml'
        original = '[versions]\nprojectVersion = "1.0.0"\n'
        catalog.write_text(original)
        _write_version_catalog_version(catalog, '1.0.0')
        assert catalog.read_text() == original


# Settings parsing (Kotlin DSL and multi-include)


class TestParseSettingsGradleKts:
    """Tests for _parse_settings_gradle() with Kotlin DSL."""

    def test_parses_kotlin_dsl_include(self, tmp_path: Path) -> None:
        """Should parse include() function calls in Kotlin DSL."""
        settings = tmp_path / 'settings.gradle.kts'
        settings.write_text('rootProject.name = "my-project"\ninclude(":core")\ninclude(":plugins:google")\n')
        includes = _parse_settings_gradle(settings)
        assert 'core' in includes
        assert 'plugins:google' in includes

    def test_parses_multi_include(self, tmp_path: Path) -> None:
        """Should parse multi-include: include(":a", ":b")."""
        settings = tmp_path / 'settings.gradle.kts'
        settings.write_text('rootProject.name = "my-project"\ninclude(":core", ":plugins:google", ":plugins:vertex")\n')
        includes = _parse_settings_gradle(settings)
        assert 'core' in includes
        assert 'plugins:google' in includes
        assert 'plugins:vertex' in includes

    def test_parses_groovy_multi_include(self, tmp_path: Path) -> None:
        """Should parse Groovy multi-include: include ':a', ':b'."""
        settings = tmp_path / 'settings.gradle'
        settings.write_text("rootProject.name = 'my-project'\ninclude ':core', ':plugins:google'\n")
        includes = _parse_settings_gradle(settings)
        assert 'core' in includes
        assert 'plugins:google' in includes

    def test_returns_empty_for_missing_file(self, tmp_path: Path) -> None:
        """Should return empty list for missing file."""
        includes = _parse_settings_gradle(tmp_path / 'settings.gradle.kts')
        assert includes == []


# MavenWorkspace.discover() with gradle.properties version


def _setup_gradle_props_workspace(root: Path) -> None:
    """Create a Gradle workspace using gradle.properties for versions."""
    (root / 'settings.gradle').write_text("include ':core'\ninclude ':plugin'\n")
    (root / 'gradle.properties').write_text('VERSION_NAME=1.5.0\nGROUP=com.example\n')

    core = root / 'core'
    core.mkdir()
    (core / 'build.gradle').write_text(
        "group = 'com.example'\ndependencies {\n    implementation 'com.google.guava:guava:33.0.0-jre'\n}\n"
    )

    plugin = root / 'plugin'
    plugin.mkdir()
    (plugin / 'build.gradle').write_text(
        "group = 'com.example'\ndependencies {\n    implementation 'com.example:core:1.5.0'\n}\n"
    )


class TestMavenWorkspaceDiscoverGradleProperties:
    """Tests for MavenWorkspace.discover() with gradle.properties version."""

    @pytest.mark.asyncio
    async def test_discovers_version_from_gradle_properties(self, tmp_path: Path) -> None:
        """discover() should fall back to gradle.properties VERSION_NAME."""
        _setup_gradle_props_workspace(tmp_path)
        ws = MavenWorkspace(workspace_root=tmp_path)
        packages = await ws.discover()
        core = next(p for p in packages if p.name == 'core')
        assert core.version == '1.5.0'

    @pytest.mark.asyncio
    async def test_build_gradle_version_takes_precedence(self, tmp_path: Path) -> None:
        """discover() should prefer build.gradle version over gradle.properties."""
        _setup_gradle_props_workspace(tmp_path)
        # Add version to build.gradle
        core_build = tmp_path / 'core' / 'build.gradle'
        core_build.write_text("version = '2.0.0'\ngroup = 'com.example'\n")
        ws = MavenWorkspace(workspace_root=tmp_path)
        packages = await ws.discover()
        core = next(p for p in packages if p.name == 'core')
        assert core.version == '2.0.0'


# MavenWorkspace.discover() with version catalog


def _setup_version_catalog_workspace(root: Path) -> None:
    """Create a Gradle workspace using libs.versions.toml for versions."""
    (root / 'settings.gradle.kts').write_text('include(":core")\n')
    gradle_dir = root / 'gradle'
    gradle_dir.mkdir()
    (gradle_dir / 'libs.versions.toml').write_text(
        '[versions]\n'
        'projectVersion = "3.0.0"\n'
        'kotlin = "1.9.22"\n'
        '\n'
        '[libraries]\n'
        'guava = { module = "com.google.guava:guava", version = "33.0.0-jre" }\n'
    )

    core = root / 'core'
    core.mkdir()
    (core / 'build.gradle.kts').write_text(
        'group = "com.example"\ndependencies {\n    implementation("com.google.guava:guava:33.0.0-jre")\n}\n'
    )


class TestMavenWorkspaceDiscoverVersionCatalog:
    """Tests for MavenWorkspace.discover() with version catalog."""

    @pytest.mark.asyncio
    async def test_discovers_version_from_catalog(self, tmp_path: Path) -> None:
        """discover() should fall back to libs.versions.toml."""
        _setup_version_catalog_workspace(tmp_path)
        ws = MavenWorkspace(workspace_root=tmp_path)
        packages = await ws.discover()
        assert len(packages) == 1
        assert packages[0].version == '3.0.0'


# MavenWorkspace.rewrite_version() with new formats


class TestMavenWorkspaceRewriteVersionGradleProperties:
    """Tests for MavenWorkspace.rewrite_version() with gradle.properties."""

    @pytest.mark.asyncio
    async def test_rewrites_gradle_properties_version(self, tmp_path: Path) -> None:
        """rewrite_version() should handle gradle.properties."""
        props = tmp_path / 'gradle.properties'
        props.write_text('VERSION_NAME=1.0.0\nGROUP=com.example\n')
        ws = MavenWorkspace(workspace_root=tmp_path)
        old = await ws.rewrite_version(props, '2.0.0')
        assert old == '1.0.0'
        assert 'VERSION_NAME=2.0.0' in props.read_text()


class TestMavenWorkspaceRewriteVersionCatalog:
    """Tests for MavenWorkspace.rewrite_version() with libs.versions.toml."""

    @pytest.mark.asyncio
    async def test_rewrites_version_catalog(self, tmp_path: Path) -> None:
        """rewrite_version() should handle libs.versions.toml."""
        catalog = tmp_path / 'libs.versions.toml'
        catalog.write_text('[versions]\nprojectVersion = "1.0.0"\nkotlin = "1.9.22"\n')
        ws = MavenWorkspace(workspace_root=tmp_path)
        old = await ws.rewrite_version(catalog, '2.0.0')
        assert old == '1.0.0'
        text = catalog.read_text()
        assert 'projectVersion = "2.0.0"' in text
        assert 'kotlin = "1.9.22"' in text


# MavenWorkspace.discover() with Kotlin DSL settings


class TestMavenWorkspaceDiscoverKotlinDsl:
    """Tests for MavenWorkspace.discover() with settings.gradle.kts."""

    @pytest.mark.asyncio
    async def test_discovers_from_settings_kts(self, tmp_path: Path) -> None:
        """discover() should work with settings.gradle.kts."""
        (tmp_path / 'settings.gradle.kts').write_text(
            'rootProject.name = "my-project"\ninclude(":core")\ninclude(":plugin")\n'
        )
        core = tmp_path / 'core'
        core.mkdir()
        (core / 'build.gradle.kts').write_text('version = "1.0.0"\ngroup = "com.example"\n')
        plugin = tmp_path / 'plugin'
        plugin.mkdir()
        (plugin / 'build.gradle.kts').write_text('version = "1.1.0"\ngroup = "com.example"\n')

        ws = MavenWorkspace(workspace_root=tmp_path)
        packages = await ws.discover()
        names = [p.name for p in packages]
        assert 'core' in names
        assert 'plugin' in names

    @pytest.mark.asyncio
    async def test_discovers_from_multi_include_kts(self, tmp_path: Path) -> None:
        """discover() should handle multi-include in settings.gradle.kts."""
        (tmp_path / 'settings.gradle.kts').write_text('include(":core", ":plugin")\n')
        for name in ('core', 'plugin'):
            d = tmp_path / name
            d.mkdir()
            (d / 'build.gradle.kts').write_text('version = "1.0.0"\ngroup = "com.example"\n')

        ws = MavenWorkspace(workspace_root=tmp_path)
        packages = await ws.discover()
        assert len(packages) == 2
