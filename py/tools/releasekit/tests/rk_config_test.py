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
from releasekit.config import (
    ALLOWED_ECOSYSTEMS,
    CONFIG_FILENAME,
    VALID_KEYS,
    VALID_WORKSPACE_KEYS,
    ReleaseConfig,
    WorkspaceConfig,
    load_config,
    resolve_group_refs,
)
from releasekit.errors import ReleaseKitError


class TestWorkspaceConfigDefaults:
    """WorkspaceConfig has sensible defaults."""

    def test_default_tag_format(self) -> None:
        """Test default tag format."""
        ws = WorkspaceConfig()
        assert ws.tag_format == '{name}-v{version}'

    def test_default_umbrella_tag(self) -> None:
        """Test default umbrella tag."""
        ws = WorkspaceConfig()
        assert ws.umbrella_tag == 'v{version}'

    def test_default_root(self) -> None:
        """Test default root."""
        ws = WorkspaceConfig()
        assert ws.root == '.'

    def test_default_groups_empty(self) -> None:
        """Test default groups empty."""
        ws = WorkspaceConfig()
        assert ws.groups == {}

    def test_default_exclude_empty(self) -> None:
        """Test default exclude empty."""
        ws = WorkspaceConfig()
        assert ws.exclude == []

    def test_default_changelog_true(self) -> None:
        """Test default changelog true."""
        ws = WorkspaceConfig()
        assert ws.changelog is True

    def test_default_smoke_test_true(self) -> None:
        """Test default smoke test true."""
        ws = WorkspaceConfig()
        assert ws.smoke_test is True

    def test_frozen(self) -> None:
        """Test frozen."""
        ws = WorkspaceConfig()
        with pytest.raises(AttributeError):
            ws.tag_format = 'oops'  # type: ignore[misc]


class TestReleaseConfigDefaults:
    """ReleaseConfig has sensible defaults for global fields."""

    def test_default_publish_from(self) -> None:
        """Test default publish from."""
        cfg = ReleaseConfig()
        assert cfg.publish_from == 'local'

    def test_default_forge(self) -> None:
        """Test default forge."""
        cfg = ReleaseConfig()
        assert cfg.forge == 'github'

    def test_default_workspaces_empty(self) -> None:
        """Test default workspaces empty."""
        cfg = ReleaseConfig()
        assert cfg.workspaces == {}

    def test_frozen(self) -> None:
        """Test frozen."""
        cfg = ReleaseConfig()
        with pytest.raises(AttributeError):
            cfg.forge = 'oops'  # type: ignore[misc]


class TestLoadConfigNoFile:
    """load_config returns defaults when releasekit.toml is absent."""

    def test_missing_file_returns_defaults(self, tmp_path: Path) -> None:
        """Test missing file returns defaults."""
        cfg = load_config(tmp_path)
        assert cfg.publish_from == 'local'
        assert cfg.workspaces == {}
        assert cfg.config_path is None


class TestLoadConfigEmpty:
    """load_config returns defaults when releasekit.toml is empty."""

    def test_empty_file_returns_defaults(self, tmp_path: Path) -> None:
        """Test empty file returns defaults."""
        config_file = tmp_path / CONFIG_FILENAME
        config_file.write_text('')
        cfg = load_config(tmp_path)
        assert cfg.workspaces == {}
        assert cfg.config_path == config_file


