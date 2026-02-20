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

"""Tests for releasekit.graph module."""

from __future__ import annotations

from pathlib import Path

import pytest
from releasekit.errors import ReleaseKitError
from releasekit.graph import (
    build_graph,
    detect_cycles,
    filter_graph,
    forward_deps,
    reverse_deps,
    topo_sort,
)
from releasekit.workspace import Package


def _pkg(name: str, internal_deps: list[str] | None = None, *, tmp_path: Path | None = None) -> Package:
    """Create a minimal Package for testing."""
    base = tmp_path or Path('/dev/null').parent
    return Package(
        name=name,
        version='1.0.0',
        path=base / name,
        manifest_path=base / name / 'pyproject.toml',
        internal_deps=internal_deps or [],
    )


class TestBuildGraph:
    """build_graph creates correct forward and reverse edges."""

    def test_empty(self) -> None:
        """Empty package list produces empty graph."""
        graph = build_graph([])
        assert len(graph) == 0, f'Expected empty graph, got {len(graph)}'

    def test_single_package(self) -> None:
        """Single package has no edges."""
        graph = build_graph([_pkg('core')])
        assert graph.names == ['core'], f'Expected [core], got {graph.names}'
        assert graph.edges['core'] == [], f'Expected no edges, got {graph.edges["core"]}'

    def test_forward_edges(self) -> None:
        """Forward edges point from dependent to dependency."""
        packages = [
            _pkg('core'),
            _pkg('plugin', internal_deps=['core']),
        ]
        graph = build_graph(packages)
        assert graph.edges['plugin'] == ['core'], f'Expected plugin->core, got {graph.edges["plugin"]}'
        assert graph.edges['core'] == [], f'Expected core has no deps, got {graph.edges["core"]}'

    def test_reverse_edges(self) -> None:
        """Reverse edges point from dependency to dependent."""
        packages = [
            _pkg('core'),
            _pkg('plugin', internal_deps=['core']),
        ]
        graph = build_graph(packages)
        assert graph.reverse_edges['core'] == ['plugin'], f'Expected core<-plugin, got {graph.reverse_edges["core"]}'

    def test_diamond(self) -> None:
        """Diamond: A depends on B and C, both depend on D."""
        packages = [
            _pkg('d'),
            _pkg('b', ['d']),
            _pkg('c', ['d']),
            _pkg('a', ['b', 'c']),
        ]
        graph = build_graph(packages)
        assert graph.edges['a'] == ['b', 'c'], f'Expected a->[b,c], got {graph.edges["a"]}'
        assert sorted(graph.reverse_edges['d']) == ['b', 'c'], f'Expected d<-[b,c], got {graph.reverse_edges["d"]}'


class TestDetectCycles:
    """detect_cycles finds circular dependencies."""

    def test_acyclic(self) -> None:
        """Acyclic graph returns empty list."""
        packages = [_pkg('a'), _pkg('b', ['a'])]
        graph = build_graph(packages)
        cycles = detect_cycles(graph)
        assert not cycles, f'Expected no cycles, got {cycles}'

    def test_self_cycle(self) -> None:
        """Self-referencing package is detected as a cycle."""
        packages = [_pkg('a', ['a'])]
        graph = build_graph(packages)
        cycles = detect_cycles(graph)
        assert cycles, 'Expected cycle, got none'

    def test_triangle_cycle(self) -> None:
        """A->B->C->A cycle is detected."""
        packages = [
            _pkg('a', ['b']),
            _pkg('b', ['c']),
            _pkg('c', ['a']),
        ]
        graph = build_graph(packages)
        cycles = detect_cycles(graph)
        assert cycles, 'Expected cycle, got none'

    def test_mixed_acyclic_and_cyclic(self) -> None:
        """Only cyclic nodes appear in detected cycles."""
        packages = [
            _pkg('ok'),
            _pkg('x', ['y']),
            _pkg('y', ['x']),
        ]
        graph = build_graph(packages)
        cycles = detect_cycles(graph)
        assert cycles, 'Expected cycles, got none'
        cycle_names = {name for cycle in cycles for name in cycle}
        assert 'ok' not in cycle_names, f'ok should not be in any cycle, got {cycles}'


