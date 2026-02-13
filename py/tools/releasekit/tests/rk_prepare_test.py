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

"""Tests for releasekit.prepare module."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from releasekit.backends._run import CommandResult
from releasekit.backends.registry import ChecksumResult
from releasekit.config import ReleaseConfig
from releasekit.prepare import PrepareResult, _build_pr_body, _embed_manifest, _package_paths, prepare_release
from releasekit.versions import PackageVersion
from releasekit.workspace import Package

_OK = CommandResult(command=[], returncode=0, stdout='', stderr='')


class TestPrepareResult:
    """Tests for PrepareResult dataclass."""

    def test_empty_is_ok(self) -> None:
        """Empty result is OK with no bumps or skips."""
        result = PrepareResult()
        if not result.ok:
            raise AssertionError('Empty result should be OK')
        if result.bumped:
            raise AssertionError('Expected no bumped')
        if result.skipped:
            raise AssertionError('Expected no skipped')

    def test_with_errors(self) -> None:
        """Result with errors is not OK."""
        result = PrepareResult(errors={'preflight:dirty': 'unclean'})
        if result.ok:
            raise AssertionError('Should not be OK with errors')

    def test_with_bumped(self) -> None:
        """Result with bumped packages is OK."""
        ver = PackageVersion(name='genkit', old_version='0.1.0', new_version='0.2.0', bump='minor')
        result = PrepareResult(bumped=[ver])
        if not result.ok:
            raise AssertionError('Bumped result should be OK')
        if len(result.bumped) != 1:
            raise AssertionError(f'Expected 1 bumped, got {len(result.bumped)}')


class TestEmbedManifest:
    """Tests for _embed_manifest."""

    def test_appends_when_no_markers(self) -> None:
        """Appends manifest block when no markers exist."""
        body = '# Release\nSome content.'
        result = _embed_manifest(body, '{"test": true}')
        if '<!-- releasekit:manifest:start -->' not in result:
            raise AssertionError('Missing start marker')
        if '<!-- releasekit:manifest:end -->' not in result:
            raise AssertionError('Missing end marker')
        if '{"test": true}' not in result:
            raise AssertionError('Missing JSON content')

    def test_replaces_existing_markers(self) -> None:
        """Replaces existing manifest block in-place."""
        body = (
            '# Release\n'
            '<!-- releasekit:manifest:start -->\n'
            '```json\n{"old": true}\n```\n'
            '<!-- releasekit:manifest:end -->\n'
        )
        result = _embed_manifest(body, '{"new": true}')
        if '{"old": true}' in result:
            raise AssertionError('Old manifest should be replaced')
        if '{"new": true}' not in result:
            raise AssertionError('New manifest should be present')
        if '<!-- releasekit:manifest:start -->' not in result:
            raise AssertionError('Start marker should be present')
        if '<!-- releasekit:manifest:end -->' not in result:
            raise AssertionError('End marker should be present')

    def test_json_in_code_block(self) -> None:
        """Manifest is wrapped in a JSON code block."""
        result = _embed_manifest('body', '{}')
        if '```json' not in result:
            raise AssertionError('JSON should be in a code block')


class TestBuildPrBody:
    """Tests for _build_pr_body."""

    def test_includes_version_header(self) -> None:
        """PR body includes release version header."""
        body = _build_pr_body({'genkit': '## genkit v0.2.0\n- feat: new'}, '{}', '0.2.0')
        if '# Release v0.2.0' not in body:
            raise AssertionError('Missing version header')

    def test_includes_changelogs(self) -> None:
        """PR body includes changelogs for all packages."""
        changelogs = {
            'a': '## a\n- fix',
            'b': '## b\n- feat',
        }
        body = _build_pr_body(changelogs, '{}', '1.0.0')
        if '## a' not in body:
            raise AssertionError('Missing changelog for a')
        if '## b' not in body:
            raise AssertionError('Missing changelog for b')

    def test_embeds_manifest(self) -> None:
        """PR body contains embedded release manifest."""
        body = _build_pr_body({}, '{"x":1}', '1.0.0')
        if '<!-- releasekit:manifest:start -->' not in body:
            raise AssertionError('Missing manifest')


class TestPackagePaths:
    """Tests for _package_paths."""

    def test_builds_name_to_path_map(self, tmp_path: object) -> None:
        """Maps package names to their directory paths."""
        pkg_path = Path('/workspace/packages/genkit')
        pkg = Package(
            name='genkit',
            version='0.1.0',
            path=pkg_path,
            pyproject_path=pkg_path / 'pyproject.toml',
        )
        paths = _package_paths([pkg])
        if paths.get('genkit') != str(pkg_path):
            raise AssertionError(f'Unexpected path: {paths}')

    def test_empty_packages(self) -> None:
        """Empty input returns empty map."""
        if _package_paths([]):
            raise AssertionError('Expected empty map')


class _FakeVCS:
    """Minimal VCS for prepare tests."""

    def __init__(self, *, log_lines: list[str] | None = None) -> None:
        self._log_lines = log_lines or ['aaa1111 feat: initial']

    async def is_clean(self, *, dry_run: bool = False) -> bool:
        return True

    async def is_shallow(self) -> bool:
        return False

    async def current_sha(self) -> str:
        return 'abc123'

    async def log(
        self,
        *,
        since_tag: str | None = None,
        paths: list[str] | None = None,
        format: str = '%H %s',
        first_parent: bool = False,
    ) -> list[str]:
        return self._log_lines

    async def diff_files(self, *, since_tag: str | None = None) -> list[str]:
        return ['packages/genkit/src/main.py']

    async def commit(self, message: str, *, paths: list[str] | None = None, dry_run: bool = False) -> CommandResult:
        return _OK

    async def tag(self, tag_name: str, *, message: str | None = None, dry_run: bool = False) -> CommandResult:
        return _OK

    async def tag_exists(self, tag_name: str) -> bool:
        return False

    async def delete_tag(self, tag_name: str, *, remote: bool = False, dry_run: bool = False) -> CommandResult:
        return _OK

    async def push(self, *, tags: bool = False, remote: str = 'origin', dry_run: bool = False) -> CommandResult:
        return _OK

    async def checkout_branch(self, branch: str, *, create: bool = False, dry_run: bool = False) -> CommandResult:
        return _OK


class _FakePM:
    """Minimal package manager for prepare tests."""

    async def build(
        self,
        package_dir: Path,
        *,
        output_dir: Path | None = None,
        no_sources: bool = True,
        dry_run: bool = False,
    ) -> CommandResult:
        return _OK

    async def publish(
        self,
        dist_dir: Path,
        *,
        check_url: str | None = None,
        index_url: str | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        return _OK

    async def lock(
        self,
        *,
        check_only: bool = False,
        upgrade_package: str | None = None,
        cwd: Path | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        return _OK

    async def version_bump(
        self,
        package_dir: Path,
        new_version: str,
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        return _OK

    async def resolve_check(
        self,
        package_name: str,
        version: str,
        *,
        index_url: str | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        return _OK

    async def smoke_test(
        self,
        package_name: str,
        version: str,
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        return _OK


class _FakeForge:
    """Forge that records label operations and simulates PR creation."""

    def __init__(self, *, existing_prs: list[dict[str, Any]] | None = None, create_pr_url: str = '') -> None:
        self._existing_prs = existing_prs or []
        self._create_pr_url = create_pr_url
        self.labels_added: list[tuple[int, list[str]]] = []

    async def is_available(self) -> bool:
        return True

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
        return _OK

    async def delete_release(self, tag: str, *, dry_run: bool = False) -> CommandResult:
        return _OK

    async def promote_release(self, tag: str, *, dry_run: bool = False) -> CommandResult:
        return _OK

    async def list_releases(self, *, limit: int = 10) -> list[dict[str, Any]]:
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
        return CommandResult(command=[], returncode=0, stdout=self._create_pr_url, stderr='')

    async def pr_data(self, pr_number: int) -> dict[str, Any]:
        return {}

    async def list_prs(
        self,
        *,
        label: str = '',
        state: str = 'open',
        head: str = '',
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        return self._existing_prs

    async def add_labels(self, pr_number: int, labels: list[str], *, dry_run: bool = False) -> CommandResult:
        self.labels_added.append((pr_number, labels))
        return _OK

    async def remove_labels(self, pr_number: int, labels: list[str], *, dry_run: bool = False) -> CommandResult:
        return _OK

    async def update_pr(
        self,
        pr_number: int,
        *,
        title: str = '',
        body: str = '',
        dry_run: bool = False,
    ) -> CommandResult:
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
        return _OK


class _FakeRegistry:
    """Minimal registry for prepare tests."""

    async def check_published(self, package_name: str, version: str) -> bool:
        return False

    async def poll_available(
        self,
        package_name: str,
        version: str,
        *,
        timeout: float = 300.0,
        interval: float = 5.0,
    ) -> bool:
        return True

    async def project_exists(self, package_name: str) -> bool:
        return False

    async def latest_version(self, package_name: str) -> str | None:
        return None

    async def verify_checksum(
        self,
        package_name: str,
        version: str,
        local_checksums: dict[str, str],
    ) -> ChecksumResult:
        return ChecksumResult()


class TestPrepareLabelOnNewPR:
    """Tests that autorelease: pending label is added to new PRs."""

    def _make_workspace(self, tmp_path: Path) -> Path:
        """Create a minimal workspace with one package."""
        ws = tmp_path / 'workspace'
        ws.mkdir()
        pkg_dir = ws / 'packages' / 'genkit'
        pkg_dir.mkdir(parents=True)
        pyproject = pkg_dir / 'pyproject.toml'
        pyproject.write_text(
            '[project]\nname = "genkit"\nversion = "0.1.0"\ndependencies = []\n\n[tool.uv]\ndev-dependencies = []\n',
            encoding='utf-8',
        )
        # Root pyproject with workspace config.
        root_pyproject = ws / 'pyproject.toml'
        root_pyproject.write_text(
            '[project]\nname = "workspace"\nversion = "0.0.0"\n\n[tool.uv.workspace]\nmembers = ["packages/*"]\n',
            encoding='utf-8',
        )
        # Minimal releasekit config.
        config_file = ws / 'releasekit.toml'
        config_file.write_text(
            '[releasekit]\ntag_format = "{name}-v{version}"\numbrella_tag = "v{version}"\n',
            encoding='utf-8',
        )
        # uv.lock stub.
        (ws / 'uv.lock').write_text('', encoding='utf-8')
        return ws

    def test_label_added_to_existing_pr(self, tmp_path: Path) -> None:
        """Label is added when updating an existing PR."""
        forge = _FakeForge(existing_prs=[{'number': 99, 'url': 'https://github.com/test/pr/99'}])
        vcs = _FakeVCS()
        config = ReleaseConfig()

        asyncio.run(
            prepare_release(
                vcs=vcs,
                pm=_FakePM(),
                forge=forge,
                registry=_FakeRegistry(),
                config=config,
                workspace_root=self._make_workspace(tmp_path),
                dry_run=False,
                force=True,
            ),
        )

        # Check that label was added to PR #99.
        label_prs = [pr for pr, labels in forge.labels_added if 'autorelease: pending' in labels]
        if 99 not in label_prs:
            raise AssertionError(f'Expected label on PR #99, got labels_added={forge.labels_added}')

    def test_label_added_to_new_pr(self, tmp_path: Path) -> None:
        """Label is added when creating a brand-new PR."""
        forge = _FakeForge(
            existing_prs=[],
            create_pr_url='https://github.com/test/pull/101',
        )
        vcs = _FakeVCS()
        config = ReleaseConfig()

        asyncio.run(
            prepare_release(
                vcs=vcs,
                pm=_FakePM(),
                forge=forge,
                registry=_FakeRegistry(),
                config=config,
                workspace_root=self._make_workspace(tmp_path),
                dry_run=False,
                force=True,
            ),
        )

        # Check that label was added to PR #101 (extracted from URL).
        label_prs = [pr for pr, labels in forge.labels_added if 'autorelease: pending' in labels]
        if 101 not in label_prs:
            raise AssertionError(f'Expected label on PR #101, got labels_added={forge.labels_added}')
