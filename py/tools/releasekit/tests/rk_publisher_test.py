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
from tests._fakes import OK as _OK, FakePM, FakeRegistry, FakeVCS


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


def _make_pkg(name: str, workspace_root: Path, *, version: str = '0.1.0') -> Package:
    """Create a test package directory with a pyproject.toml."""
    pkg_dir = workspace_root / 'packages' / name
    pkg_dir.mkdir(parents=True, exist_ok=True)
    pyproject = pkg_dir / 'pyproject.toml'
    pyproject.write_text(f'[project]\nname = "{name}"\nversion = "{version}"\n', encoding='utf-8')
    return Package(name=name, version=version, path=pkg_dir, manifest_path=pyproject)


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
        if config.max_retries != 3:
            raise AssertionError(f'Expected max_retries=3, got {config.max_retries}')

    def test_custom_values(self) -> None:
        """Custom config values are respected."""
        config = PublishConfig(
            concurrency=10,
            dry_run=True,
            check_url='https://test.pypi.org/simple/',
            registry_url='https://test.pypi.org/legacy/',
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
            manifest_path=plugin.manifest_path,
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


class TestPublishWorkspaceNonDryRun:
    """Tests for publish_workspace with real (non-dry-run) paths."""

    def test_build_no_dist_files(self, tmp_path: Path) -> None:
        """Build that produces no dist files records failure."""
        pkg = _make_pkg('genkit', tmp_path)
        graph = build_graph([pkg])
        versions = [PackageVersion(name='genkit', old_version='0.1.0', new_version='0.2.0', bump='minor')]
        config = PublishConfig(dry_run=False, workspace_root=tmp_path, smoke_test=False, verify_checksums=False)

        result = asyncio.run(
            publish_workspace(
                vcs=FakeVCS(),
                pm=FakePM(),  # No build_files → empty dist dir.
                forge=None,
                registry=FakeRegistry(),
                graph=graph,
                packages=[pkg],
                versions=versions,
                config=config,
            ),
        )

        assert not result.ok
        assert 'genkit' in result.failed
        assert 'No distribution files' in result.failed['genkit']

    def test_poll_timeout(self, tmp_path: Path) -> None:
        """Registry poll timeout records failure."""
        pkg = _make_pkg('genkit', tmp_path)
        graph = build_graph([pkg])
        versions = [PackageVersion(name='genkit', old_version='0.1.0', new_version='0.2.0', bump='minor')]
        config = PublishConfig(
            dry_run=False,
            workspace_root=tmp_path,
            smoke_test=False,
            verify_checksums=False,
            poll_timeout=0.1,
            poll_interval=0.05,
        )

        build_files = {
            'genkit-0.2.0.tar.gz': b'tarball',
            'genkit-0.2.0.whl': b'wheel',
        }

        result = asyncio.run(
            publish_workspace(
                vcs=FakeVCS(),
                pm=FakePM(build_files=build_files),
                forge=None,
                registry=FakeRegistry(available=False),
                graph=graph,
                packages=[pkg],
                versions=versions,
                config=config,
            ),
        )

        assert not result.ok
        assert 'genkit' in result.failed
        assert 'not available on registry' in result.failed['genkit']

    def test_checksum_mismatch(self, tmp_path: Path) -> None:
        """Checksum mismatch records failure."""
        pkg = _make_pkg('genkit', tmp_path)
        graph = build_graph([pkg])
        versions = [PackageVersion(name='genkit', old_version='0.1.0', new_version='0.2.0', bump='minor')]
        config = PublishConfig(
            dry_run=False,
            workspace_root=tmp_path,
            smoke_test=False,
            verify_checksums=True,
        )

        build_files = {
            'genkit-0.2.0.tar.gz': b'tarball',
            'genkit-0.2.0.whl': b'wheel',
        }

        result = asyncio.run(
            publish_workspace(
                vcs=FakeVCS(),
                pm=FakePM(build_files=build_files),
                forge=None,
                registry=FakeRegistry(checksums_ok=False),
                graph=graph,
                packages=[pkg],
                versions=versions,
                config=config,
            ),
        )

        assert not result.ok
        assert 'genkit' in result.failed
        assert 'Checksum verification failed' in result.failed['genkit']

    def test_smoke_test_runs(self, tmp_path: Path) -> None:
        """Smoke test is invoked when enabled."""
        pkg = _make_pkg('genkit', tmp_path)
        graph = build_graph([pkg])
        versions = [PackageVersion(name='genkit', old_version='0.1.0', new_version='0.2.0', bump='minor')]
        config = PublishConfig(
            dry_run=False,
            workspace_root=tmp_path,
            smoke_test=True,
            verify_checksums=False,
        )

        smoke_called: list[str] = []

        class SmokePM(FakePM):
            async def build(
                self,
                package_dir: Path,
                *,
                output_dir: Path | None = None,
                no_sources: bool = True,
                dry_run: bool = False,
            ) -> CommandResult:
                """Build."""
                if output_dir:
                    (output_dir / 'genkit-0.2.0.whl').write_bytes(b'wheel')
                return _OK

            async def smoke_test(self, package_name: str, version: str, *, dry_run: bool = False) -> CommandResult:
                """Smoke test."""
                smoke_called.append(package_name)
                return _OK

        result = asyncio.run(
            publish_workspace(
                vcs=FakeVCS(),
                pm=SmokePM(),
                forge=None,
                registry=FakeRegistry(),
                graph=graph,
                packages=[pkg],
                versions=versions,
                config=config,
            ),
        )

        assert result.ok
        assert 'genkit' in smoke_called

    def test_unexpected_error_wrapped(self, tmp_path: Path) -> None:
        """Unexpected exception during publish is wrapped and recorded."""
        pkg = _make_pkg('genkit', tmp_path)
        graph = build_graph([pkg])
        versions = [PackageVersion(name='genkit', old_version='0.1.0', new_version='0.2.0', bump='minor')]
        config = PublishConfig(dry_run=False, workspace_root=tmp_path, smoke_test=False, verify_checksums=False)

        class BoomPM(FakePM):
            async def build(
                self,
                package_dir: Path,
                *,
                output_dir: Path | None = None,
                no_sources: bool = True,
                dry_run: bool = False,
            ) -> CommandResult:
                """Build."""
                raise RuntimeError('unexpected boom')

        result = asyncio.run(
            publish_workspace(
                vcs=FakeVCS(),
                pm=BoomPM(),
                forge=None,
                registry=FakeRegistry(),
                graph=graph,
                packages=[pkg],
                versions=versions,
                config=config,
            ),
        )

        assert not result.ok
        assert 'genkit' in result.failed
        assert 'Unexpected error' in result.failed['genkit']

    def test_workspace_label_state_file(self, tmp_path: Path) -> None:
        """State file uses workspace label when configured."""
        pkg = _make_pkg('genkit', tmp_path)
        graph = build_graph([pkg])
        versions = [PackageVersion(name='genkit', old_version='0.1.0', new_version='0.2.0', bump='minor')]
        config = PublishConfig(dry_run=True, workspace_root=tmp_path, workspace_label='py')

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
            ),
        )

        state_path = tmp_path / '.releasekit-state--py.json'
        assert state_path.is_file(), f'Expected state file at {state_path}'
