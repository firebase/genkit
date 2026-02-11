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

"""Protocol conformance tests for all Forge and VCS backends.

These tests verify that every backend (GitHub, GitLab, Git, Mercurial)
correctly implements its respective protocol. They use dry-run mode
exclusively so they don't require real CLI tools to be installed.

This is the "second implementation" smoke test: if the protocol is
too GitHub-specific or too Git-specific, these tests will catch it.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from releasekit.backends.forge import Forge, GitHubAPIBackend, GitHubCLIBackend
from releasekit.backends.forge.bitbucket import BitbucketAPIBackend
from releasekit.backends.forge.gitlab import GitLabCLIBackend
from releasekit.backends.vcs import VCS, GitCLIBackend
from releasekit.backends.vcs.mercurial import MercurialCLIBackend
from releasekit.logging import configure_logging

configure_logging(quiet=True)


class TestForgeProtocolConformance:
    """Every Forge backend must satisfy the runtime-checkable Forge protocol."""

    def test_github_implements_forge(self, tmp_path: Path) -> None:
        """GitHubCLIBackend should be a runtime-checkable Forge."""
        backend = GitHubCLIBackend(repo='firebase/genkit', cwd=tmp_path)
        assert isinstance(backend, Forge)

    def test_github_api_implements_forge(self) -> None:
        """GitHubAPIBackend should be a runtime-checkable Forge."""
        backend = GitHubAPIBackend(owner='firebase', repo='genkit', token='test')
        assert isinstance(backend, Forge)

    def test_gitlab_implements_forge(self, tmp_path: Path) -> None:
        """GitLabCLIBackend should be a runtime-checkable Forge."""
        backend = GitLabCLIBackend(project='firebase/genkit', cwd=tmp_path)
        assert isinstance(backend, Forge)

    def test_bitbucket_implements_forge(self) -> None:
        """BitbucketAPIBackend should be a runtime-checkable Forge."""
        backend = BitbucketAPIBackend(
            workspace='myteam',
            repo_slug='genkit',
            token='fake-token-for-protocol-test',
        )
        assert isinstance(backend, Forge)


class TestForgeDryRunConformance:
    """Dry-run behavior should be consistent across all Forge backends.

    Every forge must return CommandResult with dry_run=True and ok=True
    when called with dry_run=True.
    """

    @pytest.fixture(params=['github', 'gitlab', 'bitbucket'])
    def forge(self, request: pytest.FixtureRequest, tmp_path: Path) -> Forge:
        """Parametrized fixture providing each Forge backend."""
        if request.param == 'github':
            return GitHubCLIBackend(repo='firebase/genkit', cwd=tmp_path)
        if request.param == 'gitlab':
            return GitLabCLIBackend(project='firebase/genkit', cwd=tmp_path)
        return BitbucketAPIBackend(
            workspace='myteam',
            repo_slug='genkit',
            token='fake-token-for-protocol-test',
        )

    @pytest.mark.asyncio
    async def test_create_release_dry_run(self, forge: Forge) -> None:
        """create_release(dry_run=True) returns synthetic success."""
        result = await forge.create_release('v1.0.0', title='Release v1.0.0', dry_run=True)
        assert result.ok
        assert result.dry_run

    @pytest.mark.asyncio
    async def test_delete_release_dry_run(self, forge: Forge) -> None:
        """delete_release(dry_run=True) returns synthetic success."""
        result = await forge.delete_release('v1.0.0', dry_run=True)
        assert result.ok
        assert result.dry_run

    @pytest.mark.asyncio
    async def test_create_pr_dry_run(self, forge: Forge) -> None:
        """create_pr(dry_run=True) returns synthetic success."""
        result = await forge.create_pr(
            title='chore(release): v0.6.0',
            head='release/v0.6.0',
            body='Release manifest',
            dry_run=True,
        )
        assert result.ok
        assert result.dry_run

    @pytest.mark.asyncio
    async def test_add_labels_dry_run(self, forge: Forge) -> None:
        """add_labels(dry_run=True) returns synthetic success."""
        result = await forge.add_labels(42, ['autorelease: pending'], dry_run=True)
        assert result.ok
        assert result.dry_run

    @pytest.mark.asyncio
    async def test_remove_labels_dry_run(self, forge: Forge) -> None:
        """remove_labels(dry_run=True) returns synthetic success."""
        result = await forge.remove_labels(42, ['autorelease: pending'], dry_run=True)
        assert result.ok
        assert result.dry_run

    @pytest.mark.asyncio
    async def test_update_pr_dry_run(self, forge: Forge) -> None:
        """update_pr(dry_run=True) returns synthetic success."""
        result = await forge.update_pr(
            42,
            title='chore(release): v0.6.0',
            body='Updated manifest',
            dry_run=True,
        )
        assert result.ok
        assert result.dry_run


class TestVCSProtocolConformance:
    """Every VCS backend must satisfy the runtime-checkable VCS protocol."""

    def test_git_implements_vcs(self, tmp_path: Path) -> None:
        """GitCLIBackend should be a runtime-checkable VCS."""
        backend = GitCLIBackend(repo_root=tmp_path)
        assert isinstance(backend, VCS)

    def test_mercurial_implements_vcs(self, tmp_path: Path) -> None:
        """MercurialCLIBackend should be a runtime-checkable VCS."""
        backend = MercurialCLIBackend(repo_root=tmp_path)
        assert isinstance(backend, VCS)


class TestVCSDryRunConformance:
    """Dry-run behavior should be consistent across all VCS backends."""

    @pytest.fixture(params=['git', 'mercurial'])
    def vcs(self, request: pytest.FixtureRequest, tmp_path: Path) -> VCS:
        """Parametrized fixture providing each VCS backend."""
        if request.param == 'git':
            return GitCLIBackend(repo_root=tmp_path)
        return MercurialCLIBackend(repo_root=tmp_path)

    @pytest.mark.asyncio
    async def test_is_clean_dry_run(self, vcs: VCS) -> None:
        """is_clean(dry_run=True) returns True without running anything."""
        result = await vcs.is_clean(dry_run=True)
        assert result is True

    @pytest.mark.asyncio
    async def test_commit_dry_run(self, vcs: VCS) -> None:
        """commit(dry_run=True) returns synthetic success."""
        result = await vcs.commit('chore: bump versions', dry_run=True)
        assert result.ok
        assert result.dry_run

    @pytest.mark.asyncio
    async def test_tag_dry_run(self, vcs: VCS) -> None:
        """tag(dry_run=True) returns synthetic success."""
        result = await vcs.tag('genkit-v0.6.0', message='Release v0.6.0', dry_run=True)
        assert result.ok
        assert result.dry_run

    @pytest.mark.asyncio
    async def test_delete_tag_dry_run(self, vcs: VCS) -> None:
        """delete_tag(dry_run=True) returns synthetic success."""
        result = await vcs.delete_tag('genkit-v0.6.0', dry_run=True)
        assert result.ok
        assert result.dry_run

    @pytest.mark.asyncio
    async def test_push_dry_run(self, vcs: VCS) -> None:
        """push(dry_run=True) returns synthetic success."""
        result = await vcs.push(tags=True, dry_run=True)
        assert result.ok
        assert result.dry_run

    @pytest.mark.asyncio
    async def test_checkout_branch_dry_run(self, vcs: VCS) -> None:
        """checkout_branch(dry_run=True) returns synthetic success."""
        result = await vcs.checkout_branch('release/v0.6.0', create=True, dry_run=True)
        assert result.ok
        assert result.dry_run


class TestMercurialSpecifics:
    """Tests for Mercurial-specific behavior."""

    @pytest.mark.asyncio
    async def test_shallow_always_false(self, tmp_path: Path) -> None:
        """Mercurial doesn't support shallow clones."""
        backend = MercurialCLIBackend(repo_root=tmp_path)
        result = await backend.is_shallow()
        assert result is False

    @pytest.mark.asyncio
    async def test_push_maps_origin_to_default(self, tmp_path: Path) -> None:
        """Mercurial uses 'default' instead of 'origin'."""
        backend = MercurialCLIBackend(repo_root=tmp_path)
        result = await backend.push(remote='origin', dry_run=True)
        # The dry_run command should show 'default', not 'origin'.
        assert 'default' in result.command
        assert 'origin' not in result.command


