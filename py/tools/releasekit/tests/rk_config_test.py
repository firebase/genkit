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
    DEFAULT_VERSIONING_SCHEMES,
    VALID_KEYS,
    VALID_PACKAGE_KEYS,
    VALID_WORKSPACE_KEYS,
    PackageConfig,
    ReleaseConfig,
    WorkspaceConfig,
    build_package_configs,
    load_config,
    resolve_group_refs,
    resolve_package_config,
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

    def test_no_overlap_except_allowed(self) -> None:
        """Test no overlap except workspace and Phase 8 shared keys.

        Phase 8 keys (release_mode, schedule, hooks, branches,
        versioning_scheme, calver_format) intentionally exist in both
        global and workspace scopes for the override hierarchy.
        """
        allowed_shared = {
            'ai',
            'announcements',
            'branches',
            'calver_format',
            'hooks',
            'license_headers',
            'release_mode',
            'schedule',
            'versioning_scheme',
            'workspace',
        }
        overlap = (VALID_KEYS - allowed_shared) & VALID_WORKSPACE_KEYS
        assert overlap == set(), f'Unexpected keys in both global and workspace: {overlap}'

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


# DEFAULT_VERSIONING_SCHEMES


class TestDefaultVersioningSchemes:
    """DEFAULT_VERSIONING_SCHEMES maps ecosystems to correct defaults."""

    def test_python_defaults_to_pep440(self) -> None:
        """Python ecosystem defaults to pep440."""
        assert DEFAULT_VERSIONING_SCHEMES['python'] == 'pep440'

    def test_js_defaults_to_semver(self) -> None:
        """JS ecosystem defaults to semver."""
        assert DEFAULT_VERSIONING_SCHEMES['js'] == 'semver'

    def test_go_defaults_to_semver(self) -> None:
        """Go ecosystem defaults to semver."""
        assert DEFAULT_VERSIONING_SCHEMES['go'] == 'semver'

    def test_rust_defaults_to_semver(self) -> None:
        """Rust ecosystem defaults to semver."""
        assert DEFAULT_VERSIONING_SCHEMES['rust'] == 'semver'

    def test_dart_defaults_to_semver(self) -> None:
        """Dart ecosystem defaults to semver."""
        assert DEFAULT_VERSIONING_SCHEMES['dart'] == 'semver'

    def test_java_defaults_to_semver(self) -> None:
        """Java ecosystem defaults to semver."""
        assert DEFAULT_VERSIONING_SCHEMES['java'] == 'semver'

    def test_only_python_uses_pep440(self) -> None:
        """Only python uses pep440; all others use semver."""
        for eco, scheme in DEFAULT_VERSIONING_SCHEMES.items():
            if eco == 'python':
                assert scheme == 'pep440', f'{eco} should be pep440'
            else:
                assert scheme == 'semver', f'{eco} should be semver, got {scheme}'

    def test_ecosystem_applied_on_load(self, tmp_path: Path) -> None:
        """Ecosystem default is applied when versioning_scheme is not set."""
        config_path = tmp_path / CONFIG_FILENAME
        config_path.write_text(
            '[workspace.py]\necosystem = "python"\nroot = "py"\n',
            encoding='utf-8',
        )
        cfg = load_config(tmp_path)
        assert cfg.workspaces['py'].versioning_scheme == 'pep440'

    def test_js_ecosystem_gets_semver(self, tmp_path: Path) -> None:
        """JS ecosystem gets semver by default."""
        config_path = tmp_path / CONFIG_FILENAME
        config_path.write_text(
            '[workspace.js]\necosystem = "js"\nroot = "js"\n',
            encoding='utf-8',
        )
        cfg = load_config(tmp_path)
        assert cfg.workspaces['js'].versioning_scheme == 'semver'

    def test_explicit_scheme_overrides_ecosystem_default(self, tmp_path: Path) -> None:
        """Explicit versioning_scheme overrides the ecosystem default."""
        config_path = tmp_path / CONFIG_FILENAME
        config_path.write_text(
            '[workspace.py]\necosystem = "python"\nversioning_scheme = "semver"\nroot = "py"\n',
            encoding='utf-8',
        )
        cfg = load_config(tmp_path)
        assert cfg.workspaces['py'].versioning_scheme == 'semver'


# PackageConfig


class TestPackageConfigDefaults:
    """PackageConfig has sensible defaults."""

    def test_default_versioning_scheme_empty(self) -> None:
        """Default versioning_scheme is empty (inherits from workspace)."""
        pc = PackageConfig()
        assert pc.versioning_scheme == ''

    def test_default_booleans_are_none(self) -> None:
        """Boolean fields default to None (inherit from workspace)."""
        pc = PackageConfig()
        assert pc.changelog is None
        assert pc.smoke_test is None
        assert pc.major_on_zero is None
        assert pc.provenance is None


