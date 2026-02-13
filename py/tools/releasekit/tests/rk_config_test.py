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
from releasekit.config import CONFIG_FILENAME, VALID_KEYS, ReleaseConfig, load_config, resolve_group_refs
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


class TestLoadConfigNoFile:
    """load_config returns defaults when releasekit.toml is absent."""

    def test_missing_file_returns_defaults(self, tmp_path: Path) -> None:
        """Missing releasekit.toml returns all defaults (no error)."""
        cfg = load_config(tmp_path)
        assert cfg.tag_format == '{name}-v{version}', f'Expected default tag_format, got {cfg.tag_format}'
        assert cfg.config_path is None, f'Expected config_path=None, got {cfg.config_path}'


class TestLoadConfigEmpty:
    """load_config returns defaults when releasekit.toml is empty."""

    def test_empty_file_returns_defaults(self, tmp_path: Path) -> None:
        """Empty releasekit.toml returns all defaults."""
        config_file = tmp_path / CONFIG_FILENAME
        config_file.write_text('')
        cfg = load_config(tmp_path)
        assert cfg.tag_format == '{name}-v{version}', f'Expected default tag_format, got {cfg.tag_format}'
        assert cfg.config_path == config_file, f'Expected config_path={config_file}, got {cfg.config_path}'


class TestLoadConfigValid:
    """load_config correctly reads valid config."""

    def test_custom_tag_format(self, tmp_path: Path) -> None:
        """Custom tag_format is read correctly."""
        config_file = tmp_path / CONFIG_FILENAME
        config_file.write_text('tag_format = "{name}@{version}"\n')
        cfg = load_config(tmp_path)
        assert cfg.tag_format == '{name}@{version}', f'Expected custom tag_format, got {cfg.tag_format}'

    def test_publish_from_ci(self, tmp_path: Path) -> None:
        """Publish_from=ci is accepted."""
        config_file = tmp_path / CONFIG_FILENAME
        config_file.write_text('publish_from = "ci"\n')
        cfg = load_config(tmp_path)
        assert cfg.publish_from == 'ci', f'Expected publish_from=ci, got {cfg.publish_from}'

    def test_groups(self, tmp_path: Path) -> None:
        """Groups are parsed as dict of string lists."""
        config_file = tmp_path / CONFIG_FILENAME
        config_file.write_text('[groups]\ncore = ["genkit"]\nplugins = ["genkit-plugin-*"]\n')
        cfg = load_config(tmp_path)
        assert cfg.groups == {'core': ['genkit'], 'plugins': ['genkit-plugin-*']}, f'Unexpected groups: {cfg.groups}'

    def test_exclude(self, tmp_path: Path) -> None:
        """Exclude patterns are read as a list."""
        config_file = tmp_path / CONFIG_FILENAME
        config_file.write_text('exclude = ["sample-*"]\n')
        cfg = load_config(tmp_path)
        assert cfg.exclude == ['sample-*'], f'Expected exclude, got {cfg.exclude}'

    def test_http_pool_size(self, tmp_path: Path) -> None:
        """Http_pool_size is read as an integer."""
        config_file = tmp_path / CONFIG_FILENAME
        config_file.write_text('http_pool_size = 20\n')
        cfg = load_config(tmp_path)
        assert cfg.http_pool_size == 20, f'Expected 20, got {cfg.http_pool_size}'

    def test_synchronize(self, tmp_path: Path) -> None:
        """Synchronize flag is read correctly."""
        config_file = tmp_path / CONFIG_FILENAME
        config_file.write_text('synchronize = true\n')
        cfg = load_config(tmp_path)
        assert cfg.synchronize is True, f'Expected synchronize=True, got {cfg.synchronize}'

    def test_config_path_set(self, tmp_path: Path) -> None:
        """Config path points to the loaded file."""
        config_file = tmp_path / CONFIG_FILENAME
        config_file.write_text('tag_format = "v{version}"\n')
        cfg = load_config(tmp_path)
        assert cfg.config_path == config_file, f'Expected config_path={config_file}, got {cfg.config_path}'


