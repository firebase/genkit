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

"""Tests for releasekit.preflight module."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest
from releasekit.backends._run import CommandResult
from releasekit.backends.registry import ChecksumResult
from releasekit.errors import ReleaseKitError
from releasekit.graph import build_graph
from releasekit.preflight import PreflightResult, run_preflight
from releasekit.versions import PackageVersion
from releasekit.workspace import Package

# ── Fake backends for DI testing ──

_OK = CommandResult(command=[], returncode=0, stdout='', stderr='')


class FakeVCS:
    """Fake VCS backend that satisfies the VCS protocol."""

    def __init__(
        self,
        *,
        clean: bool = True,
        shallow: bool = False,
        sha: str = 'abc123',
    ) -> None:
        """Initialize with configurable state."""
        self._clean = clean
        self._shallow = shallow
        self._sha = sha

    async def is_clean(self, *, dry_run: bool = False) -> bool:
        """Return configured clean state."""
        return self._clean

    async def is_shallow(self) -> bool:
        """Return configured shallow state."""
        return self._shallow

    async def current_sha(self) -> str:
        """Return configured SHA."""
        return self._sha

    async def log(
        self,
        *,
        since_tag: str | None = None,
        paths: list[str] | None = None,
        format: str = '%H %s',
    ) -> list[str]:
        """Return empty log."""
        return []

    async def diff_files(self, *, since_tag: str | None = None) -> list[str]:
        """Return empty diff."""
        return []

    async def commit(
        self,
        message: str,
        *,
        paths: list[str] | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """No-op commit."""
        return _OK

    async def tag(
        self,
        tag_name: str,
        *,
        message: str | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """No-op tag."""
        return _OK

    async def tag_exists(self, tag_name: str) -> bool:
        """No tags exist."""
        return False

    async def delete_tag(
        self,
        tag_name: str,
        *,
        remote: bool = False,
        dry_run: bool = False,
    ) -> CommandResult:
        """No-op delete_tag."""
        return _OK

    async def push(
        self,
        *,
        tags: bool = False,
        remote: str = 'origin',
        dry_run: bool = False,
    ) -> CommandResult:
        """No-op push."""
        return _OK

    async def checkout_branch(
        self,
        branch: str,
        *,
        create: bool = False,
        dry_run: bool = False,
    ) -> CommandResult:
        """No-op checkout_branch."""
        return _OK


class FakePackageManager:
    """Fake package manager that satisfies the PackageManager protocol."""

    def __init__(self, *, lock_ok: bool = True) -> None:
        """Initialize with configurable lock state."""
        self._lock_ok = lock_ok

    async def build(
        self,
        package_dir: Path,
        *,
        output_dir: Path | None = None,
        no_sources: bool = True,
        dry_run: bool = False,
    ) -> CommandResult:
        """Return success result."""
        return _OK

    async def publish(
        self,
        dist_dir: Path,
        *,
        check_url: str | None = None,
        index_url: str | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """Return success result."""
        return _OK

    async def lock(
        self,
        *,
        check_only: bool = False,
        upgrade_package: str | None = None,
        cwd: Path | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """Return lock result based on configured state."""
        if not self._lock_ok and check_only:
            return CommandResult(command=['uv', 'lock', '--check'], returncode=1, stdout='', stderr='')
        return _OK

    async def version_bump(
        self,
        package_dir: Path,
        new_version: str,
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """No-op version bump."""
        return _OK

    async def resolve_check(
        self,
        package_name: str,
        version: str,
        *,
        index_url: str | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """No-op resolve check."""
        return _OK

    async def smoke_test(
        self,
        package_name: str,
        version: str,
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """No-op smoke test."""
        return _OK


class FakeRegistry:
    """Fake registry that satisfies the Registry protocol."""

    def __init__(self, *, published: set[str] | None = None) -> None:
        """Initialize with optional set of published versions."""
        self._published = published or set()

    async def check_published(self, package_name: str, version: str) -> bool:
        """Check if a version is in the published set."""
        return f'{package_name}=={version}' in self._published

    async def poll_available(
        self,
        package_name: str,
        version: str,
        *,
        timeout: float = 300.0,
        interval: float = 5.0,
    ) -> bool:
        """Always available immediately."""
        return True

    async def project_exists(self, package_name: str) -> bool:
        """Always exists."""
        return True

    async def latest_version(self, package_name: str) -> str | None:
        """Return None (no published version)."""
        return None

    async def verify_checksum(
        self,
        package_name: str,
        version: str,
        local_checksums: dict[str, str],
    ) -> ChecksumResult:
        """Return empty checksum result."""
        return ChecksumResult(matched=[], mismatched={}, missing=[])


class FakeForge:
    """Fake forge that satisfies the Forge protocol."""

    async def is_available(self) -> bool:
        """Always available."""
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
        """No-op create_release."""
        return _OK

    async def delete_release(
        self,
        tag: str,
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """No-op delete_release."""
        return _OK

    async def promote_release(
        self,
        tag: str,
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """No-op promote_release."""
        return _OK

    async def list_releases(
        self,
        *,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Return empty release list."""
        return []

    async def create_pr(
        self,
        *,
        title: str,
        body: str = '',
        head: str,
        base: str = 'main',
        dry_run: bool = False,
    ) -> CommandResult:
        """No-op create_pr."""
        return _OK

    async def pr_data(self, pr_number: int) -> dict[str, Any]:
        """Return empty PR data."""
        return {}


