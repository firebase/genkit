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

import asyncio
import os
from pathlib import Path

import tomlkit
from releasekit.config import CONFIG_FILENAME, ReleaseConfig, load_config
from releasekit.detection import _is_submodule, _parse_gitmodules, detect_ecosystems
from releasekit.init import (
    TagScanReport,
    _detect_discrepancies,
    _detect_ecosystem,
    detect_groups,
    generate_config_toml,
    print_scaffold_preview,
    print_tag_scan_report,
    scaffold_config,
    scaffold_multi_config,
    scan_and_bootstrap,
)
from releasekit.migrate import ClassifiedTag
from releasekit.workspace import Package
from tests._fakes import FakeVCS


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

    def test_force_overwrites_existing(self, tmp_path: Path) -> None:
        """--force overwrites existing releasekit.toml."""
        ws = tmp_path / 'ws'
        _create_minimal_workspace(ws)

        config_file = ws / CONFIG_FILENAME
        config_file.write_text('old = "content"\n', encoding='utf-8')

        result = scaffold_config(ws, force=True)
        assert result  # Should return new content
        content = config_file.read_text(encoding='utf-8')
        assert 'workspace' in content
        assert 'old' not in content

    def test_gitignore_idempotent(self, tmp_path: Path) -> None:
        """Running scaffold twice doesn't duplicate .gitignore patterns."""
        ws = tmp_path / 'ws'
        _create_minimal_workspace(ws)

        scaffold_config(ws)
        # Remove config to allow second run.
        (ws / CONFIG_FILENAME).unlink()
        scaffold_config(ws)

        gitignore = ws / '.gitignore'
        content = gitignore.read_text(encoding='utf-8')
        assert content.count('*.bak') == 1

    def test_gitignore_appends_to_existing(self, tmp_path: Path) -> None:
        """.gitignore with existing content gets patterns appended."""
        ws = tmp_path / 'ws'
        _create_minimal_workspace(ws)
        gitignore = ws / '.gitignore'
        gitignore.write_text('node_modules/\n', encoding='utf-8')

        scaffold_config(ws)

        content = gitignore.read_text(encoding='utf-8')
        assert 'node_modules/' in content
        assert '*.bak' in content

    def test_gitignore_no_trailing_newline(self, tmp_path: Path) -> None:
        """.gitignore without trailing newline gets one added."""
        ws = tmp_path / 'ws'
        _create_minimal_workspace(ws)
        gitignore = ws / '.gitignore'
        gitignore.write_text('node_modules/', encoding='utf-8')  # no trailing newline

        scaffold_config(ws)

        content = gitignore.read_text(encoding='utf-8')
        assert 'node_modules/' in content
        assert '*.bak' in content


