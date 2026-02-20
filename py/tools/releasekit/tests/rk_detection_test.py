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

"""Tests for multi-ecosystem detection."""

from __future__ import annotations

from pathlib import Path

import pytest
from releasekit.backends.workspace.clojure import ClojureWorkspace
from releasekit.detection import (
    Ecosystem,
    detect_ecosystems,
    find_monorepo_root,
)
from releasekit.errors import ReleaseKitError


def _create_git_repo(root: Path) -> Path:
    """Create a minimal .git directory to mark a monorepo root."""
    (root / '.git').mkdir(parents=True, exist_ok=True)
    return root


def _create_uv_workspace(directory: Path) -> Path:
    """Create a pyproject.toml with [tool.uv.workspace] at ``directory``."""
    directory.mkdir(parents=True, exist_ok=True)
    pyproject = directory / 'pyproject.toml'
    pyproject.write_text(
        '[project]\nname = "test"\nversion = "0.1.0"\n\n[tool.uv.workspace]\nmembers = ["packages/*"]\n',
        encoding='utf-8',
    )
    return directory


def _create_pnpm_workspace(directory: Path) -> Path:
    """Create a pnpm-workspace.yaml at ``directory``."""
    directory.mkdir(parents=True, exist_ok=True)
    workspace_yaml = directory / 'pnpm-workspace.yaml'
    workspace_yaml.write_text(
        'packages:\n  - "packages/*"\n',
        encoding='utf-8',
    )
    return directory


def _create_go_workspace(directory: Path) -> Path:
    """Create a go.work at ``directory``."""
    directory.mkdir(parents=True, exist_ok=True)
    go_work = directory / 'go.work'
    go_work.write_text(
        'go 1.24\n\nuse (\n\t./genkit\n)\n',
        encoding='utf-8',
    )
    return directory


def _create_dart_workspace(directory: Path) -> Path:
    """Create a melos.yaml + pubspec.yaml at ``directory``."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'melos.yaml').write_text(
        'name: workspace\n\npackages:\n  - packages/*\n',
        encoding='utf-8',
    )
    (directory / 'pubspec.yaml').write_text(
        'name: workspace\nversion: 0.0.0\n',
        encoding='utf-8',
    )
    return directory


def _create_java_workspace(directory: Path) -> Path:
    """Create a settings.gradle at ``directory``."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'settings.gradle').write_text(
        "include ':core'\n",
        encoding='utf-8',
    )
    return directory


def _create_kotlin_workspace(directory: Path) -> Path:
    """Create a Kotlin/Gradle workspace at ``directory``."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'settings.gradle.kts').write_text(
        'include(":core")\n',
        encoding='utf-8',
    )
    (directory / 'build.gradle.kts').write_text(
        'plugins {\n    kotlin("jvm") version "1.9.0"\n}\n',
        encoding='utf-8',
    )
    return directory


def _create_clojure_workspace(directory: Path) -> Path:
    """Create a Leiningen project at ``directory``."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'project.clj').write_text(
        '(defproject example "0.1.0")\n',
        encoding='utf-8',
    )
    return directory


def _create_clojure_deps_workspace(directory: Path) -> Path:
    """Create a tools.deps (deps.edn) project at ``directory``."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'deps.edn').write_text(
        '{:deps {org.clojure/clojure {:mvn/version "1.11.1"}}}\n',
        encoding='utf-8',
    )
    return directory


def _create_cargo_workspace(directory: Path) -> Path:
    """Create a Cargo.toml with [workspace] at ``directory``."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'Cargo.toml').write_text(
        '[workspace]\nmembers = ["core"]\n',
        encoding='utf-8',
    )
    return directory


