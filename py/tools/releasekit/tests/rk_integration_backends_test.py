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

"""Integration tests for Go, Dart, Java, and Rust ecosystem backends.

These tests exercise real multi-module workflows end-to-end using
on-disk workspaces and the public API surface. They verify that the
new backends compose correctly at runtime — catching wiring bugs,
import errors, dataclass field mismatches, and protocol violations
that unit tests miss.

Each test class covers a distinct integration path:

- discover_packages() dispatch for each ecosystem
- detect_ecosystems() → workspace instantiation round-trip
- scaffold_config() → load_config() for new ecosystems
- Discover → Graph → Plan pipeline through new backends
- Config validation with new ecosystem values
- Workspace rewrite_version / rewrite_dependency_version round-trips
"""

from __future__ import annotations

from pathlib import Path

import pytest
from releasekit.backends.workspace import (
    CargoWorkspace,
    DartWorkspace,
    GoWorkspace,
    MavenWorkspace,
    Package,
    Workspace,
)
from releasekit.config import CONFIG_FILENAME, load_config
from releasekit.detection import Ecosystem, detect_ecosystems
from releasekit.graph import build_graph, detect_cycles, topo_sort
from releasekit.init import generate_config_toml, scaffold_multi_config
from releasekit.plan import PlanStatus, build_plan
from releasekit.versions import PackageVersion
from releasekit.workspace import discover_packages


def _git(root: Path) -> Path:
    """Create a minimal .git directory."""
    (root / '.git').mkdir(parents=True, exist_ok=True)
    return root


def _go_workspace(root: Path, modules: list[str]) -> None:
    """Create a go.work + go.mod files for a Go workspace."""
    root.mkdir(parents=True, exist_ok=True)
    use_block = '\n'.join(f'\t./{m}' for m in modules)
    (root / 'go.work').write_text(
        f'go 1.24\n\nuse (\n{use_block}\n)\n',
        encoding='utf-8',
    )


def _go_module(
    root: Path,
    subdir: str,
    module_path: str,
    requires: list[str] | None = None,
) -> Path:
    """Go module."""
    mod_dir = root / subdir
    mod_dir.mkdir(parents=True, exist_ok=True)
    req = ''
    if requires:
        req_block = '\n'.join(f'\t{r} v0.1.0' for r in requires)
        req = f'\nrequire (\n{req_block}\n)\n'
    (mod_dir / 'go.mod').write_text(
        f'module {module_path}\n\ngo 1.24\n{req}',
        encoding='utf-8',
    )
    return mod_dir


def _dart_workspace(root: Path, patterns: list[str]) -> None:
    """Create a melos.yaml + root pubspec.yaml."""
    root.mkdir(parents=True, exist_ok=True)
    items = '\n'.join(f'  - {p}' for p in patterns)
    (root / 'melos.yaml').write_text(
        f'name: workspace\n\npackages:\n{items}\n',
        encoding='utf-8',
    )
    (root / 'pubspec.yaml').write_text(
        'name: workspace\nversion: 0.0.0\npublish_to: none\n',
        encoding='utf-8',
    )


def _dart_package(
    root: Path,
    subdir: str,
    name: str,
    version: str = '1.0.0',
    deps: dict[str, str] | None = None,
) -> Path:
    """Dart package."""
    pkg_dir = root / subdir
    pkg_dir.mkdir(parents=True, exist_ok=True)
    lines = [f'name: {name}', f'version: {version}']
    if deps:
        lines.append('dependencies:')
        for d, v in deps.items():
            lines.append(f'  {d}: {v}')
    (pkg_dir / 'pubspec.yaml').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return pkg_dir


_POM = """\
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>{gid}</groupId>
    <artifactId>{aid}</artifactId>
    <version>{ver}</version>
    {extra}
</project>
"""


def _maven_workspace(root: Path, modules: list[str]) -> None:
    """Create a parent pom.xml with <modules>."""
    root.mkdir(parents=True, exist_ok=True)
    mods = '\n'.join(f'        <module>{m}</module>' for m in modules)
    (root / 'pom.xml').write_text(
        _POM.format(
            gid='com.example',
            aid='parent',
            ver='1.0.0',
            extra=f'<modules>\n{mods}\n    </modules>',
        ),
        encoding='utf-8',
    )


def _maven_module(
    root: Path,
    subdir: str,
    aid: str,
    version: str = '1.0.0',
    deps: list[str] | None = None,
) -> Path:
    """Maven module."""
    mod_dir = root / subdir
    mod_dir.mkdir(parents=True, exist_ok=True)
    dep_xml = ''
    if deps:
        entries = '\n'.join(f'        <dependency><artifactId>{d}</artifactId></dependency>' for d in deps)
        dep_xml = f'<dependencies>\n{entries}\n    </dependencies>'
    (mod_dir / 'pom.xml').write_text(
        _POM.format(gid='com.example', aid=aid, ver=version, extra=dep_xml),
        encoding='utf-8',
    )
    return mod_dir


