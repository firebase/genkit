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

"""Tests for releasekit.config module."""

from __future__ import annotations

from pathlib import Path

import pytest
from releasekit.config import VALID_KEYS, ReleaseConfig, load_config
from releasekit.errors import ReleaseKitError


class TestReleaseConfigDefaults:
    """ReleaseConfig has sensible defaults when no config is provided."""

    def test_default_tag_format(self) -> None:
        """Default tag_format uses {name}-v{version}."""
        cfg = ReleaseConfig()
        assert cfg.tag_format == '{name}-v{version}', f'Expected default tag_format, got {cfg.tag_format}'

    def test_default_umbrella_tag(self) -> None:
        """Default umbrella_tag uses v{version}."""
        cfg = ReleaseConfig()
        assert cfg.umbrella_tag == 'v{version}', f'Expected default umbrella_tag, got {cfg.umbrella_tag}'

    def test_default_publish_from(self) -> None:
        """Default publish_from is local."""
        cfg = ReleaseConfig()
        assert cfg.publish_from == 'local', f'Expected default publish_from, got {cfg.publish_from}'

    def test_default_groups_empty(self) -> None:
        """Default groups is an empty dict."""
        cfg = ReleaseConfig()
        assert cfg.groups == {}, f'Expected empty groups, got {cfg.groups}'

    def test_default_exclude_empty(self) -> None:
        """Default exclude is an empty list."""
        cfg = ReleaseConfig()
        assert cfg.exclude == [], f'Expected empty exclude, got {cfg.exclude}'

    def test_default_changelog_true(self) -> None:
        """Default changelog is True."""
        cfg = ReleaseConfig()
        assert cfg.changelog is True, f'Expected changelog=True, got {cfg.changelog}'

    def test_default_smoke_test_true(self) -> None:
        """Default smoke_test is True."""
        cfg = ReleaseConfig()
        assert cfg.smoke_test is True, f'Expected smoke_test=True, got {cfg.smoke_test}'

    def test_frozen(self) -> None:
        """ReleaseConfig is immutable."""
        cfg = ReleaseConfig()
        with pytest.raises(AttributeError):
            cfg.tag_format = 'oops'  # type: ignore[misc]


class TestLoadConfigMissingFile:
    """load_config raises when pyproject.toml is missing."""

    def test_missing_file(self, tmp_path: Path) -> None:
        """Missing pyproject.toml raises RK-CONFIG-NOT-FOUND."""
        with pytest.raises(ReleaseKitError) as exc_info:
            load_config(tmp_path / 'pyproject.toml')
        assert 'RK-CONFIG-NOT-FOUND' in str(exc_info.value), f'Expected RK-CONFIG-NOT-FOUND, got {exc_info.value}'


class TestLoadConfigNoSection:
    """load_config returns defaults when [tool.releasekit] is absent."""

    def test_no_releasekit_section(self, tmp_path: Path) -> None:
        """Absent [tool.releasekit] section returns all defaults."""
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text('[project]\nname = "test"\n')
        cfg = load_config(pyproject)
        assert cfg.tag_format == '{name}-v{version}', f'Expected default tag_format, got {cfg.tag_format}'
        assert cfg.config_path == pyproject, f'Expected config_path={pyproject}, got {cfg.config_path}'


class TestLoadConfigValid:
    """load_config correctly reads valid config."""

    def test_custom_tag_format(self, tmp_path: Path) -> None:
        """Custom tag_format is read correctly."""
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text('[tool.releasekit]\ntag_format = "{name}@{version}"\n')
        cfg = load_config(pyproject)
        assert cfg.tag_format == '{name}@{version}', f'Expected custom tag_format, got {cfg.tag_format}'

    def test_publish_from_ci(self, tmp_path: Path) -> None:
        """Publish_from=ci is accepted."""
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text('[tool.releasekit]\npublish_from = "ci"\n')
        cfg = load_config(pyproject)
        assert cfg.publish_from == 'ci', f'Expected publish_from=ci, got {cfg.publish_from}'

    def test_groups(self, tmp_path: Path) -> None:
        """Groups are parsed as dict of string lists."""
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text(
            '[tool.releasekit]\n[tool.releasekit.groups]\ncore = ["genkit"]\nplugins = ["genkit-plugin-*"]\n'
        )
        cfg = load_config(pyproject)
        assert cfg.groups == {'core': ['genkit'], 'plugins': ['genkit-plugin-*']}, f'Unexpected groups: {cfg.groups}'

    def test_exclude(self, tmp_path: Path) -> None:
        """Exclude patterns are read as a list."""
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text('[tool.releasekit]\nexclude = ["sample-*"]\n')
        cfg = load_config(pyproject)
        assert cfg.exclude == ['sample-*'], f'Expected exclude, got {cfg.exclude}'

    def test_http_pool_size(self, tmp_path: Path) -> None:
        """Http_pool_size is read as an integer."""
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text('[tool.releasekit]\nhttp_pool_size = 20\n')
        cfg = load_config(pyproject)
        assert cfg.http_pool_size == 20, f'Expected 20, got {cfg.http_pool_size}'


