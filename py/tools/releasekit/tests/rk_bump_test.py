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

"""Tests for releasekit.bump (version string rewriting)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from releasekit.bump import BumpTarget, bump_file, bump_pyproject
from releasekit.errors import ReleaseKitError


class TestBumpPyproject:
    """Tests for bump_pyproject."""

    def test_updates_version(self, tmp_path: Path) -> None:
        """Updates [project].version in pyproject.toml."""
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text(
            '[project]\nname = "mypackage"\nversion = "0.4.0"\n',
            encoding='utf-8',
        )

        old = bump_pyproject(pyproject, '0.5.0')

        assert old == '0.4.0'
        content = pyproject.read_text(encoding='utf-8')
        assert 'version = "0.5.0"' in content

    def test_preserves_comments(self, tmp_path: Path) -> None:
        """Comments in pyproject.toml are preserved after bump."""
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text(
            '# This is my project\n[project]\nname = "mypackage"\nversion = "1.0.0"  # current version\n',
            encoding='utf-8',
        )

        bump_pyproject(pyproject, '2.0.0')

        content = pyproject.read_text(encoding='utf-8')
        assert '# This is my project' in content
        assert 'version = "2.0.0"' in content

    def test_missing_version_key(self, tmp_path: Path) -> None:
        """Raises ReleaseKitError when [project].version is missing."""
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text('[project]\nname = "mypackage"\n', encoding='utf-8')

        with pytest.raises(ReleaseKitError) as exc_info:
            bump_pyproject(pyproject, '1.0.0')
        assert 'No [project].version key' in exc_info.value.info.message

    def test_missing_project_section(self, tmp_path: Path) -> None:
        """Raises ReleaseKitError when [project] section is missing."""
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text('[tool.other]\nkey = "value"\n', encoding='utf-8')

        with pytest.raises(ReleaseKitError):
            bump_pyproject(pyproject, '1.0.0')

    def test_file_not_found(self, tmp_path: Path) -> None:
        """Raises ReleaseKitError for missing file."""
        with pytest.raises(ReleaseKitError):
            bump_pyproject(tmp_path / 'nonexistent.toml', '1.0.0')

    def test_invalid_toml(self, tmp_path: Path) -> None:
        """Raises ReleaseKitError for malformed TOML."""
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text('this is not valid toml [[[', encoding='utf-8')

        with pytest.raises(ReleaseKitError):
            bump_pyproject(pyproject, '1.0.0')


class TestBumpFile:
    """Tests for bump_file."""

    def test_default_pattern(self, tmp_path: Path) -> None:
        """Updates __version__ with the default pattern."""
        init_py = tmp_path / '__init__.py'
        init_py.write_text("__version__ = '0.4.0'\n", encoding='utf-8')

        target = BumpTarget(path=init_py)
        old = bump_file(target, '0.5.0')

        assert old == '0.4.0'
        content = init_py.read_text(encoding='utf-8')
        assert "__version__ = '0.5.0'" in content

    def test_double_quotes(self, tmp_path: Path) -> None:
        """Works with double-quoted version strings."""
        init_py = tmp_path / '__init__.py'
        init_py.write_text('__version__ = "1.2.3"\n', encoding='utf-8')

        target = BumpTarget(path=init_py)
        old = bump_file(target, '2.0.0')

        assert old == '1.2.3'
        content = init_py.read_text(encoding='utf-8')
        assert '__version__ = "2.0.0"' in content

    def test_custom_pattern_one_group(self, tmp_path: Path) -> None:
        """Supports single-group custom patterns."""
        version_file = tmp_path / 'version.txt'
        version_file.write_text('VERSION=1.0.0\n', encoding='utf-8')

        target = BumpTarget(
            path=version_file,
            pattern=r'^VERSION=(\d+\.\d+\.\d+)',
        )
        old = bump_file(target, '2.0.0')

        assert old == '1.0.0'
        assert '2.0.0' in version_file.read_text(encoding='utf-8')

    def test_pattern_not_found(self, tmp_path: Path) -> None:
        """Raises ReleaseKitError when pattern doesn't match."""
        some_file = tmp_path / 'empty.py'
        some_file.write_text('# no version here\n', encoding='utf-8')

        target = BumpTarget(path=some_file)
        with pytest.raises(ReleaseKitError) as exc_info:
            bump_file(target, '1.0.0')
        assert 'not found' in exc_info.value.info.message

    def test_file_not_found(self, tmp_path: Path) -> None:
        """Raises ReleaseKitError for missing file."""
        target = BumpTarget(path=tmp_path / 'nonexistent.py')
        with pytest.raises(ReleaseKitError):
            bump_file(target, '1.0.0')

    def test_preserves_surrounding_content(self, tmp_path: Path) -> None:
        """Other file content is preserved during version bump."""
        init_py = tmp_path / '__init__.py'
        init_py.write_text(
            '"""My package."""\n\n__version__ = "1.0.0"\n\n__all__ = ["main"]\n',
            encoding='utf-8',
        )

        target = BumpTarget(path=init_py)
        bump_file(target, '2.0.0')

        content = init_py.read_text(encoding='utf-8')
        assert '"""My package."""' in content
        assert '__version__ = "2.0.0"' in content
        assert '__all__ = ["main"]' in content

    def test_write_error_raises(self, tmp_path: Path) -> None:
        """Write error in bump_file raises ReleaseKitError."""
        init_py = tmp_path / '__init__.py'
        init_py.write_text('__version__ = "1.0.0"\n', encoding='utf-8')
        target = BumpTarget(path=init_py)

        os.chmod(init_py, 0o444)  # noqa: S103
        try:
            with pytest.raises(ReleaseKitError, match='Cannot write'):
                bump_file(target, '2.0.0')
        finally:
            os.chmod(init_py, 0o644)  # noqa: S103


class TestBumpPyprojectWriteError:
    """Tests for bump_pyproject write error path."""

    def test_write_error_raises(self, tmp_path: Path) -> None:
        """Write error in bump_pyproject raises ReleaseKitError."""
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text(
            '[project]\nname = "foo"\nversion = "1.0.0"\n',
            encoding='utf-8',
        )

        os.chmod(pyproject, 0o444)  # noqa: S103
        try:
            with pytest.raises(ReleaseKitError, match='Cannot write'):
                bump_pyproject(pyproject, '2.0.0')
        finally:
            os.chmod(pyproject, 0o644)  # noqa: S103