class TestDetectEcosystem:
    """Tests for _detect_ecosystem helper."""

    def test_python_default(self, tmp_path: Path) -> None:
        """Empty directory defaults to python."""
        eco, label = _detect_ecosystem(tmp_path)
        assert eco == 'python'
        assert label == 'py'

    def test_js_pnpm_workspace(self, tmp_path: Path) -> None:
        """pnpm-workspace.yaml triggers JS detection."""
        (tmp_path / 'pnpm-workspace.yaml').write_text('packages:\n  - packages/*\n')
        eco, label = _detect_ecosystem(tmp_path)
        assert eco == 'js'
        assert label == 'js'

    def test_js_package_json(self, tmp_path: Path) -> None:
        """package.json triggers JS detection."""
        (tmp_path / 'package.json').write_text('{}')
        eco, label = _detect_ecosystem(tmp_path)
        assert eco == 'js'
        assert label == 'js'

    def test_rust_cargo_workspace(self, tmp_path: Path) -> None:
        """Cargo.toml with [workspace] triggers Rust detection."""
        (tmp_path / 'Cargo.toml').write_text('[workspace]\nmembers = ["crates/*"]\n')
        eco, label = _detect_ecosystem(tmp_path)
        assert eco == 'rust'
        assert label == 'rust'

    def test_rust_cargo_no_workspace(self, tmp_path: Path) -> None:
        """Cargo.toml without [workspace] falls through."""
        (tmp_path / 'Cargo.toml').write_text('[package]\nname = "foo"\n')
        eco, _label = _detect_ecosystem(tmp_path)
        assert eco == 'python'  # falls through to default

    def test_go_workspace(self, tmp_path: Path) -> None:
        """go.work triggers Go detection."""
        (tmp_path / 'go.work').write_text('go 1.21\n')
        eco, label = _detect_ecosystem(tmp_path)
        assert eco == 'go'
        assert label == 'go'

    def test_go_mod(self, tmp_path: Path) -> None:
        """go.mod triggers Go detection."""
        (tmp_path / 'go.mod').write_text('module example.com/foo\n')
        eco, label = _detect_ecosystem(tmp_path)
        assert eco == 'go'
        assert label == 'go'

    def test_jvm_gradle_kts(self, tmp_path: Path) -> None:
        """build.gradle.kts triggers Java/JVM detection."""
        (tmp_path / 'build.gradle.kts').write_text('plugins {}')
        eco, label = _detect_ecosystem(tmp_path)
        assert eco == 'java'
        assert label == 'java'

    def test_jvm_gradle(self, tmp_path: Path) -> None:
        """build.gradle triggers Java/JVM detection."""
        (tmp_path / 'build.gradle').write_text('apply plugin: "java"')
        eco, label = _detect_ecosystem(tmp_path)
        assert eco == 'java'
        assert label == 'java'

    def test_jvm_maven(self, tmp_path: Path) -> None:
        """pom.xml triggers Java/JVM detection."""
        (tmp_path / 'pom.xml').write_text('<project></project>')
        eco, label = _detect_ecosystem(tmp_path)
        assert eco == 'java'
        assert label == 'java'

    def test_dart_pubspec(self, tmp_path: Path) -> None:
        """pubspec.yaml triggers Dart detection."""
        (tmp_path / 'pubspec.yaml').write_text('name: foo\n')
        eco, label = _detect_ecosystem(tmp_path)
        assert eco == 'dart'
        assert label == 'dart'


class TestPrintScaffoldPreview:
    """Tests for print_scaffold_preview."""

    def test_empty_fragment_no_output(self, capsys: object) -> None:
        """Empty fragment produces no output."""
        print_scaffold_preview('')
        # No assertion needed — just verify no crash.

    def test_plain_text_output(self, capsys: object) -> None:
        """Non-TTY output prints plain text."""
        print_scaffold_preview('forge = "github"\n')
        # In test environment (non-TTY), should print plain text.


class TestDetectEcosystemEdgeCases:
    """Edge cases for _detect_ecosystem."""

    def test_cargo_toml_unreadable(self, tmp_path: Path) -> None:
        """Unreadable Cargo.toml falls through to default."""
        cargo = tmp_path / 'Cargo.toml'
        cargo.write_text('[workspace]\nmembers = ["crates/*"]\n')
        os.chmod(cargo, 0o000)  # noqa: S103
        try:
            eco, _label = _detect_ecosystem(tmp_path)
            assert eco == 'python'  # Falls through due to OSError
        finally:
            os.chmod(cargo, 0o644)  # noqa: S103


class TestDetectGroupsEdgeCases:
    """Edge cases for detect_groups."""

    def test_single_package_no_glob(self) -> None:
        """Single package in a group doesn't get a glob pattern."""
        pkgs = [
            Package(
                name='genkit-plugin-foo',
                version='0.1.0',
                path=Path('/ws/plugins/foo'),
                manifest_path=Path('/ws/plugins/foo/pyproject.toml'),
            ),
        ]
        groups = detect_groups(pkgs)
        assert groups['plugins'] == ['genkit-plugin-foo']

    def test_no_hyphen_names_listed_individually(self) -> None:
        """Packages without hyphens are listed individually."""
        pkgs = [
            Package(
                name='alpha',
                version='0.1.0',
                path=Path('/ws/libs/alpha'),
                manifest_path=Path('/ws/libs/alpha/pyproject.toml'),
            ),
            Package(
                name='beta',
                version='0.1.0',
                path=Path('/ws/libs/beta'),
                manifest_path=Path('/ws/libs/beta/pyproject.toml'),
            ),
        ]
        groups = detect_groups(pkgs)
        assert sorted(groups['libs']) == ['alpha', 'beta']


