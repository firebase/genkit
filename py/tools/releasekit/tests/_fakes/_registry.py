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

"""Fake Registry backend for tests.

Provides a configurable :class:`FakeRegistry` that satisfies the full
:class:`~releasekit.backends.registry.Registry` protocol.
"""

from __future__ import annotations

from releasekit.backends.registry import ChecksumResult


class FakeRegistry:
    """Configurable Registry test double."""

    def __init__(
        self,
        *,
        available: bool = True,
        checksums_ok: bool = True,
        published: set[str] | None = None,
    ) -> None:
        """Initialize with configurable state.

        Args:
            available: Value returned by ``poll_available()``.
            checksums_ok: If ``True``, ``verify_checksum()`` reports all
                matched.  If ``False``, reports a mismatch.
            published: Set of ``"name==version"`` strings that
                ``check_published()`` considers already published.
        """
        self._available = available
        self._checksums_ok = checksums_ok
        self._published = published or set()

    async def check_published(self, package_name: str, version: str) -> bool:
        """Check if a version is in the published set."""
        return f'{package_name}=={version}' in self._published

    async def poll_available(
        self,
        package_name: str,
        version: str,
        *,
        timeout: float = 300.0,
        interval: float = 5.0,
    ) -> bool:
        """Return configured availability."""
        return self._available

    async def project_exists(self, package_name: str) -> bool:
        """Always exists."""
        return True

    async def latest_version(self, package_name: str) -> str | None:
        """Return None (no published version)."""
        return None

    async def verify_checksum(
        self,
        package_name: str,
        version: str,
        local_checksums: dict[str, str],
    ) -> ChecksumResult:
        """Return checksum result based on configured state."""
        if self._checksums_ok:
            return ChecksumResult(
                matched=list(local_checksums.keys()),
                mismatched={},
                missing=[],
            )
        return ChecksumResult(
            matched=[],
            mismatched={'bad.whl': ('aaa', 'bbb')},
            missing=[],
        )

    async def list_versions(self, package_name: str) -> list[str]:
        """Return versions from the published set."""
        return [entry.split('==')[1] for entry in sorted(self._published) if entry.startswith(f'{package_name}==')]

    async def yank_version(
        self,
        package_name: str,
        version: str,
        *,
        reason: str = '',
        dry_run: bool = False,
    ) -> bool:
        """Simulate yank by removing from published set."""
        key = f'{package_name}=={version}'
        if key in self._published:
            if not dry_run:
                self._published.discard(key)
            return True
        return False
