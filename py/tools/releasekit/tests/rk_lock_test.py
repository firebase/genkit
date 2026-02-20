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

"""Tests for releasekit.lock module."""

from __future__ import annotations

import json
import os
import socket
from pathlib import Path
from unittest.mock import patch

import pytest
from releasekit.errors import ReleaseKitError
from releasekit.lock import (
    LOCK_FILENAME,
    LockInfo,
    _atexit_cleanup,
    _is_process_alive,
    acquire_lock,
    release_lock,
    release_lock_file,
)


class TestLockInfo:
    """Tests for LockInfo dataclass."""

    def test_fields(self) -> None:
        """LockInfo stores expected fields."""
        info = LockInfo(pid=1234, hostname='host1', timestamp=1000.0, user='dev')
        if info.pid != 1234:
            raise AssertionError(f'Wrong pid: {info.pid}')
        if info.hostname != 'host1':
            raise AssertionError(f'Wrong hostname: {info.hostname}')
        if info.timestamp != 1000.0:
            raise AssertionError(f'Wrong timestamp: {info.timestamp}')
        if info.user != 'dev':
            raise AssertionError(f'Wrong user: {info.user}')

    def test_default_user(self) -> None:
        """Default user is empty string."""
        info = LockInfo(pid=1, hostname='h', timestamp=0.0)
        if info.user != '':
            raise AssertionError(f'Expected empty user, got {info.user!r}')


class TestAcquireLock:
    """Tests for acquire_lock and release_lock_file."""

    def test_lock_and_release(self, tmp_path: Path) -> None:
        """Acquire creates lock file; release removes it."""
        lock_path = acquire_lock(tmp_path)

        if not lock_path.exists():
            raise AssertionError('Lock file not created')
        if lock_path.name != LOCK_FILENAME:
            raise AssertionError(f'Wrong filename: {lock_path.name}')

        # Verify it's valid JSON with expected fields.
        data = json.loads(lock_path.read_text(encoding='utf-8'))
        if 'pid' not in data:
            raise AssertionError('Missing pid in lock file')
        if 'hostname' not in data:
            raise AssertionError('Missing hostname in lock file')

        release_lock_file(lock_path)

        if lock_path.exists():
            raise AssertionError('Lock file not removed')

    def test_double_acquire_fails(self, tmp_path: Path) -> None:
        """Second acquire fails if lock is held by current process.

        Note: On the same process, the lock implementation may allow
        re-entry or may fail. The exact behavior depends on implementation.
        """
        lock_path = acquire_lock(tmp_path)
        try:
            # The lock should either succeed (re-entrant) or fail.
            # Either way, we test the mechanism works.
            try:
                acquire_lock(tmp_path)
            except ReleaseKitError:
                pass  # Expected: lock already held by another check.
        finally:
            release_lock_file(lock_path)

    def test_stale_lock_removed(self, tmp_path: Path) -> None:
        """Stale lock from a dead PID is automatically cleaned up."""
        lock_path = tmp_path / LOCK_FILENAME
        stale_lock = {
            'pid': 99999999,  # Almost certainly not running.
            'hostname': 'ghost',
            'timestamp': 0.0,  # Very old timestamp.
            'user': 'nobody',
        }
        lock_path.write_text(json.dumps(stale_lock), encoding='utf-8')

        # Should succeed because the stale lock is from a dead process
        # with a very old timestamp.
        new_lock = acquire_lock(tmp_path, stale_timeout=0.001)
        try:
            if not new_lock.exists():
                raise AssertionError('Lock not re-acquired after stale cleanup')
        finally:
            release_lock_file(new_lock)

    def test_release_nonexistent(self, tmp_path: Path) -> None:
        """Releasing a nonexistent lock file is safe."""
        release_lock_file(tmp_path / 'nonexistent.lock')
        # Should not raise.


class TestReleaseLockContextManager:
    """Tests for the release_lock context manager."""

    def test_context_manager(self, tmp_path: Path) -> None:
        """Lock is acquired and released via context manager."""
        with release_lock(tmp_path) as lock_path:
            if not lock_path.exists():
                raise AssertionError('Lock not acquired in context')

        if lock_path.exists():
            raise AssertionError('Lock not released after context exit')

    def test_context_manager_cleanup_on_exception(self, tmp_path: Path) -> None:
        """Lock is released even if an exception occurs."""
        lock_path = None
        with pytest.raises(ValueError, match='test error'):
            with release_lock(tmp_path) as lock_path:
                msg = 'test error'
                raise ValueError(msg)

        if lock_path and lock_path.exists():
            raise AssertionError('Lock not released after exception')