class TestFindMonorepoRoot:
    """Tests for :func:`find_monorepo_root`."""

    def test_finds_git_root(self, tmp_path: Path) -> None:
        """Finds .git directory at the root."""
        _create_git_repo(tmp_path)
        result = find_monorepo_root(tmp_path)
        if result != tmp_path:
            pytest.fail(f'Expected {tmp_path}, got {result}')

    def test_finds_git_root_from_subdir(self, tmp_path: Path) -> None:
        """Walks up from a subdirectory to find .git."""
        _create_git_repo(tmp_path)
        subdir = tmp_path / 'py' / 'packages' / 'genkit'
        subdir.mkdir(parents=True)
        result = find_monorepo_root(subdir)
        if result != tmp_path:
            pytest.fail(f'Expected {tmp_path}, got {result}')

    def test_raises_when_not_found(self, tmp_path: Path) -> None:
        """Raises ReleaseKitError when no .git directory exists."""
        # Use a deeply nested path with no .git anywhere in ancestry.
        isolated = tmp_path / 'no_git_here' / 'at_all'
        isolated.mkdir(parents=True)
        with pytest.raises(ReleaseKitError, match='monorepo root'):
            find_monorepo_root(isolated)

    def test_defaults_to_cwd(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Uses CWD when no start path is provided."""
        _create_git_repo(tmp_path)
        monkeypatch.chdir(tmp_path)
        result = find_monorepo_root()
        if result != tmp_path:
            pytest.fail(f'Expected {tmp_path}, got {result}')


class TestDetectEcosystems:
    """Tests for :func:`detect_ecosystems`."""

    def test_detects_uv_at_root(self, tmp_path: Path) -> None:
        """Detects a uv workspace at the monorepo root."""
        _create_git_repo(tmp_path)
        _create_uv_workspace(tmp_path)
        result = detect_ecosystems(tmp_path)
        if len(result) != 1:
            pytest.fail(f'Expected 1 ecosystem, got {len(result)}')
        if result[0].ecosystem != Ecosystem.PYTHON:
            pytest.fail(f'Expected python, got {result[0].ecosystem}')
        if result[0].root != tmp_path.resolve():
            pytest.fail(f'Expected {tmp_path}, got {result[0].root}')
        if result[0].workspace is None:
            pytest.fail('Expected UvWorkspace, got None')

    def test_detects_uv_in_subdir(self, tmp_path: Path) -> None:
        """Detects a uv workspace in a subdirectory (py/)."""
        _create_git_repo(tmp_path)
        py_dir = tmp_path / 'py'
        _create_uv_workspace(py_dir)
        result = detect_ecosystems(tmp_path)
        if len(result) != 1:
            pytest.fail(f'Expected 1 ecosystem, got {len(result)}')
        if result[0].ecosystem != Ecosystem.PYTHON:
            pytest.fail(f'Expected python, got {result[0].ecosystem}')
        if result[0].root != py_dir.resolve():
            pytest.fail(f'Expected {py_dir}, got {result[0].root}')

    def test_detects_uv_in_python_subdir(self, tmp_path: Path) -> None:
        """Detects a uv workspace in a python/ subdirectory."""
        _create_git_repo(tmp_path)
        python_dir = tmp_path / 'python'
        _create_uv_workspace(python_dir)
        result = detect_ecosystems(tmp_path)
        if len(result) != 1:
            pytest.fail(f'Expected 1 ecosystem, got {len(result)}')
        if result[0].ecosystem != Ecosystem.PYTHON:
            pytest.fail(f'Expected python, got {result[0].ecosystem}')
        if result[0].root != python_dir.resolve():
            pytest.fail(f'Expected {python_dir}, got {result[0].root}')

    def test_detects_pnpm_in_subdir(self, tmp_path: Path) -> None:
        """Detects a pnpm workspace in a subdirectory (js/)."""
        _create_git_repo(tmp_path)
        js_dir = tmp_path / 'js'
        _create_pnpm_workspace(js_dir)
        result = detect_ecosystems(tmp_path)
        if len(result) != 1:
            pytest.fail(f'Expected 1 ecosystem, got {len(result)}')
        if result[0].ecosystem != Ecosystem.JS:
            pytest.fail(f'Expected js, got {result[0].ecosystem}')

    def test_detects_pnpm_in_typescript_subdir(self, tmp_path: Path) -> None:
        """Detects a pnpm workspace in a typescript/ subdirectory."""
        _create_git_repo(tmp_path)
        ts_dir = tmp_path / 'typescript'
        _create_pnpm_workspace(ts_dir)
        result = detect_ecosystems(tmp_path)
        if len(result) != 1:
            pytest.fail(f'Expected 1 ecosystem, got {len(result)}')
        if result[0].ecosystem != Ecosystem.JS:
            pytest.fail(f'Expected js, got {result[0].ecosystem}')

    def test_detects_go_in_subdir(self, tmp_path: Path) -> None:
        """Detects a Go workspace in a subdirectory (go/)."""
        _create_git_repo(tmp_path)
        go_dir = tmp_path / 'go'
        _create_go_workspace(go_dir)
        result = detect_ecosystems(tmp_path)
        if len(result) != 1:
            pytest.fail(f'Expected 1 ecosystem, got {len(result)}')
        if result[0].ecosystem != Ecosystem.GO:
            pytest.fail(f'Expected go, got {result[0].ecosystem}')
        # Go backend is now implemented — workspace should be instantiated.
        if result[0].workspace is None:
            pytest.fail('Expected GoWorkspace instance for Go, got None')

    def test_detects_go_in_golang_subdir(self, tmp_path: Path) -> None:
        """Detects a Go workspace in a golang/ subdirectory."""
        _create_git_repo(tmp_path)
        golang_dir = tmp_path / 'golang'
        _create_go_workspace(golang_dir)
        result = detect_ecosystems(tmp_path)
        if len(result) != 1:
            pytest.fail(f'Expected 1 ecosystem, got {len(result)}')
        if result[0].ecosystem != Ecosystem.GO:
            pytest.fail(f'Expected go, got {result[0].ecosystem}')

    def test_detects_multiple_ecosystems(self, tmp_path: Path) -> None:
        """Detects all three ecosystems in a polyglot monorepo."""
        _create_git_repo(tmp_path)
        _create_uv_workspace(tmp_path / 'py')
        _create_pnpm_workspace(tmp_path / 'js')
        _create_go_workspace(tmp_path / 'go')
        result = detect_ecosystems(tmp_path)
        if len(result) != 3:
            pytest.fail(f'Expected 3 ecosystems, got {len(result)}: {[e.ecosystem for e in result]}')
        types = {e.ecosystem for e in result}
        expected = {Ecosystem.PYTHON, Ecosystem.JS, Ecosystem.GO}
        if types != expected:
            pytest.fail(f'Expected {expected}, got {types}')

    def test_sorted_by_ecosystem_name(self, tmp_path: Path) -> None:
        """Results are sorted alphabetically by ecosystem name."""
        _create_git_repo(tmp_path)
        _create_uv_workspace(tmp_path / 'py')
        _create_pnpm_workspace(tmp_path / 'js')
        _create_go_workspace(tmp_path / 'go')
        result = detect_ecosystems(tmp_path)
        names = [e.ecosystem.value for e in result]
        if names != sorted(names):
            pytest.fail(f'Expected sorted order, got {names}')

    def test_no_ecosystems_detected(self, tmp_path: Path) -> None:
        """Returns empty list when no ecosystems are found."""
        _create_git_repo(tmp_path)
        result = detect_ecosystems(tmp_path)
        if len(result) != 0:
            pytest.fail(f'Expected 0 ecosystems, got {len(result)}')

    def test_filter_python_only(self, tmp_path: Path) -> None:
        """--ecosystem=python returns only python ecosystems."""
        _create_git_repo(tmp_path)
        _create_uv_workspace(tmp_path / 'py')
        _create_pnpm_workspace(tmp_path / 'js')
        _create_go_workspace(tmp_path / 'go')
        result = detect_ecosystems(tmp_path, ecosystem_filter=Ecosystem.PYTHON)
        if len(result) != 1:
            pytest.fail(f'Expected 1 ecosystem, got {len(result)}')
        if result[0].ecosystem != Ecosystem.PYTHON:
            pytest.fail(f'Expected python, got {result[0].ecosystem}')

    def test_filter_js_only(self, tmp_path: Path) -> None:
        """--ecosystem=js returns only JS ecosystems."""
        _create_git_repo(tmp_path)
        _create_uv_workspace(tmp_path / 'py')
        _create_pnpm_workspace(tmp_path / 'js')
        result = detect_ecosystems(tmp_path, ecosystem_filter=Ecosystem.JS)
        if len(result) != 1:
            pytest.fail(f'Expected 1 ecosystem, got {len(result)}')
        if result[0].ecosystem != Ecosystem.JS:
            pytest.fail(f'Expected js, got {result[0].ecosystem}')

    def test_filter_returns_empty_when_no_match(self, tmp_path: Path) -> None:
        """Filtering for a non-present ecosystem returns empty list."""
        _create_git_repo(tmp_path)
        _create_uv_workspace(tmp_path / 'py')
        result = detect_ecosystems(tmp_path, ecosystem_filter=Ecosystem.GO)
        if len(result) != 0:
            pytest.fail(f'Expected 0 ecosystems, got {len(result)}')

    def test_pyproject_without_uv_workspace_ignored(self, tmp_path: Path) -> None:
        """A pyproject.toml without [tool.uv.workspace] is not a uv workspace."""
        _create_git_repo(tmp_path)
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text(
            '[project]\nname = "standalone"\nversion = "1.0"\n',
            encoding='utf-8',
        )
        result = detect_ecosystems(tmp_path)
        if len(result) != 0:
            pytest.fail(f'Expected 0 ecosystems, got {len(result)}')

    def test_hidden_dirs_skipped(self, tmp_path: Path) -> None:
        """Directories starting with '.' are not scanned."""
        _create_git_repo(tmp_path)
        hidden = tmp_path / '.hidden'
        _create_uv_workspace(hidden)
        result = detect_ecosystems(tmp_path)
        if len(result) != 0:
            pytest.fail(f'Expected 0 ecosystems, got {len(result)}')

    def test_both_root_and_subdir_uv(self, tmp_path: Path) -> None:
        """Both root and subdir uv workspaces are detected."""
        _create_git_repo(tmp_path)
        _create_uv_workspace(tmp_path)
        _create_uv_workspace(tmp_path / 'py')
        result = detect_ecosystems(tmp_path)
        python_results = [e for e in result if e.ecosystem == Ecosystem.PYTHON]
        # Both should be detected — they're different workspace roots.
        if len(python_results) != 2:
            pytest.fail(f'Expected 2 python ecosystems, got {len(python_results)}')

    def test_two_ecosystems_same_root(self, tmp_path: Path) -> None:
        """Two different ecosystems at the same root are both detected."""
        _create_git_repo(tmp_path)
        _create_uv_workspace(tmp_path)
        _create_pnpm_workspace(tmp_path)
        result = detect_ecosystems(tmp_path)
        types = {e.ecosystem for e in result}
        expected = {Ecosystem.PYTHON, Ecosystem.JS}
        if types != expected:
            pytest.fail(f'Expected {expected}, got {types}')

    def test_detects_dart_in_subdir(self, tmp_path: Path) -> None:
        """Detects a Dart workspace in a subdirectory."""
        _create_git_repo(tmp_path)
        dart_dir = tmp_path / 'dart'
        _create_dart_workspace(dart_dir)
        result = detect_ecosystems(tmp_path)
        assert len(result) == 1
        assert result[0].ecosystem == Ecosystem.DART
        assert result[0].workspace is not None

    def test_detects_dart_in_flutter_subdir(self, tmp_path: Path) -> None:
        """Detects a Dart workspace in a flutter/ subdirectory."""
        _create_git_repo(tmp_path)
        flutter_dir = tmp_path / 'flutter'
        _create_dart_workspace(flutter_dir)
        result = detect_ecosystems(tmp_path)
        assert len(result) == 1
        assert result[0].ecosystem == Ecosystem.DART
        assert result[0].workspace is not None

    def test_detects_java_in_subdir(self, tmp_path: Path) -> None:
        """Detects a Java workspace in a subdirectory."""
        _create_git_repo(tmp_path)
        java_dir = tmp_path / 'java'
        _create_java_workspace(java_dir)
        result = detect_ecosystems(tmp_path)
        assert len(result) == 1
        assert result[0].ecosystem == Ecosystem.JAVA
        assert result[0].workspace is not None

    def test_detects_java_in_jvm_subdir(self, tmp_path: Path) -> None:
        """Detects a Java workspace in a jvm/ subdirectory."""
        _create_git_repo(tmp_path)
        jvm_dir = tmp_path / 'jvm'
        _create_java_workspace(jvm_dir)
        result = detect_ecosystems(tmp_path)
        assert len(result) == 1
        assert result[0].ecosystem == Ecosystem.JAVA
        assert result[0].workspace is not None

    def test_detects_rust_in_subdir(self, tmp_path: Path) -> None:
        """Detects a Rust/Cargo workspace in a subdirectory."""
        _create_git_repo(tmp_path)
        rust_dir = tmp_path / 'rust'
        _create_cargo_workspace(rust_dir)
        result = detect_ecosystems(tmp_path)
        assert len(result) == 1
        assert result[0].ecosystem == Ecosystem.RUST
        assert result[0].workspace is not None

    def test_detects_rust_in_rs_subdir(self, tmp_path: Path) -> None:
        """Detects a Rust/Cargo workspace in an rs/ subdirectory."""
        _create_git_repo(tmp_path)
        rs_dir = tmp_path / 'rs'
        _create_cargo_workspace(rs_dir)
        result = detect_ecosystems(tmp_path)
        assert len(result) == 1
        assert result[0].ecosystem == Ecosystem.RUST
        assert result[0].workspace is not None

    def test_cargo_toml_without_workspace_ignored(self, tmp_path: Path) -> None:
        """A Cargo.toml without [workspace] is not detected as Rust."""
        _create_git_repo(tmp_path)
        rust_dir = tmp_path / 'rust'
        rust_dir.mkdir(parents=True)
        (rust_dir / 'Cargo.toml').write_text(
            '[package]\nname = "standalone"\nversion = "1.0.0"\n',
            encoding='utf-8',
        )
        result = detect_ecosystems(tmp_path)
        rust_results = [e for e in result if e.ecosystem == Ecosystem.RUST]
        assert len(rust_results) == 0

    def test_filter_rust_only(self, tmp_path: Path) -> None:
        """--ecosystem=rust returns only Rust ecosystems."""
        _create_git_repo(tmp_path)
        _create_uv_workspace(tmp_path / 'py')
        _create_cargo_workspace(tmp_path / 'rust')
        result = detect_ecosystems(tmp_path, ecosystem_filter=Ecosystem.RUST)
        assert len(result) == 1
        assert result[0].ecosystem == Ecosystem.RUST

    def test_detects_kotlin_in_subdir(self, tmp_path: Path) -> None:
        """Detects a Kotlin workspace in a subdirectory."""
        _create_git_repo(tmp_path)
        kotlin_dir = tmp_path / 'kotlin'
        _create_kotlin_workspace(kotlin_dir)
        result = detect_ecosystems(tmp_path)
        assert len(result) == 1
        assert result[0].ecosystem == Ecosystem.KOTLIN
        assert result[0].workspace is not None

    def test_detects_kotlin_in_kt_subdir(self, tmp_path: Path) -> None:
        """Detects a Kotlin workspace in a kt/ subdirectory."""
        _create_git_repo(tmp_path)
        kt_dir = tmp_path / 'kt'
        _create_kotlin_workspace(kt_dir)
        result = detect_ecosystems(tmp_path)
        assert len(result) == 1
        assert result[0].ecosystem == Ecosystem.KOTLIN

    def test_kotlin_preferred_over_java(self, tmp_path: Path) -> None:
        """Kotlin DSL with kotlin plugin is detected as kotlin, not java."""
        _create_git_repo(tmp_path)
        # A Kotlin workspace also has settings.gradle.kts, which would
        # match _is_java_workspace — but kotlin should win.
        kotlin_dir = tmp_path / 'app'
        _create_kotlin_workspace(kotlin_dir)
        result = detect_ecosystems(tmp_path)
        ecosystems = {e.ecosystem for e in result}
        assert Ecosystem.KOTLIN in ecosystems
        assert Ecosystem.JAVA not in ecosystems

    def test_filter_kotlin_only(self, tmp_path: Path) -> None:
        """--ecosystem=kotlin returns only Kotlin ecosystems."""
        _create_git_repo(tmp_path)
        _create_uv_workspace(tmp_path / 'py')
        _create_kotlin_workspace(tmp_path / 'kotlin')
        result = detect_ecosystems(tmp_path, ecosystem_filter=Ecosystem.KOTLIN)
        assert len(result) == 1
        assert result[0].ecosystem == Ecosystem.KOTLIN

    def test_detects_clojure_lein_in_subdir(self, tmp_path: Path) -> None:
        """Detects a Clojure/Leiningen workspace in a subdirectory."""
        _create_git_repo(tmp_path)
        clj_dir = tmp_path / 'clojure'
        _create_clojure_workspace(clj_dir)
        result = detect_ecosystems(tmp_path)
        assert len(result) == 1
        assert result[0].ecosystem == Ecosystem.CLOJURE
        assert isinstance(result[0].workspace, ClojureWorkspace)

    def test_detects_clojure_deps_edn(self, tmp_path: Path) -> None:
        """Detects a Clojure/tools.deps workspace via deps.edn."""
        _create_git_repo(tmp_path)
        clj_dir = tmp_path / 'clj'
        _create_clojure_deps_workspace(clj_dir)
        result = detect_ecosystems(tmp_path)
        assert len(result) == 1
        assert result[0].ecosystem == Ecosystem.CLOJURE

    def test_filter_clojure_only(self, tmp_path: Path) -> None:
        """--ecosystem=clojure returns only Clojure ecosystems."""
        _create_git_repo(tmp_path)
        _create_uv_workspace(tmp_path / 'py')
        _create_clojure_workspace(tmp_path / 'clojure')
        result = detect_ecosystems(tmp_path, ecosystem_filter=Ecosystem.CLOJURE)
        assert len(result) == 1
        assert result[0].ecosystem == Ecosystem.CLOJURE

    def test_detects_all_eight_ecosystems(self, tmp_path: Path) -> None:
        """Detects all eight ecosystems in a polyglot monorepo."""
        _create_git_repo(tmp_path)
        _create_uv_workspace(tmp_path / 'py')
        _create_pnpm_workspace(tmp_path / 'js')
        _create_go_workspace(tmp_path / 'go')
        _create_dart_workspace(tmp_path / 'dart')
        _create_java_workspace(tmp_path / 'java')
        _create_kotlin_workspace(tmp_path / 'kotlin')
        _create_clojure_workspace(tmp_path / 'clojure')
        _create_cargo_workspace(tmp_path / 'rust')
        result = detect_ecosystems(tmp_path)
        types = {e.ecosystem for e in result}
        expected = {
            Ecosystem.PYTHON,
            Ecosystem.JS,
            Ecosystem.GO,
            Ecosystem.DART,
            Ecosystem.JAVA,
            Ecosystem.KOTLIN,
            Ecosystem.CLOJURE,
            Ecosystem.RUST,
        }
        assert types == expected