class TestLoadConfigInvalid:
    """load_config raises on invalid config values."""

    def test_unknown_key(self, tmp_path: Path) -> None:
        """Unknown key raises RK-CONFIG-INVALID-KEY."""
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text('[tool.releasekit]\nunknwon_key = "value"\n')
        with pytest.raises(ReleaseKitError) as exc_info:
            load_config(pyproject)
        assert 'RK-CONFIG-INVALID-KEY' in str(exc_info.value), f'Expected RK-CONFIG-INVALID-KEY, got {exc_info.value}'

    def test_unknown_key_suggests_fix(self, tmp_path: Path) -> None:
        """Typo 'tag_fromat' suggests 'tag_format'."""
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text('[tool.releasekit]\ntag_fromat = "oops"\n')
        with pytest.raises(ReleaseKitError) as exc_info:
            load_config(pyproject)
        assert 'tag_format' in str(exc_info.value.hint), (
            f'Expected hint to suggest tag_format, got {exc_info.value.hint}'
        )

    def test_invalid_publish_from(self, tmp_path: Path) -> None:
        """Invalid publish_from raises RK-CONFIG-INVALID-VALUE."""
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text('[tool.releasekit]\npublish_from = "github"\n')
        with pytest.raises(ReleaseKitError) as exc_info:
            load_config(pyproject)
        assert 'RK-CONFIG-INVALID-VALUE' in str(exc_info.value), (
            f'Expected RK-CONFIG-INVALID-VALUE, got {exc_info.value}'
        )

    def test_invalid_prerelease_mode(self, tmp_path: Path) -> None:
        """Invalid prerelease_mode raises RK-CONFIG-INVALID-VALUE."""
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text('[tool.releasekit]\nprerelease_mode = "yolo"\n')
        with pytest.raises(ReleaseKitError) as exc_info:
            load_config(pyproject)
        assert 'RK-CONFIG-INVALID-VALUE' in str(exc_info.value), (
            f'Expected RK-CONFIG-INVALID-VALUE, got {exc_info.value}'
        )

    def test_wrong_type_tag_format(self, tmp_path: Path) -> None:
        """Wrong type for tag_format raises RK-CONFIG-INVALID-VALUE."""
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text('[tool.releasekit]\ntag_format = 42\n')
        with pytest.raises(ReleaseKitError) as exc_info:
            load_config(pyproject)
        assert 'RK-CONFIG-INVALID-VALUE' in str(exc_info.value), (
            f'Expected RK-CONFIG-INVALID-VALUE, got {exc_info.value}'
        )

    def test_wrong_type_groups(self, tmp_path: Path) -> None:
        """Group value as string instead of list raises RK-CONFIG-INVALID-VALUE."""
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text('[tool.releasekit]\n[tool.releasekit.groups]\ncore = "genkit"\n')
        with pytest.raises(ReleaseKitError) as exc_info:
            load_config(pyproject)
        assert 'RK-CONFIG-INVALID-VALUE' in str(exc_info.value), (
            f'Expected RK-CONFIG-INVALID-VALUE, got {exc_info.value}'
        )


class TestValidKeys:
    """VALID_KEYS is well-formed."""

    def test_keys_are_lowercase(self) -> None:
        """All valid keys must be lowercase."""
        for key in VALID_KEYS:
            assert key == key.lower(), f'Key {key} is not lowercase'

    def test_keys_use_underscores(self) -> None:
        """Valid keys use underscores, not hyphens."""
        for key in VALID_KEYS:
            assert '-' not in key, f'Key {key} uses hyphens instead of underscores'