def _gradle_workspace(root: Path, includes: list[str]) -> None:
    """Create a settings.gradle with include directives."""
    root.mkdir(parents=True, exist_ok=True)
    lines = [f"include ':{inc}'" for inc in includes]
    (root / 'settings.gradle').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def _gradle_project(root: Path, subdir: str, version: str = '1.0.0') -> Path:
    """Gradle project."""
    proj_dir = root / subdir
    proj_dir.mkdir(parents=True, exist_ok=True)
    (proj_dir / 'build.gradle').write_text(
        f"group = 'com.example'\nversion = '{version}'\n",
        encoding='utf-8',
    )
    return proj_dir


def _cargo_workspace(root: Path, members: list[str], ws_version: str | None = None) -> None:
    """Create a root Cargo.toml with [workspace]."""
    root.mkdir(parents=True, exist_ok=True)
    members_str = ', '.join(f'"{m}"' for m in members)
    ws_pkg = ''
    if ws_version:
        ws_pkg = f'\n[workspace.package]\nversion = "{ws_version}"\n'
    (root / 'Cargo.toml').write_text(
        f'[workspace]\nmembers = [{members_str}]\n{ws_pkg}',
        encoding='utf-8',
    )


def _cargo_crate(
    root: Path,
    subdir: str,
    name: str,
    version: str = '1.0.0',
    deps: dict[str, str] | None = None,
    workspace_version: bool = False,
) -> Path:
    """Cargo crate."""
    crate_dir = root / subdir
    crate_dir.mkdir(parents=True, exist_ok=True)
    ver_line = 'version.workspace = true' if workspace_version else f'version = "{version}"'
    deps_section = ''
    if deps:
        dep_lines = '\n'.join(f'{d} = "{v}"' for d, v in deps.items())
        deps_section = f'\n[dependencies]\n{dep_lines}\n'
    (crate_dir / 'Cargo.toml').write_text(
        f'[package]\nname = "{name}"\n{ver_line}\nedition = "2021"\n{deps_section}',
        encoding='utf-8',
    )
    return crate_dir


# Pipeline: discover_packages() dispatch for each ecosystem


class TestDiscoverPackagesDispatch:
    """discover_packages() correctly dispatches to each ecosystem backend."""

    def test_go_discover(self, tmp_path: Path) -> None:
        """discover_packages(ecosystem='go') finds Go modules."""
        ws = tmp_path / 'go'
        _go_workspace(ws, ['core', 'plugin'])
        _go_module(ws, 'core', 'github.com/example/go/core')
        _go_module(
            ws,
            'plugin',
            'github.com/example/go/plugin',
            requires=['github.com/example/go/core'],
        )
        pkgs = discover_packages(ws, ecosystem='go')
        assert len(pkgs) == 2
        names = {p.name for p in pkgs}
        assert 'core' in names
        assert 'plugin' in names
        # Verify internal dep wiring.
        plugin = next(p for p in pkgs if p.name == 'plugin')
        assert len(plugin.internal_deps) >= 1

    def test_dart_discover(self, tmp_path: Path) -> None:
        """discover_packages(ecosystem='dart') finds Dart packages."""
        ws = tmp_path / 'dart'
        _dart_workspace(ws, ['packages/*'])
        _dart_package(ws, 'packages/core', 'core', '2.0.0')
        _dart_package(ws, 'packages/plugin', 'plugin', '2.0.0', deps={'core': '^2.0.0'})
        pkgs = discover_packages(ws, ecosystem='dart')
        names = {p.name for p in pkgs}
        assert 'core' in names
        assert 'plugin' in names
        plugin = next(p for p in pkgs if p.name == 'plugin')
        assert 'core' in plugin.internal_deps

    def test_java_maven_discover(self, tmp_path: Path) -> None:
        """discover_packages(ecosystem='java') finds Maven modules."""
        ws = tmp_path / 'java'
        _maven_workspace(ws, ['core', 'api'])
        _maven_module(ws, 'core', 'core', '1.0.0')
        _maven_module(ws, 'api', 'api', '1.0.0', deps=['core'])
        pkgs = discover_packages(ws, ecosystem='java')
        assert len(pkgs) == 2
        api = next(p for p in pkgs if p.name == 'api')
        assert 'core' in api.internal_deps

    def test_java_gradle_discover(self, tmp_path: Path) -> None:
        """discover_packages(ecosystem='java') finds Gradle subprojects."""
        ws = tmp_path / 'java'
        _gradle_workspace(ws, ['core', 'api'])
        _gradle_project(ws, 'core', '1.0.0')
        _gradle_project(ws, 'api', '2.0.0')
        pkgs = discover_packages(ws, ecosystem='java')
        assert len(pkgs) == 2
        api = next(p for p in pkgs if p.name == 'api')
        assert api.version == '2.0.0'

    def test_rust_discover(self, tmp_path: Path) -> None:
        """discover_packages(ecosystem='rust') finds Cargo crates."""
        ws = tmp_path / 'rust'
        _cargo_workspace(ws, ['core', 'plugin'])
        _cargo_crate(ws, 'core', 'my-core', '1.0.0')
        _cargo_crate(ws, 'plugin', 'my-plugin', '1.0.0', deps={'my-core': '1.0.0'})
        pkgs = discover_packages(ws, ecosystem='rust')
        assert len(pkgs) == 2
        plugin = next(p for p in pkgs if p.name == 'my-plugin')
        assert 'my-core' in plugin.internal_deps