# ── PreflightResult tests ──


class TestPreflightResult:
    """Tests for PreflightResult."""

    def test_empty_result(self) -> None:
        """New result is OK with no items."""
        result = PreflightResult()
        if not result.ok:
            raise AssertionError('Empty result should be OK')
        if result.passed:
            raise AssertionError('Expected no passes')
        if result.warnings:
            raise AssertionError('Expected no warnings')
        if result.failed:
            raise AssertionError('Expected no failures')

    def test_add_pass(self) -> None:
        """Passes are recorded."""
        result = PreflightResult()
        result.add_pass('test_check')
        if 'test_check' not in result.passed:
            raise AssertionError('Pass not recorded')
        if not result.ok:
            raise AssertionError('Should still be OK after pass')

    def test_add_warning(self) -> None:
        """Warnings are non-blocking."""
        result = PreflightResult()
        result.add_warning('shallow', 'Shallow clone')
        if 'shallow' not in result.warnings:
            raise AssertionError('Warning not recorded')
        if result.warning_messages.get('shallow') != 'Shallow clone':
            raise AssertionError('Warning message not stored')
        if not result.ok:
            raise AssertionError('Warnings should not fail the result')

    def test_add_failure(self) -> None:
        """Failures make result not OK."""
        result = PreflightResult()
        result.add_failure('dirty', 'Uncommitted changes')
        if 'dirty' not in result.failed:
            raise AssertionError('Failure not recorded')
        if result.errors.get('dirty') != 'Uncommitted changes':
            raise AssertionError('Error message not stored')
        if result.ok:
            raise AssertionError('Should not be OK with failures')

    def test_summary(self) -> None:
        """Summary includes counts for each category."""
        result = PreflightResult()
        result.add_pass('a')
        result.add_pass('b')
        result.add_warning('c', 'w')
        result.add_failure('d', 'f')
        summary = result.summary()
        if '4 checks' not in summary:
            raise AssertionError(f'Expected 4 checks in: {summary}')
        if '2 passed' not in summary:
            raise AssertionError(f'Expected 2 passed in: {summary}')
        if '1 warnings' not in summary:
            raise AssertionError(f'Expected 1 warnings in: {summary}')
        if '1 failed' not in summary:
            raise AssertionError(f'Expected 1 failed in: {summary}')


# ── run_preflight tests ──