class TestScaffoldConfigSampleDetection:
    """Tests for sample pattern detection in scaffold_config."""

    def test_sample_packages_excluded(self, tmp_path: Path) -> None:
        """Workspace with many sample-* packages gets exclude pattern."""
        ws = tmp_path / 'ws'
        ws.mkdir()
        (ws / 'pyproject.toml').write_text(
            '[tool.uv.workspace]\nmembers = ["packages/*", "samples/*"]\n',
            encoding='utf-8',
        )
        # Create a core package.
        core = ws / 'packages' / 'mylib'
        core.mkdir(parents=True)
        (core / 'pyproject.toml').write_text('[project]\nname = "mylib"\nversion = "1.0.0"\n')

        # Create 3+ sample packages with a common prefix.
        for i in range(3):
            s = ws / 'samples' / f'sample-app-{i}'
            s.mkdir(parents=True)
            (s / 'pyproject.toml').write_text(f'[project]\nname = "sample-app-{i}"\nversion = "0.1.0"\n')

        result = scaffold_config(ws, dry_run=True)
        assert result
        # The exclude pattern should contain a glob for samples.
        assert 'sample-*' in result or 'exclude' in result


# ---------------------------------------------------------------------------
# Tag scanning integration tests
# ---------------------------------------------------------------------------


# FakeVCS is imported from tests._fakes (see top of file).


def _write_config(ws: Path, workspace_label: str = 'py') -> Path:
    """Write a minimal releasekit.toml and return its path."""
    config_path = ws / CONFIG_FILENAME
    config_path.write_text(
        f'forge = "github"\n\n'
        f'[workspace.{workspace_label}]\n'
        f'ecosystem = "python"\n'
        f'tag_format = "{{name}}-v{{version}}"\n'
        f'umbrella_tag = "v{{version}}"\n',
        encoding='utf-8',
    )
    return config_path