# Pipeline: detect_ecosystems() → workspace → discover round-trip


class TestDetectThenDiscover:
    """detect_ecosystems() returns workspace instances that can discover packages."""

    @pytest.mark.asyncio
    async def test_go_detect_then_discover(self, tmp_path: Path) -> None:
        """Go detection yields GoWorkspace that discovers modules."""
        _git(tmp_path)
        go_dir = tmp_path / 'go'
        _go_workspace(go_dir, ['core'])
        _go_module(go_dir, 'core', 'github.com/example/go/core')
        detected = detect_ecosystems(tmp_path)
        go_eco = next(e for e in detected if e.ecosystem == Ecosystem.GO)
        assert isinstance(go_eco.workspace, GoWorkspace)
        pkgs = await go_eco.workspace.discover()
        assert len(pkgs) == 1
        assert pkgs[0].name == 'core'

    @pytest.mark.asyncio
    async def test_dart_detect_then_discover(self, tmp_path: Path) -> None:
        """Dart detection yields DartWorkspace that discovers packages."""
        _git(tmp_path)
        dart_dir = tmp_path / 'dart'
        _dart_workspace(dart_dir, ['packages/*'])
        _dart_package(dart_dir, 'packages/genkit', 'genkit', '0.5.0')
        detected = detect_ecosystems(tmp_path)
        dart_eco = next(e for e in detected if e.ecosystem == Ecosystem.DART)
        assert isinstance(dart_eco.workspace, DartWorkspace)
        pkgs = await dart_eco.workspace.discover()
        # Root pubspec + genkit package.
        genkit = next(p for p in pkgs if p.name == 'genkit')
        assert genkit.version == '0.5.0'

    @pytest.mark.asyncio
    async def test_java_detect_then_discover(self, tmp_path: Path) -> None:
        """Java detection yields MavenWorkspace that discovers modules."""
        _git(tmp_path)
        java_dir = tmp_path / 'java'
        _gradle_workspace(java_dir, ['core'])
        _gradle_project(java_dir, 'core', '3.0.0')
        detected = detect_ecosystems(tmp_path)
        java_eco = next(e for e in detected if e.ecosystem == Ecosystem.JAVA)
        assert isinstance(java_eco.workspace, MavenWorkspace)
        pkgs = await java_eco.workspace.discover()
        assert len(pkgs) == 1
        assert pkgs[0].version == '3.0.0'

    @pytest.mark.asyncio
    async def test_rust_detect_then_discover(self, tmp_path: Path) -> None:
        """Rust detection yields CargoWorkspace that discovers crates."""
        _git(tmp_path)
        rust_dir = tmp_path / 'rust'
        _cargo_workspace(rust_dir, ['core'])
        _cargo_crate(rust_dir, 'core', 'my-core', '0.1.0')
        detected = detect_ecosystems(tmp_path)
        rust_eco = next(e for e in detected if e.ecosystem == Ecosystem.RUST)
        assert isinstance(rust_eco.workspace, CargoWorkspace)
        pkgs = await rust_eco.workspace.discover()
        assert len(pkgs) == 1
        assert pkgs[0].name == 'my-core'
        assert pkgs[0].version == '0.1.0'

    @pytest.mark.asyncio
    async def test_polyglot_detect_all_six(self, tmp_path: Path) -> None:
        """All six ecosystems detected and each workspace can discover."""
        _git(tmp_path)
        # Python
        py_dir = tmp_path / 'py'
        py_dir.mkdir()
        (py_dir / 'pyproject.toml').write_text(
            '[project]\nname = "ws"\n\n[tool.uv.workspace]\nmembers = ["packages/*"]\n',
        )
        pkg = py_dir / 'packages' / 'core'
        pkg.mkdir(parents=True)
        (pkg / 'pyproject.toml').write_text('[project]\nname = "core"\nversion = "1.0.0"\n')
        # JS
        js_dir = tmp_path / 'js'
        js_dir.mkdir()
        (js_dir / 'pnpm-workspace.yaml').write_text('packages:\n  - "packages/*"\n')
        # Go
        go_dir = tmp_path / 'go'
        _go_workspace(go_dir, ['core'])
        _go_module(go_dir, 'core', 'github.com/example/go/core')
        # Dart
        dart_dir = tmp_path / 'dart'
        _dart_workspace(dart_dir, ['packages/*'])
        _dart_package(dart_dir, 'packages/genkit', 'genkit')
        # Java
        java_dir = tmp_path / 'java'
        _gradle_workspace(java_dir, ['core'])
        _gradle_project(java_dir, 'core')
        # Rust
        rust_dir = tmp_path / 'rust'
        _cargo_workspace(rust_dir, ['core'])
        _cargo_crate(rust_dir, 'core', 'my-core')

        detected = detect_ecosystems(tmp_path)
        ecosystems = {e.ecosystem for e in detected}
        assert ecosystems == {
            Ecosystem.PYTHON,
            Ecosystem.JS,
            Ecosystem.GO,
            Ecosystem.DART,
            Ecosystem.JAVA,
            Ecosystem.RUST,
        }
        # All non-JS workspaces should have a workspace instance.
        for eco in detected:
            if eco.ecosystem != Ecosystem.JS:
                assert eco.workspace is not None, f'{eco.ecosystem} workspace is None'
                assert isinstance(eco.workspace, Workspace)


