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

import hashlib
import os
import signal
from pathlib import Path

import pytest
from releasekit.errors import ReleaseKitError
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

    def test_empty_version_map_no_change(self, tmp_path: Path) -> None:
        """Empty version map pins nothing but still restores cleanly."""
        pyproject = tmp_path / 'pyproject.toml'
        original = '[project]\nname = "x"\nversion = "1.0.0"\ndependencies = ["genkit"]\n'
        pyproject.write_text(original, encoding='utf-8')

        with ephemeral_pin(pyproject, {}):
            content = pyproject.read_text(encoding='utf-8')
            if 'genkit==' in content:
                raise AssertionError('Nothing should be pinned with empty map')

        restored = pyproject.read_text(encoding='utf-8')
        if restored != original:
            raise AssertionError(f'File not restored:\n{restored}')

    def test_multiple_deps_pinned_and_restored(self, tmp_path: Path) -> None:
        """Multiple internal deps are pinned and all restored."""
        pyproject = tmp_path / 'pyproject.toml'
        original = (
            '[project]\n'
            'name = "my-app"\n'
            'version = "1.0.0"\n'
            'dependencies = [\n'
            '    "genkit",\n'
            '    "genkit-plugin-google-genai",\n'
            '    "httpx>=0.24",\n'
            ']\n'
        )
        pyproject.write_text(original, encoding='utf-8')

        version_map = {'genkit': '0.6.0', 'genkit-plugin-google-genai': '0.6.0'}

        with ephemeral_pin(pyproject, version_map):
            pinned = pyproject.read_text(encoding='utf-8')
            if 'genkit==0.6.0' not in pinned:
                raise AssertionError(f'genkit not pinned:\n{pinned}')
            if 'genkit-plugin-google-genai==0.6.0' not in pinned:
                raise AssertionError(f'plugin not pinned:\n{pinned}')
            if 'httpx==0.6.0' in pinned:
                raise AssertionError('External dep should not be pinned')

        restored = pyproject.read_text(encoding='utf-8')
        if restored != original:
            raise AssertionError(f'File not restored:\n{restored}')

    def test_sha256_verified_on_restore(self, tmp_path: Path) -> None:
        """Restored file has identical SHA-256 hash to original."""
        pyproject = tmp_path / 'pyproject.toml'
        original = '[project]\nname = "x"\nversion = "1.0.0"\ndependencies = ["genkit"]\n'
        pyproject.write_text(original, encoding='utf-8')
        original_hash = hashlib.sha256(original.encode('utf-8')).hexdigest()

        with ephemeral_pin(pyproject, {'genkit': '0.5.0'}):
            pass

        restored_hash = hashlib.sha256(pyproject.read_bytes()).hexdigest()
        if restored_hash != original_hash:
            raise AssertionError(f'Hash mismatch: expected {original_hash[:12]}, got {restored_hash[:12]}')

    def test_signal_handlers_restored(self, tmp_path: Path) -> None:
        """Signal handlers are restored to their original values after context."""
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text(
            '[project]\nname = "x"\nversion = "1.0.0"\ndependencies = []\n',
            encoding='utf-8',
        )

        old_sigterm = signal.getsignal(signal.SIGTERM)
        old_sigint = signal.getsignal(signal.SIGINT)

        with ephemeral_pin(pyproject, {}):
            pass

        if signal.getsignal(signal.SIGTERM) != old_sigterm:
            raise AssertionError('SIGTERM handler not restored')
        if signal.getsignal(signal.SIGINT) != old_sigint:
            raise AssertionError('SIGINT handler not restored')

    def test_nested_pins_restore_independently(self, tmp_path: Path) -> None:
        """Two pyproject files pinned in nested contexts restore independently."""
        pyproject_a = tmp_path / 'a' / 'pyproject.toml'
        pyproject_b = tmp_path / 'b' / 'pyproject.toml'
        pyproject_a.parent.mkdir()
        pyproject_b.parent.mkdir()

        original_a = '[project]\nname = "a"\nversion = "1.0.0"\ndependencies = ["genkit"]\n'
        original_b = '[project]\nname = "b"\nversion = "1.0.0"\ndependencies = ["genkit"]\n'
        pyproject_a.write_text(original_a, encoding='utf-8')
        pyproject_b.write_text(original_b, encoding='utf-8')

        with ephemeral_pin(pyproject_a, {'genkit': '0.5.0'}):
            with ephemeral_pin(pyproject_b, {'genkit': '0.6.0'}):
                pinned_a = pyproject_a.read_text(encoding='utf-8')
                pinned_b = pyproject_b.read_text(encoding='utf-8')
                if 'genkit==0.5.0' not in pinned_a:
                    raise AssertionError(f'a not pinned:\n{pinned_a}')
                if 'genkit==0.6.0' not in pinned_b:
                    raise AssertionError(f'b not pinned:\n{pinned_b}')

            # b should be restored, a still pinned.
            if pyproject_b.read_text(encoding='utf-8') != original_b:
                raise AssertionError('b not restored after inner context')
            if 'genkit==0.5.0' not in pyproject_a.read_text(encoding='utf-8'):
                raise AssertionError('a should still be pinned')

        # Both restored.
        if pyproject_a.read_text(encoding='utf-8') != original_a:
            raise AssertionError('a not restored after outer context')

    def test_backup_not_left_on_exception(self, tmp_path: Path) -> None:
        """Backup file is cleaned up even when exception occurs."""
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text(
            '[project]\nname = "x"\nversion = "1.0.0"\ndependencies = ["genkit"]\n',
            encoding='utf-8',
        )
        backup = pyproject.with_suffix('.toml.bak')

        try:
            with ephemeral_pin(pyproject, {'genkit': '0.5.0'}):
                if not backup.exists():
                    raise AssertionError('Backup should exist during context')
                raise ValueError('Simulated build failure')
        except ValueError:
            pass

        if backup.exists():
            raise AssertionError('Backup should be cleaned up after exception')