class TestLoadConfigValid:
    """load_config correctly reads valid config."""

    def test_publish_from_ci(self, tmp_path: Path) -> None:
        """Test publish from ci."""
        config_file = tmp_path / CONFIG_FILENAME
        config_file.write_text('publish_from = "ci"\n')
        cfg = load_config(tmp_path)
        assert cfg.publish_from == 'ci'

    def test_http_pool_size(self, tmp_path: Path) -> None:
        """Test http pool size."""
        config_file = tmp_path / CONFIG_FILENAME
        config_file.write_text('http_pool_size = 20\n')
        cfg = load_config(tmp_path)
        assert cfg.http_pool_size == 20

    def test_config_path_set(self, tmp_path: Path) -> None:
        """Test config path set."""
        config_file = tmp_path / CONFIG_FILENAME
        config_file.write_text('forge = "github"\n')
        cfg = load_config(tmp_path)
        assert cfg.config_path == config_file

    def test_workspace_section_parsed(self, tmp_path: Path) -> None:
        """Test workspace section parsed."""
        config_file = tmp_path / CONFIG_FILENAME
        config_file.write_text(
            'forge = "github"\n'
            '\n'
            '[workspace.py]\n'
            'ecosystem = "python"\n'
            'root = "py"\n'
            'tag_format = "{name}-v{version}"\n'
            'exclude = ["sample-*"]\n'
            'synchronize = true\n'
            '\n'
            '[workspace.py.groups]\n'
            'core = ["genkit"]\n'
            'plugins = ["genkit-plugin-*"]\n',
        )
        cfg = load_config(tmp_path)
        assert 'py' in cfg.workspaces
        ws = cfg.workspaces['py']
        assert ws.label == 'py'
        assert ws.ecosystem == 'python'
        assert ws.tool == 'uv'  # default for python
        assert ws.root == 'py'
        assert ws.tag_format == '{name}-v{version}'
        assert ws.exclude == ['sample-*']
        assert ws.synchronize is True
        assert ws.groups == {'core': ['genkit'], 'plugins': ['genkit-plugin-*']}

    def test_multiple_workspaces(self, tmp_path: Path) -> None:
        """Test multiple workspaces."""
        config_file = tmp_path / CONFIG_FILENAME
        config_file.write_text(
            '[workspace.py]\n'
            'ecosystem = "python"\n'
            'root = "py"\n'
            '\n'
            '[workspace.js]\n'
            'ecosystem = "js"\n'
            'root = "js"\n'
            'tag_format = "@genkit/{name}@{version}"\n',
        )
        cfg = load_config(tmp_path)
        assert len(cfg.workspaces) == 2
        assert cfg.workspaces['py'].root == 'py'
        assert cfg.workspaces['py'].tool == 'uv'  # default for python
        assert cfg.workspaces['js'].root == 'js'
        assert cfg.workspaces['js'].tool == 'pnpm'  # default for js
        assert cfg.workspaces['js'].tag_format == '@genkit/{name}@{version}'

    def test_explicit_tool_override(self, tmp_path: Path) -> None:
        """Test explicit tool override."""
        config_file = tmp_path / CONFIG_FILENAME
        config_file.write_text(
            '[workspace.py]\necosystem = "python"\ntool = "bazel"\nroot = "."\n',
        )
        cfg = load_config(tmp_path)
        assert cfg.workspaces['py'].tool == 'bazel'
        assert cfg.workspaces['py'].ecosystem == 'python'


class TestLoadConfigInvalid:
    """load_config raises on invalid config values."""

    def test_unknown_global_key(self, tmp_path: Path) -> None:
        """Test unknown global key."""
        config_file = tmp_path / CONFIG_FILENAME
        config_file.write_text('unknwon_key = "value"\n')
        with pytest.raises(ReleaseKitError) as exc_info:
            load_config(tmp_path)
        assert 'RK-CONFIG-INVALID-KEY' in str(exc_info.value)

    def test_workspace_key_at_top_level_suggests_move(self, tmp_path: Path) -> None:
        """Test workspace key at top level suggests move."""
        config_file = tmp_path / CONFIG_FILENAME
        config_file.write_text('tag_format = "oops"\n')
        with pytest.raises(ReleaseKitError) as exc_info:
            load_config(tmp_path)
        assert 'workspace' in exc_info.value.hint.lower()

    def test_invalid_publish_from(self, tmp_path: Path) -> None:
        """Test invalid publish from."""
        config_file = tmp_path / CONFIG_FILENAME
        config_file.write_text('publish_from = "github"\n')
        with pytest.raises(ReleaseKitError) as exc_info:
            load_config(tmp_path)
        assert 'RK-CONFIG-INVALID-VALUE' in str(exc_info.value)

    def test_invalid_workspace_label_uppercase(self, tmp_path: Path) -> None:
        """Test invalid workspace label uppercase."""
        config_file = tmp_path / CONFIG_FILENAME
        config_file.write_text('[workspace.MyPython]\nroot = "."\n')
        with pytest.raises(ReleaseKitError) as exc_info:
            load_config(tmp_path)
        assert 'RK-CONFIG-INVALID-KEY' in str(exc_info.value)

    def test_invalid_ecosystem_value(self, tmp_path: Path) -> None:
        """Test invalid ecosystem value."""
        config_file = tmp_path / CONFIG_FILENAME
        config_file.write_text('[workspace.py]\necosystem = "fortran"\n')
        with pytest.raises(ReleaseKitError) as exc_info:
            load_config(tmp_path)
        assert 'RK-CONFIG-INVALID-VALUE' in str(exc_info.value)

    def test_unknown_workspace_key(self, tmp_path: Path) -> None:
        """Test unknown workspace key."""
        config_file = tmp_path / CONFIG_FILENAME
        config_file.write_text('[workspace.py]\nbad_key = "x"\n')
        with pytest.raises(ReleaseKitError) as exc_info:
            load_config(tmp_path)
        assert 'RK-CONFIG-INVALID-KEY' in str(exc_info.value)

    def test_wrong_type_in_workspace(self, tmp_path: Path) -> None:
        """Test wrong type in workspace."""
        config_file = tmp_path / CONFIG_FILENAME
        config_file.write_text('[workspace.py]\ntag_format = 42\n')
        with pytest.raises(ReleaseKitError) as exc_info:
            load_config(tmp_path)
        assert 'RK-CONFIG-INVALID-VALUE' in str(exc_info.value)

    def test_wrong_type_groups_in_workspace(self, tmp_path: Path) -> None:
        """Test wrong type groups in workspace."""
        config_file = tmp_path / CONFIG_FILENAME
        config_file.write_text('[workspace.py]\n[workspace.py.groups]\ncore = "genkit"\n')
        with pytest.raises(ReleaseKitError) as exc_info:
            load_config(tmp_path)
        assert 'RK-CONFIG-INVALID-VALUE' in str(exc_info.value)

    def test_invalid_prerelease_mode_in_workspace(self, tmp_path: Path) -> None:
        """Test invalid prerelease mode in workspace."""
        config_file = tmp_path / CONFIG_FILENAME
        config_file.write_text('[workspace.py]\nprerelease_mode = "yolo"\n')
        with pytest.raises(ReleaseKitError) as exc_info:
            load_config(tmp_path)
        assert 'RK-CONFIG-INVALID-VALUE' in str(exc_info.value)

    def test_workspace_section_must_be_table(self, tmp_path: Path) -> None:
        """Test workspace section must be table."""
        config_file = tmp_path / CONFIG_FILENAME
        config_file.write_text('[workspace]\nuv = "not a table"\n')
        with pytest.raises(ReleaseKitError) as exc_info:
            load_config(tmp_path)
        assert 'RK-CONFIG-INVALID-VALUE' in str(exc_info.value)


