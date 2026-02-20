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

"""Tests for uv.lock parser and transitive dependency resolution."""

from __future__ import annotations

from pathlib import Path

from releasekit.checks._lockfile import (
    LockEntry,
    LockGraph,
    all_transitive_external_deps,
    parse_uv_lock,
    transitive_deps,
)

# ── Fixtures ─────────────────────────────────────────────────────────

_MINIMAL_LOCK = """\
version = 1

[[package]]
name = "my-app"
version = "1.0.0"
source = { editable = "." }
dependencies = [
    { name = "requests" },
    { name = "my-lib" },
]

[[package]]
name = "my-lib"
version = "0.5.0"
source = { editable = "packages/my-lib" }
dependencies = [
    { name = "pydantic" },
]

[[package]]
name = "requests"
version = "2.31.0"
source = { registry = "https://pypi.org/simple" }
dependencies = [
    { name = "urllib3" },
    { name = "certifi" },
    { name = "charset-normalizer" },
    { name = "idna" },
]

[[package]]
name = "pydantic"
version = "2.6.0"
source = { registry = "https://pypi.org/simple" }
dependencies = [
    { name = "pydantic-core" },
    { name = "typing-extensions" },
    { name = "annotated-types" },
]

[[package]]
name = "pydantic-core"
version = "2.16.0"
source = { registry = "https://pypi.org/simple" }
dependencies = [
    { name = "typing-extensions" },
]

[[package]]
name = "typing-extensions"
version = "4.9.0"
source = { registry = "https://pypi.org/simple" }

[[package]]
name = "annotated-types"
version = "0.6.0"
source = { registry = "https://pypi.org/simple" }

[[package]]
name = "urllib3"
version = "2.1.0"
source = { registry = "https://pypi.org/simple" }

[[package]]
name = "certifi"
version = "2024.2.2"
source = { registry = "https://pypi.org/simple" }

[[package]]
name = "charset-normalizer"
version = "3.3.2"
source = { registry = "https://pypi.org/simple" }

[[package]]
name = "idna"
version = "3.6"
source = { registry = "https://pypi.org/simple" }
"""


def _write_lock(tmp_path: Path, content: str = _MINIMAL_LOCK) -> Path:
    """Write a uv.lock file and return its path."""
    lock_path = tmp_path / 'uv.lock'
    lock_path.write_text(content, encoding='utf-8')
    return lock_path


def _make_graph() -> LockGraph:
    """Build a LockGraph manually for unit tests without file I/O."""
    graph = LockGraph()
    graph.entries['my-app'] = LockEntry(
        name='my-app',
        version='1.0.0',
        deps=('my-lib', 'requests'),
        is_workspace=True,
    )
    graph.entries['my-lib'] = LockEntry(
        name='my-lib',
        version='0.5.0',
        deps=('pydantic',),
        is_workspace=True,
    )
    graph.entries['requests'] = LockEntry(
        name='requests',
        version='2.31.0',
        deps=('certifi', 'charset-normalizer', 'idna', 'urllib3'),
    )
    graph.entries['pydantic'] = LockEntry(
        name='pydantic',
        version='2.6.0',
        deps=('annotated-types', 'pydantic-core', 'typing-extensions'),
    )
    graph.entries['pydantic-core'] = LockEntry(
        name='pydantic-core',
        version='2.16.0',
        deps=('typing-extensions',),
    )
    graph.entries['typing-extensions'] = LockEntry(
        name='typing-extensions',
        version='4.9.0',
        deps=(),
    )
    graph.entries['annotated-types'] = LockEntry(
        name='annotated-types',
        version='0.6.0',
        deps=(),
    )
    graph.entries['urllib3'] = LockEntry(
        name='urllib3',
        version='2.1.0',
        deps=(),
    )
    graph.entries['certifi'] = LockEntry(
        name='certifi',
        version='2024.2.2',
        deps=(),
    )
    graph.entries['charset-normalizer'] = LockEntry(
        name='charset-normalizer',
        version='3.3.2',
        deps=(),
    )
    graph.entries['idna'] = LockEntry(
        name='idna',
        version='3.6',
        deps=(),
    )
    graph.workspace_members = {'my-app', 'my-lib'}
    return graph


