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
from releasekit.detection import (
    Ecosystem,
    detect_ecosystems,
    find_monorepo_root,
)
from releasekit.errors import ReleaseKitError

# ── Helpers ──────────────────────────────────────────────────────────


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


# ── find_monorepo_root ───────────────────────────────────────────────


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


# ── detect_ecosystems ────────────────────────────────────────────────


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
        # Go backend not yet implemented.
        if result[0].workspace is not None:
            pytest.fail('Expected None workspace for Go, got an instance')

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

    # ── Filtering ────────────────────────────────────────────────────

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

    # ── Edge cases ───────────────────────────────────────────────────

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
