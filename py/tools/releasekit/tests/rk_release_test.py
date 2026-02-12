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

"""Tests for releasekit.release module."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest
from releasekit.backends._run import CommandResult
from releasekit.config import ReleaseConfig
from releasekit.release import ReleaseResult, extract_manifest, tag_release
from releasekit.versions import PackageVersion, ReleaseManifest

# ── Fake backends ──

_OK = CommandResult(command=[], returncode=0, stdout='', stderr='')


class FakeVCS:
    """Fake VCS backend for release tests."""

    def __init__(self, *, sha: str = 'abc123', log_lines: list[str] | None = None) -> None:
        """Initialize instance."""
        self._sha = sha
        self._log_lines = log_lines or []

    async def is_clean(self, *, dry_run: bool = False) -> bool:
        """Is clean."""
        return True

    async def is_shallow(self) -> bool:
        """Is shallow."""
        return False

    async def current_sha(self) -> str:
        """Current sha."""
        return self._sha

    async def log(
        self,
        *,
        since_tag: str | None = None,
        paths: list[str] | None = None,
        format: str = '%H %s',
    ) -> list[str]:
        """Log."""
        return self._log_lines

    async def diff_files(self, *, since_tag: str | None = None) -> list[str]:
        """Diff files."""
        return []

    async def commit(
        self,
        message: str,
        *,
        paths: list[str] | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """Commit."""
        return _OK

    async def tag(
        self,
        tag_name: str,
        *,
        message: str | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """Tag."""
        return _OK

    async def tag_exists(self, tag_name: str) -> bool:
        """Tag exists."""
        return False

    async def delete_tag(
        self,
        tag_name: str,
        *,
        remote: bool = False,
        dry_run: bool = False,
    ) -> CommandResult:
        """Delete tag."""
        return _OK

    async def push(
        self,
        *,
        tags: bool = False,
        remote: str = 'origin',
        dry_run: bool = False,
    ) -> CommandResult:
        """Push."""
        return _OK

    async def checkout_branch(
        self,
        branch: str,
        *,
        create: bool = False,
        dry_run: bool = False,
    ) -> CommandResult:
        """Checkout branch."""
        return _OK


class FakeForge:
    """Fake forge for release tests."""

    def __init__(
        self,
        *,
        available: bool = True,
        prs: list[dict[str, str | int | list[str]]] | None = None,
        pr_body: str = '',
    ) -> None:
        """Initialize instance."""
        self._available = available
        self._prs: list[dict[str, str | int | list[str]]] = prs or []
        self._pr_body = pr_body
        self.labels_added: list[tuple[int, list[str]]] = []
        self.labels_removed: list[tuple[int, list[str]]] = []

    async def is_available(self) -> bool:
        """Is available."""
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
        """Create release."""
        return _OK

    async def delete_release(self, tag: str, *, dry_run: bool = False) -> CommandResult:
        """Delete release."""
        return _OK

    async def promote_release(self, tag: str, *, dry_run: bool = False) -> CommandResult:
        """Promote release."""
        return _OK

    async def list_releases(self, *, limit: int = 10) -> list[dict[str, str | bool]]:
        """List releases."""
        return []

    async def create_pr(
        self,
        *,
        title: str = '',
        body: str = '',
        head: str = '',
        base: str = 'main',
        dry_run: bool = False,
    ) -> CommandResult:
        """Create pr."""
        return _OK

    async def pr_data(self, pr_number: int) -> dict[str, str | int]:
        """Pr data."""
        return {'body': self._pr_body, 'number': pr_number}

    async def list_prs(
        self,
        *,
        label: str = '',
        state: str = 'open',
        head: str = '',
        limit: int = 10,
    ) -> list[dict[str, str | int | list[str]]]:
        """List prs."""
        return self._prs

    async def add_labels(
        self,
        pr_number: int,
        labels: list[str],
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Add labels."""
        self.labels_added.append((pr_number, labels))
        return _OK

    async def remove_labels(
        self,
        pr_number: int,
        labels: list[str],
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Remove labels."""
        self.labels_removed.append((pr_number, labels))
        return _OK

    async def update_pr(
        self,
        pr_number: int,
        *,
        title: str = '',
        body: str = '',
        dry_run: bool = False,
    ) -> CommandResult:
        """Update pr."""
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
        """Merge pr."""
        return _OK


# ── Tests: ReleaseResult ──


class TestReleaseResult:
    """Tests for ReleaseResult dataclass."""

    def test_empty_is_ok(self) -> None:
        """Empty result should be OK with no tags."""
        result = ReleaseResult()
        if not result.ok:
            raise AssertionError('Empty result should be OK')
        if result.tags_created:
            raise AssertionError('Expected no tags')

    def test_with_errors(self) -> None:
        """Result with errors should not be OK."""
        result = ReleaseResult(errors={'tag:v1': 'failed'})
        if result.ok:
            raise AssertionError('Should not be OK with errors')

    def test_tags_created_property(self) -> None:
        """Tags created property delegates to TagResult."""
        from releasekit.tags import TagResult

        tag_result = TagResult(created=['v1.0.0', 'v2.0.0'])
        result = ReleaseResult(tag_result=tag_result)
        if result.tags_created != ['v1.0.0', 'v2.0.0']:
            raise AssertionError(f'Unexpected tags: {result.tags_created}')

    def test_tags_created_none(self) -> None:
        """No tags when tag_result is None."""
        result = ReleaseResult(tag_result=None)
        if result.tags_created:
            raise AssertionError('Expected no tags when tag_result is None')


# ── Tests: extract_manifest ──


class TestExtractManifest:
    """Tests for extract_manifest."""

    def _make_pr_body(self, manifest_data: dict[str, Any]) -> str:
        """Build a PR body with embedded manifest."""
        manifest_json = json.dumps(manifest_data, indent=2)
        return (
            '# Release v0.2.0\n\nSome changes.\n\n'
            '<!-- releasekit:manifest:start -->\n'
            f'```json\n{manifest_json}\n```\n'
            '<!-- releasekit:manifest:end -->'
        )

    def test_extracts_valid_manifest(self) -> None:
        """Extracts manifest from PR body with valid markers."""
        data = {
            'git_sha': 'abc123',
            'umbrella_tag': 'v0.2.0',
            'created_at': '2026-02-11T00:00:00Z',
            'packages': [
                {'name': 'genkit', 'old_version': '0.1.0', 'new_version': '0.2.0', 'bump': 'minor'},
            ],
        }
        body = self._make_pr_body(data)
        manifest = extract_manifest(body)
        if manifest is None:
            raise AssertionError('Should extract manifest')
        if manifest.git_sha != 'abc123':
            raise AssertionError(f'Wrong SHA: {manifest.git_sha}')
        if len(manifest.packages) != 1:
            raise AssertionError(f'Expected 1 package, got {len(manifest.packages)}')
        if manifest.packages[0].name != 'genkit':
            raise AssertionError(f'Wrong package name: {manifest.packages[0].name}')

    def test_no_manifest_markers(self) -> None:
        """Returns None when no manifest markers found."""
        result = extract_manifest('# Just a PR\nNo manifest here.')
        if result is not None:
            raise AssertionError('Should return None for no markers')

    def test_invalid_json(self) -> None:
        """Returns None when JSON inside markers is invalid."""
        body = '<!-- releasekit:manifest:start -->\n```json\n{not valid json}\n```\n<!-- releasekit:manifest:end -->'
        result = extract_manifest(body)
        if result is not None:
            raise AssertionError('Should return None for invalid JSON')

    def test_missing_git_sha(self) -> None:
        """Returns None when git_sha field is missing."""
        data = {
            'umbrella_tag': 'v0.2.0',
            'packages': [
                {'name': 'genkit', 'old_version': '0.1.0', 'new_version': '0.2.0', 'bump': 'minor'},
            ],
        }
        body = self._make_pr_body(data)
        result = extract_manifest(body)
        if result is not None:
            raise AssertionError('Should return None when git_sha is missing')


# ── Tests: tag_release ──


class TestTagRelease:
    """Tests for tag_release."""

    def test_from_manifest_file(self, tmp_path: Path) -> None:
        """Loads manifest from file when provided."""
        manifest = ReleaseManifest(
            git_sha='abc123',
            umbrella_tag='v0.2.0',
            packages=[
                PackageVersion(name='genkit', old_version='0.1.0', new_version='0.2.0', bump='minor'),
            ],
            created_at='2026-02-11T00:00:00Z',
        )
        manifest_path = tmp_path / 'release-manifest.json'
        manifest.save(manifest_path)

        config = ReleaseConfig()
        result = asyncio.run(
            tag_release(
                vcs=FakeVCS(),
                forge=FakeForge(),
                config=config,
                manifest_path=manifest_path,
                dry_run=True,
            ),
        )

        if not result.ok:
            raise AssertionError(f'Should be OK: {result.errors}')
        if result.manifest is None:
            raise AssertionError('Should have manifest')

    def test_no_forge_no_manifest_errors(self) -> None:
        """No forge and no manifest_path produces error."""
        config = ReleaseConfig()
        result = asyncio.run(
            tag_release(
                vcs=FakeVCS(),
                forge=None,
                config=config,
                dry_run=True,
            ),
        )

        if result.ok:
            raise AssertionError('Should fail without forge or manifest_path')
        if 'no_source' not in result.errors:
            raise AssertionError(f'Expected no_source error: {result.errors}')

    def test_no_merged_pr_errors(self) -> None:
        """No merged PR with pending label produces error."""
        config = ReleaseConfig()
        forge = FakeForge(prs=[])  # No PRs found.

        result = asyncio.run(
            tag_release(
                vcs=FakeVCS(),
                forge=forge,
                config=config,
                dry_run=True,
            ),
        )

        if result.ok:
            raise AssertionError('Should fail with no merged PR')
        if 'find_pr' not in result.errors:
            raise AssertionError(f'Expected find_pr error: {result.errors}')

    def test_manifest_not_extractable_errors(self) -> None:
        """PR body without manifest markers produces error."""
        config = ReleaseConfig()
        forge = FakeForge(
            prs=[{'number': 42, 'url': 'https://github.com/test/pr/42'}],
            pr_body='# No manifest here',
        )

        result = asyncio.run(
            tag_release(
                vcs=FakeVCS(),
                forge=forge,
                config=config,
                dry_run=True,
            ),
        )

        if result.ok:
            raise AssertionError('Should fail when manifest not extractable')
        if 'parse_manifest' not in result.errors:
            raise AssertionError(f'Expected parse_manifest error: {result.errors}')

    def test_empty_bumped_in_manifest(self, tmp_path: Path) -> None:
        """Manifest with no bumped packages returns early."""
        manifest = ReleaseManifest(
            git_sha='abc123',
            umbrella_tag='v0.1.0',
            packages=[
                PackageVersion(name='genkit', old_version='0.1.0', new_version='0.1.0', bump='none'),
            ],
            created_at='2026-02-11T00:00:00Z',
        )
        manifest_path = tmp_path / 'release-manifest.json'
        manifest.save(manifest_path)

        config = ReleaseConfig()
        result = asyncio.run(
            tag_release(
                vcs=FakeVCS(),
                forge=FakeForge(),
                config=config,
                manifest_path=manifest_path,
                dry_run=True,
            ),
        )

        if not result.ok:
            raise AssertionError(f'Should be OK (nothing to tag): {result.errors}')
        if result.manifest is None:
            raise AssertionError('Should still have manifest')

    def test_forge_label_update(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Labels are swapped when forge available and PR found."""
        # Run from tmp_path so any file writes don't pollute the project root.
        monkeypatch.chdir(tmp_path)

        manifest_data = {
            'git_sha': 'abc123',
            'umbrella_tag': 'v0.2.0',
            'created_at': '2026-02-11T00:00:00Z',
            'packages': [
                {'name': 'genkit', 'old_version': '0.1.0', 'new_version': '0.2.0', 'bump': 'minor'},
            ],
        }
        manifest_json = json.dumps(manifest_data, indent=2)
        pr_body = f'<!-- releasekit:manifest:start -->\n```json\n{manifest_json}\n```\n<!-- releasekit:manifest:end -->'
        forge = FakeForge(
            prs=[{'number': 42, 'url': 'https://github.com/test/pr/42'}],
            pr_body=pr_body,
        )

        config = ReleaseConfig()
        result = asyncio.run(
            tag_release(
                vcs=FakeVCS(),
                forge=forge,
                config=config,
                dry_run=False,
            ),
        )

        if not result.ok:
            raise AssertionError(f'Should be OK: {result.errors}')
        if result.pr_number != 42:
            raise AssertionError(f'Expected PR #42, got {result.pr_number}')
