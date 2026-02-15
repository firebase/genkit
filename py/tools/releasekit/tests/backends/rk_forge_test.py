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

"""Tests for releasekit.backends.forge module."""

from __future__ import annotations

from pathlib import Path

import pytest
from releasekit.backends.forge import Forge, GitHubCLIBackend
from releasekit.logging import configure_logging

configure_logging(quiet=True)


class TestGitHubCLIBackendProtocol:
    """Verify GitHubCLIBackend implements the Forge protocol."""

    def test_implements_protocol(self, tmp_path: Path) -> None:
        """GitHubCLIBackend should be a runtime-checkable Forge."""
        backend = GitHubCLIBackend(repo='firebase/genkit', cwd=tmp_path)
        assert isinstance(backend, Forge)


class TestGitHubCLIBackendDryRun:
    """Tests for GitHubCLIBackend in dry-run mode."""

    @pytest.mark.asyncio
    async def test_create_release_dry_run(self, tmp_path: Path) -> None:
        """create_release() in dry-run should return synthetic success."""
        backend = GitHubCLIBackend(repo='firebase/genkit', cwd=tmp_path)
        result = await backend.create_release('v1.0.0', title='Release v1.0.0', dry_run=True)
        assert result.ok
        assert result.dry_run

    @pytest.mark.asyncio
    async def test_create_release_draft(self, tmp_path: Path) -> None:
        """create_release(draft=True) should include --draft."""
        backend = GitHubCLIBackend(repo='firebase/genkit', cwd=tmp_path)
        result = await backend.create_release('v1.0.0', draft=True, dry_run=True)
        assert '--draft' in result.command

    @pytest.mark.asyncio
    async def test_create_release_prerelease(self, tmp_path: Path) -> None:
        """create_release(prerelease=True) should include --prerelease."""
        backend = GitHubCLIBackend(repo='firebase/genkit', cwd=tmp_path)
        result = await backend.create_release('v1.0.0', prerelease=True, dry_run=True)
        assert '--prerelease' in result.command

    @pytest.mark.asyncio
    async def test_delete_release_dry_run(self, tmp_path: Path) -> None:
        """delete_release() in dry-run should return synthetic success."""
        backend = GitHubCLIBackend(repo='firebase/genkit', cwd=tmp_path)
        result = await backend.delete_release('v1.0.0', dry_run=True)
        assert result.ok
        assert result.dry_run

    @pytest.mark.asyncio
    async def test_promote_release_dry_run(self, tmp_path: Path) -> None:
        """promote_release() in dry-run should return synthetic success."""
        backend = GitHubCLIBackend(repo='firebase/genkit', cwd=tmp_path)
        result = await backend.promote_release('v1.0.0', dry_run=True)
        assert result.ok

    @pytest.mark.asyncio
    async def test_create_pr_dry_run(self, tmp_path: Path) -> None:
        """create_pr() in dry-run should include branch info."""
        backend = GitHubCLIBackend(repo='firebase/genkit', cwd=tmp_path)
        result = await backend.create_pr(
            title='Test PR',
            head='feat/test',
            body='Test body',
            dry_run=True,
        )
        assert result.ok
        assert 'feat/test' in result.command

    @pytest.mark.asyncio
    async def test_add_labels_dry_run(self, tmp_path: Path) -> None:
        """add_labels() in dry-run should include label args."""
        backend = GitHubCLIBackend(repo='firebase/genkit', cwd=tmp_path)
        result = await backend.add_labels(
            42,
            ['autorelease: pending', 'release'],
            dry_run=True,
        )
        assert result.ok
        assert result.dry_run
        assert '--add-label' in result.command
        assert 'autorelease: pending' in result.command

    @pytest.mark.asyncio
    async def test_remove_labels_dry_run(self, tmp_path: Path) -> None:
        """remove_labels() in dry-run should include label args."""
        backend = GitHubCLIBackend(repo='firebase/genkit', cwd=tmp_path)
        result = await backend.remove_labels(
            42,
            ['autorelease: pending'],
            dry_run=True,
        )
        assert result.ok
        assert result.dry_run
        assert '--remove-label' in result.command

    @pytest.mark.asyncio
    async def test_update_pr_dry_run(self, tmp_path: Path) -> None:
        """update_pr() in dry-run should include title/body args."""
        backend = GitHubCLIBackend(repo='firebase/genkit', cwd=tmp_path)
        result = await backend.update_pr(
            42,
            title='chore(release): v0.6.0',
            body='Release manifest here',
            dry_run=True,
        )
        assert result.ok
        assert result.dry_run
        assert '--title' in result.command
        assert '--body-file' in result.command
