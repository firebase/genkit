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

"""Fake Forge backend for tests.

Provides a configurable :class:`FakeForge` that satisfies the full
:class:`~releasekit.backends.forge.Forge` protocol.  Records PR and
release operations for assertions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from releasekit.backends._run import CommandResult
from tests._fakes._vcs import OK


class FakeForge:
    """Configurable Forge test double.

    Records PR, release, and label operations for assertions.
    """

    def __init__(self, *, available: bool = True) -> None:
        """Initialize with availability flag."""
        self._available = available
        self.prs_created: list[dict[str, Any]] = []
        self.releases_created: list[dict[str, Any]] = []
        self.labels_added: list[tuple[int, list[str]]] = []
        self.labels_removed: list[tuple[int, list[str]]] = []
        self.prs_merged: list[int] = []

    async def is_available(self) -> bool:
        """Return configured availability."""
        return self._available

    async def create_release(
        self,
        tag: str,
        *,
        title: str | None = None,
        body: str = '',
        draft: bool = False,
        prerelease: bool = False,
        assets: list[Path] | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """Record release creation."""
        self.releases_created.append({
            'tag': tag,
            'title': title or tag,
            'body': body,
            'draft': draft,
            'prerelease': prerelease,
        })
        return OK

    async def delete_release(
        self,
        tag: str,
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """No-op delete_release."""
        return OK

    async def promote_release(
        self,
        tag: str,
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """No-op promote_release."""
        return OK

    async def list_releases(
        self,
        *,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Return recorded releases."""
        return list(self.releases_created[:limit])

    async def create_pr(
        self,
        *,
        title: str,
        body: str = '',
        head: str,
        base: str = 'main',
        dry_run: bool = False,
    ) -> CommandResult:
        """Record PR creation."""
        self.prs_created.append({
            'title': title,
            'body': body,
            'head': head,
            'base': base,
        })
        return OK

    async def pr_data(self, pr_number: int) -> dict[str, Any]:
        """Return empty PR data."""
        return {}

    async def list_prs(
        self,
        *,
        label: str = '',
        state: str = 'open',
        head: str = '',
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Return empty PR list."""
        return []

    async def add_labels(
        self,
        pr_number: int,
        labels: list[str],
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Record label addition."""
        self.labels_added.append((pr_number, labels))
        return OK

    async def remove_labels(
        self,
        pr_number: int,
        labels: list[str],
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Record label removal."""
        self.labels_removed.append((pr_number, labels))
        return OK

    async def update_pr(
        self,
        pr_number: int,
        *,
        title: str = '',
        body: str = '',
        dry_run: bool = False,
    ) -> CommandResult:
        """No-op update_pr."""
        return OK

    async def merge_pr(
        self,
        pr_number: int,
        *,
        method: str = 'squash',
        commit_message: str = '',
        delete_branch: bool = True,
        dry_run: bool = False,
    ) -> CommandResult:
        """Record PR merge."""
        self.prs_merged.append(pr_number)
        return OK
