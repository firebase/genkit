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

"""Tests for releasekit.commitback — post-release version bumping."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from releasekit.backends._run import CommandResult
from releasekit.commitback import CommitbackResult, _next_dev_version, create_commitback_pr
from releasekit.versions import PackageVersion, ReleaseManifest

_OK = CommandResult(command=[], returncode=0, stdout='', stderr='')


class FakeVCS:
    """Minimal VCS double for commitback tests."""

    def __init__(self) -> None:
        """Initialize with empty tracking lists."""
        self.branches_created: list[str] = []
        self.commits: list[str] = []
        self.pushes: int = 0

    async def checkout_branch(self, branch: str, *, create: bool = False, dry_run: bool = False) -> CommandResult:
        """Record branch creation."""
        if create:
            self.branches_created.append(branch)
        return _OK

    async def commit(self, message: str, *, paths: list[str] | None = None, dry_run: bool = False) -> CommandResult:
        """Record commit message."""
        self.commits.append(message)
        return _OK

    async def push(self, *, tags: bool = False, remote: str = 'origin', dry_run: bool = False) -> CommandResult:
        """Record push call."""
        self.pushes += 1
        return _OK

    async def is_clean(self, *, dry_run: bool = False) -> bool:
        """Always clean."""
        return True

    async def is_shallow(self) -> bool:
        """Never shallow."""
        return False

    async def default_branch(self) -> str:
        """Always main."""
        return 'main'

    async def list_tags(self, *, pattern: str = '') -> list[str]:
        """Return empty list."""
        return []

    async def current_branch(self) -> str:
        """Always main."""
        return 'main'

    async def current_sha(self) -> str:
        """Return a fake SHA."""
        return 'abc123'

    async def log(
        self,
        *,
        since_tag: str | None = None,
        paths: list[str] | None = None,
        format: str = '%H %s',
        first_parent: bool = False,
        no_merges: bool = False,
        max_commits: int = 0,
    ) -> list[str]:
        """Return empty log."""
        return []

    async def diff_files(self, *, since_tag: str | None = None) -> list[str]:
        """Return empty diff."""
        return []

    async def tag(self, tag_name: str, *, message: str | None = None, dry_run: bool = False) -> CommandResult:
        """No-op tag."""
        return _OK

    async def tag_exists(self, tag_name: str) -> bool:
        """No tags exist."""
        return False

    async def delete_tag(self, tag_name: str, *, remote: bool = False, dry_run: bool = False) -> CommandResult:
        """No-op delete_tag."""
        return _OK


class FakeForge:
    """Minimal Forge double for commitback tests."""

    def __init__(self, *, available: bool = True) -> None:
        """Initialize with availability flag."""
        self._available = available
        self.prs_created: list[dict[str, str]] = []

    async def is_available(self) -> bool:
        """Check availability."""
        return self._available

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
        self.prs_created.append({'title': title, 'head': head, 'base': base})
        return _OK

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
        """No-op create_release."""
        return _OK

    async def delete_release(self, tag: str, *, dry_run: bool = False) -> CommandResult:
        """No-op delete_release."""
        return _OK

    async def promote_release(self, tag: str, *, dry_run: bool = False) -> CommandResult:
        """No-op promote_release."""
        return _OK

    async def list_releases(self, *, limit: int = 10) -> list[dict[str, Any]]:
        """Return empty release list."""
        return []

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
        """Stub list_prs."""
        return []

    async def add_labels(
        self,
        pr_number: int,
        labels: list[str],
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Stub add_labels."""
        return _OK

    async def remove_labels(
        self,
        pr_number: int,
        labels: list[str],
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Stub remove_labels."""
        return _OK

    async def update_pr(
        self,
        pr_number: int,
        *,
        title: str = '',
        body: str = '',
        dry_run: bool = False,
    ) -> CommandResult:
        """Stub update_pr."""
        return _OK

    async def merge_pr(
        self,
        pr_number: int,
        *,
        method: str = 'squash',
        commit_message: str = '',
        delete_branch: bool = True,
        dry_run: bool = False,
    ) -> CommandResult:
        """Stub merge_pr."""
        return _OK


class TestNextDevVersion:
    """Tests for _next_dev_version helper."""

    def test_basic(self) -> None:
        """Standard patch bump to dev version."""
        if _next_dev_version('0.5.0') != '0.5.1.dev0':
            raise AssertionError(f'got {_next_dev_version("0.5.0")}')

    def test_major(self) -> None:
        """Major version bumps to dev correctly."""
        if _next_dev_version('1.0.0') != '1.0.1.dev0':
            raise AssertionError(f'got {_next_dev_version("1.0.0")}')

    def test_triple_digit_patch(self) -> None:
        """Triple-digit patch version increments correctly."""
        if _next_dev_version('1.2.99') != '1.2.100.dev0':
            raise AssertionError(f'got {_next_dev_version("1.2.99")}')

    def test_prerelease_stripped(self) -> None:
        """Prerelease suffix is stripped before bumping."""
        result = _next_dev_version('0.5.0rc1')
        if result != '0.5.1.dev0':
            raise AssertionError(f'got {result}')


class TestCommitbackResult:
    """Tests for CommitbackResult dataclass."""

    def test_ok_when_no_errors(self) -> None:
        """Result is ok when no errors are present."""
        result = CommitbackResult(branch='test', bumped=['a'])
        if not result.ok:
            raise AssertionError('Expected ok=True')

    def test_not_ok_when_errors(self) -> None:
        """Result is not ok when errors are present."""
        result = CommitbackResult(errors=['something broke'])
        if result.ok:
            raise AssertionError('Expected ok=False')


class TestCreateCommitbackPr:
    """Tests for create_commitback_pr function."""

    @pytest.mark.asyncio
    async def test_empty_manifest(self) -> None:
        """No bumped packages produces no work."""
        manifest = ReleaseManifest(git_sha='abc123', packages=[])
        vcs = FakeVCS()
        result = await create_commitback_pr(manifest=manifest, vcs=vcs)
        if result.bumped:
            raise AssertionError(f'Expected no bumped packages: {result.bumped}')

    @pytest.mark.asyncio
    async def test_creates_branch(self) -> None:
        """Creates a post-release branch for the commitback PR."""
        manifest = ReleaseManifest(
            git_sha='abc123',
            umbrella_tag='v0.5.0',
            packages=[
                PackageVersion(name='genkit', old_version='0.4.0', new_version='0.5.0', bump='minor'),
            ],
        )
        vcs = FakeVCS()
        result = await create_commitback_pr(manifest=manifest, vcs=vcs)
        if 'chore/post-release-0.5.0' not in vcs.branches_created:
            raise AssertionError(f'Expected branch creation: {vcs.branches_created}')
        if result.branch != 'chore/post-release-0.5.0':
            raise AssertionError(f'Expected branch name: {result.branch}')

    @pytest.mark.asyncio
    async def test_bumps_packages(self, tmp_path: Path) -> None:
        """Bumps pyproject.toml version for each package."""
        pkg_dir = tmp_path / 'genkit'
        pkg_dir.mkdir()
        pyproject = pkg_dir / 'pyproject.toml'
        pyproject.write_text('[project]\nname = "genkit"\nversion = "0.5.0"\n')

        manifest = ReleaseManifest(
            git_sha='abc123',
            umbrella_tag='v0.5.0',
            packages=[
                PackageVersion(name='genkit', old_version='0.4.0', new_version='0.5.0', bump='minor'),
            ],
        )
        vcs = FakeVCS()
        result = await create_commitback_pr(
            manifest=manifest,
            vcs=vcs,
            package_paths={'genkit': pkg_dir},
        )
        if 'genkit' not in result.bumped:
            raise AssertionError(f'Expected genkit in bumped: {result.bumped}')
        if result.ok is not True:
            raise AssertionError(f'Expected ok=True: {result.errors}')

        # Verify pyproject.toml was updated.
        content = pyproject.read_text()
        if '0.5.1.dev0' not in content:
            raise AssertionError(f'Expected dev version in pyproject.toml:\n{content}')

    @pytest.mark.asyncio
    async def test_commits_and_pushes(self, tmp_path: Path) -> None:
        """Commits version bumps and pushes the branch."""
        pkg_dir = tmp_path / 'genkit'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text('[project]\nname = "genkit"\nversion = "0.5.0"\n')

        manifest = ReleaseManifest(
            git_sha='abc123',
            umbrella_tag='v0.5.0',
            packages=[
                PackageVersion(name='genkit', old_version='0.4.0', new_version='0.5.0', bump='minor'),
            ],
        )
        vcs = FakeVCS()
        await create_commitback_pr(manifest=manifest, vcs=vcs, package_paths={'genkit': pkg_dir})

        if len(vcs.commits) != 1:
            raise AssertionError(f'Expected 1 commit, got {len(vcs.commits)}')
        if vcs.pushes != 1:
            raise AssertionError(f'Expected 1 push, got {vcs.pushes}')

    @pytest.mark.asyncio
    async def test_creates_pr_with_forge(self, tmp_path: Path) -> None:
        """Creates a PR when forge is available."""
        pkg_dir = tmp_path / 'genkit'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text('[project]\nname = "genkit"\nversion = "0.5.0"\n')

        manifest = ReleaseManifest(
            git_sha='abc123',
            umbrella_tag='v0.5.0',
            packages=[
                PackageVersion(name='genkit', old_version='0.4.0', new_version='0.5.0', bump='minor'),
            ],
        )
        vcs = FakeVCS()
        forge = FakeForge()
        result = await create_commitback_pr(
            manifest=manifest,
            vcs=vcs,
            forge=forge,
            package_paths={'genkit': pkg_dir},
        )
        if not result.pr_created:
            raise AssertionError('Expected PR to be created')
        if len(forge.prs_created) != 1:
            raise AssertionError(f'Expected 1 PR, got {len(forge.prs_created)}')

    @pytest.mark.asyncio
    async def test_skips_pr_when_forge_unavailable(self, tmp_path: Path) -> None:
        """Skips PR creation when forge is not available."""
        pkg_dir = tmp_path / 'genkit'
        pkg_dir.mkdir()
        (pkg_dir / 'pyproject.toml').write_text('[project]\nname = "genkit"\nversion = "0.5.0"\n')

        manifest = ReleaseManifest(
            git_sha='abc123',
            umbrella_tag='v0.5.0',
            packages=[
                PackageVersion(name='genkit', old_version='0.4.0', new_version='0.5.0', bump='minor'),
            ],
        )
        vcs = FakeVCS()
        forge = FakeForge(available=False)
        result = await create_commitback_pr(
            manifest=manifest,
            vcs=vcs,
            forge=forge,
            package_paths={'genkit': pkg_dir},
        )
        if result.pr_created:
            raise AssertionError('Expected PR not to be created')
        if len(forge.prs_created) != 0:
            raise AssertionError(f'Expected 0 PRs, got {len(forge.prs_created)}')

    @pytest.mark.asyncio
    async def test_missing_package_path(self) -> None:
        """Package with no path mapping is skipped."""
        manifest = ReleaseManifest(
            git_sha='abc123',
            umbrella_tag='v0.5.0',
            packages=[
                PackageVersion(name='genkit', old_version='0.4.0', new_version='0.5.0', bump='minor'),
            ],
        )
        vcs = FakeVCS()
        result = await create_commitback_pr(manifest=manifest, vcs=vcs, package_paths={})
        if result.bumped:
            raise AssertionError(f'Expected no bumps: {result.bumped}')