class TestScanAndBootstrap:
    """Tests for scan_and_bootstrap()."""

    def test_no_tags_graceful_skip(self, tmp_path: Path) -> None:
        """No tags in repo produces empty report, no bootstrap_sha."""
        ws = tmp_path / 'ws'
        ws.mkdir()
        config_path = _write_config(ws)
        config = load_config(ws)
        vcs = FakeVCS()

        report = asyncio.run(scan_and_bootstrap(config_path, config, vcs))

        assert report.classified == []
        assert report.unclassified == []
        assert report.bootstrap_shas == {}
        assert report.written is False

    def test_tags_write_bootstrap_sha(self, tmp_path: Path) -> None:
        """Matching tags result in bootstrap_sha written to config."""
        ws = tmp_path / 'ws'
        ws.mkdir()
        config_path = _write_config(ws)
        config = load_config(ws)
        vcs = FakeVCS(
            tag_list=['genkit-v0.5.0', 'genkit-v0.4.0'],
            tags={'genkit-v0.5.0', 'genkit-v0.4.0'},
            tag_shas={'genkit-v0.5.0': 'abc123def456', 'genkit-v0.4.0': 'older000'},
        )

        report = asyncio.run(scan_and_bootstrap(config_path, config, vcs))

        assert len(report.classified) == 2
        assert 'py' in report.bootstrap_shas
        assert report.bootstrap_shas['py'] == 'abc123def456'
        assert report.written is True

        # Verify the TOML was actually updated.
        updated = tomlkit.parse(config_path.read_text(encoding='utf-8')).unwrap()
        assert updated['workspace']['py']['bootstrap_sha'] == 'abc123def456'

    def test_umbrella_tags_classified(self, tmp_path: Path) -> None:
        """Umbrella tags are classified and used for bootstrap_sha."""
        ws = tmp_path / 'ws'
        ws.mkdir()
        config_path = _write_config(ws)
        config = load_config(ws)
        vcs = FakeVCS(
            tag_list=['v1.0.0'],
            tags={'v1.0.0'},
            tag_shas={'v1.0.0': 'umbrella_sha_123'},
        )

        report = asyncio.run(scan_and_bootstrap(config_path, config, vcs))

        assert len(report.classified) == 1
        assert report.classified[0].is_umbrella is True
        assert report.bootstrap_shas['py'] == 'umbrella_sha_123'
        assert report.written is True

    def test_unclassified_tags_reported(self, tmp_path: Path) -> None:
        """Tags that don't match any format are reported as unclassified."""
        ws = tmp_path / 'ws'
        ws.mkdir()
        config_path = _write_config(ws)
        config = load_config(ws)
        vcs = FakeVCS(
            tag_list=['genkit-v0.5.0', 'random-tag', 'another-tag'],
            tags={'genkit-v0.5.0', 'random-tag', 'another-tag'},
            tag_shas={'genkit-v0.5.0': 'sha_good'},
        )

        report = asyncio.run(scan_and_bootstrap(config_path, config, vcs))

        assert len(report.classified) == 1
        assert len(report.unclassified) == 2
        assert 'random-tag' in report.unclassified
        assert 'another-tag' in report.unclassified

    def test_dry_run_no_write(self, tmp_path: Path) -> None:
        """Dry run computes bootstrap_sha but does not write to config."""
        ws = tmp_path / 'ws'
        ws.mkdir()
        config_path = _write_config(ws)
        original_content = config_path.read_text(encoding='utf-8')
        config = load_config(ws)
        vcs = FakeVCS(
            tag_list=['genkit-v0.5.0'],
            tags={'genkit-v0.5.0'},
            tag_shas={'genkit-v0.5.0': 'sha_dry_run'},
        )

        report = asyncio.run(scan_and_bootstrap(config_path, config, vcs, dry_run=True))

        assert report.bootstrap_shas['py'] == 'sha_dry_run'
        assert report.written is False
        # Config file should be unchanged.
        assert config_path.read_text(encoding='utf-8') == original_content

    def test_no_workspaces_configured(self, tmp_path: Path) -> None:
        """Config with no workspaces returns empty report."""
        ws = tmp_path / 'ws'
        ws.mkdir()
        config_path = ws / CONFIG_FILENAME
        config_path.write_text('forge = "github"\n', encoding='utf-8')
        config = ReleaseConfig(config_path=config_path)
        vcs = FakeVCS(tag_list=['v1.0.0'], tags={'v1.0.0'})

        report = asyncio.run(scan_and_bootstrap(config_path, config, vcs))

        assert report.classified == []
        assert report.bootstrap_shas == {}

    def test_no_tags_match_any_workspace(self, tmp_path: Path) -> None:
        """All tags are unclassified when none match workspace formats."""
        ws = tmp_path / 'ws'
        ws.mkdir()
        config_path = _write_config(ws)
        config = load_config(ws)
        vcs = FakeVCS(tag_list=['totally-unrelated-1.0', 'nope-2.0'], tags={'totally-unrelated-1.0', 'nope-2.0'})

        report = asyncio.run(scan_and_bootstrap(config_path, config, vcs))

        assert report.classified == []
        assert len(report.unclassified) == 2
        assert len(report.discrepancies) == 1
        assert 'none matched' in report.discrepancies[0]

    def test_picks_latest_semver(self, tmp_path: Path) -> None:
        """When multiple versions exist, picks the latest by semver."""
        ws = tmp_path / 'ws'
        ws.mkdir()
        config_path = _write_config(ws)
        config = load_config(ws)
        vcs = FakeVCS(
            tag_list=['genkit-v0.3.0', 'genkit-v1.2.0', 'genkit-v0.9.0'],
            tags={'genkit-v0.3.0', 'genkit-v1.2.0', 'genkit-v0.9.0'},
            tag_shas={
                'genkit-v0.3.0': 'sha_030',
                'genkit-v1.2.0': 'sha_120',
                'genkit-v0.9.0': 'sha_090',
            },
        )

        report = asyncio.run(scan_and_bootstrap(config_path, config, vcs))

        assert report.bootstrap_shas['py'] == 'sha_120'
        assert report.latest_per_workspace['py'].version == '1.2.0'