class TestResolvePackageConfig:
    """resolve_package_config merges workspace defaults with per-package overrides."""

    def test_no_packages_returns_workspace_defaults(self) -> None:
        """When no packages overrides exist, workspace defaults are returned."""
        ws = WorkspaceConfig(versioning_scheme='pep440', major_on_zero=True)
        result = resolve_package_config(ws, 'genkit')
        assert result.versioning_scheme == 'pep440'
        assert result.major_on_zero is True

    def test_exact_package_override(self) -> None:
        """Exact package name match overrides workspace defaults."""
        ws = WorkspaceConfig(
            versioning_scheme='pep440',
            packages={'my-js-lib': PackageConfig(versioning_scheme='semver')},
        )
        result = resolve_package_config(ws, 'my-js-lib')
        assert result.versioning_scheme == 'semver'

    def test_unmatched_package_gets_workspace_defaults(self) -> None:
        """Unmatched package inherits workspace defaults."""
        ws = WorkspaceConfig(
            versioning_scheme='pep440',
            packages={'my-js-lib': PackageConfig(versioning_scheme='semver')},
        )
        result = resolve_package_config(ws, 'my-py-lib')
        assert result.versioning_scheme == 'pep440'

    def test_group_override(self) -> None:
        """Group membership match overrides workspace defaults."""
        ws = WorkspaceConfig(
            versioning_scheme='pep440',
            groups={'plugins': ['genkit-plugin-*']},
            packages={'plugins': PackageConfig(versioning_scheme='semver')},
        )
        result = resolve_package_config(ws, 'genkit-plugin-foo')
        assert result.versioning_scheme == 'semver'

    def test_exact_match_beats_group(self) -> None:
        """Exact package name match takes precedence over group match."""
        ws = WorkspaceConfig(
            versioning_scheme='pep440',
            groups={'plugins': ['genkit-plugin-*']},
            packages={
                'genkit-plugin-foo': PackageConfig(versioning_scheme='calver'),
                'plugins': PackageConfig(versioning_scheme='semver'),
            },
        )
        result = resolve_package_config(ws, 'genkit-plugin-foo')
        assert result.versioning_scheme == 'calver'

    def test_empty_override_inherits_from_workspace(self) -> None:
        """Empty override fields inherit from workspace."""
        ws = WorkspaceConfig(
            versioning_scheme='pep440',
            dist_tag='latest',
            major_on_zero=True,
            packages={'genkit': PackageConfig(registry_url='https://test.pypi.org')},
        )
        result = resolve_package_config(ws, 'genkit')
        assert result.versioning_scheme == 'pep440'
        assert result.dist_tag == 'latest'
        assert result.major_on_zero is True
        assert result.registry_url == 'https://test.pypi.org'


class TestBuildPackageConfigs:
    """build_package_configs builds a dict for all packages."""

    def test_builds_dict_for_all_packages(self) -> None:
        """Returns a dict keyed by package name."""
        ws = WorkspaceConfig(
            versioning_scheme='semver',
            packages={'pkg-a': PackageConfig(versioning_scheme='pep440')},
        )
        result = build_package_configs(ws, ['pkg-a', 'pkg-b'])
        assert result['pkg-a'].versioning_scheme == 'pep440'
        assert result['pkg-b'].versioning_scheme == 'semver'


class TestPackageConfigParsing:
    """TOML parsing of [workspace.<label>.packages.<name>] sections."""

    def test_load_packages_section(self, tmp_path: Path) -> None:
        """Packages section is parsed into PackageConfig dict."""
        config_path = tmp_path / CONFIG_FILENAME
        config_path.write_text(
            '[workspace.mono]\n'
            'root = "."\n'
            '\n'
            '[workspace.mono.packages."my-js-lib"]\n'
            'versioning_scheme = "semver"\n'
            'dist_tag = "next"\n'
            '\n'
            '[workspace.mono.packages."my-py-lib"]\n'
            'versioning_scheme = "pep440"\n'
            'registry_url = "https://test.pypi.org"\n',
            encoding='utf-8',
        )
        cfg = load_config(tmp_path)
        ws = cfg.workspaces['mono']
        assert 'my-js-lib' in ws.packages
        assert 'my-py-lib' in ws.packages
        assert ws.packages['my-js-lib'].versioning_scheme == 'semver'
        assert ws.packages['my-js-lib'].dist_tag == 'next'
        assert ws.packages['my-py-lib'].versioning_scheme == 'pep440'
        assert ws.packages['my-py-lib'].registry_url == 'https://test.pypi.org'

    def test_invalid_package_key_raises(self, tmp_path: Path) -> None:
        """Unknown key in packages section raises ReleaseKitError."""
        config_path = tmp_path / CONFIG_FILENAME
        config_path.write_text(
            '[workspace.mono]\nroot = "."\n\n[workspace.mono.packages."my-lib"]\nbad_key = "oops"\n',
            encoding='utf-8',
        )
        with pytest.raises(ReleaseKitError, match='Unknown key'):
            load_config(tmp_path)

    def test_invalid_versioning_scheme_in_package_raises(self, tmp_path: Path) -> None:
        """Invalid versioning_scheme in packages section raises."""
        config_path = tmp_path / CONFIG_FILENAME
        config_path.write_text(
            '[workspace.mono]\nroot = "."\n\n[workspace.mono.packages."my-lib"]\nversioning_scheme = "invalid"\n',
            encoding='utf-8',
        )
        with pytest.raises(ReleaseKitError, match='versioning_scheme'):
            load_config(tmp_path)

    def test_packages_key_in_valid_workspace_keys(self) -> None:
        """'packages' is a valid workspace key."""
        assert 'packages' in VALID_WORKSPACE_KEYS

    def test_valid_package_keys_are_subset_of_workspace_keys(self) -> None:
        """All VALID_PACKAGE_KEYS are also in VALID_WORKSPACE_KEYS."""
        assert VALID_PACKAGE_KEYS <= VALID_WORKSPACE_KEYS