class TestValidKeys:
    """VALID_KEYS and VALID_WORKSPACE_KEYS are well-formed."""

    def test_global_keys_are_lowercase(self) -> None:
        """Test global keys are lowercase."""
        for key in VALID_KEYS:
            assert key == key.lower(), f'Key {key} is not lowercase'

    def test_workspace_keys_are_lowercase(self) -> None:
        """Test workspace keys are lowercase."""
        for key in VALID_WORKSPACE_KEYS:
            assert key == key.lower(), f'Key {key} is not lowercase'

    def test_global_keys_use_underscores(self) -> None:
        """Test global keys use underscores."""
        for key in VALID_KEYS:
            assert '-' not in key, f'Key {key} uses hyphens'

    def test_workspace_keys_use_underscores(self) -> None:
        """Test workspace keys use underscores."""
        for key in VALID_WORKSPACE_KEYS:
            assert '-' not in key, f'Key {key} uses hyphens'

    def test_no_overlap_except_workspace(self) -> None:
        """Test no overlap except workspace."""
        overlap = (VALID_KEYS - {'workspace'}) & VALID_WORKSPACE_KEYS
        assert overlap == set(), f'Keys in both global and workspace: {overlap}'

    def test_allowed_ecosystems_are_lowercase(self) -> None:
        """Test allowed ecosystems are lowercase."""
        for eco in ALLOWED_ECOSYSTEMS:
            assert eco == eco.lower()


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


