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

"""Tests for the GitHub CLI forge backend.

Mocks run_command to avoid real gh calls.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from releasekit.backends._run import CommandResult
from releasekit.backends.forge.github import GitHubCLIBackend


def _ok(stdout: str = '', **kw: Any) -> CommandResult:  # noqa: ANN401
    """Ok."""
    return CommandResult(command=['gh'], return_code=0, stdout=stdout, **kw)


def _fail(stderr: str = '', **kw: Any) -> CommandResult:  # noqa: ANN401
    """Fail."""
    return CommandResult(command=['gh'], return_code=1, stderr=stderr, **kw)


@pytest.fixture()
def gh() -> GitHubCLIBackend:
    """Gh."""
    return GitHubCLIBackend(repo='firebase/genkit', cwd=Path('/fake'))


class TestIsAvailable:
    """Tests for Is Available."""

    @pytest.mark.asyncio()
    async def test_available(self, gh: GitHubCLIBackend) -> None:
        """Test available."""
        with (
            patch('shutil.which', return_value='/usr/bin/gh'),
            patch('releasekit.backends.forge.github.run_command', return_value=_ok()),
        ):
            assert await gh.is_available() is True

    @pytest.mark.asyncio()
    async def test_gh_not_installed(self, gh: GitHubCLIBackend) -> None:
        """Test gh not installed."""
        with patch('shutil.which', return_value=None):
            assert await gh.is_available() is False

    @pytest.mark.asyncio()
    async def test_gh_not_authenticated(self, gh: GitHubCLIBackend) -> None:
        """Test gh not authenticated."""
        with (
            patch('shutil.which', return_value='/usr/bin/gh'),
            patch('releasekit.backends.forge.github.run_command', return_value=_fail()),
        ):
            assert await gh.is_available() is False


class TestCreateRelease:
    """Tests for Create Release."""

    @pytest.mark.asyncio()
    async def test_basic(self, gh: GitHubCLIBackend) -> None:
        """Test basic."""
        with patch.object(gh, '_gh', return_value=_ok()) as m:
            await gh.create_release('v1.0.0', title='Release v1.0.0', body='notes')
            args = m.call_args[0]
            assert 'release' in args
            assert 'create' in args
            assert 'v1.0.0' in args
            assert '--title' in args
            assert '--notes-file' in args

    @pytest.mark.asyncio()
    async def test_generate_notes(self, gh: GitHubCLIBackend) -> None:
        """Test generate notes."""
        with patch.object(gh, '_gh', return_value=_ok()) as m:
            await gh.create_release('v1.0.0')
            args = m.call_args[0]
            assert '--generate-notes' in args

    @pytest.mark.asyncio()
    async def test_draft_prerelease(self, gh: GitHubCLIBackend) -> None:
        """Test draft prerelease."""
        with patch.object(gh, '_gh', return_value=_ok()) as m:
            await gh.create_release('v1.0.0', draft=True, prerelease=True)
            args = m.call_args[0]
            assert '--draft' in args
            assert '--prerelease' in args

    @pytest.mark.asyncio()
    async def test_assets(self, gh: GitHubCLIBackend) -> None:
        """Test assets."""
        with patch.object(gh, '_gh', return_value=_ok()) as m:
            await gh.create_release('v1.0.0', assets=[Path('/fake/assets/a.tar.gz')])
            args = m.call_args[0]
            assert '/fake/assets/a.tar.gz' in args

    @pytest.mark.asyncio()
    async def test_dry_run(self, gh: GitHubCLIBackend) -> None:
        """Test dry run."""
        with patch.object(gh, '_gh', return_value=_ok()) as m:
            await gh.create_release('v1.0.0', dry_run=True)
            assert m.call_args[1].get('dry_run') is True


class TestDeleteRelease:
    """Tests for Delete Release."""

    @pytest.mark.asyncio()
    async def test_delete(self, gh: GitHubCLIBackend) -> None:
        """Test delete."""
        with patch.object(gh, '_gh', return_value=_ok()) as m:
            await gh.delete_release('v1.0.0')
            args = m.call_args[0]
            assert 'release' in args
            assert 'delete' in args
            assert '--yes' in args


class TestPromoteRelease:
    """Tests for Promote Release."""

    @pytest.mark.asyncio()
    async def test_promote(self, gh: GitHubCLIBackend) -> None:
        """Test promote."""
        with patch.object(gh, '_gh', return_value=_ok()) as m:
            await gh.promote_release('v1.0.0')
            args = m.call_args[0]
            assert 'release' in args
            assert 'edit' in args
            assert '--draft=false' in args


class TestListReleases:
    """Tests for List Releases."""

    @pytest.mark.asyncio()
    async def test_success(self, gh: GitHubCLIBackend) -> None:
        """Test success."""
        data = [{'tagName': 'v1.0.0', 'name': 'Release 1', 'isDraft': False, 'isPrerelease': False}]
        with patch.object(gh, '_gh', return_value=_ok(stdout=json.dumps(data))):
            releases = await gh.list_releases()
            assert len(releases) == 1
            assert releases[0]['tag'] == 'v1.0.0'

    @pytest.mark.asyncio()
    async def test_failure(self, gh: GitHubCLIBackend) -> None:
        """Test failure."""
        with patch.object(gh, '_gh', return_value=_fail()):
            assert await gh.list_releases() == []

    @pytest.mark.asyncio()
    async def test_bad_json(self, gh: GitHubCLIBackend) -> None:
        """Test bad json."""
        with patch.object(gh, '_gh', return_value=_ok(stdout='not json')):
            assert await gh.list_releases() == []


class TestCreatePR:
    """Tests for Create PR."""

    @pytest.mark.asyncio()
    async def test_basic(self, gh: GitHubCLIBackend) -> None:
        """Test basic."""
        with patch.object(gh, '_gh', return_value=_ok()) as m:
            await gh.create_pr(title='PR title', head='feat/x', base='main', body='body')
            args = m.call_args[0]
            assert 'pr' in args
            assert 'create' in args
            assert '--body-file' in args


class TestPRData:
    """Tests for PRData."""

    @pytest.mark.asyncio()
    async def test_success(self, gh: GitHubCLIBackend) -> None:
        """Test success."""
        data = {'title': 'PR', 'body': 'desc', 'author': {'login': 'user'}}
        with patch.object(gh, '_gh', return_value=_ok(stdout=json.dumps(data))):
            result = await gh.pr_data(42)
            assert result['title'] == 'PR'

    @pytest.mark.asyncio()
    async def test_failure(self, gh: GitHubCLIBackend) -> None:
        """Test failure."""
        with patch.object(gh, '_gh', return_value=_fail()):
            assert await gh.pr_data(42) == {}

    @pytest.mark.asyncio()
    async def test_bad_json(self, gh: GitHubCLIBackend) -> None:
        """Test bad json."""
        with patch.object(gh, '_gh', return_value=_ok(stdout='not json')):
            assert await gh.pr_data(42) == {}


class TestListPRs:
    """Tests for List PRs."""

    @pytest.mark.asyncio()
    async def test_with_filters(self, gh: GitHubCLIBackend) -> None:
        """Test with filters."""
        with patch.object(gh, '_gh', return_value=_ok(stdout='[]')) as m:
            await gh.list_prs(label='autorelease', state='closed', head='release/1.0')
            args = m.call_args[0]
            assert '--label' in args
            assert '--head' in args
            assert '--state' in args

    @pytest.mark.asyncio()
    async def test_failure(self, gh: GitHubCLIBackend) -> None:
        """Test failure."""
        with patch.object(gh, '_gh', return_value=_fail()):
            assert await gh.list_prs() == []

    @pytest.mark.asyncio()
    async def test_bad_json(self, gh: GitHubCLIBackend) -> None:
        """Test bad json."""
        with patch.object(gh, '_gh', return_value=_ok(stdout='not json')):
            assert await gh.list_prs() == []


class TestAddLabels:
    """Tests for Add Labels."""

    @pytest.mark.asyncio()
    async def test_add(self, gh: GitHubCLIBackend) -> None:
        """Test add."""
        with patch.object(gh, '_gh', return_value=_ok()) as m:
            await gh.add_labels(42, ['bug', 'urgent'])
            args = m.call_args[0]
            assert '--add-label' in args


class TestRemoveLabels:
    """Tests for Remove Labels."""

    @pytest.mark.asyncio()
    async def test_remove(self, gh: GitHubCLIBackend) -> None:
        """Test remove."""
        with patch.object(gh, '_gh', return_value=_ok()) as m:
            await gh.remove_labels(42, ['bug'])
            args = m.call_args[0]
            assert '--remove-label' in args


class TestUpdatePR:
    """Tests for Update PR."""

    @pytest.mark.asyncio()
    async def test_update(self, gh: GitHubCLIBackend) -> None:
        """Test update."""
        with patch.object(gh, '_gh', return_value=_ok()) as m:
            await gh.update_pr(42, title='New title', body='New body')
            args = m.call_args[0]
            assert '--title' in args
            assert '--body-file' in args


class TestMergePR:
    """Tests for Merge PR."""

    @pytest.mark.asyncio()
    async def test_squash(self, gh: GitHubCLIBackend) -> None:
        """Test squash."""
        with patch.object(gh, '_gh', return_value=_ok()) as m:
            await gh.merge_pr(42)
            args = m.call_args[0]
            assert '--squash' in args
            assert '--delete-branch' in args

    @pytest.mark.asyncio()
    async def test_merge_method(self, gh: GitHubCLIBackend) -> None:
        """Test merge method."""
        with patch.object(gh, '_gh', return_value=_ok()) as m:
            await gh.merge_pr(42, method='rebase', delete_branch=False)
            args = m.call_args[0]
            assert '--rebase' in args
            assert '--delete-branch' not in args

    @pytest.mark.asyncio()
    async def test_commit_message(self, gh: GitHubCLIBackend) -> None:
        """Test commit message."""
        with patch.object(gh, '_gh', return_value=_ok()) as m:
            await gh.merge_pr(42, commit_message='chore: release')
            args = m.call_args[0]
            assert '--subject' in args