# Pipeline: Discover → Graph → Plan for new ecosystems


class TestGraphPlanPipelineNewEcosystems:
    """Discover → build_graph → topo_sort → build_plan for new ecosystems."""

    def test_go_graph_plan(self, tmp_path: Path) -> None:
        """Go: discover → graph → plan pipeline."""
        ws = tmp_path / 'go'
        _go_workspace(ws, ['core', 'plugin'])
        _go_module(ws, 'core', 'github.com/example/go/core')
        _go_module(
            ws,
            'plugin',
            'github.com/example/go/plugin',
            requires=['github.com/example/go/core'],
        )
        pkgs = discover_packages(ws, ecosystem='go')
        graph = build_graph(pkgs)
        assert len(graph) == 2
        cycles = detect_cycles(graph)
        assert cycles == []
        levels = topo_sort(graph)
        assert len(levels) >= 2
        level_0_names = {p.name for p in levels[0]}
        assert 'core' in level_0_names

        versions = [
            PackageVersion(name='core', old_version='1.24', new_version='1.25', bump='minor'),
            PackageVersion(name='plugin', old_version='1.24', new_version='1.24.1', bump='patch'),
        ]
        plan = build_plan(versions, levels)
        assert len(plan.entries) == 2
        included = [e for e in plan.entries if e.status == PlanStatus.INCLUDED]
        assert len(included) == 2

    def test_dart_graph_plan(self, tmp_path: Path) -> None:
        """Dart: discover → graph → plan pipeline."""
        ws = tmp_path / 'dart'
        _dart_workspace(ws, ['packages/*'])
        _dart_package(ws, 'packages/core', 'core', '1.0.0')
        _dart_package(ws, 'packages/plugin', 'plugin', '1.0.0', deps={'core': '^1.0.0'})
        pkgs = discover_packages(ws, ecosystem='dart')
        # Filter out the root workspace pubspec if present.
        pkgs = [p for p in pkgs if p.name != 'workspace']
        graph = build_graph(pkgs)
        assert len(graph) == 2
        assert 'core' in graph.edges.get('plugin', [])
        cycles = detect_cycles(graph)
        assert cycles == []

    def test_maven_graph_plan(self, tmp_path: Path) -> None:
        """Maven: discover → graph → plan pipeline."""
        ws = tmp_path / 'java'
        _maven_workspace(ws, ['core', 'api'])
        _maven_module(ws, 'core', 'core', '1.0.0')
        _maven_module(ws, 'api', 'api', '1.0.0', deps=['core'])
        pkgs = discover_packages(ws, ecosystem='java')
        graph = build_graph(pkgs)
        assert len(graph) == 2
        assert 'core' in graph.edges.get('api', [])
        cycles = detect_cycles(graph)
        assert cycles == []

    def test_cargo_graph_plan(self, tmp_path: Path) -> None:
        """Cargo: discover → graph → plan pipeline."""
        ws = tmp_path / 'rust'
        _cargo_workspace(ws, ['core', 'plugin'])
        _cargo_crate(ws, 'core', 'my-core', '1.0.0')
        _cargo_crate(ws, 'plugin', 'my-plugin', '1.0.0', deps={'my-core': '1.0.0'})
        pkgs = discover_packages(ws, ecosystem='rust')
        graph = build_graph(pkgs)
        assert len(graph) == 2
        assert 'my-core' in graph.edges.get('my-plugin', [])
        cycles = detect_cycles(graph)
        assert cycles == []
        levels = topo_sort(graph)
        assert len(levels) >= 2
        level_0_names = {p.name for p in levels[0]}
        assert 'my-core' in level_0_names


