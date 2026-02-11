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

"""Tests for releasekit.publisher module."""

from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Sequence
from pathlib import Path

import pytest
from releasekit.backends._run import CommandResult
from releasekit.backends.registry import ChecksumResult
from releasekit.graph import build_graph
from releasekit.observer import PublishObserver, PublishStage
from releasekit.publisher import (
    PublishConfig,
    PublishResult,
    _build_version_map,
    _compute_dist_checksum,
    publish_workspace,
)
from releasekit.versions import PackageVersion
from releasekit.workspace import Package

# ── Fake backends ──

_OK = CommandResult(command=[], returncode=0, stdout='', stderr='')


class FakeVCS:
    """Fake VCS backend."""

    def __init__(self, *, sha: str = 'abc123') -> None:
        """Initialize instance."""
        self._sha = sha

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
        return []

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


class FakePM:
    """Fake PackageManager backend."""

    def __init__(self, *, build_files: dict[str, bytes] | None = None) -> None:
        """Initialize instance."""
        self._build_files = build_files or {}

    async def build(
        self,
        package_dir: Path,
        *,
        output_dir: Path | None = None,
        no_sources: bool = True,
        dry_run: bool = False,
    ) -> CommandResult:
        """Build."""
        if output_dir and self._build_files:
            for name, content in self._build_files.items():
                (output_dir / name).write_bytes(content)
        return _OK

    async def publish(
        self,
        dist_dir: Path,
        *,
        check_url: str | None = None,
        index_url: str | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """Publish."""
        return _OK

    async def lock(
        self,
        *,
        check_only: bool = False,
        upgrade_package: str | None = None,
        cwd: Path | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """Lock."""
        return _OK

    async def version_bump(
        self,
        package_dir: Path,
        new_version: str,
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Version bump."""
        return _OK

    async def resolve_check(
        self,
        package_name: str,
        version: str,
        *,
        index_url: str | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """Resolve check."""
        return _OK

    async def smoke_test(
        self,
        package_name: str,
        version: str,
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Smoke test."""
        return _OK


class FakeRegistry:
    """Fake registry backend."""

    def __init__(self, *, available: bool = True, checksums_ok: bool = True) -> None:
        """Initialize instance."""
        self._available = available
        self._checksums_ok = checksums_ok

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
        return self._available

    async def project_exists(self, package_name: str) -> bool:
        """Project exists."""
        return True

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
        if self._checksums_ok:
            return ChecksumResult(matched=list(local_checksums.keys()), mismatched={}, missing=[])
        return ChecksumResult(
            matched=[],
            mismatched={'bad.whl': ('aaa', 'bbb')},
            missing=[],
        )


class FakeForge:
    """Fake forge backend."""

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
        return {}

    async def list_prs(
        self,
        *,
        label: str = '',
        state: str = 'open',
        head: str = '',
        limit: int = 10,
    ) -> list[dict[str, str | int | list[str]]]:
        """List prs."""
        return []

    async def add_labels(
        self,
        pr_number: int,
        labels: list[str],
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Add labels."""
        return _OK

    async def remove_labels(
        self,
        pr_number: int,
        labels: list[str],
        *,
        dry_run: bool = False,
    ) -> CommandResult:
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


class SpyObserver(PublishObserver):
    """Observer that records all events for assertions."""

    def __init__(self) -> None:
        """Initialize instance."""
        self.inited: list[tuple[str, int, str]] = []
        self.stages: list[tuple[str, PublishStage]] = []
        self.errors: list[tuple[str, str]] = []
        self.completed: bool = False

    def init_packages(self, packages: Sequence[tuple[str, int, str]]) -> None:
        """Init packages."""
        self.inited = list(packages)

    def on_stage(self, name: str, stage: PublishStage) -> None:
        """On stage."""
        self.stages.append((name, stage))

    def on_error(self, name: str, error: str) -> None:
        """On error."""
        self.errors.append((name, error))

    def on_complete(self) -> None:
        """On complete."""
        self.completed = True


# ── Helpers ──


def _make_pkg(name: str, workspace_root: Path, *, version: str = '0.1.0') -> Package:
    """Create a test package directory with a pyproject.toml."""
    pkg_dir = workspace_root / 'packages' / name
    pkg_dir.mkdir(parents=True, exist_ok=True)
    pyproject = pkg_dir / 'pyproject.toml'
    pyproject.write_text(f'[project]\nname = "{name}"\nversion = "{version}"\n', encoding='utf-8')
    return Package(name=name, version=version, path=pkg_dir, pyproject_path=pyproject)


# ── Tests: PublishConfig ──


class TestPublishConfig:
    """Tests for PublishConfig defaults and construction."""

    def test_defaults(self) -> None:
        """Default config has sensible values."""
        config = PublishConfig()
        if config.concurrency != 5:
            raise AssertionError(f'Expected concurrency=5, got {config.concurrency}')
        if config.dry_run:
            raise AssertionError('Expected dry_run=False')
        if not config.smoke_test:
            raise AssertionError('Expected smoke_test=True')
        if not config.verify_checksums:
            raise AssertionError('Expected verify_checksums=True')
        if config.max_retries != 0:
            raise AssertionError(f'Expected max_retries=0, got {config.max_retries}')

    def test_custom_values(self) -> None:
        """Custom config values are respected."""
        config = PublishConfig(
            concurrency=10,
            dry_run=True,
            check_url='https://test.pypi.org/simple/',
            index_url='https://test.pypi.org/legacy/',
            poll_timeout=60.0,
        )
        if config.concurrency != 10:
            raise AssertionError(f'Expected 10, got {config.concurrency}')
        if not config.dry_run:
            raise AssertionError('Expected dry_run=True')
        if config.check_url != 'https://test.pypi.org/simple/':
            raise AssertionError(f'Unexpected check_url: {config.check_url}')

    def test_frozen(self) -> None:
        """PublishConfig is immutable."""
        config = PublishConfig()
        with pytest.raises(AttributeError):
            config.concurrency = 99  # type: ignore[misc]


# ── Tests: PublishResult ──


class TestPublishResult:
    """Tests for PublishResult."""

    def test_empty_result(self) -> None:
        """Empty result is OK."""
        result = PublishResult()
        if not result.ok:
            raise AssertionError('Empty result should be OK')
        if result.summary() != 'no packages processed':
            raise AssertionError(f'Unexpected summary: {result.summary()}')

    def test_with_published(self) -> None:
        """Published packages appear in summary."""
        result = PublishResult(published=['a', 'b'])
        if not result.ok:
            raise AssertionError('Should be OK with published only')
        if '2 published' not in result.summary():
            raise AssertionError(f'Expected "2 published" in: {result.summary()}')

    def test_with_failures(self) -> None:
        """Failed packages make result not OK."""
        result = PublishResult(failed={'a': 'boom'})
        if result.ok:
            raise AssertionError('Should not be OK with failures')
        if '1 failed' not in result.summary():
            raise AssertionError(f'Expected "1 failed" in: {result.summary()}')

    def test_mixed_summary(self) -> None:
        """Summary includes all categories."""
        result = PublishResult(published=['a'], skipped=['b'], failed={'c': 'err'})
        summary = result.summary()
        if '1 published' not in summary:
            raise AssertionError(f'Missing "1 published" in: {summary}')
        if '1 skipped' not in summary:
            raise AssertionError(f'Missing "1 skipped" in: {summary}')
        if '1 failed' not in summary:
            raise AssertionError(f'Missing "1 failed" in: {summary}')


# ── Tests: helper functions ──


class TestBuildVersionMap:
    """Tests for _build_version_map."""

    def test_filters_skipped(self) -> None:
        """Skipped packages are excluded."""
        versions = [
            PackageVersion(name='a', old_version='1.0.0', new_version='1.1.0', bump='minor'),
            PackageVersion(name='b', old_version='2.0.0', new_version='2.0.0', bump='none', skipped=True),
        ]
        vmap = _build_version_map(versions)
        if 'a' not in vmap:
            raise AssertionError('Expected a in version map')
        if 'b' in vmap:
            raise AssertionError('Skipped package should not be in version map')

    def test_empty(self) -> None:
        """Empty input gives empty map."""
        if _build_version_map([]):
            raise AssertionError('Expected empty map')


class TestComputeDistChecksum:
    """Tests for _compute_dist_checksum."""

    def test_computes_checksums(self, tmp_path: Path) -> None:
        """Computes SHA-256 for .whl and .tar.gz files."""
        whl = tmp_path / 'pkg-1.0.0.whl'
        whl.write_bytes(b'wheel content')
        tar = tmp_path / 'pkg-1.0.0.tar.gz'
        tar.write_bytes(b'tarball content')
        txt = tmp_path / 'readme.txt'
        txt.write_bytes(b'ignored')

        checksums = _compute_dist_checksum(tmp_path)
        if len(checksums) != 2:
            raise AssertionError(f'Expected 2 checksums, got {len(checksums)}')
        if checksums['pkg-1.0.0.whl'] != hashlib.sha256(b'wheel content').hexdigest():
            raise AssertionError('Wrong whl checksum')
        if checksums['pkg-1.0.0.tar.gz'] != hashlib.sha256(b'tarball content').hexdigest():
            raise AssertionError('Wrong tar.gz checksum')

    def test_empty_dir(self, tmp_path: Path) -> None:
        """Empty directory gives empty checksums."""
        if _compute_dist_checksum(tmp_path):
            raise AssertionError('Expected empty checksums')


# ── Tests: publish_workspace (dry_run) ──


class TestPublishWorkspaceDryRun:
    """Tests for publish_workspace in dry_run mode."""

    def test_all_skipped(self, tmp_path: Path) -> None:
        """All skipped packages gives empty result."""
        pkg = _make_pkg('genkit', tmp_path)
        graph = build_graph([pkg])
        versions = [PackageVersion(name='genkit', old_version='0.1.0', new_version='0.1.0', bump='none', skipped=True)]
        config = PublishConfig(dry_run=True, workspace_root=tmp_path)

        result = asyncio.run(
            publish_workspace(
                vcs=FakeVCS(),
                pm=FakePM(),
                forge=None,
                registry=FakeRegistry(),
                graph=graph,
                packages=[pkg],
                versions=versions,
                config=config,
            ),
        )

        if not result.ok:
            raise AssertionError(f'Should be OK: {result.failed}')
        if 'genkit' not in result.skipped:
            raise AssertionError(f'Expected genkit in skipped: {result.skipped}')
        if result.published:
            raise AssertionError(f'Expected no published: {result.published}')

    def test_single_package_dry_run(self, tmp_path: Path) -> None:
        """Single package publishes successfully in dry_run."""
        pkg = _make_pkg('genkit', tmp_path)
        graph = build_graph([pkg])
        versions = [PackageVersion(name='genkit', old_version='0.1.0', new_version='0.2.0', bump='minor')]
        config = PublishConfig(dry_run=True, workspace_root=tmp_path)
        observer = SpyObserver()

        result = asyncio.run(
            publish_workspace(
                vcs=FakeVCS(),
                pm=FakePM(),
                forge=None,
                registry=FakeRegistry(),
                graph=graph,
                packages=[pkg],
                versions=versions,
                config=config,
                observer=observer,
            ),
        )

        if not result.ok:
            raise AssertionError(f'Should be OK: {result.failed}')
        if 'genkit' not in result.published:
            raise AssertionError(f'Expected genkit published: {result.published}')
        if not observer.completed:
            raise AssertionError('Observer should have been completed')

    def test_multi_level_packages(self, tmp_path: Path) -> None:
        """Packages across levels publish in order."""
        core = _make_pkg('core', tmp_path)
        plugin = _make_pkg('plugin', tmp_path)
        plugin_pkg = Package(
            name='plugin',
            version='0.1.0',
            path=plugin.path,
            pyproject_path=plugin.pyproject_path,
            internal_deps=['core'],
        )
        graph = build_graph([core, plugin_pkg])
        versions = [
            PackageVersion(name='core', old_version='0.1.0', new_version='0.2.0', bump='minor'),
            PackageVersion(name='plugin', old_version='0.1.0', new_version='0.1.1', bump='patch'),
        ]
        config = PublishConfig(dry_run=True, workspace_root=tmp_path)

        result = asyncio.run(
            publish_workspace(
                vcs=FakeVCS(),
                pm=FakePM(),
                forge=None,
                registry=FakeRegistry(),
                graph=graph,
                packages=[core, plugin_pkg],
                versions=versions,
                config=config,
            ),
        )

        if not result.ok:
            raise AssertionError(f'Should be OK: {result.failed}')
        if len(result.published) != 2:
            raise AssertionError(f'Expected 2 published, got {len(result.published)}')

    def test_observer_receives_events(self, tmp_path: Path) -> None:
        """Observer is notified at each stage."""
        pkg = _make_pkg('genkit', tmp_path)
        graph = build_graph([pkg])
        versions = [PackageVersion(name='genkit', old_version='0.1.0', new_version='0.2.0', bump='minor')]
        config = PublishConfig(dry_run=True, workspace_root=tmp_path)
        observer = SpyObserver()

        asyncio.run(
            publish_workspace(
                vcs=FakeVCS(),
                pm=FakePM(),
                forge=None,
                registry=FakeRegistry(),
                graph=graph,
                packages=[pkg],
                versions=versions,
                config=config,
                observer=observer,
            ),
        )

        if not observer.inited:
            raise AssertionError('Observer should have been initialized')
        if not observer.completed:
            raise AssertionError('Observer should have been completed')
        stage_names = [s.name for _, s in observer.stages]
        if 'PINNING' not in stage_names:
            raise AssertionError(f'Missing PINNING stage: {stage_names}')
        if 'BUILDING' not in stage_names:
            raise AssertionError(f'Missing BUILDING stage: {stage_names}')

    def test_state_persisted(self, tmp_path: Path) -> None:
        """Run state is saved to disk after publish."""
        pkg = _make_pkg('genkit', tmp_path)
        graph = build_graph([pkg])
        versions = [PackageVersion(name='genkit', old_version='0.1.0', new_version='0.2.0', bump='minor')]
        config = PublishConfig(dry_run=True, workspace_root=tmp_path)

        result = asyncio.run(
            publish_workspace(
                vcs=FakeVCS(),
                pm=FakePM(),
                forge=None,
                registry=FakeRegistry(),
                graph=graph,
                packages=[pkg],
                versions=versions,
                config=config,
            ),
        )

        state_path = tmp_path / '.releasekit-state.json'
        if not state_path.is_file():
            raise AssertionError('State file should exist')
        if result.state is None:
            raise AssertionError('Result should have state')

    def test_null_observer_used_when_none(self, tmp_path: Path) -> None:
        """No observer defaults to NullProgressUI without crashing."""
        pkg = _make_pkg('genkit', tmp_path)
        graph = build_graph([pkg])
        versions = [PackageVersion(name='genkit', old_version='0.1.0', new_version='0.2.0', bump='minor')]
        config = PublishConfig(dry_run=True, workspace_root=tmp_path)

        # Should not raise — NullProgressUI handles all calls.
        result = asyncio.run(
            publish_workspace(
                vcs=FakeVCS(),
                pm=FakePM(),
                forge=None,
                registry=FakeRegistry(),
                graph=graph,
                packages=[pkg],
                versions=versions,
                config=config,
                observer=None,
            ),
        )
        if not result.ok:
            raise AssertionError(f'Should be OK: {result.failed}')