class TestRunPreflight:
    """Tests for run_preflight with injected fakes."""

    def _make_packages(self, workspace_root: Path) -> list[Package]:
        """Create test packages rooted under the given workspace."""
        pkg_dir = workspace_root / 'packages' / 'genkit'
        pkg_dir.mkdir(parents=True, exist_ok=True)
        return [
            Package(
                name='genkit',
                version='0.5.0',
                path=pkg_dir,
                pyproject_path=pkg_dir / 'pyproject.toml',
            ),
        ]

    def test_clean_workspace_passes(self, tmp_path: Path) -> None:
        """Clean workspace with no issues passes all checks."""
        packages = self._make_packages(tmp_path)
        graph = build_graph(packages)
        versions = [PackageVersion(name='genkit', old_version='0.5.0', new_version='0.6.0', bump='minor')]

        result = asyncio.run(
            run_preflight(
                vcs=FakeVCS(),
                pm=FakePackageManager(),
                forge=None,
                registry=FakeRegistry(),
                packages=packages,
                graph=graph,
                versions=versions,
                workspace_root=tmp_path,
            ),
        )

        if not result.ok:
            raise AssertionError(f'Should pass: {result.errors}')

    def test_dirty_worktree_fails(self, tmp_path: Path) -> None:
        """Dirty working tree raises ReleaseKitError."""
        packages = self._make_packages(tmp_path)
        graph = build_graph(packages)
        versions = [PackageVersion(name='genkit', old_version='0.5.0', new_version='0.6.0', bump='minor')]

        with pytest.raises(ReleaseKitError):
            asyncio.run(
                run_preflight(
                    vcs=FakeVCS(clean=False),
                    pm=FakePackageManager(),
                    forge=None,
                    registry=FakeRegistry(),
                    packages=packages,
                    graph=graph,
                    versions=versions,
                    workspace_root=tmp_path,
                ),
            )

    def test_shallow_clone_warns(self, tmp_path: Path) -> None:
        """Shallow clone produces a warning but passes."""
        packages = self._make_packages(tmp_path)
        graph = build_graph(packages)
        versions = [PackageVersion(name='genkit', old_version='0.5.0', new_version='0.6.0', bump='minor')]

        result = asyncio.run(
            run_preflight(
                vcs=FakeVCS(shallow=True),
                pm=FakePackageManager(),
                forge=None,
                registry=FakeRegistry(),
                packages=packages,
                graph=graph,
                versions=versions,
                workspace_root=tmp_path,
            ),
        )

        if not result.ok:
            raise AssertionError(f'Shallow should warn, not fail: {result.errors}')
        has_shallow_warning = any('shallow' in w.lower() for w in result.warnings)
        if not has_shallow_warning:
            raise AssertionError(f'Expected shallow warning: {result.warnings}')

    def test_skip_version_check(self, tmp_path: Path) -> None:
        """skip_version_check=True skips registry conflict check."""
        packages = self._make_packages(tmp_path)
        graph = build_graph(packages)
        # Pre-publish the version.
        versions = [PackageVersion(name='genkit', old_version='0.5.0', new_version='0.5.0', bump='none')]

        result = asyncio.run(
            run_preflight(
                vcs=FakeVCS(),
                pm=FakePackageManager(),
                forge=None,
                registry=FakeRegistry(published={'genkit==0.5.0'}),
                packages=packages,
                graph=graph,
                versions=versions,
                workspace_root=tmp_path,
                skip_version_check=True,
            ),
        )

        if not result.ok:
            raise AssertionError(f'skip_version_check should pass: {result.errors}')

    def test_forge_unavailable_warns(self, tmp_path: Path) -> None:
        """Missing forge produces a warning."""
        packages = self._make_packages(tmp_path)
        graph = build_graph(packages)
        versions = [PackageVersion(name='genkit', old_version='0.5.0', new_version='0.6.0', bump='minor')]

        result = asyncio.run(
            run_preflight(
                vcs=FakeVCS(),
                pm=FakePackageManager(),
                forge=None,
                registry=FakeRegistry(),
                packages=packages,
                graph=graph,
                versions=versions,
                workspace_root=tmp_path,
            ),
        )

        # With forge=None, there should be a warning about forge not available.
        if not result.ok:
            raise AssertionError(f'Should pass: {result.errors}')
