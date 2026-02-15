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

"""Per-package status tracking with resume support.

Tracks the publish status of each package in a JSON state file. The state
file allows interrupted releases to resume from where they left off,
skipping packages that have already been published.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                               │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ RunState            │ A checklist: ✅ genkit, ✅ plugin-foo,         │
    │                     │ ⬜ plugin-bar, ...                             │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Atomic save         │ Write to a temp file first, then rename.      │
    │                     │ If we crash mid-write, the old file is fine.  │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ SHA validation      │ Resume only works if HEAD hasn't changed.     │
    │                     │ Different HEAD = different versions possible.  │
    └─────────────────────┴────────────────────────────────────────────────┘

Status transitions::

    pending → building → publishing → verifying → published
                                                 → failed
    pending → skipped (no changes / excluded)

Usage::

    from releasekit.state import PackageStatus, RunState

    state = RunState(git_sha='abc123')
    state.set_status('genkit', PackageStatus.BUILDING)
    state.set_status('genkit', PackageStatus.PUBLISHED)
    state.save(Path('.releasekit-state.json'))

    # Resume after crash:
    loaded = RunState.load(Path('.releasekit-state.json'))
    loaded.validate_sha('abc123')  # Ensure HEAD hasn't changed
    for name in loaded.pending_packages():
        ...  # Continue from where we left off
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from releasekit.errors import E, ReleaseKitError
from releasekit.logging import get_logger

logger = get_logger(__name__)

STATE_FILENAME = '.releasekit-state.json'


class PackageStatus(str, Enum):
    """Status of a package in the publish pipeline.

    Transitions::

        pending → building → publishing → verifying → published
                                                     → failed
        pending → skipped
    """

    PENDING = 'pending'
    BUILDING = 'building'
    PUBLISHING = 'publishing'
    VERIFYING = 'verifying'
    PUBLISHED = 'published'
    SKIPPED = 'skipped'
    FAILED = 'failed'


@dataclass
class PackageState:
    """Status record for a single package.

    Attributes:
        name: Normalized package name.
        status: Current status in the pipeline.
        version: Target version being published.
        error: Error message if status is ``FAILED``.
        level: Topological level (for ordering).
    """

    name: str
    status: PackageStatus = PackageStatus.PENDING
    version: str = ''
    error: str = ''
    level: int = 0


@dataclass
class RunState:
    """Complete state of a release run.

    Tracks per-package status and supports atomic persistence for
    crash recovery.

    Attributes:
        git_sha: HEAD SHA when the run started.
        packages: Per-package status records, keyed by name.
        created_at: ISO 8601 timestamp when the state was created.
    """

    git_sha: str
    packages: dict[str, PackageState] = field(default_factory=dict)
    created_at: str = ''

    def set_status(
        self,
        name: str,
        status: PackageStatus,
        *,
        error: str = '',
    ) -> None:
        """Update the status of a package.

        Args:
            name: Package name.
            status: New status.
            error: Error message (only for FAILED status).
        """
        if name not in self.packages:
            self.packages[name] = PackageState(name=name)
        pkg = self.packages[name]
        pkg.status = status
        if error:
            pkg.error = error
        logger.debug('status_changed', package=name, status=status.value)

    def init_package(
        self,
        name: str,
        *,
        version: str = '',
        level: int = 0,
        status: PackageStatus = PackageStatus.PENDING,
    ) -> None:
        """Initialize a package in the state.

        Args:
            name: Package name.
            version: Target version.
            level: Topological level.
            status: Initial status.
        """
        self.packages[name] = PackageState(
            name=name,
            status=status,
            version=version,
            level=level,
        )

    def pending_packages(self) -> list[str]:
        """Return names of packages still pending."""
        return sorted(name for name, pkg in self.packages.items() if pkg.status == PackageStatus.PENDING)

    def failed_packages(self) -> list[str]:
        """Return names of packages that failed."""
        return sorted(name for name, pkg in self.packages.items() if pkg.status == PackageStatus.FAILED)

    def published_packages(self) -> list[str]:
        """Return names of packages that were published."""
        return sorted(name for name, pkg in self.packages.items() if pkg.status == PackageStatus.PUBLISHED)

    def is_complete(self) -> bool:
        """Return True if all packages are in a terminal state."""
        terminal = {PackageStatus.PUBLISHED, PackageStatus.SKIPPED, PackageStatus.FAILED}
        return all(pkg.status in terminal for pkg in self.packages.values())

    def validate_sha(self, current_sha: str) -> None:
        """Ensure the current HEAD matches the state's SHA.

        Args:
            current_sha: Current HEAD SHA.

        Raises:
            ReleaseKitError: If SHAs don't match.
        """
        if self.git_sha != current_sha:
            raise ReleaseKitError(
                E.STATE_SHA_MISMATCH,
                f'State file was created at SHA {self.git_sha!r}, but HEAD is now {current_sha!r}.',
                hint='Delete the state file and restart the release.',
            )

    def save(self, path: Path) -> None:
        """Atomically save the state to a JSON file.

        Uses ``tempfile`` + ``os.replace`` for crash safety: if the
        process dies mid-write, the previous state file is untouched.

        Args:
            path: Destination file path.

        Raises:
            OSError: If the file cannot be written.
        """
        data = {
            'git_sha': self.git_sha,
            'created_at': self.created_at,
            'packages': {
                name: {
                    'name': pkg.name,
                    'status': pkg.status.value,
                    'version': pkg.version,
                    'error': pkg.error,
                    'level': pkg.level,
                }
                for name, pkg in self.packages.items()
            },
        }
        content = json.dumps(data, indent=2) + '\n'

        # Write to a temp file in the same directory, then atomically rename.
        fd, tmp_path = tempfile.mkstemp(
            dir=path.parent,
            prefix='.releasekit-state-',
            suffix='.tmp',
        )
        closed = False
        try:
            os.write(fd, content.encode('utf-8'))
            os.close(fd)
            closed = True
            os.replace(tmp_path, path)
        except BaseException:
            if not closed:
                os.close(fd)
            Path(tmp_path).unlink(missing_ok=True)
            raise

        logger.debug('state_saved', path=str(path), packages=len(self.packages))

    @classmethod
    def load(cls, path: Path) -> RunState:
        """Load state from a JSON file.

        Args:
            path: Path to the state file.

        Returns:
            A :class:`RunState` instance.

        Raises:
            OSError: If the file cannot be read.
            ReleaseKitError: If the JSON is malformed or corrupted.
        """
        try:
            text = path.read_text(encoding='utf-8')
        except OSError as exc:
            raise OSError(f'Failed to read state file {path}: {exc}') from exc

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ReleaseKitError(
                E.STATE_CORRUPTED,
                f'State file {path} contains invalid JSON: {exc}',
                hint='Delete the state file and restart the release.',
            ) from exc

        try:
            git_sha = data['git_sha']
        except KeyError as exc:
            raise ReleaseKitError(
                E.STATE_CORRUPTED,
                f'State file {path} is missing required field: git_sha',
                hint='Delete the state file and restart the release.',
            ) from exc

        packages: dict[str, PackageState] = {}
        for name, pkg_data in data.get('packages', {}).items():
            try:
                status = PackageStatus(pkg_data.get('status', 'pending'))
            except ValueError:
                status = PackageStatus.PENDING
            packages[name] = PackageState(
                name=pkg_data.get('name', name),
                status=status,
                version=pkg_data.get('version', ''),
                error=pkg_data.get('error', ''),
                level=pkg_data.get('level', 0),
            )

        state = cls(
            git_sha=git_sha,
            packages=packages,
            created_at=data.get('created_at', ''),
        )
        logger.info(
            'state_loaded',
            path=str(path),
            packages=len(packages),
            pending=len(state.pending_packages()),
        )
        return state


__all__ = [
    'STATE_FILENAME',
    'PackageState',
    'PackageStatus',
    'RunState',
]