class TestBitbucketSpecifics:
    """Tests for Bitbucket-specific behavior."""

    def test_auth_required(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """BitbucketAPIBackend raises ValueError without credentials."""
        monkeypatch.delenv('BITBUCKET_TOKEN', raising=False)
        monkeypatch.delenv('BITBUCKET_USERNAME', raising=False)
        monkeypatch.delenv('BITBUCKET_APP_PASSWORD', raising=False)
        with pytest.raises(ValueError, match='Bitbucket auth required'):
            BitbucketAPIBackend(workspace='team', repo_slug='repo')

    def test_token_auth(self) -> None:
        """Token auth sets Bearer header."""
        backend = BitbucketAPIBackend(
            workspace='team',
            repo_slug='repo',
            token='test-token',
        )
        assert 'Authorization' in backend._headers
        assert backend._headers['Authorization'] == 'Bearer test-token'

    def test_app_password_auth(self) -> None:
        """App password auth sets BasicAuth."""
        backend = BitbucketAPIBackend(
            workspace='team',
            repo_slug='repo',
            username='user',
            app_password='pass',
        )
        assert backend._auth is not None

    @pytest.mark.asyncio
    async def test_labels_are_noop(self) -> None:
        """Bitbucket has no PR labels — add/remove return synthetic ok."""
        backend = BitbucketAPIBackend(
            workspace='team',
            repo_slug='repo',
            token='fake',
        )
        add_result = await backend.add_labels(42, ['autorelease: pending'])
        remove_result = await backend.remove_labels(42, ['autorelease: pending'])

        # Both should succeed (synthetic results) since labels don't exist.
        assert add_result.ok
        assert remove_result.ok