class TestTopoSort:
    """topo_sort produces correct level groupings."""

    def test_single_level(self) -> None:
        """Independent packages are all at level 0."""
        packages = [_pkg('a'), _pkg('b'), _pkg('c')]
        graph = build_graph(packages)
        levels = topo_sort(graph)
        assert len(levels) == 1, f'Expected 1 level, got {len(levels)}'
        names = sorted(p.name for p in levels[0])
        assert names == ['a', 'b', 'c'], f'Expected [a,b,c], got {names}'

    def test_two_levels(self) -> None:
        """Simple A->B produces two levels."""
        packages = [
            _pkg('core'),
            _pkg('plugin', ['core']),
        ]
        graph = build_graph(packages)
        levels = topo_sort(graph)
        assert len(levels) == 2, f'Expected 2 levels, got {len(levels)}'
        assert levels[0][0].name == 'core', f'Expected core at level 0, got {levels[0][0].name}'
        assert levels[1][0].name == 'plugin', f'Expected plugin at level 1, got {levels[1][0].name}'

    def test_three_levels(self) -> None:
        """Linear chain A->B->C produces three levels."""
        packages = [
            _pkg('base'),
            _pkg('mid', ['base']),
            _pkg('top', ['mid']),
        ]
        graph = build_graph(packages)
        levels = topo_sort(graph)
        assert len(levels) == 3, f'Expected 3 levels, got {len(levels)}'
        level_names = [[p.name for p in level] for level in levels]
        assert level_names == [['base'], ['mid'], ['top']], f'Expected linear chain, got {level_names}'

    def test_diamond_levels(self) -> None:
        """Diamond graph produces 3 levels with parallel middle level."""
        packages = [
            _pkg('d'),
            _pkg('b', ['d']),
            _pkg('c', ['d']),
            _pkg('a', ['b', 'c']),
        ]
        graph = build_graph(packages)
        levels = topo_sort(graph)
        assert len(levels) == 3, f'Expected 3 levels, got {len(levels)}'
        assert levels[0][0].name == 'd', f'Expected d at level 0, got {levels[0][0].name}'
        mid = sorted(p.name for p in levels[1])
        assert mid == ['b', 'c'], f'Expected [b,c] at level 1, got {mid}'
        assert levels[2][0].name == 'a', f'Expected a at level 2, got {levels[2][0].name}'

    def test_cycle_raises(self) -> None:
        """Cyclic graph raises RK-GRAPH-CYCLE-DETECTED."""
        packages = [_pkg('a', ['b']), _pkg('b', ['a'])]
        graph = build_graph(packages)
        with pytest.raises(ReleaseKitError) as exc_info:
            topo_sort(graph)
        assert 'RK-GRAPH-CYCLE-DETECTED' in str(exc_info.value), (
            f'Expected RK-GRAPH-CYCLE-DETECTED, got {exc_info.value}'
        )

    def test_genkit_like_workspace(self) -> None:
        """Simulated genkit workspace: core + many plugins = 2 levels."""
        packages = [
            _pkg('genkit'),
            _pkg('genkit-plugin-google-genai', ['genkit']),
            _pkg('genkit-plugin-vertex-ai', ['genkit']),
            _pkg('genkit-plugin-ollama', ['genkit']),
            _pkg('genkit-plugin-anthropic', ['genkit']),
        ]
        graph = build_graph(packages)
        levels = topo_sort(graph)
        assert len(levels) == 2, f'Expected 2 levels, got {len(levels)}'
        assert levels[0][0].name == 'genkit', 'Expected genkit at level 0'
        plugin_names = sorted(p.name for p in levels[1])
        assert len(plugin_names) == 4, f'Expected 4 plugins at level 1, got {len(plugin_names)}'


class TestForwardDeps:
    """forward_deps returns transitive dependencies."""

    def test_no_deps(self) -> None:
        """Package with no deps returns empty set."""
        graph = build_graph([_pkg('a')])
        assert forward_deps(graph, 'a') == set(), 'Expected empty set'

    def test_direct_dep(self) -> None:
        """Direct dependency is included."""
        graph = build_graph([_pkg('a'), _pkg('b', ['a'])])
        assert forward_deps(graph, 'b') == {'a'}, f'Expected {{a}}, got {forward_deps(graph, "b")}'

    def test_transitive_deps(self) -> None:
        """Transitive dependencies are followed."""
        graph = build_graph([
            _pkg('a'),
            _pkg('b', ['a']),
            _pkg('c', ['b']),
        ])
        assert forward_deps(graph, 'c') == {'a', 'b'}, f'Expected {{a, b}}, got {forward_deps(graph, "c")}'