# ── parse_uv_lock ────────────────────────────────────────────────────


class TestParseUvLock:
    """Tests for parse_uv_lock."""

    def test_parse_minimal(self, tmp_path: Path) -> None:
        """Parse a minimal uv.lock file."""
        lock_path = _write_lock(tmp_path)
        graph = parse_uv_lock(lock_path)
        assert len(graph.entries) == 11
        assert graph.workspace_members == {'my-app', 'my-lib'}

    def test_workspace_members_detected(self, tmp_path: Path) -> None:
        """Workspace members have is_workspace=True."""
        lock_path = _write_lock(tmp_path)
        graph = parse_uv_lock(lock_path)
        assert graph.entries['my-app'].is_workspace is True
        assert graph.entries['my-lib'].is_workspace is True
        assert graph.entries['requests'].is_workspace is False

    def test_deps_parsed(self, tmp_path: Path) -> None:
        """Dependencies are correctly parsed."""
        lock_path = _write_lock(tmp_path)
        graph = parse_uv_lock(lock_path)
        assert 'requests' in graph.entries['my-app'].deps
        assert 'my-lib' in graph.entries['my-app'].deps
        assert 'pydantic' in graph.entries['my-lib'].deps

    def test_external_deps_parsed(self, tmp_path: Path) -> None:
        """External package deps are parsed."""
        lock_path = _write_lock(tmp_path)
        graph = parse_uv_lock(lock_path)
        req = graph.entries['requests']
        assert set(req.deps) == {'urllib3', 'certifi', 'charset-normalizer', 'idna'}

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        """Missing lockfile returns empty graph."""
        graph = parse_uv_lock(tmp_path / 'nonexistent.lock')
        assert len(graph.entries) == 0

    def test_invalid_toml_returns_empty(self, tmp_path: Path) -> None:
        """Invalid TOML returns empty graph."""
        bad = tmp_path / 'uv.lock'
        bad.write_text('this is not valid toml [[[', encoding='utf-8')
        graph = parse_uv_lock(bad)
        assert len(graph.entries) == 0

    def test_empty_lock_returns_empty(self, tmp_path: Path) -> None:
        """Empty lockfile returns empty graph."""
        lock_path = tmp_path / 'uv.lock'
        lock_path.write_text('version = 1\n', encoding='utf-8')
        graph = parse_uv_lock(lock_path)
        assert len(graph.entries) == 0

    def test_version_preserved(self, tmp_path: Path) -> None:
        """Version strings are preserved."""
        lock_path = _write_lock(tmp_path)
        graph = parse_uv_lock(lock_path)
        assert graph.entries['requests'].version == '2.31.0'
        assert graph.entries['pydantic'].version == '2.6.0'

    def test_name_normalized(self, tmp_path: Path) -> None:
        """Package names are normalized (underscores → hyphens, lowercase)."""
        lock_content = """\
version = 1

[[package]]
name = "My_Package"
version = "1.0.0"
source = { registry = "https://pypi.org/simple" }
"""
        lock_path = tmp_path / 'uv.lock'
        lock_path.write_text(lock_content, encoding='utf-8')
        graph = parse_uv_lock(lock_path)
        assert 'my-package' in graph.entries


# ── transitive_deps ──────────────────────────────────────────────────