# Pipeline: scaffold_config → load_config for new ecosystems


class TestScaffoldConfigNewEcosystems:
    """scaffold_multi_config() and generate_config_toml() work for new ecosystems."""

    def test_scaffold_multi_go(self, tmp_path: Path) -> None:
        """scaffold_multi_config for Go workspace, then load it back."""
        root = tmp_path / 'repo'
        root.mkdir()
        go_dir = root / 'go'
        _go_workspace(go_dir, ['core'])
        _go_module(go_dir, 'core', 'github.com/example/go/core')
        toml_content = scaffold_multi_config(root, [('go', 'go', go_dir)])
        assert toml_content
        config = load_config(root)
        assert 'go' in config.workspaces
        assert config.workspaces['go'].ecosystem == 'go'

    def test_scaffold_multi_dart(self, tmp_path: Path) -> None:
        """scaffold_multi_config for Dart workspace, then load it back."""
        root = tmp_path / 'repo'
        root.mkdir()
        dart_dir = root / 'dart'
        _dart_workspace(dart_dir, ['packages/*'])
        _dart_package(dart_dir, 'packages/core', 'core')
        toml_content = scaffold_multi_config(root, [('dart', 'dart', dart_dir)])
        assert toml_content
        config = load_config(root)
        assert config.workspaces['dart'].ecosystem == 'dart'

    def test_scaffold_multi_java(self, tmp_path: Path) -> None:
        """scaffold_multi_config for Java workspace, then load it back."""
        root = tmp_path / 'repo'
        root.mkdir()
        java_dir = root / 'java'
        _gradle_workspace(java_dir, ['core'])
        _gradle_project(java_dir, 'core')
        toml_content = scaffold_multi_config(root, [('java', 'java', java_dir)])
        assert toml_content
        config = load_config(root)
        assert config.workspaces['java'].ecosystem == 'java'

    def test_scaffold_multi_rust(self, tmp_path: Path) -> None:
        """scaffold_multi_config for Rust workspace, then load it back."""
        root = tmp_path / 'repo'
        root.mkdir()
        rust_dir = root / 'rust'
        _cargo_workspace(rust_dir, ['core'])
        _cargo_crate(rust_dir, 'core', 'my-core')
        toml_content = scaffold_multi_config(root, [('rust', 'rust', rust_dir)])
        assert toml_content
        config = load_config(root)
        assert config.workspaces['rust'].ecosystem == 'rust'

    def test_scaffold_multi_all_ecosystems(self, tmp_path: Path) -> None:
        """scaffold_multi_config with all ecosystems produces valid config."""
        root = tmp_path / 'repo'
        root.mkdir()
        # Go
        go_dir = root / 'go'
        _go_workspace(go_dir, ['core'])
        _go_module(go_dir, 'core', 'github.com/example/go/core')
        # Dart
        dart_dir = root / 'dart'
        _dart_workspace(dart_dir, ['packages/*'])
        _dart_package(dart_dir, 'packages/core', 'core')
        # Java
        java_dir = root / 'java'
        _gradle_workspace(java_dir, ['core'])
        _gradle_project(java_dir, 'core')
        # Rust
        rust_dir = root / 'rust'
        _cargo_workspace(rust_dir, ['core'])
        _cargo_crate(rust_dir, 'core', 'my-core')

        ecosystems = [
            ('go', 'go', go_dir),
            ('dart', 'dart', dart_dir),
            ('java', 'java', java_dir),
            ('rust', 'rust', rust_dir),
        ]
        toml_content = scaffold_multi_config(root, ecosystems)
        assert toml_content
        config = load_config(root)
        assert len(config.workspaces) == 4
        eco_set = {ws.ecosystem for ws in config.workspaces.values()}
        assert eco_set == {'go', 'dart', 'java', 'rust'}

    def test_generate_config_all_ecosystems(self, tmp_path: Path) -> None:
        """generate_config_toml() accepts all six ecosystem values."""
        for eco in ('python', 'js', 'go', 'dart', 'java', 'rust'):
            toml_content = generate_config_toml(
                groups={'core': ['core-*']},
                workspace_label=eco,
                ecosystem=eco,
            )
            config_path = tmp_path / f'{eco}' / CONFIG_FILENAME
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(toml_content, encoding='utf-8')
            config = load_config(config_path.parent)
            assert config.workspaces[eco].ecosystem == eco