class TestReverseDeps:
    """reverse_deps returns transitive dependents."""

    def test_no_dependents(self) -> None:
        """Package with no dependents returns empty set."""
        graph = build_graph([_pkg('a')])
        assert reverse_deps(graph, 'a') == set(), 'Expected empty set'

    def test_direct_dependent(self) -> None:
        """Direct dependent is included."""
        graph = build_graph([_pkg('a'), _pkg('b', ['a'])])
        assert reverse_deps(graph, 'a') == {'b'}, f'Expected {{b}}, got {reverse_deps(graph, "a")}'

    def test_transitive_dependents(self) -> None:
        """Transitive dependents are followed."""
        graph = build_graph([
            _pkg('a'),
            _pkg('b', ['a']),
            _pkg('c', ['b']),
        ])
        assert reverse_deps(graph, 'a') == {'b', 'c'}, f'Expected {{b, c}}, got {reverse_deps(graph, "a")}'


class TestFilterGraph:
    """filter_graph selects subsets with dependency inclusion."""

    def test_include_with_deps(self) -> None:
        """Including a package auto-includes its dependencies."""
        graph = build_graph([
            _pkg('core'),
            _pkg('plugin', ['core']),
            _pkg('unrelated'),
        ])
        filtered = filter_graph(graph, include_packages=['plugin'])
        assert sorted(filtered.names) == ['core', 'plugin'], f'Expected [core, plugin], got {filtered.names}'

    def test_exclude(self) -> None:
        """Exclude patterns remove matching packages."""
        graph = build_graph([
            _pkg('core'),
            _pkg('sample-demo'),
        ])
        filtered = filter_graph(graph, exclude_packages=['sample-*'])
        assert filtered.names == ['core'], f'Expected [core], got {filtered.names}'

    def test_group_filter(self) -> None:
        """Group filter selects packages matching group patterns."""
        graph = build_graph([
            _pkg('genkit'),
            _pkg('genkit-plugin-foo'),
            _pkg('sample-bar'),
        ])
        groups = {'plugins': ['genkit-plugin-*']}
        filtered = filter_graph(graph, include_groups=groups, group_name='plugins')
        assert filtered.names == ['genkit-plugin-foo'], f'Expected [genkit-plugin-foo], got {filtered.names}'

    def test_unknown_group_raises(self) -> None:
        """Unknown group name raises ReleaseKitError."""
        graph = build_graph([_pkg('core')])
        groups = {'plugins': ['genkit-plugin-*']}
        with pytest.raises(ReleaseKitError):
            filter_graph(graph, include_groups=groups, group_name='nonexistent')


class TestDependencyGraphProperties:
    """DependencyGraph dataclass properties."""

    def test_names_sorted(self) -> None:
        """Names property returns sorted package names."""
        graph = build_graph([_pkg('z'), _pkg('a'), _pkg('m')])
        assert graph.names == ['a', 'm', 'z'], f'Expected sorted names, got {graph.names}'

    def test_len(self) -> None:
        """Len() returns the number of packages."""
        graph = build_graph([_pkg('a'), _pkg('b')])
        assert len(graph) == 2, f'Expected 2, got {len(graph)}'


class TestTransitiveDepsEdgeCases:
    """Edge cases for forward_deps and reverse_deps."""

    def test_forward_deps_leaf_node(self) -> None:
        """Leaf node (no deps) returns empty set."""
        graph = build_graph([_pkg('a')])
        result = forward_deps(graph, 'a')
        assert result == set()

    def test_reverse_deps_leaf_node(self) -> None:
        """Leaf node (no dependents) returns empty set."""
        graph = build_graph([_pkg('a'), _pkg('b', internal_deps=['a'])])
        # 'b' depends on 'a', so nothing depends on 'b'.
        result = reverse_deps(graph, 'b')
        assert result == set()

    def test_forward_deps_unknown_node(self) -> None:
        """Unknown node returns empty set."""
        graph = build_graph([_pkg('a')])
        result = forward_deps(graph, 'nonexistent')
        assert result == set()

    def test_reverse_deps_unknown_node(self) -> None:
        """Unknown node returns empty set."""
        graph = build_graph([_pkg('a')])
        result = reverse_deps(graph, 'nonexistent')
        assert result == set()