class TestPinDependenciesErrors:
    """Tests for pin_dependencies error handling."""

    def test_read_error(self, tmp_path: Path) -> None:
        """Raises ReleaseKitError when file cannot be read."""
        nonexistent = tmp_path / 'nonexistent' / 'pyproject.toml'
        with pytest.raises(ReleaseKitError, match='Cannot read'):
            pin_dependencies(nonexistent, {'genkit': '0.5.0'})

    def test_parse_error(self, tmp_path: Path) -> None:
        """Raises ReleaseKitError when TOML is invalid."""
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text('not valid toml {{{{', encoding='utf-8')
        with pytest.raises(ReleaseKitError, match='Cannot parse'):
            pin_dependencies(pyproject, {'genkit': '0.5.0'})

    def test_malformed_dep_specifier_fallback(self, tmp_path: Path) -> None:
        """Malformed dep specifier uses regex fallback for name extraction."""
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text(
            '[project]\nname = "x"\nversion = "1.0.0"\ndependencies = [\n    "genkit [extra",\n]\n',
            encoding='utf-8',
        )
        # Should not crash — fallback extracts "genkit " → "genkit"
        pin_dependencies(pyproject, {'genkit': '0.5.0'})
        content = pyproject.read_text(encoding='utf-8')
        assert '0.5.0' in content

    def test_optional_deps_non_list_skipped(self, tmp_path: Path) -> None:
        """Non-list optional-dependencies values are skipped."""
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text(
            '[project]\nname = "x"\nversion = "1.0.0"\n'
            'dependencies = ["genkit"]\n'
            '\n[project.optional-dependencies]\n'
            'dev = ["genkit-plugin-test"]\n',
            encoding='utf-8',
        )
        version_map = {'genkit': '0.5.0', 'genkit-plugin-test': '0.5.0'}
        pin_dependencies(pyproject, version_map)
        content = pyproject.read_text(encoding='utf-8')
        assert 'genkit==0.5.0' in content
        assert 'genkit-plugin-test==0.5.0' in content


class TestPinDependenciesNonListOptional:
    """Tests for non-list optional-dependencies values."""

    def test_non_list_optional_deps_skipped(self, tmp_path: Path) -> None:
        """Non-list value in optional-dependencies is silently skipped."""
        pyproject = tmp_path / 'pyproject.toml'
        # Manually craft TOML where optional-dependencies has a non-list value.
        # tomlkit will parse inline tables as dicts, so we use a string value.
        pyproject.write_text(
            '[project]\n'
            'name = "x"\n'
            'version = "1.0.0"\n'
            'dependencies = ["genkit"]\n'
            '\n'
            '[project.optional-dependencies]\n'
            'dev = "not-a-list"\n',
            encoding='utf-8',
        )
        version_map = {'genkit': '0.5.0'}
        pin_dependencies(pyproject, version_map)
        content = pyproject.read_text(encoding='utf-8')
        assert 'genkit==0.5.0' in content

    def test_write_error_raises(self, tmp_path: Path) -> None:
        """Write error during pin raises ReleaseKitError."""
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text(
            '[project]\nname = "x"\nversion = "1.0.0"\ndependencies = ["genkit"]\n',
            encoding='utf-8',
        )
        # Make file read-only so write fails.
        os.chmod(pyproject, 0o444)  # noqa: S103
        try:
            with pytest.raises(ReleaseKitError, match='Cannot write'):
                pin_dependencies(pyproject, {'genkit': '0.5.0'})
        finally:
            os.chmod(pyproject, 0o644)  # noqa: S103


class TestEphemeralPinErrors:
    """Tests for ephemeral_pin error paths."""

    def test_backup_creation_error(self, tmp_path: Path) -> None:
        """Raises ReleaseKitError when backup cannot be created."""
        # Create pyproject in a subdirectory, then make the dir read-only
        # so the backup file cannot be created.
        sub = tmp_path / 'readonly'
        sub.mkdir()
        pyproject = sub / 'pyproject.toml'
        pyproject.write_text('[project]\nname = "x"\nversion = "1.0.0"\n', encoding='utf-8')

        # Remove write permission from the directory.
        os.chmod(sub, 0o555)  # noqa: S103
        try:
            with pytest.raises(ReleaseKitError, match='Cannot create backup'):
                with ephemeral_pin(pyproject, {'genkit': '0.5.0'}):
                    pass
        finally:
            os.chmod(sub, 0o755)  # noqa: S103