# Pipeline: Config validation with new ecosystem values


class TestConfigValidationNewEcosystems:
    """Config loading validates new ecosystem values correctly."""

    def test_valid_go_config(self, tmp_path: Path) -> None:
        """Go ecosystem config loads without error."""
        (tmp_path / CONFIG_FILENAME).write_text(
            'forge = "github"\n\n[workspace.go]\necosystem = "go"\nroot = "go"\n',
        )
        config = load_config(tmp_path)
        assert config.workspaces['go'].ecosystem == 'go'

    def test_valid_dart_config(self, tmp_path: Path) -> None:
        """Dart ecosystem config loads without error."""
        (tmp_path / CONFIG_FILENAME).write_text(
            'forge = "github"\n\n[workspace.dart]\necosystem = "dart"\nroot = "dart"\n',
        )
        config = load_config(tmp_path)
        assert config.workspaces['dart'].ecosystem == 'dart'

    def test_valid_java_config(self, tmp_path: Path) -> None:
        """Java ecosystem config loads without error."""
        (tmp_path / CONFIG_FILENAME).write_text(
            'forge = "github"\n\n[workspace.java]\necosystem = "java"\nroot = "java"\n',
        )
        config = load_config(tmp_path)
        assert config.workspaces['java'].ecosystem == 'java'

    def test_valid_rust_config(self, tmp_path: Path) -> None:
        """Rust ecosystem config loads without error."""
        (tmp_path / CONFIG_FILENAME).write_text(
            'forge = "github"\n\n[workspace.rust]\necosystem = "rust"\nroot = "rust"\n',
        )
        config = load_config(tmp_path)
        assert config.workspaces['rust'].ecosystem == 'rust'

    def test_multi_workspace_all_ecosystems(self, tmp_path: Path) -> None:
        """Config with all six ecosystems loads correctly."""
        (tmp_path / CONFIG_FILENAME).write_text(
            'forge = "github"\n'
            'repo_owner = "org"\n'
            'repo_name = "repo"\n'
            '\n'
            '[workspace.py]\necosystem = "python"\nroot = "py"\n\n'
            '[workspace.js]\necosystem = "js"\nroot = "js"\n\n'
            '[workspace.go]\necosystem = "go"\nroot = "go"\n\n'
            '[workspace.dart]\necosystem = "dart"\nroot = "dart"\n\n'
            '[workspace.java]\necosystem = "java"\nroot = "java"\n\n'
            '[workspace.rust]\necosystem = "rust"\nroot = "rust"\n',
        )
        config = load_config(tmp_path)
        assert len(config.workspaces) == 6
        ecosystems = {ws.ecosystem for ws in config.workspaces.values()}
        assert ecosystems == {'python', 'js', 'go', 'dart', 'java', 'rust'}


# Pipeline: Workspace rewrite_version round-trip


