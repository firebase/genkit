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

"""Tests for releasekit.init module."""

from __future__ import annotations

from pathlib import Path

import tomlkit
from releasekit.config import CONFIG_FILENAME
from releasekit.init import (
    detect_groups,
    generate_config_toml,
    scaffold_config,
)
from releasekit.workspace import Package


def _make_packages() -> list[Package]:
    """Create a test package set mimicking the genkit workspace."""
    return [
        Package(
            name='genkit',
            version='0.5.0',
            path=Path('/ws/packages/genkit'),
            manifest_path=Path('/ws/packages/genkit/pyproject.toml'),
        ),
        Package(
            name='genkit-plugin-google-genai',
            version='0.5.0',
            path=Path('/ws/plugins/google-genai'),
            manifest_path=Path('/ws/plugins/google-genai/pyproject.toml'),
            internal_deps=['genkit'],
        ),
        Package(
            name='genkit-plugin-vertex-ai',
            version='0.5.0',
            path=Path('/ws/plugins/vertex-ai'),
            manifest_path=Path('/ws/plugins/vertex-ai/pyproject.toml'),
            internal_deps=['genkit'],
        ),
        Package(
            name='genkit-plugin-ollama',
            version='0.5.0',
            path=Path('/ws/plugins/ollama'),
            manifest_path=Path('/ws/plugins/ollama/pyproject.toml'),
            internal_deps=['genkit'],
        ),
        Package(
            name='provider-google-genai-hello',
            version='0.1.0',
            path=Path('/ws/samples/provider-google-genai-hello'),
            manifest_path=Path('/ws/samples/provider-google-genai-hello/pyproject.toml'),
            internal_deps=['genkit', 'genkit-plugin-google-genai'],
        ),
    ]


class TestDetectGroups:
    """Tests for detect_groups()."""

    def test_detects_packages(self) -> None:
        """Packages under packages/ are grouped as 'packages'."""
        pkgs = _make_packages()
        groups = detect_groups(pkgs)

        if 'packages' not in groups:
            raise AssertionError('Missing packages group')
        if 'genkit' not in groups['packages']:
            raise AssertionError('genkit should be in packages group')

    def test_detects_plugins(self) -> None:
        """Packages with '-plugin-' are 'plugins'."""
        pkgs = _make_packages()
        groups = detect_groups(pkgs)

        if 'plugins' not in groups:
            raise AssertionError('Missing plugins group')

    def test_detects_samples(self) -> None:
        """Packages in samples/ directory are 'samples'."""
        pkgs = _make_packages()
        groups = detect_groups(pkgs)

        if 'samples' not in groups:
            raise AssertionError('Missing samples group')

    def test_empty_packages(self) -> None:
        """Empty package list produces empty groups."""
        groups = detect_groups([])
        if groups:
            msg = f'Expected empty groups, got {groups}'
            raise AssertionError(msg)

    def test_plugin_glob_pattern(self) -> None:
        """Multiple plugins with same prefix get a glob pattern."""
        pkgs = _make_packages()
        groups = detect_groups(pkgs)

        plugins = groups.get('plugins', [])
        # Should be a glob like 'genkit-plugin-*' since all share the prefix.
        if plugins and len(plugins) == 1:
            if '*' not in plugins[0]:
                msg = f'Expected glob pattern, got {plugins}'
                raise AssertionError(msg)


class TestGenerateConfigToml:
    """Tests for generate_config_toml()."""

    def test_produces_valid_toml(self) -> None:
        """Generated output is valid TOML with workspace section."""
        groups = {'core': ['genkit'], 'plugins': ['genkit-plugin-*']}
        output = generate_config_toml(groups)

        doc = tomlkit.parse(output)
        if 'workspace' not in doc:
            raise AssertionError('Missing workspace section')

    def test_contains_workspace_section(self) -> None:
        """Generated TOML includes [workspace.<label>] section."""
        output = generate_config_toml({}, workspace_label='py', ecosystem='python')
        if '[workspace.py]' not in output:
            raise AssertionError('Missing [workspace.py] section')

    def test_contains_ecosystem(self) -> None:
        """Generated TOML includes ecosystem field in workspace."""
        output = generate_config_toml({}, ecosystem='python')
        if 'ecosystem = "python"' not in output:
            raise AssertionError('Missing ecosystem field')

    def test_contains_tag_format(self) -> None:
        """Generated TOML includes tag_format in workspace section."""
        output = generate_config_toml({})
        if 'tag_format' not in output:
            raise AssertionError('Missing tag_format')

    def test_contains_groups(self) -> None:
        """Generated TOML includes groups when provided."""
        groups = {'core': ['genkit']}
        output = generate_config_toml(groups)
        if 'core' not in output:
            raise AssertionError('Missing core group')

    def test_exclude_patterns(self) -> None:
        """Generated TOML includes exclude patterns."""
        output = generate_config_toml({}, exclude=['sample-*'])
        if 'sample-*' not in output:
            raise AssertionError('Missing exclude pattern')

    def test_no_tool_nesting(self) -> None:
        """Generated TOML does NOT have [tool.releasekit] nesting."""
        output = generate_config_toml({})
        if '[tool]' in output:
            raise AssertionError('Should not have [tool] section')

    def test_js_ecosystem(self) -> None:
        """Generated TOML for JS ecosystem."""
        output = generate_config_toml({}, workspace_label='js', ecosystem='js')
        doc = tomlkit.parse(output)
        workspace_table = doc.unwrap()['workspace']
        ws = workspace_table['js']
        if ws['ecosystem'] != 'js':
            raise AssertionError(f'Expected js ecosystem, got {ws["ecosystem"]}')

    def test_global_forge_present(self) -> None:
        """Generated TOML includes forge at top level."""
        output = generate_config_toml({})
        doc = tomlkit.parse(output)
        if 'forge' not in doc:
            raise AssertionError('Missing forge at top level')

    def test_roundtrip_through_load_config(self, tmp_path: Path) -> None:
        """Generated TOML can be loaded by load_config."""
        from releasekit.config import load_config

        groups = {'core': ['genkit'], 'plugins': ['genkit-plugin-*']}
        output = generate_config_toml(
            groups,
            workspace_label='py',
            ecosystem='python',
            exclude=['sample-*'],
        )
        config_path = tmp_path / CONFIG_FILENAME
        config_path.write_text(output, encoding='utf-8')

        cfg = load_config(tmp_path)
        if 'py' not in cfg.workspaces:
            raise AssertionError('Missing py workspace after load')
        ws = cfg.workspaces['py']
        if ws.ecosystem != 'python':
            raise AssertionError(f'Expected python, got {ws.ecosystem}')
        if ws.groups != groups:
            raise AssertionError(f'Groups mismatch: {ws.groups}')


