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

"""Tests for releasekit.pin (ephemeral dependency pinning)."""

from __future__ import annotations

from pathlib import Path

from releasekit.pin import ephemeral_pin, pin_dependencies


class TestPinDependencies:
    """Tests for pin_dependencies."""

    def test_pins_internal_deps(self, tmp_path: Path) -> None:
        """Internal dependencies are pinned to exact versions."""
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text(
            '[project]\n'
            'name = "my-plugin"\n'
            'version = "0.5.0"\n'
            'dependencies = [\n'
            '    "genkit",\n'
            '    "httpx>=0.24",\n'
            ']\n',
            encoding='utf-8',
        )

        version_map = {'genkit': '0.5.0'}
        pin_dependencies(pyproject, version_map)

        content = pyproject.read_text(encoding='utf-8')
        assert 'genkit==0.5.0' in content
        # External deps should not be modified.
        assert 'httpx' in content

    def test_pins_with_underscore_names(self, tmp_path: Path) -> None:
        """Handles name normalization (underscores → hyphens)."""
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text(
            '[project]\nname = "my-app"\nversion = "1.0.0"\ndependencies = [\n    "genkit_plugin_foo",\n]\n',
            encoding='utf-8',
        )

        version_map = {'genkit-plugin-foo': '0.5.0'}
        pin_dependencies(pyproject, version_map)

        content = pyproject.read_text(encoding='utf-8')
        assert 'genkit_plugin_foo==0.5.0' in content

    def test_pins_optional_deps(self, tmp_path: Path) -> None:
        """Optional dependencies are also pinned."""
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text(
            '[project]\n'
            'name = "my-app"\n'
            'version = "1.0.0"\n'
            'dependencies = ["genkit"]\n'
            '\n'
            '[project.optional-dependencies]\n'
            'dev = ["genkit-plugin-test"]\n',
            encoding='utf-8',
        )

        version_map = {'genkit': '0.5.0', 'genkit-plugin-test': '0.5.0'}
        pin_dependencies(pyproject, version_map)

        content = pyproject.read_text(encoding='utf-8')
        assert 'genkit==0.5.0' in content
        assert 'genkit-plugin-test==0.5.0' in content

    def test_returns_original_content(self, tmp_path: Path) -> None:
        """Returns the original file content before modification."""
        pyproject = tmp_path / 'pyproject.toml'
        original = '[project]\nname = "x"\nversion = "1.0.0"\ndependencies = ["genkit"]\n'
        pyproject.write_text(original, encoding='utf-8')

        returned = pin_dependencies(pyproject, {'genkit': '0.5.0'})
        assert returned == original

    def test_no_deps_to_pin(self, tmp_path: Path) -> None:
        """No modification when version_map matches nothing."""
        pyproject = tmp_path / 'pyproject.toml'
        original = '[project]\nname = "x"\nversion = "1.0.0"\ndependencies = ["httpx"]\n'
        pyproject.write_text(original, encoding='utf-8')

        pin_dependencies(pyproject, {'genkit': '0.5.0'})

        content = pyproject.read_text(encoding='utf-8')
        assert 'httpx' in content
        assert 'genkit' not in content


class TestEphemeralPin:
    """Tests for the ephemeral_pin context manager."""

    def test_restores_on_exit(self, tmp_path: Path) -> None:
        """File is restored to original state after context exits."""
        pyproject = tmp_path / 'pyproject.toml'
        original = '[project]\nname = "x"\nversion = "1.0.0"\ndependencies = ["genkit"]\n'
        pyproject.write_text(original, encoding='utf-8')

        with ephemeral_pin(pyproject, {'genkit': '0.5.0'}):
            # During the context, deps are pinned.
            pinned = pyproject.read_text(encoding='utf-8')
            assert 'genkit==0.5.0' in pinned

        # After context, original is restored.
        restored = pyproject.read_text(encoding='utf-8')
        assert restored == original

    def test_restores_on_exception(self, tmp_path: Path) -> None:
        """File is restored even when an exception occurs."""
        pyproject = tmp_path / 'pyproject.toml'
        original = '[project]\nname = "x"\nversion = "1.0.0"\ndependencies = ["genkit"]\n'
        pyproject.write_text(original, encoding='utf-8')

        try:
            with ephemeral_pin(pyproject, {'genkit': '0.5.0'}):
                raise RuntimeError('Build failed!')
        except RuntimeError:
            pass

        restored = pyproject.read_text(encoding='utf-8')
        assert restored == original

    def test_backup_cleaned_up(self, tmp_path: Path) -> None:
        """The .bak file is removed after successful restore."""
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text(
            '[project]\nname = "x"\nversion = "1.0.0"\ndependencies = ["genkit"]\n',
            encoding='utf-8',
        )
        backup = pyproject.with_suffix('.toml.bak')

        with ephemeral_pin(pyproject, {'genkit': '0.5.0'}):
            assert backup.exists()

        assert not backup.exists()

    def test_yields_path(self, tmp_path: Path) -> None:
        """The context manager yields the pyproject path."""
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text(
            '[project]\nname = "x"\nversion = "1.0.0"\ndependencies = []\n',
            encoding='utf-8',
        )

        with ephemeral_pin(pyproject, {}) as path:
            assert path == pyproject.resolve()