class TestDetectDiscrepancies:
    """Tests for _detect_discrepancies()."""

    def test_no_discrepancies(self) -> None:
        """Clean tag set produces no discrepancies."""
        classified = [
            ClassifiedTag(tag='genkit-v0.5.0', workspace_label='py', package_name='genkit', version='0.5.0'),
        ]
        msgs = _detect_discrepancies(classified, [], {'py': classified[0]})
        assert msgs == []

    def test_unclassified_tags_reported(self) -> None:
        """Unclassified tags produce a discrepancy message."""
        msgs = _detect_discrepancies([], ['random-tag', 'other-tag'], {})
        assert len(msgs) == 1
        assert '2 tag(s)' in msgs[0]
        assert 'random-tag' in msgs[0]

    def test_umbrella_only_warning(self) -> None:
        """Workspace with only umbrella tags produces a warning."""
        classified = [
            ClassifiedTag(tag='v1.0.0', workspace_label='py', version='1.0.0', is_umbrella=True),
        ]
        msgs = _detect_discrepancies(classified, [], {'py': classified[0]})
        assert any('only umbrella tags' in m for m in msgs)

    def test_mixed_tag_formats_warning(self) -> None:
        """Multiple tag formats for same workspace produces a warning."""
        classified = [
            ClassifiedTag(tag='genkit-v0.5.0', workspace_label='py', package_name='genkit', version='0.5.0'),
            ClassifiedTag(tag='genkit/v0.4.0', workspace_label='py', package_name='genkit', version='0.4.0'),
        ]
        msgs = _detect_discrepancies(classified, [], {'py': classified[0]})
        assert any('multiple tag formats' in m for m in msgs)

    def test_many_unclassified_truncated(self) -> None:
        """More than 10 unclassified tags are truncated with '...'."""
        unclassified = [f'tag-{i}' for i in range(15)]
        msgs = _detect_discrepancies([], unclassified, {})
        assert '...' in msgs[0]
        assert '15 tag(s)' in msgs[0]


class TestPrintTagScanReport:
    """Tests for print_tag_scan_report()."""

    def test_no_tags_message(self, capsys: object) -> None:
        """Empty report prints info message."""
        report = TagScanReport()
        print_tag_scan_report(report)
        # Should not crash; prints info about no tags.

    def test_with_classified_tags(self, capsys: object) -> None:
        """Report with classified tags prints scan summary."""
        ct = ClassifiedTag(
            tag='genkit-v0.5.0',
            workspace_label='py',
            package_name='genkit',
            version='0.5.0',
            commit_sha='abc123def456',
        )
        report = TagScanReport(
            classified=[ct],
            latest_per_workspace={'py': ct},
            bootstrap_shas={'py': 'abc123def456'},
            written=True,
        )
        print_tag_scan_report(report)
        # Should not crash.

    def test_dry_run_message(self, capsys: object) -> None:
        """Dry-run report shows 'Would write' instead of written."""
        ct = ClassifiedTag(
            tag='v1.0.0',
            workspace_label='py',
            version='1.0.0',
            commit_sha='sha123',
            is_umbrella=True,
        )
        report = TagScanReport(
            classified=[ct],
            latest_per_workspace={'py': ct},
            bootstrap_shas={'py': 'sha123'},
            written=False,
        )
        print_tag_scan_report(report)
        # Should not crash.

    def test_discrepancies_printed(self, capsys: object) -> None:
        """Report with discrepancies prints warning section."""
        ct = ClassifiedTag(
            tag='genkit-v0.5.0',
            workspace_label='py',
            package_name='genkit',
            version='0.5.0',
            commit_sha='sha1',
        )
        report = TagScanReport(
            classified=[ct],
            unclassified=['random-tag'],
            latest_per_workspace={'py': ct},
            bootstrap_shas={'py': 'sha1'},
            discrepancies=['1 tag(s) could not be matched: random-tag'],
            written=True,
        )
        print_tag_scan_report(report)
        # Should not crash.


