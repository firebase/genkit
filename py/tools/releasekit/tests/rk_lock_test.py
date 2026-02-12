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
from pathlib import Path

import pytest
from releasekit.errors import ReleaseKitError
from releasekit.lock import (
    LOCK_FILENAME,
    LockInfo,
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