class TestLoadConfigInvalid:
    """load_config raises on invalid config values."""

    def test_unknown_key(self, tmp_path: Path) -> None:
        """Unknown key raises RK-CONFIG-INVALID-KEY."""
        config_file = tmp_path / CONFIG_FILENAME
        config_file.write_text('unknwon_key = "value"\n')
        with pytest.raises(ReleaseKitError) as exc_info:
            load_config(tmp_path)
        assert 'RK-CONFIG-INVALID-KEY' in str(exc_info.value), f'Expected RK-CONFIG-INVALID-KEY, got {exc_info.value}'

    def test_unknown_key_suggests_fix(self, tmp_path: Path) -> None:
        """Typo 'tag_fromat' suggests 'tag_format'."""
        config_file = tmp_path / CONFIG_FILENAME
        config_file.write_text('tag_fromat = "oops"\n')
        with pytest.raises(ReleaseKitError) as exc_info:
            load_config(tmp_path)
        assert 'tag_format' in str(exc_info.value.hint), (
            f'Expected hint to suggest tag_format, got {exc_info.value.hint}'
        )

    def test_invalid_publish_from(self, tmp_path: Path) -> None:
        """Invalid publish_from raises RK-CONFIG-INVALID-VALUE."""
        config_file = tmp_path / CONFIG_FILENAME
        config_file.write_text('publish_from = "github"\n')
        with pytest.raises(ReleaseKitError) as exc_info:
            load_config(tmp_path)
        assert 'RK-CONFIG-INVALID-VALUE' in str(exc_info.value), (
            f'Expected RK-CONFIG-INVALID-VALUE, got {exc_info.value}'
        )

    def test_invalid_prerelease_mode(self, tmp_path: Path) -> None:
        """Invalid prerelease_mode raises RK-CONFIG-INVALID-VALUE."""
        config_file = tmp_path / CONFIG_FILENAME
        config_file.write_text('prerelease_mode = "yolo"\n')
        with pytest.raises(ReleaseKitError) as exc_info:
            load_config(tmp_path)
        assert 'RK-CONFIG-INVALID-VALUE' in str(exc_info.value), (
            f'Expected RK-CONFIG-INVALID-VALUE, got {exc_info.value}'
        )

    def test_wrong_type_tag_format(self, tmp_path: Path) -> None:
        """Wrong type for tag_format raises RK-CONFIG-INVALID-VALUE."""
        config_file = tmp_path / CONFIG_FILENAME
        config_file.write_text('tag_format = 42\n')
        with pytest.raises(ReleaseKitError) as exc_info:
            load_config(tmp_path)
        assert 'RK-CONFIG-INVALID-VALUE' in str(exc_info.value), (
            f'Expected RK-CONFIG-INVALID-VALUE, got {exc_info.value}'
        )

    def test_wrong_type_groups(self, tmp_path: Path) -> None:
        """Group value as string instead of list raises RK-CONFIG-INVALID-VALUE."""
        config_file = tmp_path / CONFIG_FILENAME
        config_file.write_text('[groups]\ncore = "genkit"\n')
        with pytest.raises(ReleaseKitError) as exc_info:
            load_config(tmp_path)
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


class TestConfigFilename:
    """CONFIG_FILENAME constant is correct."""

    def test_filename(self) -> None:
        """Config filename is releasekit.toml."""
        assert CONFIG_FILENAME == 'releasekit.toml'


class TestResolveGroupRefs:
    """resolve_group_refs expands group: references recursively with cycle detection."""

    def test_basic_expansion(self) -> None:
        """group:name expands to the patterns in that group."""
        groups = {'plugins': ['genkit-plugin-*', 'genkit-plugin-firebase']}
        result = resolve_group_refs(['group:plugins'], groups)
        assert result == ['genkit-plugin-*', 'genkit-plugin-firebase']

    def test_nested_expansion(self) -> None:
        """Groups can reference other groups recursively."""
        groups = {
            'google': ['genkit-plugin-google-*'],
            'community': ['genkit-plugin-ollama'],
            'all_plugins': ['group:google', 'group:community'],
        }
        result = resolve_group_refs(['group:all_plugins'], groups)
        assert result == ['genkit-plugin-google-*', 'genkit-plugin-ollama']

    def test_deeply_nested(self) -> None:
        """Three levels of nesting resolves correctly."""
        groups = {
            'leaf': ['pkg-a'],
            'mid': ['group:leaf', 'pkg-b'],
            'top': ['group:mid'],
        }
        result = resolve_group_refs(['group:top'], groups)
        assert result == ['pkg-a', 'pkg-b']

    def test_direct_cycle_raises(self) -> None:
        """A group referencing itself raises ReleaseKitError."""
        groups = {'a': ['group:a']}
        with pytest.raises(ReleaseKitError) as exc_info:
            resolve_group_refs(['group:a'], groups)
        assert 'Cycle' in str(exc_info.value)

    def test_indirect_cycle_raises(self) -> None:
        """A → B → A cycle raises ReleaseKitError."""
        groups = {
            'a': ['group:b'],
            'b': ['group:a'],
        }
        with pytest.raises(ReleaseKitError) as exc_info:
            resolve_group_refs(['group:a'], groups)
        assert 'Cycle' in str(exc_info.value)

    def test_unknown_group_raises(self) -> None:
        """Referencing a non-existent group raises ReleaseKitError."""
        groups = {'plugins': ['genkit-plugin-*']}
        with pytest.raises(ReleaseKitError) as exc_info:
            resolve_group_refs(['group:nonexistent'], groups)
        assert 'nonexistent' in str(exc_info.value)

    def test_mixed_patterns_and_refs(self) -> None:
        """Plain patterns pass through, group: refs expand."""
        groups = {'samples': ['sample-*']}
        result = resolve_group_refs(['genkit', 'group:samples', 'other-pkg'], groups)
        assert result == ['genkit', 'sample-*', 'other-pkg']

    def test_empty_patterns(self) -> None:
        """Empty pattern list returns empty."""
        result = resolve_group_refs([], {'g': ['a']})
        assert result == []

    def test_no_groups(self) -> None:
        """Patterns without group: refs pass through even when groups is empty."""
        result = resolve_group_refs(['genkit', 'genkit-plugin-*'], {})
        assert result == ['genkit', 'genkit-plugin-*']