# ---------------------------------------------------------------------------
# scaffold_multi_config tests
# ---------------------------------------------------------------------------


class TestScaffoldMultiConfig:
    """Tests for scaffold_multi_config()."""

    def test_generates_multiple_workspaces(self, tmp_path: Path) -> None:
        """Generates one [workspace.<label>] per ecosystem."""
        ecosystems = [
            ('python', 'py', tmp_path / 'py'),
            ('js', 'js', tmp_path / 'js'),
        ]
        # Create minimal workspace dirs (discovery will fail gracefully).
        (tmp_path / 'py').mkdir()
        (tmp_path / 'js').mkdir()

        result = scaffold_multi_config(tmp_path, ecosystems, dry_run=True)
        doc = tomlkit.parse(result).unwrap()

        assert 'forge' in doc
        assert 'py' in doc['workspace']
        assert 'js' in doc['workspace']
        assert doc['workspace']['py']['ecosystem'] == 'python'
        assert doc['workspace']['js']['ecosystem'] == 'js'

    def test_includes_root_for_nested_workspaces(self, tmp_path: Path) -> None:
        """Nested workspace roots get a 'root' field."""
        py_root = tmp_path / 'py'
        py_root.mkdir()

        result = scaffold_multi_config(
            tmp_path,
            [('python', 'py', py_root)],
            dry_run=True,
        )
        doc = tomlkit.parse(result).unwrap()
        assert doc['workspace']['py']['root'] == 'py'

    def test_omits_root_for_same_dir(self, tmp_path: Path) -> None:
        """Workspace at monorepo root omits 'root' field."""
        result = scaffold_multi_config(
            tmp_path,
            [('python', 'py', tmp_path)],
            dry_run=True,
        )
        doc = tomlkit.parse(result).unwrap()
        assert 'root' not in doc['workspace']['py']

    def test_umbrella_tag_uses_label(self, tmp_path: Path) -> None:
        """Umbrella tag format includes the workspace label."""
        (tmp_path / 'js').mkdir()
        result = scaffold_multi_config(
            tmp_path,
            [('js', 'js', tmp_path / 'js')],
            dry_run=True,
        )
        doc = tomlkit.parse(result).unwrap()
        assert doc['workspace']['js']['umbrella_tag'] == 'js/v{version}'

    def test_dry_run_no_write(self, tmp_path: Path) -> None:
        """Dry run does not write files."""
        result = scaffold_multi_config(
            tmp_path,
            [('python', 'py', tmp_path)],
            dry_run=True,
        )
        assert result  # content generated
        assert not (tmp_path / 'releasekit.toml').exists()

    def test_writes_file(self, tmp_path: Path) -> None:
        """Non-dry-run writes releasekit.toml."""
        result = scaffold_multi_config(
            tmp_path,
            [('python', 'py', tmp_path)],
        )
        assert result
        assert (tmp_path / 'releasekit.toml').exists()

    def test_no_overwrite_without_force(self, tmp_path: Path) -> None:
        """Existing config is not overwritten without --force."""
        (tmp_path / 'releasekit.toml').write_text('existing = true\n')
        result = scaffold_multi_config(
            tmp_path,
            [('python', 'py', tmp_path)],
        )
        assert result == ''
        assert 'existing' in (tmp_path / 'releasekit.toml').read_text()

    def test_force_overwrites(self, tmp_path: Path) -> None:
        """--force overwrites existing config."""
        (tmp_path / 'releasekit.toml').write_text('existing = true\n')
        result = scaffold_multi_config(
            tmp_path,
            [('python', 'py', tmp_path)],
            force=True,
        )
        assert result
        assert 'existing' not in (tmp_path / 'releasekit.toml').read_text()

    def test_empty_ecosystems(self, tmp_path: Path) -> None:
        """Empty ecosystems list returns empty string."""
        result = scaffold_multi_config(tmp_path, [])
        assert result == ''


