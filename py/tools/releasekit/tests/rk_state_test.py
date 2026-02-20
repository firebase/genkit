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

"""Tests for releasekit.state module."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from releasekit.errors import ReleaseKitError
from releasekit.state import (
    PackageState,
    PackageStatus,
    RunState,
)


class TestPackageStatus:
    """Tests for the PackageStatus enum."""

    def test_values(self) -> None:
        """All expected status values exist."""
        expected = {'pending', 'building', 'publishing', 'verifying', 'published', 'skipped', 'failed'}
        got = {s.value for s in PackageStatus}
        if got != expected:
            msg = f'Expected {expected}, got {got}'
            raise AssertionError(msg)

    def test_terminal_states(self) -> None:
        """Published, skipped, and failed are terminal states."""
        terminals = {PackageStatus.PUBLISHED, PackageStatus.SKIPPED, PackageStatus.FAILED}
        for status in terminals:
            if status.value not in ('published', 'skipped', 'failed'):
                msg = f'Unexpected terminal state value: {status.value}'
                raise AssertionError(msg)


class TestPackageState:
    """Tests for the PackageState dataclass."""

    def test_defaults(self) -> None:
        """Default state is PENDING with empty fields."""
        state = PackageState(name='genkit')
        if state.status != PackageStatus.PENDING:
            raise AssertionError(f'Expected PENDING, got {state.status}')
        if state.version != '':
            raise AssertionError(f'Expected empty version, got {state.version!r}')
        if state.error != '':
            raise AssertionError(f'Expected empty error, got {state.error!r}')
        if state.level != 0:
            raise AssertionError(f'Expected level 0, got {state.level}')

    def test_with_all_fields(self) -> None:
        """All fields can be set."""
        state = PackageState(
            name='genkit-plugin-foo',
            status=PackageStatus.FAILED,
            version='1.2.3',
            error='Build failed',
            level=2,
        )
        if state.name != 'genkit-plugin-foo':
            raise AssertionError(f'Wrong name: {state.name}')
        if state.status != PackageStatus.FAILED:
            raise AssertionError(f'Wrong status: {state.status}')
        if state.version != '1.2.3':
            raise AssertionError(f'Wrong version: {state.version}')
        if state.error != 'Build failed':
            raise AssertionError(f'Wrong error: {state.error}')
        if state.level != 2:
            raise AssertionError(f'Wrong level: {state.level}')


class TestRunState:
    """Tests for RunState."""

    def test_init_empty(self) -> None:
        """New RunState has no packages."""
        state = RunState(git_sha='abc123')
        if state.git_sha != 'abc123':
            raise AssertionError(f'Wrong SHA: {state.git_sha}')
        if state.packages:
            raise AssertionError('Expected empty packages')

    def test_init_package(self) -> None:
        """init_package adds a package to the state."""
        state = RunState(git_sha='abc')
        state.init_package('genkit', version='0.5.0', level=0)

        if 'genkit' not in state.packages:
            raise AssertionError('genkit not in packages')
        pkg = state.packages['genkit']
        if pkg.version != '0.5.0':
            raise AssertionError(f'Wrong version: {pkg.version}')
        if pkg.level != 0:
            raise AssertionError(f'Wrong level: {pkg.level}')
        if pkg.status != PackageStatus.PENDING:
            raise AssertionError(f'Wrong status: {pkg.status}')

    def test_set_status(self) -> None:
        """set_status updates the package status."""
        state = RunState(git_sha='abc')
        state.init_package('genkit', version='0.5.0')
        state.set_status('genkit', PackageStatus.BUILDING)

        if state.packages['genkit'].status != PackageStatus.BUILDING:
            raise AssertionError('Status not updated')

    def test_set_status_with_error(self) -> None:
        """set_status records an error message on FAILED."""
        state = RunState(git_sha='abc')
        state.init_package('genkit', version='0.5.0')
        state.set_status('genkit', PackageStatus.FAILED, error='Build broke')

        pkg = state.packages['genkit']
        if pkg.status != PackageStatus.FAILED:
            raise AssertionError('Status not FAILED')
        if pkg.error != 'Build broke':
            raise AssertionError(f'Wrong error: {pkg.error}')

    def test_pending_packages(self) -> None:
        """pending_packages returns names with PENDING status."""
        state = RunState(git_sha='a')
        state.init_package('a')
        state.init_package('b')
        state.set_status('a', PackageStatus.PUBLISHED)

        pending = state.pending_packages()
        if pending != ['b']:
            raise AssertionError(f'Expected ["b"], got {pending}')

    def test_failed_packages(self) -> None:
        """failed_packages returns names with FAILED status."""
        state = RunState(git_sha='a')
        state.init_package('a')
        state.init_package('b')
        state.set_status('b', PackageStatus.FAILED, error='oops')

        failed = state.failed_packages()
        if failed != ['b']:
            raise AssertionError(f'Expected ["b"], got {failed}')

    def test_published_packages(self) -> None:
        """published_packages returns names with PUBLISHED status."""
        state = RunState(git_sha='a')
        state.init_package('a')
        state.init_package('b')
        state.set_status('a', PackageStatus.PUBLISHED)

        published = state.published_packages()
        if published != ['a']:
            raise AssertionError(f'Expected ["a"], got {published}')

    def test_is_complete(self) -> None:
        """is_complete is True when all packages are in terminal state."""
        state = RunState(git_sha='a')
        state.init_package('a')
        state.init_package('b')

        if state.is_complete():
            raise AssertionError('Should not be complete with pending packages')

        state.set_status('a', PackageStatus.PUBLISHED)
        state.set_status('b', PackageStatus.SKIPPED)

        if not state.is_complete():
            raise AssertionError('Should be complete')

    def test_validate_sha_match(self) -> None:
        """validate_sha passes when SHAs match."""
        state = RunState(git_sha='abc123')
        state.validate_sha('abc123')  # Should not raise.

    def test_validate_sha_mismatch(self) -> None:
        """validate_sha raises on SHA mismatch."""
        state = RunState(git_sha='abc123')
        with pytest.raises(ReleaseKitError):
            state.validate_sha('def456')

    def test_save_and_load(self, tmp_path: Path) -> None:
        """Round-trip save/load preserves all data."""
        path = tmp_path / 'state.json'

        state = RunState(git_sha='abc123')
        state.init_package('genkit', version='0.5.0', level=0)
        state.init_package('genkit-plugin-x', version='0.5.0', level=1)
        state.set_status('genkit', PackageStatus.PUBLISHED)
        state.set_status('genkit-plugin-x', PackageStatus.FAILED, error='timeout')
        state.save(path)

        if not path.exists():
            raise AssertionError('State file not created')

        loaded = RunState.load(path)
        if loaded.git_sha != 'abc123':
            raise AssertionError(f'SHA mismatch: {loaded.git_sha}')
        if len(loaded.packages) != 2:
            raise AssertionError(f'Expected 2 packages, got {len(loaded.packages)}')

        genkit = loaded.packages['genkit']
        if genkit.status != PackageStatus.PUBLISHED:
            raise AssertionError(f'Wrong status: {genkit.status}')

        plugin = loaded.packages['genkit-plugin-x']
        if plugin.status != PackageStatus.FAILED:
            raise AssertionError(f'Wrong status: {plugin.status}')
        if plugin.error != 'timeout':
            raise AssertionError(f'Wrong error: {plugin.error}')

    def test_save_is_valid_json(self, tmp_path: Path) -> None:
        """Saved state file is valid JSON."""
        path = tmp_path / 'state.json'
        state = RunState(git_sha='abc')
        state.init_package('x', version='1.0.0')
        state.save(path)

        data = json.loads(path.read_text(encoding='utf-8'))
        if 'git_sha' not in data:
            raise AssertionError('Missing git_sha in JSON')
        if 'packages' not in data:
            raise AssertionError('Missing packages in JSON')

    def test_load_corrupted_json(self, tmp_path: Path) -> None:
        """Loading invalid JSON raises ReleaseKitError."""
        path = tmp_path / 'state.json'
        path.write_text('not valid json {{{', encoding='utf-8')

        with pytest.raises(ReleaseKitError):
            RunState.load(path)

    def test_set_status_auto_creates_package(self) -> None:
        """set_status creates a PackageState if the name doesn't exist yet."""
        state = RunState(git_sha='abc')
        state.set_status('new-pkg', PackageStatus.BUILDING)
        assert 'new-pkg' in state.packages
        assert state.packages['new-pkg'].status == PackageStatus.BUILDING

    def test_load_nonexistent_file(self, tmp_path: Path) -> None:
        """Loading a nonexistent file raises OSError."""
        path = tmp_path / 'does_not_exist.json'
        with pytest.raises(OSError, match='Failed to read'):
            RunState.load(path)

    def test_load_missing_git_sha(self, tmp_path: Path) -> None:
        """Loading state without git_sha raises ReleaseKitError."""
        path = tmp_path / 'state.json'
        path.write_text(json.dumps({'packages': {}}), encoding='utf-8')
        with pytest.raises(ReleaseKitError, match='missing required field'):
            RunState.load(path)

    def test_load_invalid_status_falls_back_to_pending(self, tmp_path: Path) -> None:
        """Loading state with invalid status value falls back to PENDING."""
        path = tmp_path / 'state.json'
        data = {
            'git_sha': 'abc',
            'packages': {
                'foo': {'name': 'foo', 'status': 'INVALID_STATUS', 'version': '1.0.0'},
            },
        }
        path.write_text(json.dumps(data), encoding='utf-8')
        loaded = RunState.load(path)
        assert loaded.packages['foo'].status == PackageStatus.PENDING

    def test_save_write_error_cleans_up_temp(self, tmp_path: Path) -> None:
        """Save failure cleans up temp file and re-raises."""
        state = RunState(git_sha='abc')
        state.init_package('x', version='1.0.0')

        # Make directory read-only so mkstemp succeeds but os.replace fails.
        save_dir = tmp_path / 'readonly'
        save_dir.mkdir()
        path = save_dir / 'state.json'

        # Write initial state so the file exists.
        state.save(path)

        # Now make the directory read-only to prevent os.replace.
        os.chmod(save_dir, 0o555)  # noqa: S103
        try:
            with pytest.raises(OSError):
                state.save(path)
        finally:
            os.chmod(save_dir, 0o755)  # noqa: S103