class TestNewConfigFields:
    """Tests for major_on_zero, pr_title_template, and extra_files config fields."""

    def test_default_major_on_zero_false(self) -> None:
        """Default major_on_zero is False."""
        cfg = ReleaseConfig()
        assert cfg.major_on_zero is False

    def test_default_pr_title_template(self) -> None:
        """Default pr_title_template uses chore(release): v{version}."""
        cfg = ReleaseConfig()
        assert cfg.pr_title_template == 'chore(release): v{version}'

    def test_default_extra_files_empty(self) -> None:
        """Default extra_files is an empty list."""
        cfg = ReleaseConfig()
        assert cfg.extra_files == []

    def test_load_major_on_zero_true(self, tmp_path: Path) -> None:
        """major_on_zero = true is loaded from config."""
        config_path = tmp_path / CONFIG_FILENAME
        config_path.write_text('major_on_zero = true\n', encoding='utf-8')
        cfg = load_config(tmp_path)
        assert cfg.major_on_zero is True

    def test_load_pr_title_template(self, tmp_path: Path) -> None:
        """pr_title_template is loaded from config."""
        config_path = tmp_path / CONFIG_FILENAME
        config_path.write_text(
            'pr_title_template = "release: {version}"\n',
            encoding='utf-8',
        )
        cfg = load_config(tmp_path)
        assert cfg.pr_title_template == 'release: {version}'

    def test_load_extra_files(self, tmp_path: Path) -> None:
        """extra_files list is loaded from config."""
        config_path = tmp_path / CONFIG_FILENAME
        config_path.write_text(
            'extra_files = ["src/mypackage/__init__.py"]\n',
            encoding='utf-8',
        )
        cfg = load_config(tmp_path)
        assert cfg.extra_files == ['src/mypackage/__init__.py']

    def test_load_extra_files_with_pattern(self, tmp_path: Path) -> None:
        """extra_files with path:pattern format is loaded."""
        config_path = tmp_path / CONFIG_FILENAME
        config_path.write_text(
            'extra_files = ["src/version.h:^#define VERSION \\"([^\\"]+)\\"$"]\n',
            encoding='utf-8',
        )
        cfg = load_config(tmp_path)
        assert len(cfg.extra_files) == 1
        assert ':' in cfg.extra_files[0]

    def test_major_on_zero_wrong_type_raises(self, tmp_path: Path) -> None:
        """major_on_zero with wrong type raises ReleaseKitError."""
        config_path = tmp_path / CONFIG_FILENAME
        config_path.write_text('major_on_zero = "yes"\n', encoding='utf-8')
        with pytest.raises(ReleaseKitError):
            load_config(tmp_path)

    def test_pr_title_template_wrong_type_raises(self, tmp_path: Path) -> None:
        """pr_title_template with wrong type raises ReleaseKitError."""
        config_path = tmp_path / CONFIG_FILENAME
        config_path.write_text('pr_title_template = 42\n', encoding='utf-8')
        with pytest.raises(ReleaseKitError):
            load_config(tmp_path)

    def test_extra_files_wrong_type_raises(self, tmp_path: Path) -> None:
        """extra_files with wrong type raises ReleaseKitError."""
        config_path = tmp_path / CONFIG_FILENAME
        config_path.write_text('extra_files = "not-a-list"\n', encoding='utf-8')
        with pytest.raises(ReleaseKitError):
            load_config(tmp_path)
