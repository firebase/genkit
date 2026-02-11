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

from releasekit.backends._run import CommandResult
from releasekit.commitback import CommitbackResult, _next_dev_version, create_commitback_pr
from releasekit.versions import PackageVersion, ReleaseManifest


class FakeVCS:
    """Minimal VCS double for commitback tests."""

    def __init__(self) -> None:
        self.branches_created: list[str] = []
        self.commits: list[str] = []
        self.pushes: int = 0

    def checkout_branch(
        self, branch: str, *, create: bool = False, dry_run: bool = False
    ) -> CommandResult:
        if create:
            self.branches_created.append(branch)
        return CommandResult(command=[], returncode=0, stdout='', stderr='')

    def commit(
        self, message: str, *, paths: list[str] | None = None, dry_run: bool = False
    ) -> CommandResult:
        self.commits.append(message)
        return CommandResult(command=[], returncode=0, stdout='', stderr='')

    def push(
        self, *, tags: bool = False, remote: str = 'origin', dry_run: bool = False
    ) -> CommandResult:
        self.pushes += 1
        return CommandResult(command=[], returncode=0, stdout='', stderr='')

    def is_clean(self, *, dry_run: bool = False) -> bool:
        return True

    def is_shallow(self) -> bool:
        return False

    def current_sha(self) -> str:
        return 'abc123'

    def log(
        self,
        *,
        since_tag: str | None = None,
        paths: list[str] | None = None,
        format: str = '%H %s',
    ) -> list[str]:
        return []

    def diff_files(self, *, since_tag: str | None = None) -> list[str]:
        return []

    def tag(
        self, tag_name: str, *, message: str | None = None, dry_run: bool = False
    ) -> CommandResult:
        return CommandResult(command=[], returncode=0, stdout='', stderr='')

    def tag_exists(self, tag_name: str) -> bool:
        return False

    def delete_tag(
        self, tag_name: str, *, remote: bool = False, dry_run: bool = False
    ) -> CommandResult:
        return CommandResult(command=[], returncode=0, stdout='', stderr='')


class FakeForge:
    """Minimal Forge double for commitback tests."""

    def __init__(self, *, available: bool = True) -> None:
        self._available = available
        self.prs_created: list[dict[str, str]] = []

    def is_available(self) -> bool:
        return self._available

    def create_pr(
        self,
        *,
        title: str,
        body: str = '',
        head: str,
        base: str = 'main',
        dry_run: bool = False,
    ) -> CommandResult:
        self.prs_created.append({'title': title, 'head': head, 'base': base})
        return CommandResult(command=[], returncode=0, stdout='', stderr='')


class TestNextDevVersion:
    """Tests for _next_dev_version helper."""

    def test_basic(self) -> None:
        if _next_dev_version('0.5.0') != '0.5.1.dev0':
            raise AssertionError(f'got {_next_dev_version("0.5.0")}')

    def test_major(self) -> None:
        if _next_dev_version('1.0.0') != '1.0.1.dev0':
            raise AssertionError(f'got {_next_dev_version("1.0.0")}')

    def test_triple_digit_patch(self) -> None:
        if _next_dev_version('1.2.99') != '1.2.100.dev0':
            raise AssertionError(f'got {_next_dev_version("1.2.99")}')

    def test_prerelease_stripped(self) -> None:
        result = _next_dev_version('0.5.0rc1')
        if result != '0.5.1.dev0':
            raise AssertionError(f'got {result}')


class TestCommitbackResult:
    """Tests for CommitbackResult dataclass."""

    def test_ok_when_no_errors(self) -> None:
        result = CommitbackResult(branch='test', bumped=['a'])
        if not result.ok:
            raise AssertionError('Expected ok=True')

    def test_not_ok_when_errors(self) -> None:
        result = CommitbackResult(errors=['something broke'])
        if result.ok:
            raise AssertionError('Expected ok=False')


class TestCreateCommitbackPr:
    """Tests for create_commitback_pr function."""

    def test_empty_manifest(self) -> None:
        """No bumped packages → no work done."""
        manifest = ReleaseManifest(git_sha='abc123', packages=[])
        vcs = FakeVCS()
        result = create_commitback_pr(manifest=manifest, vcs=vcs)
        if result.bumped:
            raise AssertionError(f'Expected no bumped packages: {result.bumped}')

    def test_creates_branch(self) -> None:
        manifest = ReleaseManifest(
            git_sha='abc123',
            umbrella_tag='v0.5.0',
            packages=[
                PackageVersion(name='genkit', old_version='0.4.0', new_version='0.5.0', bump='minor'),
            ],
        )
        vcs = FakeVCS()
        # No package_paths → nothing to bump, but branch is created.
        result = create_commitback_pr(manifest=manifest, vcs=vcs)
        if 'chore/post-release-0.5.0' not in vcs.branches_created:
            raise AssertionError(f'Expected branch creation: {vcs.branches_created}')
        if result.branch != 'chore/post-release-0.5.0':
            raise AssertionError(f'Expected branch name: {result.branch}')

    def test_bumps_packages(self, tmp_path: Path) -> None:
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
        result = create_commitback_pr(
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

    def test_commits_and_pushes(self, tmp_path: Path) -> None:
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
        create_commitback_pr(manifest=manifest, vcs=vcs, package_paths={'genkit': pkg_dir})

        if len(vcs.commits) != 1:
            raise AssertionError(f'Expected 1 commit, got {len(vcs.commits)}')
        if vcs.pushes != 1:
            raise AssertionError(f'Expected 1 push, got {vcs.pushes}')

    def test_creates_pr_with_forge(self, tmp_path: Path) -> None:
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
        result = create_commitback_pr(
            manifest=manifest,
            vcs=vcs,
            forge=forge,
            package_paths={'genkit': pkg_dir},
        )
        if not result.pr_created:
            raise AssertionError('Expected PR to be created')
        if len(forge.prs_created) != 1:
            raise AssertionError(f'Expected 1 PR, got {len(forge.prs_created)}')

    def test_skips_pr_when_forge_unavailable(self, tmp_path: Path) -> None:
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
        result = create_commitback_pr(
            manifest=manifest,
            vcs=vcs,
            forge=forge,
            package_paths={'genkit': pkg_dir},
        )
        if result.pr_created:
            raise AssertionError('Expected PR not to be created')
        if len(forge.prs_created) != 0:
            raise AssertionError(f'Expected 0 PRs, got {len(forge.prs_created)}')

    def test_missing_package_path(self) -> None:
        """Package with no path mapping is skipped."""
        manifest = ReleaseManifest(
            git_sha='abc123',
            umbrella_tag='v0.5.0',
            packages=[
                PackageVersion(name='genkit', old_version='0.4.0', new_version='0.5.0', bump='minor'),
            ],
        )
        vcs = FakeVCS()
        result = create_commitback_pr(manifest=manifest, vcs=vcs, package_paths={})
        if result.bumped:
            raise AssertionError(f'Expected no bumps: {result.bumped}')