def _create_minimal_workspace(ws: Path) -> None:
    """Create a minimal uv workspace for testing scaffold_config."""
    ws.mkdir(exist_ok=True)
    pyproject = ws / 'pyproject.toml'
    pyproject.write_text(
        '[tool.uv.workspace]\nmembers = ["packages/*"]\n',
        encoding='utf-8',
    )
    pkg_dir = ws / 'packages' / 'mylib'
    pkg_dir.mkdir(parents=True)
    (pkg_dir / 'pyproject.toml').write_text(
        '[project]\nname = "mylib"\nversion = "1.0.0"\n',
        encoding='utf-8',
    )


class TestScaffoldConfig:
    """Tests for scaffold_config()."""

    def test_dry_run_no_write(self, tmp_path: Path) -> None:
        """Dry run returns TOML but does not write files."""
        ws = tmp_path / 'ws'
        _create_minimal_workspace(ws)

        result = scaffold_config(ws, dry_run=True)

        if not result:
            raise AssertionError('Expected TOML content for dry run')

        # releasekit.toml should NOT have been created.
        config_file = ws / CONFIG_FILENAME
        if config_file.exists():
            raise AssertionError('Dry run should not write releasekit.toml')

    def test_writes_releasekit_toml(self, tmp_path: Path) -> None:
        """Non-dry-run creates releasekit.toml with workspace section."""
        ws = tmp_path / 'ws'
        _create_minimal_workspace(ws)

        scaffold_config(ws)

        config_file = ws / CONFIG_FILENAME
        if not config_file.exists():
            raise AssertionError('Expected releasekit.toml to be created')
        content = config_file.read_text(encoding='utf-8')
        if 'workspace' not in content:
            raise AssertionError('Expected workspace section in releasekit.toml')
        if 'ecosystem' not in content:
            raise AssertionError('Expected ecosystem field in releasekit.toml')

    def test_does_not_modify_pyproject(self, tmp_path: Path) -> None:
        """scaffold_config does NOT modify pyproject.toml."""
        ws = tmp_path / 'ws'
        _create_minimal_workspace(ws)
        pyproject = ws / 'pyproject.toml'
        original_content = pyproject.read_text(encoding='utf-8')

        scaffold_config(ws)

        after_content = pyproject.read_text(encoding='utf-8')
        if original_content != after_content:
            raise AssertionError('pyproject.toml should not be modified')

    def test_idempotent_no_force(self, tmp_path: Path) -> None:
        """Running twice without --force skips the second time."""
        ws = tmp_path / 'ws'
        _create_minimal_workspace(ws)

        # Pre-create releasekit.toml to simulate existing config.
        config_file = ws / CONFIG_FILENAME
        config_file.write_text('tag_format = "existing"\n', encoding='utf-8')

        result = scaffold_config(ws)
        if result:
            raise AssertionError('Expected empty result for existing config')

    def test_gitignore_updated(self, tmp_path: Path) -> None:
        """.gitignore gets releasekit patterns."""
        ws = tmp_path / 'ws'
        _create_minimal_workspace(ws)

        scaffold_config(ws)

        gitignore = ws / '.gitignore'
        if not gitignore.exists():
            raise AssertionError('.gitignore should be created')
        content = gitignore.read_text(encoding='utf-8')
        if '*.bak' not in content:
            raise AssertionError('Missing *.bak pattern in .gitignore')