# ---------------------------------------------------------------------------
# Submodule exclusion tests
# ---------------------------------------------------------------------------


class TestParseGitmodules:
    """Tests for _parse_gitmodules()."""

    def test_parses_paths(self, tmp_path: Path) -> None:
        """Extracts submodule paths from .gitmodules."""
        (tmp_path / '.gitmodules').write_text(
            '[submodule "vendor/lib"]\n'
            '    path = vendor/lib\n'
            '    url = https://github.com/example/lib.git\n'
            '[submodule "third_party/proto"]\n'
            '    path = third_party/proto\n'
            '    url = https://github.com/example/proto.git\n',
        )
        paths = _parse_gitmodules(tmp_path)
        assert paths == {'vendor/lib', 'third_party/proto'}

    def test_no_gitmodules(self, tmp_path: Path) -> None:
        """Returns empty set when .gitmodules doesn't exist."""
        assert _parse_gitmodules(tmp_path) == set()

    def test_empty_gitmodules(self, tmp_path: Path) -> None:
        """Returns empty set for empty .gitmodules."""
        (tmp_path / '.gitmodules').write_text('')
        assert _parse_gitmodules(tmp_path) == set()


class TestIsSubmodule:
    """Tests for _is_submodule()."""

    def test_git_file_is_submodule(self, tmp_path: Path) -> None:
        """Directory with .git file (not dir) is a submodule."""
        sub = tmp_path / 'vendor'
        sub.mkdir()
        (sub / '.git').write_text('gitdir: ../.git/modules/vendor\n')
        assert _is_submodule(sub) is True

    def test_git_dir_is_not_submodule(self, tmp_path: Path) -> None:
        """Directory with .git directory is not a submodule."""
        sub = tmp_path / 'repo'
        sub.mkdir()
        (sub / '.git').mkdir()
        assert _is_submodule(sub) is False

    def test_no_git_is_not_submodule(self, tmp_path: Path) -> None:
        """Directory without .git is not a submodule."""
        sub = tmp_path / 'normal'
        sub.mkdir()
        assert _is_submodule(sub) is False


class TestDetectEcosystemsSubmoduleExclusion:
    """Tests that detect_ecosystems skips submodules."""

    def test_skips_gitmodules_listed_dir(self, tmp_path: Path) -> None:
        """Directories listed in .gitmodules are skipped."""
        # Set up monorepo root.
        (tmp_path / '.git').mkdir()

        # Real workspace.
        py_dir = tmp_path / 'py'
        py_dir.mkdir()
        (py_dir / 'pyproject.toml').write_text(
            '[tool.uv.workspace]\nmembers = ["packages/*"]\n',
        )

        # Submodule with a workspace marker (should be skipped).
        vendor = tmp_path / 'vendor'
        vendor.mkdir()
        (vendor / 'pyproject.toml').write_text(
            '[tool.uv.workspace]\nmembers = ["lib/*"]\n',
        )

        # .gitmodules lists vendor as a submodule.
        (tmp_path / '.gitmodules').write_text(
            '[submodule "vendor"]\n    path = vendor\n    url = x\n',
        )

        result = detect_ecosystems(tmp_path)
        roots = [e.root for e in result]
        assert py_dir.resolve() in roots
        assert vendor.resolve() not in roots

    def test_skips_git_file_submodule(self, tmp_path: Path) -> None:
        """Directories with .git file are skipped even without .gitmodules."""
        (tmp_path / '.git').mkdir()

        sub = tmp_path / 'external'
        sub.mkdir()
        (sub / '.git').write_text('gitdir: ../.git/modules/external\n')
        (sub / 'pyproject.toml').write_text(
            '[tool.uv.workspace]\nmembers = ["*"]\n',
        )

        result = detect_ecosystems(tmp_path)
        roots = [e.root for e in result]
        assert sub.resolve() not in roots
