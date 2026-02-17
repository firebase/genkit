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

"""Fake PackageManager backend for tests.

Provides a configurable :class:`FakePM` that satisfies the full
:class:`~releasekit.backends.pm.PackageManager` protocol.
"""

from __future__ import annotations

from pathlib import Path

from releasekit.backends._run import CommandResult
from tests._fakes._vcs import OK


class FakePM:
    """Configurable PackageManager test double.

    Constructor keyword arguments control build-time side effects
    (e.g. writing fake dist files).
    """

    def __init__(
        self,
        *,
        build_files: dict[str, bytes] | None = None,
        lock_ok: bool = True,
    ) -> None:
        """Initialize with optional build artifacts and lock state.

        Args:
            build_files: Mapping of filename → content to write into
                ``output_dir`` during ``build()``.
            lock_ok: If ``False``, ``lock(check_only=True)`` returns a
                non-zero exit code.
        """
        self._build_files = build_files or {}
        self._lock_ok = lock_ok

    async def build(
        self,
        package_dir: Path,
        *,
        output_dir: Path | None = None,
        no_sources: bool = True,
        dry_run: bool = False,
    ) -> CommandResult:
        """Build — optionally writes fake dist files."""
        if output_dir and self._build_files:
            for name, content in self._build_files.items():
                (output_dir / name).write_bytes(content)
        return OK

    async def publish(
        self,
        dist_dir: Path,
        *,
        check_url: str | None = None,
        registry_url: str | None = None,
        dist_tag: str | None = None,
        publish_branch: str | None = None,
        provenance: bool = False,
        dry_run: bool = False,
    ) -> CommandResult:
        """No-op publish."""
        return OK

    async def lock(
        self,
        *,
        check_only: bool = False,
        upgrade_package: str | None = None,
        cwd: Path | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """Return lock result based on configured state."""
        if not self._lock_ok and check_only:
            return CommandResult(
                command=['uv', 'lock', '--check'],
                return_code=1,
                stdout='',
                stderr='',
            )
        return OK

    async def version_bump(
        self,
        package_dir: Path,
        new_version: str,
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """No-op version bump."""
        return OK

    async def resolve_check(
        self,
        package_name: str,
        version: str,
        *,
        registry_url: str | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """No-op resolve check."""
        return OK

    async def smoke_test(
        self,
        package_name: str,
        version: str,
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """No-op smoke test."""
        return OK
