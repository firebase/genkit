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

"""Advisory lock file to prevent concurrent release runs.

Writes a ``.releasekit.lock`` file containing PID, hostname, and
timestamp. If a lock file already exists from a different process, the
acquisition fails. Stale locks (older than ``stale_timeout``) are
automatically removed.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                               │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Advisory lock       │ A file that says "I'm working here, don't     │
    │                     │ touch!" Like a sign on a door.                │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Stale detection     │ If the sign has been there too long and the   │
    │                     │ person is gone, we take it down.              │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ atexit cleanup      │ Remove the sign when we leave, even if we     │
    │                     │ forget to do it manually.                     │
    └─────────────────────┴────────────────────────────────────────────────┘

Usage::

    from releasekit.lock import release_lock

    with release_lock(Path('.')) as lock_path:
        # Lock is held; safe to publish
        ...
    # Lock is released automatically

    # Or manually:
    from releasekit.lock import acquire_lock, release_lock_file

    lock_path = acquire_lock(Path('.'))
    try:
        ...
    finally:
        release_lock_file(lock_path)
"""

from __future__ import annotations

import atexit
import json
import os
import socket
import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path

from releasekit.errors import E, ReleaseKitError
from releasekit.logging import get_logger

logger = get_logger(__name__)

LOCK_FILENAME = '.releasekit.lock'

# Default stale timeout: 30 minutes.
DEFAULT_STALE_TIMEOUT: float = 1800.0


@dataclass(frozen=True)
class LockInfo:
    """Metadata stored in the lock file.

    Attributes:
        pid: Process ID that holds the lock.
        hostname: Machine hostname.
        timestamp: Unix timestamp when the lock was acquired.
        user: Username of the lock holder.
    """

    pid: int
    hostname: str
    timestamp: float
    user: str = ''


def _read_lock(lock_path: Path) -> LockInfo | None:
    """Read and parse an existing lock file, returning None if absent/corrupt."""
    if not lock_path.exists():
        return None

    try:
        text = lock_path.read_text(encoding='utf-8')
        data = json.loads(text)
        return LockInfo(
            pid=int(data['pid']),
            hostname=str(data['hostname']),
            timestamp=float(data['timestamp']),
            user=str(data.get('user', '')),
        )
    except (OSError, json.JSONDecodeError, KeyError, ValueError, TypeError):
        logger.warning('lock_file_corrupt', path=str(lock_path))
        return None


def _is_process_alive(pid: int) -> bool:
    """Return True if a process with the given PID exists on this host."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but we lack permission to signal it.
        return True
    return True


def _is_stale(info: LockInfo, stale_timeout: float) -> bool:
    """Return True if the lock is stale (too old or process is dead)."""
    # Lock file stores wall-clock time for cross-machine comparison.
    wall_age = time.time() - info.timestamp
    if wall_age > stale_timeout:
        return True

    # On the same host, check if the process is still alive.
    if info.hostname == socket.gethostname() and not _is_process_alive(info.pid):
        return True

    return False


def acquire_lock(
    workspace_root: Path,
    *,
    stale_timeout: float = DEFAULT_STALE_TIMEOUT,
) -> Path:
    """Acquire an advisory release lock.

    Args:
        workspace_root: Directory to place the lock file in.
        stale_timeout: Seconds after which a lock is considered stale.

    Returns:
        Path to the lock file.

    Raises:
        ReleaseKitError: If the lock is already held by another process.
    """
    lock_path = workspace_root / LOCK_FILENAME
    existing = _read_lock(lock_path)

    if existing is not None:
        if _is_stale(existing, stale_timeout):
            logger.warning(
                'stale_lock_removed',
                path=str(lock_path),
                pid=existing.pid,
                hostname=existing.hostname,
            )
            lock_path.unlink(missing_ok=True)
        else:
            raise ReleaseKitError(
                E.LOCK_ACQUISITION_FAILED,
                f'Release lock held by PID {existing.pid} on {existing.hostname} (user={existing.user!r}).',
                hint=(f"If the process is no longer running, delete '{lock_path}' manually."),
            )
    elif lock_path.exists():
        # File exists but _read_lock returned None → corrupt lock file.
        # Remove it so the atomic O_CREAT|O_EXCL open below can succeed.
        logger.warning('corrupt_lock_removed', path=str(lock_path))
        lock_path.unlink(missing_ok=True)

    info = LockInfo(
        pid=os.getpid(),
        hostname=socket.gethostname(),
        timestamp=time.time(),
        user=os.environ.get('USER', os.environ.get('USERNAME', '')),
    )

    # Use O_CREAT | O_EXCL for atomic creation — prevents TOCTOU race
    # where two processes both see "no lock" and both try to create one.
    # Write to a temp file first, then atomically rename to avoid
    # partial reads by concurrent processes.
    content = json.dumps(asdict(info), indent=2) + '\n'
    try:
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError:
        # Another process created the lock between our stale check and
        # our open(). Re-read and report the conflict.
        rival = _read_lock(lock_path)
        rival_pid = rival.pid if rival else '?'
        rival_host = rival.hostname if rival else '?'
        raise ReleaseKitError(
            E.LOCK_ACQUISITION_FAILED,
            f'Release lock held by PID {rival_pid} on {rival_host}.',
            hint=f"If the process is no longer running, delete '{lock_path}' manually.",
        ) from None
    except OSError as exc:
        raise ReleaseKitError(
            E.LOCK_ACQUISITION_FAILED,
            f'Failed to write lock file: {exc}',
            hint='Check file permissions on the .releasekit-lock file and its parent directory.',
        ) from exc
    try:
        os.write(fd, content.encode('utf-8'))
    except BaseException:
        os.close(fd)
        lock_path.unlink(missing_ok=True)
        raise
    os.close(fd)

    logger.info('lock_acquired', path=str(lock_path), pid=info.pid)

    # Register atexit cleanup so the lock is released even on unhandled
    # exceptions.
    atexit.register(_atexit_cleanup, lock_path, info.pid)

    return lock_path


def release_lock_file(lock_path: Path) -> None:
    """Release the lock by removing the lock file.

    Safe to call multiple times. Only removes the lock if it was acquired
    by the current process (prevents removing another process's lock).

    Args:
        lock_path: Path to the lock file to remove.
    """
    existing = _read_lock(lock_path)
    if existing is not None and existing.pid != os.getpid():
        logger.warning(
            'lock_owned_by_other',
            path=str(lock_path),
            owner_pid=existing.pid,
            current_pid=os.getpid(),
        )
        return

    lock_path.unlink(missing_ok=True)
    logger.info('lock_released', path=str(lock_path))


def _atexit_cleanup(lock_path: Path, owner_pid: int) -> None:
    """Atexit handler that removes the lock if we still own it."""
    if os.getpid() != owner_pid:
        return
    lock_path.unlink(missing_ok=True)


@contextmanager
def release_lock(
    workspace_root: Path,
    *,
    stale_timeout: float = DEFAULT_STALE_TIMEOUT,
) -> Generator[Path]:
    """Context manager that acquires and releases the release lock.

    Args:
        workspace_root: Directory to place the lock file in.
        stale_timeout: Seconds after which a lock is considered stale.

    Yields:
        Path to the lock file.

    Raises:
        ReleaseKitError: If the lock cannot be acquired.
    """
    lock_path = acquire_lock(workspace_root, stale_timeout=stale_timeout)
    try:
        yield lock_path
    finally:
        release_lock_file(lock_path)


__all__ = [
    'LOCK_FILENAME',
    'LockInfo',
    'acquire_lock',
    'release_lock',
    'release_lock_file',
]
