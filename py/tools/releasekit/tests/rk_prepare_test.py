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
from unittest.mock import AsyncMock, patch

import pytest
from releasekit.backends._run import CommandResult
from releasekit.backends.registry import ChecksumResult
from releasekit.config import ReleaseConfig, WorkspaceConfig
from releasekit.preflight import PreflightResult
from releasekit.prepare import (
    _GITHUB_BODY_LIMIT,
    PrepareResult,
    _build_pr_body,
    _embed_manifest,
    _package_paths,
    prepare_release,
)
from releasekit.versions import PackageVersion
from releasekit.workspace import Package
from tests._fakes import OK as _OK, FakePM as _FakePM, FakeVCS as _BaseFakeVCS


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
        """PR body includes changelogs for all packages in details blocks."""
        changelogs = {
            'a': '## a\n- fix',
            'b': '## b\n- feat',
        }
        body = _build_pr_body(changelogs, '{}', '1.0.0')
        if '## a' not in body:
            raise AssertionError('Missing changelog for a')
        if '## b' not in body:
            raise AssertionError('Missing changelog for b')
        # Changelogs should be in collapsible details.
        if '<details>' not in body:
            raise AssertionError('Missing details block')

    def test_embeds_manifest(self) -> None:
        """PR body contains embedded release manifest."""
        body = _build_pr_body({}, '{"x":1}', '1.0.0')
        if '<!-- releasekit:manifest:start -->' not in body:
            raise AssertionError('Missing manifest')

    def test_includes_summary_table(self) -> None:
        """PR body includes a summary table with package names."""
        changelogs = {
            'genkit': '## 0.2.0 (2026-01-01)\n- feat: new',
            'genkit-plugin-x': '## 0.2.0 (2026-01-01)\n- fix: bug',
        }
        body = _build_pr_body(changelogs, '{}', '0.2.0')
        if '`genkit`' not in body:
            raise AssertionError('Missing genkit in summary table')
        if '`genkit-plugin-x`' not in body:
            raise AssertionError('Missing genkit-plugin-x in summary table')
        if '| Package |' not in body:
            raise AssertionError('Missing table header')

    def test_truncates_when_too_large(self) -> None:
        """Body is truncated; largest changelogs are dropped first."""
        # Create changelogs of varying sizes: most are small, a few are huge.
        changelogs: dict[str, str] = {}
        for i in range(80):
            # Small changelogs (~30 chars each).
            changelogs[f'small-{i:03d}'] = f'## 0.1.{i}\n\n- fix: minor\n'
        for i in range(10):
            # Huge changelogs (~10 KB each → 100 KB total, exceeds limit).
            changelogs[f'huge-{i:02d}'] = f'## 1.0.{i}\n\n' + ('- feat: a very big change\n' * 400)

        manifest = '{"test": true}'
        body = _build_pr_body(changelogs, manifest, '1.0.0')

        if len(body) > _GITHUB_BODY_LIMIT:
            raise AssertionError(f'Body exceeds limit: {len(body)} > {_GITHUB_BODY_LIMIT}')
        # Manifest must always be present.
        if '<!-- releasekit:manifest:start -->' not in body:
            raise AssertionError('Missing manifest in truncated body')
        # Truncation notice should appear.
        if 'omitted' not in body:
            raise AssertionError('Missing truncation notice')
        # Small changelogs should be included (they fit).
        if '<b>small-000</b>' not in body:
            raise AssertionError('Small changelog was dropped but should be included')
        # Huge changelogs should be the ones dropped (largest first).
        # At least some huge ones should be missing from the body.
        huge_in_body = sum(1 for i in range(10) if f'<b>huge-{i:02d}</b>' in body)
        if huge_in_body == 10:
            raise AssertionError('All huge changelogs included — expected some to be dropped')