class TestWorkspaceConfigFields:
    """Tests for per-workspace fields loaded via [workspace.*] sections."""

    def test_default_major_on_zero_false(self) -> None:
        """Test default major on zero false."""
        ws = WorkspaceConfig()
        assert ws.major_on_zero is False

    def test_default_extra_files_empty(self) -> None:
        """Test default extra files empty."""
        ws = WorkspaceConfig()
        assert ws.extra_files == []

    def test_default_pr_title_template(self) -> None:
        """Test default pr title template."""
        cfg = ReleaseConfig()
        assert cfg.pr_title_template == 'chore(release): v{version}'

    def test_load_major_on_zero_true(self, tmp_path: Path) -> None:
        """Test load major on zero true."""
        config_path = tmp_path / CONFIG_FILENAME
        config_path.write_text(
            '[workspace.py]\nmajor_on_zero = true\n',
            encoding='utf-8',
        )
        cfg = load_config(tmp_path)
        assert cfg.workspaces['py'].major_on_zero is True

    def test_load_pr_title_template(self, tmp_path: Path) -> None:
        """Test load pr title template."""
        config_path = tmp_path / CONFIG_FILENAME
        config_path.write_text(
            'pr_title_template = "release: {version}"\n',
            encoding='utf-8',
        )
        cfg = load_config(tmp_path)
        assert cfg.pr_title_template == 'release: {version}'

    def test_load_extra_files(self, tmp_path: Path) -> None:
        """Test load extra files."""
        config_path = tmp_path / CONFIG_FILENAME
        config_path.write_text(
            '[workspace.py]\nextra_files = ["src/mypackage/__init__.py"]\n',
            encoding='utf-8',
        )
        cfg = load_config(tmp_path)
        assert cfg.workspaces['py'].extra_files == ['src/mypackage/__init__.py']

    def test_load_extra_files_with_pattern(self, tmp_path: Path) -> None:
        """Test load extra files with pattern."""
        config_path = tmp_path / CONFIG_FILENAME
        config_path.write_text(
            '[workspace.py]\nextra_files = ["src/version.h:^#define VERSION \\"([^\\"]+)\\"$"]\n',
            encoding='utf-8',
        )
        cfg = load_config(tmp_path)
        assert len(cfg.workspaces['py'].extra_files) == 1
        assert ':' in cfg.workspaces['py'].extra_files[0]

    def test_major_on_zero_wrong_type_raises(self, tmp_path: Path) -> None:
        """Test major on zero wrong type raises."""
        config_path = tmp_path / CONFIG_FILENAME
        config_path.write_text('[workspace.py]\nmajor_on_zero = "yes"\n', encoding='utf-8')
        with pytest.raises(ReleaseKitError):
            load_config(tmp_path)

    def test_pr_title_template_wrong_type_raises(self, tmp_path: Path) -> None:
        """Test pr title template wrong type raises."""
        config_path = tmp_path / CONFIG_FILENAME
        config_path.write_text('pr_title_template = 42\n', encoding='utf-8')
        with pytest.raises(ReleaseKitError):
            load_config(tmp_path)

    def test_extra_files_wrong_type_raises(self, tmp_path: Path) -> None:
        """Test extra files wrong type raises."""
        config_path = tmp_path / CONFIG_FILENAME
        config_path.write_text('[workspace.py]\nextra_files = "not-a-list"\n', encoding='utf-8')
        with pytest.raises(ReleaseKitError):
            load_config(tmp_path)


class TestWorkspaceOverlapValidation:
    """Tests for cross-workspace validation that prevents broken versioning.

    When multiple workspaces are defined, their root directories must not
    overlap. Overlapping roots cause the same package to be discovered by
    multiple workspaces, leading to conflicting version bumps, duplicate
    tags, and double publishes.
    """

    def test_same_root_raises(self, tmp_path: Path) -> None:
        """Two workspaces with the same root directory are rejected."""
        config_path = tmp_path / CONFIG_FILENAME
        config_path.write_text(
            '[workspace.py]\nroot = "src"\n\n[workspace.js]\nroot = "src"\n',
            encoding='utf-8',
        )
        with pytest.raises(ReleaseKitError, match='share the same root'):
            load_config(tmp_path)

    def test_nested_root_raises(self, tmp_path: Path) -> None:
        """A workspace root nested inside another workspace root is rejected."""
        config_path = tmp_path / CONFIG_FILENAME
        config_path.write_text(
            '[workspace.mono]\nroot = "."\n\n[workspace.sub]\nroot = "packages/sub"\n',
            encoding='utf-8',
        )
        with pytest.raises(ReleaseKitError, match='is inside workspace'):
            load_config(tmp_path)

    def test_disjoint_roots_ok(self, tmp_path: Path) -> None:
        """Two workspaces with disjoint roots are accepted."""
        config_path = tmp_path / CONFIG_FILENAME
        config_path.write_text(
            '[workspace.py]\nroot = "py"\n\n[workspace.js]\nroot = "js"\n',
            encoding='utf-8',
        )
        cfg = load_config(tmp_path)
        assert len(cfg.workspaces) == 2

    def test_single_workspace_ok(self, tmp_path: Path) -> None:
        """A single workspace never triggers overlap checks."""
        config_path = tmp_path / CONFIG_FILENAME
        config_path.write_text('[workspace.py]\nroot = "."\n', encoding='utf-8')
        cfg = load_config(tmp_path)
        assert len(cfg.workspaces) == 1

    def test_propagate_bumps_default_true(self, tmp_path: Path) -> None:
        """propagate_bumps defaults to True."""
        config_path = tmp_path / CONFIG_FILENAME
        config_path.write_text('[workspace.py]\n', encoding='utf-8')
        cfg = load_config(tmp_path)
        assert cfg.workspaces['py'].propagate_bumps is True

    def test_propagate_bumps_false(self, tmp_path: Path) -> None:
        """propagate_bumps can be set to False."""
        config_path = tmp_path / CONFIG_FILENAME
        config_path.write_text('[workspace.py]\npropagate_bumps = false\n', encoding='utf-8')
        cfg = load_config(tmp_path)
        assert cfg.workspaces['py'].propagate_bumps is False
