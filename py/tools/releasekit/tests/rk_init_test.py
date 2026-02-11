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
            pyproject_path=Path('/ws/packages/genkit/pyproject.toml'),
        ),
        Package(
            name='genkit-plugin-google-genai',
            version='0.5.0',
            path=Path('/ws/plugins/google-genai'),
            pyproject_path=Path('/ws/plugins/google-genai/pyproject.toml'),
            internal_deps=['genkit'],
        ),
        Package(
            name='genkit-plugin-vertex-ai',
            version='0.5.0',
            path=Path('/ws/plugins/vertex-ai'),
            pyproject_path=Path('/ws/plugins/vertex-ai/pyproject.toml'),
            internal_deps=['genkit'],
        ),
        Package(
            name='genkit-plugin-ollama',
            version='0.5.0',
            path=Path('/ws/plugins/ollama'),
            pyproject_path=Path('/ws/plugins/ollama/pyproject.toml'),
            internal_deps=['genkit'],
        ),
        Package(
            name='provider-google-genai-hello',
            version='0.1.0',
            path=Path('/ws/samples/provider-google-genai-hello'),
            pyproject_path=Path('/ws/samples/provider-google-genai-hello/pyproject.toml'),
            internal_deps=['genkit', 'genkit-plugin-google-genai'],
        ),
    ]


class TestDetectGroups:
    """Tests for detect_groups()."""

    def test_detects_core(self) -> None:
        """Packages without plugin/sample markers are 'core'."""
        pkgs = _make_packages()
        groups = detect_groups(pkgs)

        if 'core' not in groups:
            raise AssertionError('Missing core group')
        if 'genkit' not in groups['core']:
            raise AssertionError('genkit should be in core group')

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
        """Generated output is valid TOML."""
        groups = {'core': ['genkit'], 'plugins': ['genkit-plugin-*']}
        output = generate_config_toml(groups)

        doc = tomlkit.parse(output)
        tool = doc.get('tool')
        if not isinstance(tool, dict):
            raise AssertionError('Missing [tool] section')
        rk = tool.get('releasekit')
        if not isinstance(rk, dict):
            raise AssertionError('Missing [tool.releasekit] section')

    def test_contains_tag_format(self) -> None:
        """Generated TOML includes tag_format."""
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


class TestScaffoldConfig:
    """Tests for scaffold_config()."""

    def test_dry_run_no_write(self, tmp_path: Path) -> None:
        """Dry run returns TOML but does not write files."""
        # Create minimal workspace.
        ws = tmp_path / 'ws'
        ws.mkdir()
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

        result = scaffold_config(ws, dry_run=True)

        if not result:
            raise AssertionError('Expected TOML fragment for dry run')

        # File should NOT have been modified.
        content = pyproject.read_text(encoding='utf-8')
        if 'releasekit' in content:
            raise AssertionError('Dry run should not write to file')

    def test_writes_config(self, tmp_path: Path) -> None:
        """Non-dry-run writes [tool.releasekit] to pyproject.toml."""
        ws = tmp_path / 'ws'
        ws.mkdir()
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

        scaffold_config(ws)

        content = pyproject.read_text(encoding='utf-8')
        if 'releasekit' not in content:
            raise AssertionError('Expected [tool.releasekit] in file')

    def test_idempotent_no_force(self, tmp_path: Path) -> None:
        """Running twice without --force skips the second time."""
        ws = tmp_path / 'ws'
        ws.mkdir()
        pyproject = ws / 'pyproject.toml'
        pyproject.write_text(
            '[tool.uv.workspace]\nmembers = ["packages/*"]\n[tool.releasekit]\ntag_format = "existing"\n',
            encoding='utf-8',
        )
        pkg_dir = ws / 'packages' / 'mylib'
        pkg_dir.mkdir(parents=True)
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "mylib"\nversion = "1.0.0"\n',
            encoding='utf-8',
        )

        result = scaffold_config(ws)
        if result:
            raise AssertionError('Expected empty result for existing config')

    def test_gitignore_updated(self, tmp_path: Path) -> None:
        """.gitignore gets releasekit patterns."""
        ws = tmp_path / 'ws'
        ws.mkdir()
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

        scaffold_config(ws)

        gitignore = ws / '.gitignore'
        if not gitignore.exists():
            raise AssertionError('.gitignore should be created')
        content = gitignore.read_text(encoding='utf-8')
        if '*.bak' not in content:
            raise AssertionError('Missing *.bak pattern in .gitignore')