class TestRewriteVersionRoundTrip:
    """rewrite_version() and rewrite_dependency_version() work end-to-end."""

    @pytest.mark.asyncio
    async def test_go_rewrite_is_noop(self, tmp_path: Path) -> None:
        """Go rewrite_version is a no-op (returns Go toolchain version)."""
        ws = tmp_path / 'go'
        mod_dir = _go_module(ws, 'core', 'github.com/example/go/core')
        _go_workspace(ws, ['core'])
        go_ws = GoWorkspace(ws)
        old = await go_ws.rewrite_version(mod_dir / 'go.mod', '2.0.0')
        assert old == '1.24'

    @pytest.mark.asyncio
    async def test_dart_rewrite_version(self, tmp_path: Path) -> None:
        """Dart rewrite_version updates pubspec.yaml."""
        ws = tmp_path / 'dart'
        pkg_dir = _dart_package(ws, 'packages/core', 'core', '1.0.0')
        dart_ws = DartWorkspace(ws)
        old = await dart_ws.rewrite_version(pkg_dir / 'pubspec.yaml', '2.0.0')
        assert old == '1.0.0'
        text = (pkg_dir / 'pubspec.yaml').read_text()
        assert 'version: 2.0.0' in text

    @pytest.mark.asyncio
    async def test_maven_rewrite_pom_version(self, tmp_path: Path) -> None:
        """Maven rewrite_version updates pom.xml."""
        ws = tmp_path / 'java'
        mod_dir = _maven_module(ws, 'core', 'core', '1.0.0')
        maven_ws = MavenWorkspace(ws)
        old = await maven_ws.rewrite_version(mod_dir / 'pom.xml', '2.0.0')
        assert old == '1.0.0'
        text = (mod_dir / 'pom.xml').read_text()
        assert '<version>2.0.0</version>' in text

    @pytest.mark.asyncio
    async def test_gradle_rewrite_version(self, tmp_path: Path) -> None:
        """Gradle rewrite_version updates build.gradle."""
        ws = tmp_path / 'java'
        proj_dir = _gradle_project(ws, 'core', '1.0.0')
        maven_ws = MavenWorkspace(ws)
        old = await maven_ws.rewrite_version(proj_dir / 'build.gradle', '2.0.0')
        assert old == '1.0.0'
        text = (proj_dir / 'build.gradle').read_text()
        assert "'2.0.0'" in text

    @pytest.mark.asyncio
    async def test_cargo_rewrite_version(self, tmp_path: Path) -> None:
        """Cargo rewrite_version updates Cargo.toml."""
        ws = tmp_path / 'rust'
        _cargo_workspace(ws, ['core'])
        crate_dir = _cargo_crate(ws, 'core', 'my-core', '1.0.0')
        cargo_ws = CargoWorkspace(ws)
        old = await cargo_ws.rewrite_version(crate_dir / 'Cargo.toml', '2.0.0')
        assert old == '1.0.0'
        text = (crate_dir / 'Cargo.toml').read_text()
        assert 'version = "2.0.0"' in text

    @pytest.mark.asyncio
    async def test_cargo_workspace_inherited_version_rewrite(self, tmp_path: Path) -> None:
        """Cargo workspace-inherited version rewrites root Cargo.toml."""
        ws = tmp_path / 'rust'
        _cargo_workspace(ws, ['core'], ws_version='1.0.0')
        crate_dir = _cargo_crate(ws, 'core', 'my-core', workspace_version=True)
        cargo_ws = CargoWorkspace(ws)
        old = await cargo_ws.rewrite_version(crate_dir / 'Cargo.toml', '2.0.0')
        assert old == '1.0.0'
        root_text = (ws / 'Cargo.toml').read_text()
        assert '"2.0.0"' in root_text

    @pytest.mark.asyncio
    async def test_dart_rewrite_dependency_version(self, tmp_path: Path) -> None:
        """Dart rewrite_dependency_version updates dep constraint."""
        ws = tmp_path / 'dart'
        pkg_dir = _dart_package(ws, 'packages/plugin', 'plugin', deps={'core': '^1.0.0'})
        dart_ws = DartWorkspace(ws)
        await dart_ws.rewrite_dependency_version(pkg_dir / 'pubspec.yaml', 'core', '2.0.0')
        text = (pkg_dir / 'pubspec.yaml').read_text()
        assert '^2.0.0' in text

    @pytest.mark.asyncio
    async def test_cargo_rewrite_dependency_version(self, tmp_path: Path) -> None:
        """Cargo rewrite_dependency_version updates dep version."""
        ws = tmp_path / 'rust'
        _cargo_workspace(ws, ['app'])
        crate_dir = _cargo_crate(ws, 'app', 'my-app', deps={'serde': '1.0.0'})
        cargo_ws = CargoWorkspace(ws)
        await cargo_ws.rewrite_dependency_version(crate_dir / 'Cargo.toml', 'serde', '2.0.0')
        text = (crate_dir / 'Cargo.toml').read_text()
        assert '"2.0.0"' in text

    @pytest.mark.asyncio
    async def test_go_rewrite_dependency_version(self, tmp_path: Path) -> None:
        """Go rewrite_dependency_version updates require directive."""
        ws = tmp_path / 'go'
        mod_dir = _go_module(
            ws,
            'plugin',
            'github.com/example/go/plugin',
            requires=['github.com/example/go/core'],
        )
        _go_workspace(ws, ['plugin'])
        go_ws = GoWorkspace(ws)
        await go_ws.rewrite_dependency_version(
            mod_dir / 'go.mod',
            'github.com/example/go/core',
            '1.5.0',
        )
        text = (mod_dir / 'go.mod').read_text()
        assert 'v1.5.0' in text


# Pipeline: Package dataclass conformance from all backends