class TestTransitiveDeps:
    """Tests for transitive_deps."""

    def test_direct_deps(self) -> None:
        """Direct deps of my-app include requests."""
        graph = _make_graph()
        deps = transitive_deps(graph, 'my-app', include_workspace=True)
        assert 'requests' in deps
        assert 'my-lib' in deps

    def test_transitive_through_requests(self) -> None:
        """my-app transitively depends on urllib3 via requests."""
        graph = _make_graph()
        deps = transitive_deps(graph, 'my-app')
        assert 'urllib3' in deps
        assert 'certifi' in deps
        assert 'idna' in deps
        assert 'charset-normalizer' in deps

    def test_transitive_through_workspace_member(self) -> None:
        """my-app transitively depends on pydantic via my-lib."""
        graph = _make_graph()
        deps = transitive_deps(graph, 'my-app')
        assert 'pydantic' in deps
        assert 'pydantic-core' in deps
        assert 'typing-extensions' in deps
        assert 'annotated-types' in deps

    def test_excludes_workspace_by_default(self) -> None:
        """Workspace members excluded from result by default."""
        graph = _make_graph()
        deps = transitive_deps(graph, 'my-app')
        assert 'my-lib' not in deps
        assert 'my-app' not in deps

    def test_include_workspace(self) -> None:
        """include_workspace=True includes workspace members."""
        graph = _make_graph()
        deps = transitive_deps(graph, 'my-app', include_workspace=True)
        assert 'my-lib' in deps

    def test_root_not_in_result(self) -> None:
        """Root package is never in its own transitive deps."""
        graph = _make_graph()
        deps = transitive_deps(graph, 'my-app', include_workspace=True)
        assert 'my-app' not in deps

    def test_unknown_root_returns_empty(self) -> None:
        """Unknown root returns empty set."""
        graph = _make_graph()
        assert transitive_deps(graph, 'nonexistent') == set()

    def test_leaf_has_no_transitive(self) -> None:
        """Leaf package has no transitive deps."""
        graph = _make_graph()
        assert transitive_deps(graph, 'typing-extensions') == set()

    def test_full_closure_count(self) -> None:
        """my-app has 9 external transitive deps."""
        graph = _make_graph()
        deps = transitive_deps(graph, 'my-app')
        # requests(1) + urllib3 + certifi + charset-normalizer + idna
        # + pydantic + pydantic-core + typing-extensions + annotated-types
        assert len(deps) == 9

    def test_my_lib_transitive(self) -> None:
        """my-lib has pydantic + pydantic-core + typing-extensions + annotated-types."""
        graph = _make_graph()
        deps = transitive_deps(graph, 'my-lib')
        assert deps == {
            'pydantic',
            'pydantic-core',
            'typing-extensions',
            'annotated-types',
        }


# ── all_transitive_external_deps ─────────────────────────────────────


class TestAllTransitiveExternalDeps:
    """Tests for all_transitive_external_deps."""

    def test_union_of_multiple_packages(self) -> None:
        """Union of transitive deps for multiple packages."""
        graph = _make_graph()
        deps = all_transitive_external_deps(graph, {'my-app', 'my-lib'})
        # my-app covers everything, so union should be same as my-app alone.
        assert deps == transitive_deps(graph, 'my-app')

    def test_single_package(self) -> None:
        """Single package returns its transitive deps."""
        graph = _make_graph()
        deps = all_transitive_external_deps(graph, {'my-lib'})
        assert deps == {
            'pydantic',
            'pydantic-core',
            'typing-extensions',
            'annotated-types',
        }

    def test_empty_set(self) -> None:
        """Empty package set returns empty deps."""
        graph = _make_graph()
        assert all_transitive_external_deps(graph, set()) == set()


# ── LockEntry ────────────────────────────────────────────────────────


class TestLockEntry:
    """Tests for LockEntry dataclass."""

    def test_frozen(self) -> None:
        """LockEntry is frozen."""
        import pytest

        entry = LockEntry(name='foo', version='1.0.0')
        with pytest.raises(AttributeError):
            entry.name = 'bar'  # type: ignore[misc]

    def test_defaults(self) -> None:
        """Default deps is empty tuple, is_workspace is False."""
        entry = LockEntry(name='foo', version='1.0.0')
        assert entry.deps == ()
        assert entry.is_workspace is False
