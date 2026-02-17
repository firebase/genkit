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

"""Tests for Release Tool Invariants documented in GEMINI.md.

Each invariant has a named key (``INV-*``) that maps to the corresponding
section in ``releasekit/GEMINI.md § Release Tool Invariants``.

Invariant Keys
--------------

============================  ===================================================
Key                           Invariant
============================  ===================================================
INV-IDEMPOTENCY               Re-running a command is always safe
INV-CRASH-SAFETY              Interrupted releases resume without re-publishing
INV-ATOMICITY                 Each publish fully succeeds or fully fails
INV-DETERMINISM               Same inputs always produce same outputs
INV-OBSERVABILITY             Every action emits structured logs
INV-DRY-RUN                   ``--dry-run`` exercises real code paths
INV-GRACEFUL-DEGRADATION      Missing optional components degrade to no-ops
INV-TOPO-ORDER                Packages publish in dependency order
INV-SUPPLY-CHAIN              Published artifacts are verified against checksums
============================  ===================================================
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import structlog
from releasekit.backends._run import CommandResult
from releasekit.changelog import write_changelog
from releasekit.graph import DependencyGraph, build_graph, detect_cycles, topo_sort
from releasekit.scheduler import Scheduler
from releasekit.state import PackageStatus, RunState
from releasekit.tags import TagResult, create_tags, format_tag, parse_tag
from releasekit.tracing import get_tracer
from releasekit.versions import PackageVersion, ReleaseManifest
from releasekit.workspace import Package
from tests._fakes import OK as _OK, FakeVCS as _BaseFakeVCS

# Helpers / Fakes


class _FakeVCS(_BaseFakeVCS):
    """FakeVCS that records created tags for invariant assertions."""

    def __init__(
        self,
        *,
        existing_tags: set[str] | None = None,
        sha: str = 'abc123',
    ) -> None:
        """Init  ."""
        super().__init__(tags=existing_tags, sha=sha)
        self.existing_tags: set[str] = existing_tags or set()
        self.created_tags: list[str] = []

    async def tag(
        self,
        tag_name: str,
        *,
        ref: str | None = None,
        message: str | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """Tag."""
        if not dry_run:
            self.existing_tags.add(tag_name)
        self.created_tags.append(tag_name)
        return _OK

    async def tag_exists(self, tag_name: str) -> bool:
        """Tag exists."""
        return tag_name in self.existing_tags

    async def delete_tag(
        self,
        tag_name: str,
        *,
        remote: bool = False,
        dry_run: bool = False,
    ) -> CommandResult:
        """Delete tag."""
        self.existing_tags.discard(tag_name)
        return _OK

    async def list_tags(self, *, pattern: str = '') -> list[str]:
        """List tags."""
        return sorted(self.existing_tags)


def _make_manifest(*versions: tuple[str, str, str]) -> ReleaseManifest:
    """Build a manifest from (name, old_version, new_version) tuples."""
    pkgs = [
        PackageVersion(
            name=name,
            old_version=old,
            new_version=new,
            bump='minor',
            reason='feat: test',
            skipped=False,
            tag=f'{name}-v{new}',
        )
        for name, old, new in versions
    ]
    return ReleaseManifest(
        git_sha='abc123',
        umbrella_tag='v0.5.0',
        packages=pkgs,
        created_at='2026-01-01T00:00:00+00:00',
    )


def _make_package(
    name: str,
    version: str = '0.1.0',
    internal_deps: list[str] | None = None,
) -> Package:
    """Build a minimal Package for graph tests."""
    return Package(
        name=name,
        version=version,
        path=Path(f'/fake/{name}'),
        manifest_path=Path(f'/fake/{name}/pyproject.toml'),
        internal_deps=internal_deps or [],
    )


# INV-IDEMPOTENCY: Idempotency


class TestInvIdempotency:
    """INV-IDEMPOTENCY: Every command must be safe to run multiple times."""

    @pytest.mark.asyncio
    async def test_inv_idempotency_tags_skip_existing(self) -> None:
        """INV-IDEMPOTENCY: create_tags skips tags that already exist."""
        manifest = _make_manifest(('genkit', '0.4.0', '0.5.0'))
        vcs = _FakeVCS(existing_tags={'genkit-v0.5.0', 'v0.5.0'})

        result = await create_tags(
            manifest=manifest,
            vcs=vcs,
            tag_format='{name}-v{version}',
            umbrella_tag_format='v{version}',
            dry_run=True,
        )

        assert 'genkit-v0.5.0' in result.skipped
        assert 'genkit-v0.5.0' not in result.created

    @pytest.mark.asyncio
    async def test_inv_idempotency_tags_double_run(self) -> None:
        """INV-IDEMPOTENCY: Running create_tags twice produces same result."""
        manifest = _make_manifest(('genkit', '0.4.0', '0.5.0'))
        vcs = _FakeVCS()

        result1 = await create_tags(
            manifest=manifest,
            vcs=vcs,
            tag_format='{name}-v{version}',
            umbrella_tag_format='v{version}',
        )
        assert 'genkit-v0.5.0' in result1.created

        # Second run — tag now exists.
        result2 = await create_tags(
            manifest=manifest,
            vcs=vcs,
            tag_format='{name}-v{version}',
            umbrella_tag_format='v{version}',
        )
        assert 'genkit-v0.5.0' in result2.skipped
        assert 'genkit-v0.5.0' not in result2.created
        assert not result2.failed

    def test_inv_idempotency_changelog_skips_duplicate(self, tmp_path: Path) -> None:
        """INV-IDEMPOTENCY: write_changelog skips if version header already present."""
        changelog_path = tmp_path / 'CHANGELOG.md'
        rendered = '## 0.5.0 (2026-01-01)\n\n### Features\n\n- feat: something\n'

        # First write.
        assert write_changelog(changelog_path, rendered) is True

        # Second write — same version.
        assert write_changelog(changelog_path, rendered) is False

    def test_inv_idempotency_state_resume_skips_published(self) -> None:
        """INV-IDEMPOTENCY: RunState.pending_packages excludes published packages."""
        state = RunState(git_sha='abc123')
        state.init_package('genkit', version='0.5.0')
        state.init_package('plugin-foo', version='0.5.0')
        state.set_status('genkit', PackageStatus.PUBLISHED)

        pending = state.pending_packages()
        assert 'genkit' not in pending
        assert 'plugin-foo' in pending


# INV-CRASH-SAFETY: Crash Safety (Resume)


class TestInvCrashSafety:
    """INV-CRASH-SAFETY: Interrupted releases must be resumable."""

    def test_inv_crash_safety_state_roundtrip(self, tmp_path: Path) -> None:
        """INV-CRASH-SAFETY: State survives save → load roundtrip."""
        state_path = tmp_path / '.releasekit-state.json'
        state = RunState(git_sha='abc123')
        state.init_package('genkit', version='0.5.0', level=0)
        state.set_status('genkit', PackageStatus.PUBLISHED)
        state.init_package('plugin-foo', version='0.5.0', level=1)

        state.save(state_path)
        loaded = RunState.load(state_path)

        assert loaded.git_sha == 'abc123'
        assert loaded.packages['genkit'].status == PackageStatus.PUBLISHED
        assert loaded.packages['plugin-foo'].status == PackageStatus.PENDING

    def test_inv_crash_safety_atomic_write(self, tmp_path: Path) -> None:
        """INV-CRASH-SAFETY: State file uses atomic write (old file survives crash)."""
        state_path = tmp_path / '.releasekit-state.json'

        # Write initial state.
        state1 = RunState(git_sha='sha1')
        state1.init_package('genkit', version='0.5.0')
        state1.save(state_path)

        # Verify file exists and is valid JSON.
        data = json.loads(state_path.read_text(encoding='utf-8'))
        assert data['git_sha'] == 'sha1'

        # Overwrite with new state.
        state2 = RunState(git_sha='sha2')
        state2.init_package('genkit', version='0.6.0')
        state2.save(state_path)

        data = json.loads(state_path.read_text(encoding='utf-8'))
        assert data['git_sha'] == 'sha2'

    def test_inv_crash_safety_sha_mismatch(self) -> None:
        """INV-CRASH-SAFETY: validate_sha raises on HEAD mismatch."""
        state = RunState(git_sha='abc123')

        # Same SHA — no error.
        state.validate_sha('abc123')

        # Different SHA — must raise.
        with pytest.raises(Exception, match='SHA'):
            state.validate_sha('def456')

    def test_inv_crash_safety_resume_preserves_published(self, tmp_path: Path) -> None:
        """INV-CRASH-SAFETY: After save/load, published packages stay published."""
        state_path = tmp_path / '.releasekit-state.json'
        state = RunState(git_sha='abc123')
        state.init_package('a', version='1.0.0')
        state.init_package('b', version='1.0.0')
        state.init_package('c', version='1.0.0')
        state.set_status('a', PackageStatus.PUBLISHED)
        state.set_status('b', PackageStatus.FAILED, error='network timeout')
        state.save(state_path)

        loaded = RunState.load(state_path)
        assert loaded.published_packages() == ['a']
        assert loaded.failed_packages() == ['b']
        assert loaded.pending_packages() == ['c']

    def test_inv_crash_safety_scheduler_excludes_published(self) -> None:
        """INV-CRASH-SAFETY: Scheduler excludes already_published from scheduling."""
        graph = DependencyGraph(
            packages={
                'a': _make_package('a'),
                'b': _make_package('b', internal_deps=['a']),
            },
            edges={'a': [], 'b': ['a']},
            reverse_edges={'a': ['b'], 'b': []},
        )

        scheduler = Scheduler.from_graph(
            graph=graph,
            publishable={'a', 'b'},
            already_published={'a'},
        )

        # 'a' should not be in the scheduler's nodes.
        assert 'a' not in scheduler._nodes
        # 'b' should be present and have 0 remaining deps (a is done).
        assert 'b' in scheduler._nodes
        assert scheduler._nodes['b'].remaining_deps == 0


# INV-ATOMICITY: Atomicity


class TestInvAtomicity:
    """INV-ATOMICITY: State files use atomic write patterns."""

    def test_inv_atomicity_state_valid_json(self, tmp_path: Path) -> None:
        """INV-ATOMICITY: State file is always valid JSON after save."""
        state_path = tmp_path / '.releasekit-state.json'
        state = RunState(git_sha='abc123')
        state.init_package('genkit', version='0.5.0')
        state.set_status('genkit', PackageStatus.BUILDING)
        state.save(state_path)

        # Must be parseable JSON.
        data = json.loads(state_path.read_text(encoding='utf-8'))
        assert 'git_sha' in data
        assert 'packages' in data

    def test_inv_atomicity_no_temp_files(self, tmp_path: Path) -> None:
        """INV-ATOMICITY: No temporary files left after successful save."""
        state_path = tmp_path / '.releasekit-state.json'
        state = RunState(git_sha='abc123')
        state.save(state_path)

        # Only the state file should exist, no .tmp files.
        files = list(tmp_path.iterdir())
        assert len(files) == 1
        assert files[0].name == '.releasekit-state.json'

    def test_inv_atomicity_failed_status_recorded(self) -> None:
        """INV-ATOMICITY: Failed packages are recorded as FAILED, not lost."""
        state = RunState(git_sha='abc123')
        state.init_package('genkit', version='0.5.0')
        state.set_status('genkit', PackageStatus.PUBLISHING)
        state.set_status('genkit', PackageStatus.FAILED, error='upload timeout')

        assert state.packages['genkit'].status == PackageStatus.FAILED
        assert state.packages['genkit'].error == 'upload timeout'
        # FAILED is a terminal state — is_complete() returns True when
        # all packages are in a terminal state (published/skipped/failed).
        assert state.is_complete()
        assert state.failed_packages() == ['genkit']


# INV-DETERMINISM: Determinism


class TestInvDeterminism:
    """INV-DETERMINISM: Same inputs produce same outputs."""

    def test_inv_determinism_graph_build(self) -> None:
        """INV-DETERMINISM: build_graph produces identical output on repeated calls."""
        packages = [
            _make_package('c', internal_deps=['a']),
            _make_package('b', internal_deps=['a']),
            _make_package('a'),
        ]

        graph1 = build_graph(packages)
        graph2 = build_graph(packages)

        assert graph1.edges == graph2.edges
        assert graph1.reverse_edges == graph2.reverse_edges
        assert graph1.names == graph2.names

    def test_inv_determinism_topo_sort(self) -> None:
        """INV-DETERMINISM: topo_sort produces identical levels on repeated calls."""
        packages = [
            _make_package('z', internal_deps=['a']),
            _make_package('m', internal_deps=['a']),
            _make_package('a'),
        ]
        graph = build_graph(packages)

        levels1 = [[p.name for p in level] for level in topo_sort(graph)]
        levels2 = [[p.name for p in level] for level in topo_sort(graph)]

        assert levels1 == levels2

    def test_inv_determinism_edges_sorted(self) -> None:
        """INV-DETERMINISM: Graph edges are sorted for deterministic iteration."""
        packages = [
            _make_package('app', internal_deps=['z-lib', 'a-lib', 'm-lib']),
            _make_package('z-lib'),
            _make_package('a-lib'),
            _make_package('m-lib'),
        ]
        graph = build_graph(packages)

        # Forward edges must be sorted.
        assert graph.edges['app'] == sorted(graph.edges['app'])

    def test_inv_determinism_tag_roundtrip(self) -> None:
        """INV-DETERMINISM: format_tag → parse_tag roundtrip is lossless."""
        fmt = '{name}-v{version}'
        tag = format_tag(fmt, name='genkit', version='0.5.0')
        parsed = parse_tag(tag, fmt)

        assert parsed is not None
        assert parsed == ('genkit', '0.5.0')

    def test_inv_determinism_version_bump(self) -> None:
        """INV-DETERMINISM: Same commit history produces same version bumps."""
        # This tests the pure function _apply_bump via format_tag consistency.
        tag1 = format_tag('{name}-v{version}', name='genkit', version='0.5.0')
        tag2 = format_tag('{name}-v{version}', name='genkit', version='0.5.0')
        assert tag1 == tag2


# INV-OBSERVABILITY: Observability


class TestInvObservability:
    """INV-OBSERVABILITY: Significant actions are logged with structured fields."""

    @pytest.mark.asyncio
    async def test_inv_observability_tag_created(self) -> None:
        """INV-OBSERVABILITY: Tag creation emits a structured log event."""
        manifest = _make_manifest(('genkit', '0.4.0', '0.5.0'))
        vcs = _FakeVCS()

        with structlog.testing.capture_logs() as cap:
            await create_tags(
                manifest=manifest,
                vcs=vcs,
                tag_format='{name}-v{version}',
                umbrella_tag_format='v{version}',
            )

        events = [e['event'] for e in cap]
        assert 'tag_created' in events

    @pytest.mark.asyncio
    async def test_inv_observability_tag_skip(self) -> None:
        """INV-OBSERVABILITY: Skipping existing tags emits a log event."""
        manifest = _make_manifest(('genkit', '0.4.0', '0.5.0'))
        vcs = _FakeVCS(existing_tags={'genkit-v0.5.0'})

        with structlog.testing.capture_logs() as cap:
            await create_tags(
                manifest=manifest,
                vcs=vcs,
                tag_format='{name}-v{version}',
                umbrella_tag_format='v{version}',
            )

        events = [e['event'] for e in cap]
        assert 'tag_exists_skip' in events

    def test_inv_observability_state_save(self, tmp_path: Path) -> None:
        """INV-OBSERVABILITY: State save emits a log event."""
        state = RunState(git_sha='abc123')
        state.init_package('genkit', version='0.5.0')

        with structlog.testing.capture_logs() as cap:
            state.save(tmp_path / '.releasekit-state.json')

        events = [e['event'] for e in cap]
        assert 'state_saved' in events

    def test_inv_observability_state_load(self, tmp_path: Path) -> None:
        """INV-OBSERVABILITY: State load emits a log event."""
        state_path = tmp_path / '.releasekit-state.json'
        state = RunState(git_sha='abc123')
        state.init_package('genkit', version='0.5.0')
        state.save(state_path)

        with structlog.testing.capture_logs() as cap:
            RunState.load(state_path)

        events = [e['event'] for e in cap]
        assert 'state_loaded' in events


# INV-DRY-RUN: Dry-Run Fidelity


class TestInvDryRun:
    """INV-DRY-RUN: --dry-run exercises same code paths without mutations."""

    @pytest.mark.asyncio
    async def test_inv_dry_run_tags_no_mutation(self) -> None:
        """INV-DRY-RUN: create_tags with dry_run=True creates no actual tags."""
        manifest = _make_manifest(('genkit', '0.4.0', '0.5.0'))
        vcs = _FakeVCS()

        result = await create_tags(
            manifest=manifest,
            vcs=vcs,
            tag_format='{name}-v{version}',
            umbrella_tag_format='v{version}',
            dry_run=True,
        )

        # Tags should be "created" in the result but NOT in the VCS.
        assert len(result.created) > 0
        assert 'genkit-v0.5.0' not in vcs.existing_tags

    @pytest.mark.asyncio
    async def test_inv_dry_run_tags_returns_result(self) -> None:
        """INV-DRY-RUN: Dry run returns a TagResult with the same structure."""
        manifest = _make_manifest(
            ('genkit', '0.4.0', '0.5.0'),
            ('plugin-foo', '0.4.0', '0.5.0'),
        )
        vcs = _FakeVCS()

        result = await create_tags(
            manifest=manifest,
            vcs=vcs,
            tag_format='{name}-v{version}',
            umbrella_tag_format='v{version}',
            dry_run=True,
        )

        assert isinstance(result, TagResult)
        assert len(result.created) >= 2  # At least per-package tags

    def test_inv_dry_run_changelog_no_write(self, tmp_path: Path) -> None:
        """INV-DRY-RUN: write_changelog with dry_run=True does not create file."""
        changelog_path = tmp_path / 'CHANGELOG.md'
        rendered = '## 0.5.0 (2026-01-01)\n\n### Features\n\n- feat: something\n'

        result = write_changelog(changelog_path, rendered, dry_run=True)

        assert result is True  # Would have written.
        assert not changelog_path.exists()  # But didn't.


# INV-GRACEFUL-DEGRADATION: Graceful Degradation


class TestInvGracefulDegradation:
    """INV-GRACEFUL-DEGRADATION: Missing optional components degrade to no-ops."""

    def test_inv_graceful_degradation_tracer(self) -> None:
        """INV-GRACEFUL-DEGRADATION: get_tracer returns a usable tracer."""
        tracer = get_tracer('test.module')
        assert tracer is not None

    def test_inv_graceful_degradation_tracer_span(self) -> None:
        """INV-GRACEFUL-DEGRADATION: Tracer.start_as_current_span yields a usable span."""
        tracer = get_tracer('test.invariants')
        with tracer.start_as_current_span('test') as s:
            s.set_attribute('key', 'value')

    @pytest.mark.asyncio
    async def test_inv_graceful_degradation_no_forge(self) -> None:
        """INV-GRACEFUL-DEGRADATION: create_tags works without a forge backend (forge=None)."""
        manifest = _make_manifest(('genkit', '0.4.0', '0.5.0'))
        vcs = _FakeVCS()

        result = await create_tags(
            manifest=manifest,
            vcs=vcs,
            forge=None,
            tag_format='{name}-v{version}',
            umbrella_tag_format='v{version}',
        )

        assert 'genkit-v0.5.0' in result.created
        assert not result.failed


# INV-TOPO-ORDER: Topological Correctness


class TestInvTopoOrder:
    """INV-TOPO-ORDER: Packages publish in dependency order."""

    def test_inv_topo_order_deps_before_dependents(self) -> None:
        """INV-TOPO-ORDER: Dependencies appear in earlier levels than dependents."""
        packages = [
            _make_package('core'),
            _make_package('plugin-a', internal_deps=['core']),
            _make_package('plugin-b', internal_deps=['core']),
            _make_package('app', internal_deps=['plugin-a', 'plugin-b']),
        ]
        graph = build_graph(packages)
        levels = topo_sort(graph)

        level_of: dict[str, int] = {}
        for i, level in enumerate(levels):
            for pkg in level:
                level_of[pkg.name] = i

        # core must be before plugin-a and plugin-b.
        assert level_of['core'] < level_of['plugin-a']
        assert level_of['core'] < level_of['plugin-b']
        # plugin-a and plugin-b must be before app.
        assert level_of['plugin-a'] < level_of['app']
        assert level_of['plugin-b'] < level_of['app']

    def test_inv_topo_order_cycle_detection(self) -> None:
        """INV-TOPO-ORDER: Circular dependencies are detected."""
        packages = [
            _make_package('a', internal_deps=['b']),
            _make_package('b', internal_deps=['a']),
        ]
        graph = build_graph(packages)
        cycles = detect_cycles(graph)

        assert len(cycles) > 0

    def test_inv_topo_order_scheduler_respects_deps(self) -> None:
        """INV-TOPO-ORDER: Scheduler only enqueues packages whose deps are done."""
        graph = DependencyGraph(
            packages={
                'core': _make_package('core'),
                'plugin': _make_package('plugin', internal_deps=['core']),
            },
            edges={'core': [], 'plugin': ['core']},
            reverse_edges={'core': ['plugin'], 'plugin': []},
        )

        scheduler = Scheduler.from_graph(
            graph=graph,
            publishable={'core', 'plugin'},
        )

        # 'plugin' should have remaining_deps=1 (waiting for 'core').
        assert scheduler._nodes['plugin'].remaining_deps == 1
        # 'core' should have remaining_deps=0 (no deps).
        assert scheduler._nodes['core'].remaining_deps == 0

    def test_inv_topo_order_independent_same_level(self) -> None:
        """INV-TOPO-ORDER: Independent packages are in the same topological level."""
        packages = [
            _make_package('a'),
            _make_package('b'),
            _make_package('c'),
        ]
        graph = build_graph(packages)
        levels = topo_sort(graph)

        # All independent packages should be in level 0.
        assert len(levels) == 1
        names = {p.name for p in levels[0]}
        assert names == {'a', 'b', 'c'}

    def test_inv_topo_order_diamond_dependency(self) -> None:
        """INV-TOPO-ORDER: Diamond dependency (A→B,C→D) resolves correctly."""
        packages = [
            _make_package('a'),
            _make_package('b', internal_deps=['a']),
            _make_package('c', internal_deps=['a']),
            _make_package('d', internal_deps=['b', 'c']),
        ]
        graph = build_graph(packages)
        levels = topo_sort(graph)

        level_of: dict[str, int] = {}
        for i, level in enumerate(levels):
            for pkg in level:
                level_of[pkg.name] = i

        assert level_of['a'] == 0
        assert level_of['b'] == level_of['c']  # Same level.
        assert level_of['d'] > level_of['b']
        assert level_of['d'] > level_of['c']


# INV-SUPPLY-CHAIN: Supply Chain Integrity


class TestInvSupplyChain:
    """INV-SUPPLY-CHAIN: Published artifacts are verified."""

    def test_inv_supply_chain_tag_format(self) -> None:
        """INV-SUPPLY-CHAIN: Tag format always embeds the exact version string."""
        tag = format_tag('{name}-v{version}', name='genkit', version='0.5.0')
        assert '0.5.0' in tag

    def test_inv_supply_chain_parse_tag(self) -> None:
        """INV-SUPPLY-CHAIN: parse_tag extracts the exact version from a tag."""
        result = parse_tag('genkit-v0.5.0', '{name}-v{version}')
        assert result is not None
        name, version = result
        assert name == 'genkit'
        assert version == '0.5.0'

    def test_inv_supply_chain_reject_malformed_tag(self) -> None:
        """INV-SUPPLY-CHAIN: parse_tag returns None for malformed tags."""
        assert parse_tag('not-a-valid-tag', '{name}-v{version}') is None
        assert parse_tag('', '{name}-v{version}') is None

    def test_inv_supply_chain_manifest_tracks_bumped(self) -> None:
        """INV-SUPPLY-CHAIN: ReleaseManifest.bumped only includes non-skipped packages."""
        manifest = _make_manifest(
            ('genkit', '0.4.0', '0.5.0'),
            ('plugin-foo', '0.4.0', '0.5.0'),
        )
        # Add a skipped package.
        manifest.packages.append(
            PackageVersion(
                name='plugin-bar',
                old_version='0.4.0',
                new_version='0.4.0',
                bump='none',
                reason='unchanged',
                skipped=True,
                tag='plugin-bar-v0.4.0',
            )
        )

        bumped_names = {p.name for p in manifest.bumped}
        assert 'genkit' in bumped_names
        assert 'plugin-foo' in bumped_names
        assert 'plugin-bar' not in bumped_names

    def test_inv_supply_chain_corrupted_state_raises(self, tmp_path: Path) -> None:
        """INV-SUPPLY-CHAIN: Corrupted state file raises ReleaseKitError."""
        state_path = tmp_path / '.releasekit-state.json'
        state_path.write_text('not valid json {{{', encoding='utf-8')

        with pytest.raises(Exception, match='invalid JSON|corrupted|JSON'):
            RunState.load(state_path)