class TestPackageDataclassConformance:
    """Packages from all backends are valid Package dataclass instances."""

    def test_go_packages_are_frozen(self, tmp_path: Path) -> None:
        """Go packages are frozen dataclass instances."""
        ws = tmp_path / 'go'
        _go_workspace(ws, ['core'])
        _go_module(ws, 'core', 'github.com/example/go/core')
        pkgs = discover_packages(ws, ecosystem='go')
        assert len(pkgs) == 1
        assert isinstance(pkgs[0], Package)
        with pytest.raises(AttributeError):
            pkgs[0].name = 'oops'  # ty: ignore[invalid-assignment]  # pyrefly: ignore[read-only] - intentionally testing frozen dataclass

    def test_dart_packages_are_frozen(self, tmp_path: Path) -> None:
        """Dart packages are frozen dataclass instances."""
        ws = tmp_path / 'dart'
        _dart_workspace(ws, ['packages/*'])
        _dart_package(ws, 'packages/core', 'core')
        pkgs = discover_packages(ws, ecosystem='dart')
        core = next(p for p in pkgs if p.name == 'core')
        assert isinstance(core, Package)
        with pytest.raises(AttributeError):
            core.name = 'oops'  # ty: ignore[invalid-assignment]  # pyrefly: ignore[read-only] - intentionally testing frozen dataclass

    def test_maven_packages_are_frozen(self, tmp_path: Path) -> None:
        """Maven packages are frozen dataclass instances."""
        ws = tmp_path / 'java'
        _maven_workspace(ws, ['core'])
        _maven_module(ws, 'core', 'core')
        pkgs = discover_packages(ws, ecosystem='java')
        assert len(pkgs) == 1
        assert isinstance(pkgs[0], Package)
        with pytest.raises(AttributeError):
            pkgs[0].name = 'oops'  # ty: ignore[invalid-assignment]  # pyrefly: ignore[read-only] - intentionally testing frozen dataclass

    def test_cargo_packages_are_frozen(self, tmp_path: Path) -> None:
        """Cargo packages are frozen dataclass instances."""
        ws = tmp_path / 'rust'
        _cargo_workspace(ws, ['core'])
        _cargo_crate(ws, 'core', 'my-core')
        pkgs = discover_packages(ws, ecosystem='rust')
        assert len(pkgs) == 1
        assert isinstance(pkgs[0], Package)
        with pytest.raises(AttributeError):
            pkgs[0].name = 'oops'  # ty: ignore[invalid-assignment]  # pyrefly: ignore[read-only] - intentionally testing frozen dataclass


# Pipeline: Exclude patterns work through discover_packages dispatch


class TestExcludePatternsDispatch:
    """exclude_patterns work through the discover_packages dispatch layer."""

    def test_go_exclude(self, tmp_path: Path) -> None:
        """Go: exclude_patterns filters modules."""
        ws = tmp_path / 'go'
        _go_workspace(ws, ['core', 'samples'])
        _go_module(ws, 'core', 'github.com/example/go/core')
        _go_module(ws, 'samples', 'github.com/example/go/samples')
        pkgs = discover_packages(ws, ecosystem='go', exclude_patterns=['samples'])
        names = {p.name for p in pkgs}
        assert 'samples' not in names
        assert 'core' in names

    def test_dart_exclude(self, tmp_path: Path) -> None:
        """Dart: exclude_patterns filters packages."""
        ws = tmp_path / 'dart'
        _dart_workspace(ws, ['packages/*'])
        _dart_package(ws, 'packages/core', 'core')
        _dart_package(ws, 'packages/example', 'example_app')
        pkgs = discover_packages(ws, ecosystem='dart', exclude_patterns=['example_*'])
        names = {p.name for p in pkgs}
        assert 'example_app' not in names

    def test_maven_exclude(self, tmp_path: Path) -> None:
        """Maven: exclude_patterns filters modules."""
        ws = tmp_path / 'java'
        _maven_workspace(ws, ['core', 'samples'])
        _maven_module(ws, 'core', 'core')
        _maven_module(ws, 'samples', 'samples')
        pkgs = discover_packages(ws, ecosystem='java', exclude_patterns=['samples'])
        names = {p.name for p in pkgs}
        assert 'samples' not in names

    def test_cargo_exclude(self, tmp_path: Path) -> None:
        """Cargo: exclude_patterns filters crates."""
        ws = tmp_path / 'rust'
        _cargo_workspace(ws, ['core', 'examples'])
        _cargo_crate(ws, 'core', 'my-core')
        _cargo_crate(ws, 'examples', 'my-examples')
        pkgs = discover_packages(ws, ecosystem='rust', exclude_patterns=['my-examples'])
        names = {p.name for p in pkgs}
        assert 'my-examples' not in names
        assert 'my-core' in names