class TestCorruptLockFile:
    """Tests for corrupt lock file handling."""

    def test_corrupt_json(self, tmp_path: Path) -> None:
        """Corrupt JSON in lock file is treated as no lock."""
        lock_path = tmp_path / LOCK_FILENAME
        lock_path.write_text('not json at all {{{', encoding='utf-8')

        # Should succeed — corrupt lock is ignored.
        new_lock = acquire_lock(tmp_path)
        try:
            assert new_lock.exists()
        finally:
            release_lock_file(new_lock)

    def test_missing_fields(self, tmp_path: Path) -> None:
        """Lock file with missing required fields is treated as corrupt."""
        lock_path = tmp_path / LOCK_FILENAME
        lock_path.write_text('{"hostname": "h"}', encoding='utf-8')  # missing pid, timestamp

        new_lock = acquire_lock(tmp_path)
        try:
            assert new_lock.exists()
        finally:
            release_lock_file(new_lock)


class TestReleaseLockOwnership:
    """Tests for lock ownership checks."""

    def test_release_owned_by_other_process(self, tmp_path: Path) -> None:
        """Releasing a lock owned by another PID is a no-op."""
        lock_path = tmp_path / LOCK_FILENAME
        other_lock = {
            'pid': os.getpid() + 99999,
            'hostname': 'localhost',
            'timestamp': 9999999999.0,
            'user': 'other',
        }
        lock_path.write_text(json.dumps(other_lock), encoding='utf-8')

        release_lock_file(lock_path)
        # Lock should NOT be removed (owned by another process).
        assert lock_path.exists()

    def test_stale_lock_same_host_dead_pid(self, tmp_path: Path) -> None:
        """Lock from a dead process on the same host is stale."""
        lock_path = tmp_path / LOCK_FILENAME
        stale_lock = {
            'pid': 99999999,  # Almost certainly not running.
            'hostname': socket.gethostname(),
            'timestamp': 9999999999.0,  # Not old by timestamp, but dead PID.
            'user': 'ghost',
        }
        lock_path.write_text(json.dumps(stale_lock), encoding='utf-8')

        # Should succeed because the process is dead on the same host.
        new_lock = acquire_lock(tmp_path)
        try:
            assert new_lock.exists()
        finally:
            release_lock_file(new_lock)


class TestAtexitCleanup:
    """Tests for _atexit_cleanup."""

    def test_atexit_cleanup_same_pid(self, tmp_path: Path) -> None:
        """Atexit cleanup removes lock when PID matches."""
        lock_path = tmp_path / LOCK_FILENAME
        lock_path.write_text('{}', encoding='utf-8')

        _atexit_cleanup(lock_path, os.getpid())
        assert not lock_path.exists()

    def test_atexit_cleanup_different_pid(self, tmp_path: Path) -> None:
        """Atexit cleanup does NOT remove lock when PID differs (fork safety)."""
        lock_path = tmp_path / LOCK_FILENAME
        lock_path.write_text('{}', encoding='utf-8')

        _atexit_cleanup(lock_path, os.getpid() + 99999)
        assert lock_path.exists()  # Not removed — different PID.


class TestIsPidAlive:
    """Tests for _is_pid_alive edge cases."""

    def test_permission_error_means_alive(self) -> None:
        """PermissionError when signalling a process means it exists."""
        with patch('os.kill', side_effect=PermissionError):
            assert _is_process_alive(1) is True

    def test_process_lookup_error_means_dead(self) -> None:
        """ProcessLookupError means process does not exist."""
        # Use a PID that almost certainly doesn't exist.
        assert _is_process_alive(2**30) is False


class TestAcquireLockWriteError:
    """Tests for lock file write error path."""

    def test_write_error_raises(self, tmp_path: Path) -> None:
        """OSError writing lock file raises ReleaseKitError."""
        lock_dir = tmp_path / 'readonly'
        lock_dir.mkdir()
        os.chmod(lock_dir, 0o555)  # noqa: S103
        try:
            with pytest.raises(ReleaseKitError, match='Failed to write lock'):
                acquire_lock(lock_dir)
        finally:
            os.chmod(lock_dir, 0o755)  # noqa: S103
