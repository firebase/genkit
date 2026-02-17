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

"""Integration tests for releasekit.

These tests exercise real multi-module workflows end-to-end using
on-disk workspaces and in-memory backend doubles. They verify that
the modules compose correctly at runtime — catching wiring bugs,
dataclass field mismatches, and protocol violations that unit tests
miss.

Each test class covers a distinct pipeline:

- Config → Discover → Graph → Plan
- Version bump → Pin → Restore round-trip
- State save → load → resume lifecycle
- Manifest save → load → SBOM generation
- Preflight → full check pipeline
- Init scaffold → config load round-trip
- Lock acquire → release lifecycle
- Release notes generation from manifest
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from releasekit.bump import bump_pyproject
from releasekit.config import CONFIG_FILENAME, load_config
from releasekit.errors import ReleaseKitError
from releasekit.formatters import format_graph
from releasekit.graph import build_graph, detect_cycles, topo_sort
from releasekit.init import generate_config_toml, scaffold_config
from releasekit.lock import LOCK_FILENAME, acquire_lock, release_lock_file
from releasekit.pin import ephemeral_pin, pin_dependencies
from releasekit.plan import PlanStatus, build_plan
from releasekit.sbom import SBOMFormat, generate_sbom, write_sbom
from releasekit.state import PackageStatus, RunState
from releasekit.tags import TagResult, format_tag
from releasekit.versions import PackageVersion, ReleaseManifest
from releasekit.workspace import discover_packages


def _write_root_pyproject(
    root: Path,
    members: str = '"packages/*", "plugins/*"',
    sources: dict[str, str] | None = None,
) -> None:
    """Write a minimal root pyproject.toml with workspace config."""
    sources_section = ''
    if sources:
        lines = []
        for name, spec in sources.items():
            lines.append(f'{name} = {spec}')
        sources_section = '\n[tool.uv.sources]\n' + '\n'.join(lines) + '\n'
    (root / 'pyproject.toml').write_text(
        f'[project]\nname = "workspace"\n\n[tool.uv.workspace]\nmembers = [{members}]\n{sources_section}',
        encoding='utf-8',
    )


def _write_package(
    root: Path,
    subdir: str,
    name: str,
    version: str = '0.1.0',
    deps: str = '',
    internal_deps: str = '',
) -> Path:
    """Write a minimal package pyproject.toml."""
    pkg_dir = root / subdir
    pkg_dir.mkdir(parents=True, exist_ok=True)
    deps_list = deps
    if internal_deps:
        deps_list = internal_deps if not deps else f'{deps}, {internal_deps}'
    deps_line = f'dependencies = [{deps_list}]' if deps_list else 'dependencies = []'
    (pkg_dir / 'pyproject.toml').write_text(
        f'[project]\nname = "{name}"\nversion = "{version}"\n{deps_line}\n',
        encoding='utf-8',
    )
    return pkg_dir


def _write_releasekit_toml(root: Path, content: str) -> Path:
    """Write releasekit.toml at the workspace root."""
    config_path = root / CONFIG_FILENAME
    config_path.write_text(content, encoding='utf-8')
    return config_path


class TestConfigDiscoverGraphPlanPipeline:
    """End-to-end: load config, discover packages, build graph, create plan."""

    def test_full_pipeline(self, tmp_path: Path) -> None:
        """Config → discover → graph → topo_sort → plan round-trip."""
        ws = tmp_path / 'ws'
        ws.mkdir()
        _write_root_pyproject(
            ws,
            sources={
                'core': '{workspace = true}',
                'plugin-a': '{workspace = true}',
                'plugin-b': '{workspace = true}',
            },
        )
        _write_package(ws, 'packages/core', 'core', '1.0.0')
        _write_package(
            ws,
            'plugins/plugin-a',
            'plugin-a',
            '1.0.0',
            internal_deps='"core"',
        )
        _write_package(
            ws,
            'plugins/plugin-b',
            'plugin-b',
            '1.0.0',
            internal_deps='"core"',
        )

        # 1. Discover packages.
        packages = discover_packages(ws)
        assert len(packages) == 3
        names = {p.name for p in packages}
        assert names == {'core', 'plugin-a', 'plugin-b'}

        # 2. Build dependency graph.
        graph = build_graph(packages)
        assert len(graph) == 3
        assert 'core' in graph.edges['plugin-a']
        assert 'core' in graph.edges['plugin-b']

        # 3. Verify no cycles.
        cycles = detect_cycles(graph)
        assert cycles == []

        # 4. Topological sort.
        levels = topo_sort(graph)
        assert len(levels) >= 2
        level_0_names = {p.name for p in levels[0]}
        assert 'core' in level_0_names

        # 5. Build execution plan.
        versions = [
            PackageVersion(
                name='core',
                old_version='1.0.0',
                new_version='1.1.0',
                bump='minor',
            ),
            PackageVersion(
                name='plugin-a',
                old_version='1.0.0',
                new_version='1.0.1',
                bump='patch',
            ),
            PackageVersion(
                name='plugin-b',
                old_version='1.0.0',
                new_version='1.0.0',
                bump='',
                skipped=True,
                reason='no changes',
            ),
        ]
        plan = build_plan(versions, levels)
        assert len(plan.entries) == 3

        included = [e for e in plan.entries if e.status == PlanStatus.INCLUDED]
        skipped = [e for e in plan.entries if e.status == PlanStatus.SKIPPED]
        assert len(included) == 2
        assert len(skipped) == 1
        assert skipped[0].name == 'plugin-b'

        # 6. Format table (smoke test — no crash).
        table = plan.format_table()
        assert 'core' in table
        assert 'plugin-a' in table

    def test_graph_formats_all_produce_output(self, tmp_path: Path) -> None:
        """All graph formatters produce non-empty output from real packages."""
        ws = tmp_path / 'ws'
        ws.mkdir()
        _write_root_pyproject(
            ws,
            members='"packages/*"',
            sources={'a': '{workspace = true}', 'b': '{workspace = true}'},
        )
        _write_package(ws, 'packages/a', 'a', '1.0.0')
        _write_package(ws, 'packages/b', 'b', '1.0.0', internal_deps='"a"')

        packages = discover_packages(ws)
        graph = build_graph(packages)

        for fmt_name in ('table', 'json', 'csv', 'dot', 'mermaid', 'd2', 'levels', 'ascii'):
            output = format_graph(graph, packages, fmt=fmt_name)
            assert output, f'{fmt_name} format produced empty output'
            assert len(output) > 10, f'{fmt_name} format too short: {output!r}'


class TestBumpPinRestorePipeline:
    """End-to-end: bump version, pin deps, restore original."""

    def test_bump_then_pin_then_restore(self, tmp_path: Path) -> None:
        """Bump pyproject version, pin internal deps, then restore."""
        ws = tmp_path / 'ws'
        ws.mkdir()

        # Create core package.
        core_dir = ws / 'packages' / 'core'
        core_dir.mkdir(parents=True)
        core_pyproject = core_dir / 'pyproject.toml'
        core_pyproject.write_text(
            '[project]\nname = "core"\nversion = "1.0.0"\ndependencies = []\n',
            encoding='utf-8',
        )

        # Create plugin that depends on core.
        plugin_dir = ws / 'plugins' / 'plugin-a'
        plugin_dir.mkdir(parents=True)
        plugin_pyproject = plugin_dir / 'pyproject.toml'
        plugin_original = (
            '[project]\nname = "plugin-a"\nversion = "1.0.0"\ndependencies = [\n    "core",\n    "httpx>=0.24",\n]\n'
        )
        plugin_pyproject.write_text(plugin_original, encoding='utf-8')

        # 1. Bump core version.
        old_version = bump_pyproject(core_pyproject, '1.1.0')
        assert old_version == '1.0.0'
        assert '1.1.0' in core_pyproject.read_text(encoding='utf-8')

        # 2. Pin plugin deps to new core version.
        version_map = {'core': '1.1.0'}
        pin_dependencies(plugin_pyproject, version_map)
        pinned = plugin_pyproject.read_text(encoding='utf-8')
        assert 'core==1.1.0' in pinned
        assert 'httpx' in pinned  # External dep untouched.

        # 3. Ephemeral pin round-trip — restore original.
        plugin_pyproject.write_text(plugin_original, encoding='utf-8')
        with ephemeral_pin(plugin_pyproject, version_map):
            during = plugin_pyproject.read_text(encoding='utf-8')
            assert 'core==1.1.0' in during

        after = plugin_pyproject.read_text(encoding='utf-8')
        assert after == plugin_original

    def test_bump_multiple_packages_consistent(self, tmp_path: Path) -> None:
        """Bumping multiple packages keeps versions consistent."""
        ws = tmp_path / 'ws'
        ws.mkdir()

        pyprojects: list[Path] = []
        for name in ('alpha', 'beta', 'gamma'):
            pkg_dir = ws / 'packages' / name
            pkg_dir.mkdir(parents=True)
            pp = pkg_dir / 'pyproject.toml'
            pp.write_text(
                f'[project]\nname = "{name}"\nversion = "0.5.0"\ndependencies = []\n',
                encoding='utf-8',
            )
            pyprojects.append(pp)

        # Bump all to 0.6.0.
        for pp in pyprojects:
            bump_pyproject(pp, '0.6.0')

        # Verify all have the new version.
        for pp in pyprojects:
            content = pp.read_text(encoding='utf-8')
            assert 'version = "0.6.0"' in content


class TestStateSaveLoadResumePipeline:
    """End-to-end: create state, save, load, resume, verify."""

    def test_state_lifecycle(self, tmp_path: Path) -> None:
        """Full state lifecycle: init → set status → save → load → resume."""
        state_path = tmp_path / 'state.json'

        # 1. Create initial state.
        state = RunState(git_sha='abc123def456')
        state.init_package('core', version='1.0.0', level=0)
        state.init_package('plugin-a', version='1.0.0', level=1)
        state.init_package('plugin-b', version='1.0.0', level=1)

        # 2. Simulate partial publish.
        state.set_status('core', PackageStatus.PUBLISHED)
        state.set_status('plugin-a', PackageStatus.FAILED, error='timeout')

        assert not state.is_complete()
        assert state.published_packages() == ['core']
        assert state.failed_packages() == ['plugin-a']
        assert state.pending_packages() == ['plugin-b']

        # 3. Save.
        state.save(state_path)
        assert state_path.exists()

        # 4. Load and verify round-trip.
        loaded = RunState.load(state_path)
        assert loaded.git_sha == 'abc123def456'
        assert loaded.packages['core'].status == PackageStatus.PUBLISHED
        assert loaded.packages['plugin-a'].status == PackageStatus.FAILED
        assert loaded.packages['plugin-a'].error == 'timeout'
        assert loaded.packages['plugin-b'].status == PackageStatus.PENDING

        # 5. Resume: complete remaining packages.
        loaded.set_status('plugin-a', PackageStatus.PUBLISHED)
        loaded.set_status('plugin-b', PackageStatus.PUBLISHED)
        assert loaded.is_complete()

        # 6. Save again and verify.
        loaded.save(state_path)
        final = RunState.load(state_path)
        assert final.is_complete()
        assert len(final.published_packages()) == 3

    def test_state_sha_validation(self, tmp_path: Path) -> None:
        """State SHA validation catches mismatches on resume."""
        state_path = tmp_path / 'state.json'

        state = RunState(git_sha='sha_from_first_run')
        state.init_package('core', version='1.0.0')
        state.save(state_path)

        loaded = RunState.load(state_path)
        loaded.validate_sha('sha_from_first_run')  # Should not raise.

        with pytest.raises(ReleaseKitError):
            loaded.validate_sha('different_sha')


class TestManifestSBOMPipeline:
    """End-to-end: create manifest, save, load, generate SBOM."""

    def test_manifest_round_trip_then_sbom(self, tmp_path: Path) -> None:
        """Manifest save → load → SBOM generation pipeline."""
        manifest_path = tmp_path / 'manifest.json'

        # 1. Create manifest.
        manifest = ReleaseManifest(
            git_sha='abc123',
            umbrella_tag='v1.0.0',
            packages=[
                PackageVersion(
                    name='core',
                    old_version='0.9.0',
                    new_version='1.0.0',
                    bump='major',
                    tag='core-v1.0.0',
                ),
                PackageVersion(
                    name='plugin-a',
                    old_version='0.9.0',
                    new_version='1.0.0',
                    bump='major',
                    tag='plugin-a-v1.0.0',
                ),
            ],
            created_at='2026-01-15T10:00:00Z',
        )

        # 2. Save and reload.
        manifest.save(manifest_path)
        loaded = ReleaseManifest.load(manifest_path)
        assert loaded.git_sha == 'abc123'
        assert len(loaded.packages) == 2
        assert loaded.bumped == loaded.packages  # None skipped.

        # 3. Generate CycloneDX SBOM from manifest.
        cdx_str = generate_sbom(loaded, fmt=SBOMFormat.CYCLONEDX)
        cdx = json.loads(cdx_str)
        assert cdx['bomFormat'] == 'CycloneDX'
        assert len(cdx['components']) == 2
        comp_names = {c['name'] for c in cdx['components']}
        assert comp_names == {'core', 'plugin-a'}

        # 4. Generate SPDX SBOM from manifest.
        spdx_str = generate_sbom(loaded, fmt=SBOMFormat.SPDX)
        spdx = json.loads(spdx_str)
        assert spdx['spdxVersion'] == 'SPDX-2.3'
        assert len(spdx['packages']) == 2

        # 5. Write SBOM files to output directory.
        sbom_dir = tmp_path / 'sbom_out'
        cdx_path = write_sbom(loaded, sbom_dir, fmt=SBOMFormat.CYCLONEDX)
        spdx_path = write_sbom(loaded, sbom_dir, fmt=SBOMFormat.SPDX)
        assert cdx_path.exists()
        assert spdx_path.exists()

        # Verify written files are valid JSON.
        cdx_data = json.loads(cdx_path.read_text(encoding='utf-8'))
        assert cdx_data['bomFormat'] == 'CycloneDX'
        spdx_data = json.loads(spdx_path.read_text(encoding='utf-8'))
        assert spdx_data['spdxVersion'] == 'SPDX-2.3'

    def test_manifest_with_skipped_packages(self, tmp_path: Path) -> None:
        """Manifest correctly separates bumped and skipped packages."""
        manifest = ReleaseManifest(
            git_sha='def456',
            packages=[
                PackageVersion(
                    name='core',
                    old_version='1.0.0',
                    new_version='1.1.0',
                    bump='minor',
                ),
                PackageVersion(
                    name='plugin-a',
                    old_version='1.0.0',
                    new_version='1.0.0',
                    bump='',
                    skipped=True,
                ),
            ],
        )
        assert len(manifest.bumped) == 1
        assert len(manifest.skipped) == 1
        assert manifest.bumped[0].name == 'core'
        assert manifest.skipped[0].name == 'plugin-a'

        # SBOM includes all packages from the manifest.
        cdx = json.loads(generate_sbom(manifest, fmt=SBOMFormat.CYCLONEDX))
        assert len(cdx['components']) == 2
        comp_names = {c['name'] for c in cdx['components']}
        assert comp_names == {'core', 'plugin-a'}


class TestInitScaffoldConfigLoadPipeline:
    """End-to-end: scaffold config, then load it back."""

    def test_scaffold_then_load(self, tmp_path: Path) -> None:
        """scaffold_config → load_config round-trip."""
        ws = tmp_path / 'ws'
        ws.mkdir()
        _write_root_pyproject(ws, members='"packages/*"')
        _write_package(ws, 'packages/mylib', 'mylib', '1.0.0')

        # 1. Scaffold.
        toml_content = scaffold_config(ws)
        assert toml_content
        assert (ws / CONFIG_FILENAME).exists()

        # 2. Load back.
        config = load_config(ws)
        assert config.workspaces
        # Should have at least one workspace.
        ws_config = next(iter(config.workspaces.values()))
        assert ws_config.ecosystem == 'python'
        assert ws_config.tag_format  # Non-empty.

    def test_generate_config_then_load(self, tmp_path: Path) -> None:
        """generate_config_toml → write → load_config round-trip."""
        groups = {
            'core': ['mylib'],
            'plugins': ['mylib-plugin-*'],
        }
        toml_content = generate_config_toml(
            groups,
            workspace_label='py',
            ecosystem='python',
            exclude=['sample-*'],
        )

        config_path = tmp_path / CONFIG_FILENAME
        config_path.write_text(toml_content, encoding='utf-8')

        config = load_config(tmp_path)
        assert 'py' in config.workspaces
        ws_config = config.workspaces['py']
        assert ws_config.ecosystem == 'python'
        assert ws_config.groups == groups
        assert ws_config.exclude == ['sample-*']


class TestLockAcquireReleasePipeline:
    """End-to-end: acquire lock, verify exclusion, release."""

    def test_lock_lifecycle(self, tmp_path: Path) -> None:
        """Acquire → verify file exists → release → verify removed."""
        lock_path_expected = tmp_path / LOCK_FILENAME

        # 1. Acquire.
        lock_path = acquire_lock(tmp_path)
        assert lock_path.exists()
        assert lock_path == lock_path_expected

        # Verify lock file is valid JSON with expected fields.
        lock_data = json.loads(lock_path.read_text(encoding='utf-8'))
        assert 'pid' in lock_data
        assert 'hostname' in lock_data
        assert 'timestamp' in lock_data

        # 2. Release.
        release_lock_file(lock_path)
        assert not lock_path.exists()

    def test_lock_prevents_double_acquire(self, tmp_path: Path) -> None:
        """Second acquire on same directory raises ReleaseKitError."""
        lock_path = acquire_lock(tmp_path)
        try:
            with pytest.raises(ReleaseKitError):
                acquire_lock(tmp_path)
        finally:
            release_lock_file(lock_path)


class TestTagFormattingPipeline:
    """End-to-end: format tags from manifest data."""

    def test_format_tags_from_manifest(self) -> None:
        """Tag formatting produces correct tags for manifest packages."""
        manifest = ReleaseManifest(
            git_sha='abc',
            umbrella_tag='v1.0.0',
            packages=[
                PackageVersion(
                    name='core',
                    old_version='0.9.0',
                    new_version='1.0.0',
                    bump='major',
                ),
                PackageVersion(
                    name='plugin-a',
                    old_version='0.9.0',
                    new_version='1.0.0',
                    bump='major',
                ),
            ],
        )

        tag_fmt = '{name}-v{version}'
        umbrella_fmt = 'v{version}'

        for pkg in manifest.bumped:
            tag = format_tag(tag_fmt, name=pkg.name, version=pkg.new_version)
            assert tag == f'{pkg.name}-v{pkg.new_version}'

        umbrella = format_tag(
            umbrella_fmt,
            version=manifest.bumped[0].new_version,
        )
        assert umbrella == 'v1.0.0'

    def test_tag_result_ok_property(self) -> None:
        """TagResult.ok is True when no failures."""
        result = TagResult(
            created=['core-v1.0.0', 'plugin-a-v1.0.0'],
            skipped=[],
            pushed=True,
            release_url='https://github.com/org/repo/releases/tag/v1.0.0',
        )
        assert result.ok
        assert result.pushed
        assert len(result.created) == 2

    def test_tag_result_not_ok_on_failure(self) -> None:
        """TagResult.ok is False when there are failures."""
        result = TagResult(
            created=['core-v1.0.0'],
            failed={'plugin-a-v1.0.0': 'tag already exists'},
        )
        assert not result.ok


class TestCycleDetectionPipeline:
    """End-to-end: discover packages with cycles, detect them."""

    def test_circular_deps_detected(self, tmp_path: Path) -> None:
        """Circular dependencies are detected from real workspace."""
        ws = tmp_path / 'ws'
        ws.mkdir()
        _write_root_pyproject(
            ws,
            members='"packages/*"',
            sources={'a': '{workspace = true}', 'b': '{workspace = true}'},
        )
        _write_package(
            ws,
            'packages/a',
            'a',
            '1.0.0',
            internal_deps='"b"',
        )
        _write_package(
            ws,
            'packages/b',
            'b',
            '1.0.0',
            internal_deps='"a"',
        )

        packages = discover_packages(ws)
        graph = build_graph(packages)
        cycles = detect_cycles(graph)
        assert len(cycles) > 0

    def test_diamond_deps_no_cycle(self, tmp_path: Path) -> None:
        """Diamond dependency pattern (A→B, A→C, B→D, C→D) has no cycles."""
        ws = tmp_path / 'ws'
        ws.mkdir()
        _write_root_pyproject(
            ws,
            members='"packages/*"',
            sources={
                'a': '{workspace = true}',
                'b': '{workspace = true}',
                'c': '{workspace = true}',
                'd': '{workspace = true}',
            },
        )
        _write_package(ws, 'packages/d', 'd', '1.0.0')
        _write_package(ws, 'packages/b', 'b', '1.0.0', internal_deps='"d"')
        _write_package(ws, 'packages/c', 'c', '1.0.0', internal_deps='"d"')
        _write_package(
            ws,
            'packages/a',
            'a',
            '1.0.0',
            internal_deps='"b", "c"',
        )

        packages = discover_packages(ws)
        graph = build_graph(packages)
        cycles = detect_cycles(graph)
        assert cycles == []

        # Topo sort should have d at level 0, b/c at level 1, a at level 2.
        levels = topo_sort(graph)
        assert len(levels) == 3
        level_0 = {p.name for p in levels[0]}
        assert 'd' in level_0


class TestConfigValidationPipeline:
    """End-to-end: config loading with validation errors."""

    def test_unknown_key_raises(self, tmp_path: Path) -> None:
        """Unknown top-level key in releasekit.toml raises error."""
        _write_releasekit_toml(
            tmp_path, ('forge = "github"\nunknwon_key = "oops"\n\n[workspace.py]\necosystem = "python"\n')
        )
        with pytest.raises(ReleaseKitError):
            load_config(tmp_path)

    def test_invalid_ecosystem_raises(self, tmp_path: Path) -> None:
        """Invalid ecosystem value raises error."""
        _write_releasekit_toml(tmp_path, ('forge = "github"\n\n[workspace.py]\necosystem = "cobol"\n'))
        with pytest.raises(ReleaseKitError):
            load_config(tmp_path)

    def test_valid_multi_workspace_config(self, tmp_path: Path) -> None:
        """Multi-workspace config loads correctly."""
        _write_releasekit_toml(
            tmp_path,
            (
                'forge = "github"\n'
                'repo_owner = "org"\n'
                'repo_name = "repo"\n'
                '\n'
                '[workspace.py]\n'
                'ecosystem = "python"\n'
                'root = "py"\n'
                'tag_format = "{name}-v{version}"\n'
                '\n'
                '[workspace.js]\n'
                'ecosystem = "js"\n'
                'root = "js"\n'
                'tag_format = "{name}@{version}"\n'
            ),
        )
        config = load_config(tmp_path)
        assert len(config.workspaces) == 2
        assert config.workspaces['py'].ecosystem == 'python'
        assert config.workspaces['js'].ecosystem == 'js'
        assert config.forge == 'github'
        assert config.repo_owner == 'org'


class TestEphemeralPinCrashSafety:
    """End-to-end: ephemeral pin restores even on exceptions."""

    def test_nested_pins_independent_restore(self, tmp_path: Path) -> None:
        """Two files pinned in nested contexts restore independently."""
        core_dir = tmp_path / 'core'
        core_dir.mkdir()
        plugin_dir = tmp_path / 'plugin'
        plugin_dir.mkdir()

        core_pp = core_dir / 'pyproject.toml'
        plugin_pp = plugin_dir / 'pyproject.toml'

        core_original = '[project]\nname = "core"\nversion = "1.0.0"\ndependencies = ["shared"]\n'
        plugin_original = '[project]\nname = "plugin"\nversion = "1.0.0"\ndependencies = ["core", "shared"]\n'
        core_pp.write_text(core_original, encoding='utf-8')
        plugin_pp.write_text(plugin_original, encoding='utf-8')

        version_map = {'shared': '2.0.0', 'core': '1.1.0'}

        with ephemeral_pin(core_pp, version_map):
            assert 'shared==2.0.0' in core_pp.read_text(encoding='utf-8')

            with ephemeral_pin(plugin_pp, version_map):
                plugin_pinned = plugin_pp.read_text(encoding='utf-8')
                assert 'core==1.1.0' in plugin_pinned
                assert 'shared==2.0.0' in plugin_pinned

            # Plugin restored, core still pinned.
            assert plugin_pp.read_text(encoding='utf-8') == plugin_original
            assert 'shared==2.0.0' in core_pp.read_text(encoding='utf-8')

        # Both restored.
        assert core_pp.read_text(encoding='utf-8') == core_original
        assert plugin_pp.read_text(encoding='utf-8') == plugin_original

    def test_pin_restores_on_exception(self, tmp_path: Path) -> None:
        """File is restored even when an exception occurs mid-pin."""
        pp = tmp_path / 'pyproject.toml'
        original = '[project]\nname = "x"\nversion = "1.0.0"\ndependencies = ["core"]\n'
        pp.write_text(original, encoding='utf-8')

        try:
            with ephemeral_pin(pp, {'core': '2.0.0'}):
                assert 'core==2.0.0' in pp.read_text(encoding='utf-8')
                raise RuntimeError('Simulated build failure')
        except RuntimeError:
            pass

        assert pp.read_text(encoding='utf-8') == original


class TestWorkspaceDiscoveryVariants:
    """End-to-end: discover packages with various workspace layouts."""

    def test_nested_workspace_members(self, tmp_path: Path) -> None:
        """Nested glob patterns discover packages correctly."""
        ws = tmp_path / 'ws'
        ws.mkdir()
        _write_root_pyproject(
            ws,
            members='"packages/*", "plugins/*"',
            sources={
                'core': '{workspace = true}',
                'auth': '{workspace = true}',
            },
        )
        _write_package(ws, 'packages/core', 'core', '1.0.0')
        _write_package(ws, 'plugins/auth', 'auth', '1.0.0', internal_deps='"core"')

        packages = discover_packages(ws)
        assert len(packages) == 2

        graph = build_graph(packages)
        assert 'core' in graph.edges['auth']

    def test_exclude_patterns(self, tmp_path: Path) -> None:
        """Exclude patterns filter out matching packages."""
        ws = tmp_path / 'ws'
        ws.mkdir()
        (ws / 'pyproject.toml').write_text(
            '[project]\nname = "workspace"\n\n'
            '[tool.uv.workspace]\n'
            'members = ["packages/*"]\n'
            'exclude = ["packages/internal"]\n',
            encoding='utf-8',
        )
        _write_package(ws, 'packages/public', 'public', '1.0.0')
        _write_package(ws, 'packages/internal', 'internal', '1.0.0')

        packages = discover_packages(ws)
        names = {p.name for p in packages}
        assert 'public' in names
        assert 'internal' not in names

    def test_private_package_not_publishable(self, tmp_path: Path) -> None:
        """Private classifier marks package as non-publishable."""
        ws = tmp_path / 'ws'
        ws.mkdir()
        _write_root_pyproject(ws, members='"packages/*"')
        pkg_dir = ws / 'packages' / 'internal'
        pkg_dir.mkdir(parents=True)
        (pkg_dir / 'pyproject.toml').write_text(
            '[project]\nname = "internal"\nversion = "0.1.0"\n'
            'dependencies = []\n'
            'classifiers = ["Private :: Do Not Upload"]\n',
            encoding='utf-8',
        )

        packages = discover_packages(ws)
        assert len(packages) == 1
        assert packages[0].is_publishable is False


class TestPlanStateConsistency:
    """End-to-end: plan and state track the same packages."""

    def test_plan_and_state_agree(self, tmp_path: Path) -> None:
        """Execution plan and run state track identical package sets."""
        ws = tmp_path / 'ws'
        ws.mkdir()
        _write_root_pyproject(
            ws,
            members='"packages/*"',
            sources={'a': '{workspace = true}', 'b': '{workspace = true}'},
        )
        _write_package(ws, 'packages/a', 'a', '1.0.0')
        _write_package(ws, 'packages/b', 'b', '1.0.0', internal_deps='"a"')

        packages = discover_packages(ws)
        graph = build_graph(packages)
        levels = topo_sort(graph)

        versions = [
            PackageVersion(name='a', old_version='1.0.0', new_version='1.1.0', bump='minor'),
            PackageVersion(name='b', old_version='1.0.0', new_version='1.0.1', bump='patch'),
        ]

        # Build plan.
        plan = build_plan(versions, levels)
        plan_names = {e.name for e in plan.entries}

        # Build state.
        state = RunState(git_sha='abc')
        for v in versions:
            state.init_package(v.name, version=v.new_version)
        state_names = set(state.packages.keys())

        assert plan_names == state_names

        # Simulate publish.
        for v in versions:
            state.set_status(v.name, PackageStatus.PUBLISHED)
        assert state.is_complete()

        # Save and reload.
        state_path = tmp_path / 'state.json'
        state.save(state_path)
        loaded = RunState.load(state_path)
        assert loaded.is_complete()