class TestPackagePaths:
    """Tests for _package_paths."""

    def test_builds_name_to_path_map(self, tmp_path: object) -> None:
        """Maps package names to their directory paths."""
        pkg_path = Path('/workspace/packages/genkit')
        pkg = Package(
            name='genkit',
            version='0.1.0',
            path=pkg_path,
            manifest_path=pkg_path / 'pyproject.toml',
        )
        paths = _package_paths([pkg])
        if paths.get('genkit') != str(pkg_path):
            raise AssertionError(f'Unexpected path: {paths}')

    def test_empty_packages(self) -> None:
        """Empty input returns empty map."""
        if _package_paths([]):
            raise AssertionError('Expected empty map')


# _FakePM is imported directly from tests._fakes (see top of file).


class _FakeVCS(_BaseFakeVCS):
    """FakeVCS with prepare-specific defaults."""

    def __init__(self, *, log_lines: list[str] | None = None, **kwargs: object) -> None:
        """Init  ."""
        super().__init__(
            log_lines=log_lines if log_lines is not None else ['aaa1111 feat: initial'],
            diff_files=['packages/genkit/src/main.py'],
            **kwargs,  # type: ignore[arg-type]
        )


class _FakeForge:
    """Forge that records label operations and simulates PR creation."""

    def __init__(self, *, existing_prs: list[dict[str, Any]] | None = None, create_pr_url: str = '') -> None:
        """Init  ."""
        self._existing_prs = existing_prs or []
        self._create_pr_url = create_pr_url
        self.labels_added: list[tuple[int, list[str]]] = []

    async def is_available(self) -> bool:
        """Is available."""
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
        """Create release."""
        return _OK

    async def delete_release(self, tag: str, *, dry_run: bool = False) -> CommandResult:
        """Delete release."""
        return _OK

    async def promote_release(self, tag: str, *, dry_run: bool = False) -> CommandResult:
        """Promote release."""
        return _OK

    async def list_releases(self, *, limit: int = 10) -> list[dict[str, Any]]:
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
        return CommandResult(command=[], return_code=0, stdout=self._create_pr_url, stderr='')

    async def pr_data(self, pr_number: int) -> dict[str, Any]:
        """Pr data."""
        return {}

    async def list_prs(
        self,
        *,
        label: str = '',
        state: str = 'open',
        head: str = '',
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """List prs."""
        return self._existing_prs

    async def add_labels(self, pr_number: int, labels: list[str], *, dry_run: bool = False) -> CommandResult:
        """Add labels."""
        self.labels_added.append((pr_number, labels))
        return _OK

    async def remove_labels(self, pr_number: int, labels: list[str], *, dry_run: bool = False) -> CommandResult:
        """Remove labels."""
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


class _FakeRegistry:
    """Minimal registry for prepare tests."""

    async def check_published(self, package_name: str, version: str) -> bool:
        """Check published."""
        return False

    async def poll_available(
        self,
        package_name: str,
        version: str,
        *,
        timeout: float = 300.0,
        interval: float = 5.0,
    ) -> bool:
        """Poll available."""
        return True

    async def project_exists(self, package_name: str) -> bool:
        """Project exists."""
        return False

    async def latest_version(self, package_name: str) -> str | None:
        """Latest version."""
        return None

    async def verify_checksum(
        self,
        package_name: str,
        version: str,
        local_checksums: dict[str, str],
    ) -> ChecksumResult:
        """Verify checksum."""
        return ChecksumResult()

    async def list_versions(self, package_name: str) -> list[str]:
        """List versions."""
        return []

    async def yank_version(
        self,
        package_name: str,
        version: str,
        *,
        reason: str = '',
        dry_run: bool = False,
    ) -> bool:
        """Yank version."""
        return False


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
            '[workspace.uv]\ntag_format = "{name}-v{version}"\numbrella_tag = "v{version}"\n',
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
        ws_config = WorkspaceConfig()

        asyncio.run(
            prepare_release(
                vcs=vcs,
                pm=_FakePM(),
                forge=forge,
                registry=_FakeRegistry(),
                config=config,
                ws_config=ws_config,
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
        ws_config = WorkspaceConfig()

        asyncio.run(
            prepare_release(
                vcs=vcs,
                pm=_FakePM(),
                forge=forge,
                registry=_FakeRegistry(),
                config=config,
                ws_config=ws_config,
                workspace_root=self._make_workspace(tmp_path),
                dry_run=False,
                force=True,
            ),
        )

        # Check that label was added to PR #101 (extracted from URL).
        label_prs = [pr for pr, labels in forge.labels_added if 'autorelease: pending' in labels]
        if 101 not in label_prs:
            raise AssertionError(f'Expected label on PR #101, got labels_added={forge.labels_added}')


class TestPrepareNoBumps:
    """Tests for prepare_release when no packages have changes."""

    def _make_workspace(self, tmp_path: Path) -> Path:
        """Create a minimal workspace with one package."""
        ws = tmp_path / 'workspace'
        ws.mkdir()
        pkg_dir = ws / 'packages' / 'genkit'
        pkg_dir.mkdir(parents=True)
        pyproject = pkg_dir / 'pyproject.toml'
        pyproject.write_text(
            '[project]\nname = "genkit"\nversion = "0.1.0"\ndependencies = []\n',
            encoding='utf-8',
        )
        root_pyproject = ws / 'pyproject.toml'
        root_pyproject.write_text(
            '[project]\nname = "workspace"\nversion = "0.0.0"\n\n[tool.uv.workspace]\nmembers = ["packages/*"]\n',
            encoding='utf-8',
        )
        return ws

    def test_no_bumps_returns_early(self, tmp_path: Path) -> None:
        """No version bumps returns empty result with no errors."""
        vcs = _FakeVCS(log_lines=[])
        config = ReleaseConfig()
        ws_config = WorkspaceConfig()

        # Mock compute_bumps to return all-skipped versions.
        mock_bumps = AsyncMock(
            return_value=[
                PackageVersion(name='genkit', old_version='0.1.0', new_version='0.1.0', bump='none', skipped=True),
            ]
        )

        with patch('releasekit.prepare.compute_bumps', mock_bumps):
            result = asyncio.run(
                prepare_release(
                    vcs=vcs,
                    pm=_FakePM(),
                    forge=None,
                    registry=_FakeRegistry(),
                    config=config,
                    ws_config=ws_config,
                    workspace_root=self._make_workspace(tmp_path),
                    dry_run=False,
                    force=True,
                ),
            )

        assert result.ok
        assert not result.bumped
        assert not result.pr_url


class TestPrepareDryRun:
    """Tests for prepare_release in dry_run mode."""

    def _make_workspace(self, tmp_path: Path) -> Path:
        """Make workspace."""
        ws = tmp_path / 'workspace'
        ws.mkdir()
        pkg_dir = ws / 'packages' / 'genkit'
        pkg_dir.mkdir(parents=True)
        pyproject = pkg_dir / 'pyproject.toml'
        pyproject.write_text(
            '[project]\nname = "genkit"\nversion = "0.1.0"\ndependencies = []\n',
            encoding='utf-8',
        )
        root_pyproject = ws / 'pyproject.toml'
        root_pyproject.write_text(
            '[project]\nname = "workspace"\nversion = "0.0.0"\n\n[tool.uv.workspace]\nmembers = ["packages/*"]\n',
            encoding='utf-8',
        )
        return ws

    def test_dry_run_skips_side_effects(self, tmp_path: Path) -> None:
        """Dry run produces result without writing files or creating PRs."""
        vcs = _FakeVCS()
        config = ReleaseConfig()
        ws_config = WorkspaceConfig()

        result = asyncio.run(
            prepare_release(
                vcs=vcs,
                pm=_FakePM(),
                forge=None,
                registry=_FakeRegistry(),
                config=config,
                ws_config=ws_config,
                workspace_root=self._make_workspace(tmp_path),
                dry_run=True,
                force=True,
            ),
        )

        assert result.ok
        assert result.bumped
        assert result.manifest is not None
        # No PR URL since forge is None.
        assert not result.pr_url


class TestPrepareAutoMerge:
    """Tests for auto-merge functionality."""

    def _make_workspace(self, tmp_path: Path) -> Path:
        """Make workspace."""
        ws = tmp_path / 'workspace'
        ws.mkdir()
        pkg_dir = ws / 'packages' / 'genkit'
        pkg_dir.mkdir(parents=True)
        pyproject = pkg_dir / 'pyproject.toml'
        pyproject.write_text(
            '[project]\nname = "genkit"\nversion = "0.1.0"\ndependencies = []\n',
            encoding='utf-8',
        )
        root_pyproject = ws / 'pyproject.toml'
        root_pyproject.write_text(
            '[project]\nname = "workspace"\nversion = "0.0.0"\n\n[tool.uv.workspace]\nmembers = ["packages/*"]\n',
            encoding='utf-8',
        )
        return ws

    def test_auto_merge_on_new_pr(self, tmp_path: Path) -> None:
        """Auto-merge is attempted when ws_config.auto_merge is True."""
        merge_calls: list[int] = []

        class MergeForge(_FakeForge):
            def __init__(self) -> None:
                """Init  ."""
                super().__init__(existing_prs=[], create_pr_url='https://github.com/test/pull/42')

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
                merge_calls.append(pr_number)
                return _OK

        config = ReleaseConfig()
        ws_config = WorkspaceConfig(auto_merge=True)

        asyncio.run(
            prepare_release(
                vcs=_FakeVCS(),
                pm=_FakePM(),
                forge=MergeForge(),
                registry=_FakeRegistry(),
                config=config,
                ws_config=ws_config,
                workspace_root=self._make_workspace(tmp_path),
                dry_run=False,
                force=True,
            ),
        )

        assert 42 in merge_calls, f'Expected merge on PR #42, got {merge_calls}'

    def test_auto_merge_failure_logged(self, tmp_path: Path) -> None:
        """Failed auto-merge does not crash prepare_release."""

        class FailMergeForge(_FakeForge):
            def __init__(self) -> None:
                """Init  ."""
                super().__init__(existing_prs=[], create_pr_url='https://github.com/test/pull/42')

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
                return CommandResult(command=[], return_code=1, stdout='', stderr='merge failed')

        config = ReleaseConfig()
        ws_config = WorkspaceConfig(auto_merge=True)

        # Should not raise — failure is logged as warning.
        result = asyncio.run(
            prepare_release(
                vcs=_FakeVCS(),
                pm=_FakePM(),
                forge=FailMergeForge(),
                registry=_FakeRegistry(),
                config=config,
                ws_config=ws_config,
                workspace_root=self._make_workspace(tmp_path),
                dry_run=False,
                force=True,
            ),
        )

        assert result.ok


class TestPreparePreflightFailure:
    """Tests for prepare_release when preflight fails."""

    def _make_workspace(self, tmp_path: Path) -> Path:
        """Create a minimal workspace with one package."""
        ws = tmp_path / 'workspace'
        ws.mkdir()
        pkg_dir = ws / 'packages' / 'genkit'
        pkg_dir.mkdir(parents=True)
        pyproject = pkg_dir / 'pyproject.toml'
        pyproject.write_text(
            '[project]\nname = "genkit"\nversion = "0.1.0"\ndependencies = []\n',
            encoding='utf-8',
        )
        root_pyproject = ws / 'pyproject.toml'
        root_pyproject.write_text(
            '[project]\nname = "workspace"\nversion = "0.0.0"\n\n[tool.uv.workspace]\nmembers = ["packages/*"]\n',
            encoding='utf-8',
        )
        return ws

    def test_preflight_failure_returns_errors(self, tmp_path: Path) -> None:
        """Preflight failure populates result.errors and returns early."""
        vcs = _FakeVCS()
        config = ReleaseConfig()
        ws_config = WorkspaceConfig()

        failed_preflight = PreflightResult()
        failed_preflight.add_failure('dirty_worktree', 'Uncommitted changes')

        with patch('releasekit.prepare.run_preflight', AsyncMock(return_value=failed_preflight)):
            result = asyncio.run(
                prepare_release(
                    vcs=vcs,
                    pm=_FakePM(),
                    forge=None,
                    registry=_FakeRegistry(),
                    config=config,
                    ws_config=ws_config,
                    workspace_root=self._make_workspace(tmp_path),
                    dry_run=False,
                    force=False,
                ),
            )

        assert not result.ok
        assert 'preflight:dirty_worktree' in result.errors


class TestPrepareExtraFiles:
    """Tests for extra_files bumping in prepare_release."""

    def _make_workspace(self, tmp_path: Path) -> Path:
        """Create a workspace with an extra file containing a version."""
        ws = tmp_path / 'workspace'
        ws.mkdir()
        pkg_dir = ws / 'packages' / 'genkit'
        pkg_dir.mkdir(parents=True)
        pyproject = pkg_dir / 'pyproject.toml'
        pyproject.write_text(
            '[project]\nname = "genkit"\nversion = "0.1.0"\ndependencies = []\n',
            encoding='utf-8',
        )
        root_pyproject = ws / 'pyproject.toml'
        root_pyproject.write_text(
            '[project]\nname = "workspace"\nversion = "0.0.0"\n\n[tool.uv.workspace]\nmembers = ["packages/*"]\n',
            encoding='utf-8',
        )
        init_file = ws / 'packages' / 'genkit' / '__init__.py'
        init_file.write_text("__version__ = '0.1.0'\n", encoding='utf-8')
        return ws

    def test_extra_files_with_pattern(self, tmp_path: Path) -> None:
        """Extra files with colon-separated pattern are processed."""
        ws = self._make_workspace(tmp_path)
        config = ReleaseConfig()
        ws_config = WorkspaceConfig(
            extra_files=['packages/genkit/__init__.py:__version__'],
        )

        result = asyncio.run(
            prepare_release(
                vcs=_FakeVCS(),
                pm=_FakePM(),
                forge=None,
                registry=_FakeRegistry(),
                config=config,
                ws_config=ws_config,
                workspace_root=ws,
                dry_run=False,
                force=True,
            ),
        )

        assert result.ok
        assert result.bumped

    def test_extra_files_without_pattern(self, tmp_path: Path) -> None:
        """Extra files without pattern are processed."""
        ws = self._make_workspace(tmp_path)
        config = ReleaseConfig()
        ws_config = WorkspaceConfig(
            extra_files=['packages/genkit/__init__.py'],
        )

        result = asyncio.run(
            prepare_release(
                vcs=_FakeVCS(),
                pm=_FakePM(),
                forge=None,
                registry=_FakeRegistry(),
                config=config,
                ws_config=ws_config,
                workspace_root=ws,
                dry_run=False,
                force=True,
            ),
        )

        assert result.ok

    def test_extra_files_nonexistent_skipped(self, tmp_path: Path) -> None:
        """Non-existent extra files are silently skipped."""
        ws = self._make_workspace(tmp_path)
        config = ReleaseConfig()
        ws_config = WorkspaceConfig(
            extra_files=['nonexistent/file.py'],
        )

        result = asyncio.run(
            prepare_release(
                vcs=_FakeVCS(),
                pm=_FakePM(),
                forge=None,
                registry=_FakeRegistry(),
                config=config,
                ws_config=ws_config,
                workspace_root=ws,
                dry_run=False,
                force=True,
            ),
        )

        assert result.ok


class TestPreparePushFailure:
    """Tests for push failure in prepare_release."""

    def _make_workspace(self, tmp_path: Path) -> Path:
        """Create a minimal workspace."""
        ws = tmp_path / 'workspace'
        ws.mkdir()
        pkg_dir = ws / 'packages' / 'genkit'
        pkg_dir.mkdir(parents=True)
        pyproject = pkg_dir / 'pyproject.toml'
        pyproject.write_text(
            '[project]\nname = "genkit"\nversion = "0.1.0"\ndependencies = []\n',
            encoding='utf-8',
        )
        root_pyproject = ws / 'pyproject.toml'
        root_pyproject.write_text(
            '[project]\nname = "workspace"\nversion = "0.0.0"\n\n[tool.uv.workspace]\nmembers = ["packages/*"]\n',
            encoding='utf-8',
        )
        return ws

    def test_push_failure_raises(self, tmp_path: Path) -> None:
        """Push failure raises RuntimeError."""

        class FailPushVCS(_FakeVCS):
            """VCS that fails on push."""

            async def push(
                self,
                *,
                tags: bool = False,
                remote: str = 'origin',
                set_upstream: bool = True,
                dry_run: bool = False,
            ) -> CommandResult:
                """Fail push."""
                return CommandResult(
                    command=['git', 'push'],
                    return_code=1,
                    stdout='',
                    stderr='push rejected',
                )

        config = ReleaseConfig()
        ws_config = WorkspaceConfig()

        with pytest.raises(RuntimeError, match='push rejected'):
            asyncio.run(
                prepare_release(
                    vcs=FailPushVCS(),
                    pm=_FakePM(),
                    forge=None,
                    registry=_FakeRegistry(),
                    config=config,
                    ws_config=ws_config,
                    workspace_root=self._make_workspace(tmp_path),
                    dry_run=False,
                    force=True,
                ),
            )


class TestPreparePRCreationFailure:
    """Tests for PR creation failure in prepare_release."""

    def _make_workspace(self, tmp_path: Path) -> Path:
        """Create a minimal workspace."""
        ws = tmp_path / 'workspace'
        ws.mkdir()
        pkg_dir = ws / 'packages' / 'genkit'
        pkg_dir.mkdir(parents=True)
        pyproject = pkg_dir / 'pyproject.toml'
        pyproject.write_text(
            '[project]\nname = "genkit"\nversion = "0.1.0"\ndependencies = []\n',
            encoding='utf-8',
        )
        root_pyproject = ws / 'pyproject.toml'
        root_pyproject.write_text(
            '[project]\nname = "workspace"\nversion = "0.0.0"\n\n[tool.uv.workspace]\nmembers = ["packages/*"]\n',
            encoding='utf-8',
        )
        return ws

    def test_pr_creation_failure_raises(self, tmp_path: Path) -> None:
        """PR creation failure raises RuntimeError."""

        class FailCreatePRForge(_FakeForge):
            """Forge that fails to create PR."""

            async def create_pr(
                self,
                *,
                title: str = '',
                body: str = '',
                head: str = '',
                base: str = 'main',
                dry_run: bool = False,
            ) -> CommandResult:
                """Fail create PR."""
                return CommandResult(
                    command=['gh', 'pr', 'create'],
                    return_code=1,
                    stdout='',
                    stderr='API rate limit exceeded',
                )

        config = ReleaseConfig()
        ws_config = WorkspaceConfig()

        with pytest.raises(RuntimeError, match='API rate limit'):
            asyncio.run(
                prepare_release(
                    vcs=_FakeVCS(),
                    pm=_FakePM(),
                    forge=FailCreatePRForge(existing_prs=[]),
                    registry=_FakeRegistry(),
                    config=config,
                    ws_config=ws_config,
                    workspace_root=self._make_workspace(tmp_path),
                    dry_run=False,
                    force=True,
                ),
            )


class TestPreparePRNumberParsing:
    """Tests for PR number extraction from URL edge cases."""

    def _make_workspace(self, tmp_path: Path) -> Path:
        """Create a minimal workspace."""
        ws = tmp_path / 'workspace'
        ws.mkdir()
        pkg_dir = ws / 'packages' / 'genkit'
        pkg_dir.mkdir(parents=True)
        pyproject = pkg_dir / 'pyproject.toml'
        pyproject.write_text(
            '[project]\nname = "genkit"\nversion = "0.1.0"\ndependencies = []\n',
            encoding='utf-8',
        )
        root_pyproject = ws / 'pyproject.toml'
        root_pyproject.write_text(
            '[project]\nname = "workspace"\nversion = "0.0.0"\n\n[tool.uv.workspace]\nmembers = ["packages/*"]\n',
            encoding='utf-8',
        )
        return ws

    def test_unparseable_pr_url_does_not_crash(self, tmp_path: Path) -> None:
        """PR URL that cannot be parsed for a number does not crash."""

        class BadURLForge(_FakeForge):
            """Forge that returns a non-numeric PR URL."""

            async def create_pr(
                self,
                *,
                title: str = '',
                body: str = '',
                head: str = '',
                base: str = 'main',
                dry_run: bool = False,
            ) -> CommandResult:
                """Return a URL with no numeric PR number."""
                return CommandResult(
                    command=[],
                    return_code=0,
                    stdout='https://github.com/test/pull/not-a-number',
                    stderr='',
                )

        config = ReleaseConfig()
        ws_config = WorkspaceConfig()

        result = asyncio.run(
            prepare_release(
                vcs=_FakeVCS(),
                pm=_FakePM(),
                forge=BadURLForge(existing_prs=[]),
                registry=_FakeRegistry(),
                config=config,
                ws_config=ws_config,
                workspace_root=self._make_workspace(tmp_path),
                dry_run=False,
                force=True,
            ),
        )

        assert result.ok
        assert result.pr_url


class TestPreparePackageNotFound:
    """Tests for bumped package not found in workspace."""

    def _make_workspace(self, tmp_path: Path) -> Path:
        """Create a minimal workspace with one package."""
        ws = tmp_path / 'workspace'
        ws.mkdir()
        pkg_dir = ws / 'packages' / 'genkit'
        pkg_dir.mkdir(parents=True)
        pyproject = pkg_dir / 'pyproject.toml'
        pyproject.write_text(
            '[project]\nname = "genkit"\nversion = "0.1.0"\ndependencies = []\n',
            encoding='utf-8',
        )
        root_pyproject = ws / 'pyproject.toml'
        root_pyproject.write_text(
            '[project]\nname = "workspace"\nversion = "0.0.0"\n\n[tool.uv.workspace]\nmembers = ["packages/*"]\n',
            encoding='utf-8',
        )
        return ws

    def test_bumped_package_not_in_workspace(self, tmp_path: Path) -> None:
        """Bumped package missing from workspace records an error."""
        vcs = _FakeVCS()
        config = ReleaseConfig()
        ws_config = WorkspaceConfig()

        # Return a bump for a package that doesn't exist in the workspace.
        mock_bumps = AsyncMock(
            return_value=[
                PackageVersion(
                    name='nonexistent-pkg',
                    old_version='0.1.0',
                    new_version='0.2.0',
                    bump='minor',
                ),
            ]
        )

        with patch('releasekit.prepare.compute_bumps', mock_bumps):
            result = asyncio.run(
                prepare_release(
                    vcs=vcs,
                    pm=_FakePM(),
                    forge=None,
                    registry=_FakeRegistry(),
                    config=config,
                    ws_config=ws_config,
                    workspace_root=self._make_workspace(tmp_path),
                    dry_run=False,
                    force=True,
                ),
            )

        assert 'bump:nonexistent-pkg' in result.errors
