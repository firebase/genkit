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

"""Integration tests for GitHubCLIBackend command construction.

These tests verify that the ``gh`` CLI commands are constructed
correctly using dry-run mode. They require ``gh`` to be installed
but do NOT require authentication or network access.

Dry-run mode returns a synthetic ``CommandResult`` with the full
command line, allowing us to verify argument order and flag
correctness without executing anything.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from releasekit.backends.forge.github import GitHubCLIBackend
from releasekit.logging import configure_logging

configure_logging(quiet=True)

pytestmark = pytest.mark.skipif(
    shutil.which('gh') is None,
    reason='gh not found on PATH. Install gh: https://cli.github.com/',
)


class TestCreateReleaseDryRun:
    """Test gh release create command construction."""

    @pytest.mark.asyncio
    async def test_basic_release(self, tmp_path: Path) -> None:
        """create_release() should produce correct gh release create command."""
        backend = GitHubCLIBackend(repo='firebase/genkit', cwd=tmp_path)
        result = await backend.create_release('v1.0.0', title='Release v1.0.0', dry_run=True)
        assert result.ok
        cmd = result.command
        assert cmd[:2] == ['gh', 'release']
        assert 'create' in cmd
        assert 'v1.0.0' in cmd
        assert '--title' in cmd
        assert '--repo' in cmd
        assert 'firebase/genkit' in cmd

    @pytest.mark.asyncio
    async def test_draft_prerelease(self, tmp_path: Path) -> None:
        """create_release(draft=True, prerelease=True) should include both flags."""
        backend = GitHubCLIBackend(repo='firebase/genkit', cwd=tmp_path)
        result = await backend.create_release(
            'v1.0.0-rc.1',
            draft=True,
            prerelease=True,
            dry_run=True,
        )
        assert '--draft' in result.command
        assert '--prerelease' in result.command

    @pytest.mark.asyncio
    async def test_generate_notes_when_no_body(self, tmp_path: Path) -> None:
        """create_release() without body should use --generate-notes."""
        backend = GitHubCLIBackend(repo='firebase/genkit', cwd=tmp_path)
        result = await backend.create_release('v1.0.0', dry_run=True)
        assert '--generate-notes' in result.command


class TestCreatePRDryRun:
    """Test gh pr create command construction."""

    @pytest.mark.asyncio
    async def test_pr_with_body(self, tmp_path: Path) -> None:
        """create_pr() with body should use --body-file."""
        backend = GitHubCLIBackend(repo='firebase/genkit', cwd=tmp_path)
        result = await backend.create_pr(
            title='chore(release): v1.0.0',
            body='## Release\n\nChangelog here.',
            head='release/v1.0.0',
            base='main',
            dry_run=True,
        )
        assert result.ok
        cmd = result.command
        assert '--body-file' in cmd
        assert '--head' in cmd
        assert '--base' in cmd
        assert 'release/v1.0.0' in cmd

    @pytest.mark.asyncio
    async def test_pr_without_body(self, tmp_path: Path) -> None:
        """create_pr() without body should not include --body-file."""
        backend = GitHubCLIBackend(repo='firebase/genkit', cwd=tmp_path)
        result = await backend.create_pr(
            title='chore: fix',
            head='fix/bug',
            dry_run=True,
        )
        assert '--body-file' not in result.command


class TestUpdatePRDryRun:
    """Test gh pr edit command construction."""

    @pytest.mark.asyncio
    async def test_update_with_body(self, tmp_path: Path) -> None:
        """update_pr() with body should use --body-file."""
        backend = GitHubCLIBackend(repo='firebase/genkit', cwd=tmp_path)
        result = await backend.update_pr(
            42,
            title='Updated title',
            body='Updated body',
            dry_run=True,
        )
        assert result.ok
        assert '--body-file' in result.command
        assert '--title' in result.command

    @pytest.mark.asyncio
    async def test_update_title_only(self, tmp_path: Path) -> None:
        """update_pr() with title only should not include --body-file."""
        backend = GitHubCLIBackend(repo='firebase/genkit', cwd=tmp_path)
        result = await backend.update_pr(42, title='New title', dry_run=True)
        assert '--title' in result.command
        assert '--body-file' not in result.command


class TestMergePRDryRun:
    """Test gh pr merge command construction."""

    @pytest.mark.asyncio
    async def test_squash_merge(self, tmp_path: Path) -> None:
        """merge_pr() should default to --squash --auto --delete-branch."""
        backend = GitHubCLIBackend(repo='firebase/genkit', cwd=tmp_path)
        result = await backend.merge_pr(42, dry_run=True)
        assert result.ok
        cmd = result.command
        assert '--squash' in cmd
        assert '--auto' in cmd
        assert '--delete-branch' in cmd

    @pytest.mark.asyncio
    async def test_rebase_merge(self, tmp_path: Path) -> None:
        """merge_pr(method='rebase') should use --rebase."""
        backend = GitHubCLIBackend(repo='firebase/genkit', cwd=tmp_path)
        result = await backend.merge_pr(42, method='rebase', dry_run=True)
        assert '--rebase' in result.command
        assert '--squash' not in result.command


class TestLabelsDryRun:
    """Test gh pr edit label commands."""

    @pytest.mark.asyncio
    async def test_add_labels(self, tmp_path: Path) -> None:
        """add_labels() should include --add-label for each label."""
        backend = GitHubCLIBackend(repo='firebase/genkit', cwd=tmp_path)
        result = await backend.add_labels(
            42,
            ['autorelease: pending', 'release'],
            dry_run=True,
        )
        assert result.ok
        assert result.command.count('--add-label') == 2
        assert 'autorelease: pending' in result.command
        assert 'release' in result.command

    @pytest.mark.asyncio
    async def test_remove_labels(self, tmp_path: Path) -> None:
        """remove_labels() should include --remove-label for each label."""
        backend = GitHubCLIBackend(repo='firebase/genkit', cwd=tmp_path)
        result = await backend.remove_labels(
            42,
            ['autorelease: pending'],
            dry_run=True,
        )
        assert result.ok
        assert '--remove-label' in result.command
        assert 'autorelease: pending' in result.command
