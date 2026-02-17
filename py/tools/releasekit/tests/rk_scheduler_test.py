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

"""Tests for releasekit.scheduler — dependency-triggered task scheduler."""

from __future__ import annotations

import asyncio
from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest
from releasekit.graph import DependencyGraph, build_graph
from releasekit.observer import DisplayFilter, PublishObserver, PublishStage, SchedulerState, ViewMode
from releasekit.scheduler import PackageNode, Scheduler, SchedulerResult
from releasekit.workspace import Package


@pytest.fixture(autouse=True)
def _no_tty() -> Generator[None]:
    """Prevent _key_listener from modifying terminal settings in tests."""
    with patch('sys.stdin') as mock_stdin:
        mock_stdin.isatty.return_value = False
        yield


def _make_pkg(name: str, internal_deps: list[str] | None = None) -> Package:
    """Create a minimal Package for testing."""
    return Package(
        name=name,
        version='0.1.0',
        path=Path(f'/fake/{name}'),
        manifest_path=Path(f'/fake/{name}/pyproject.toml'),
        internal_deps=internal_deps or [],
        is_publishable=True,
    )


def _make_graph(*packages: Package) -> DependencyGraph:
    """Build a dependency graph from test packages."""
    return build_graph(list(packages))


class TestPackageNode:
    """Tests for PackageNode dataclass."""

    def test_basic_creation(self) -> None:
        """Node initializes with correct defaults."""
        node = PackageNode(name='foo', remaining_deps=2)
        if node.name != 'foo':
            raise AssertionError(f'Expected name=foo, got {node.name}')
        if node.remaining_deps != 2:
            raise AssertionError(f'Expected remaining_deps=2, got {node.remaining_deps}')
        if node.dependents:
            raise AssertionError(f'Expected empty dependents, got {node.dependents}')
        if node.level != 0:
            raise AssertionError(f'Expected level=0, got {node.level}')


class TestSchedulerResult:
    """Tests for SchedulerResult dataclass."""

    def test_ok_when_no_failures(self) -> None:
        """Result is ok when no packages failed."""
        result = SchedulerResult(published=['a', 'b'])
        if not result.ok:
            raise AssertionError('Expected ok=True with no failures')

    def test_not_ok_when_failed(self) -> None:
        """Result is not ok when a package failed."""
        result = SchedulerResult(failed={'a': 'boom'})
        if result.ok:
            raise AssertionError('Expected ok=False with failures')


class TestSchedulerFromGraph:
    """Tests for Scheduler.from_graph factory method."""

    def test_single_package(self) -> None:
        """Single package with no deps gets level 0 and 0 remaining."""
        pkg = _make_pkg('genkit')
        graph = _make_graph(pkg)
        sched = Scheduler.from_graph(graph, publishable={'genkit'})
        node = sched.nodes['genkit']
        if node.remaining_deps != 0:
            raise AssertionError(f'Expected 0 remaining, got {node.remaining_deps}')
        if node.level != 0:
            raise AssertionError(f'Expected level 0, got {node.level}')

    def test_linear_chain(self) -> None:
        """A → B → C: each gets correct remaining deps and levels."""
        c = _make_pkg('c')
        b = _make_pkg('b', internal_deps=['c'])
        a = _make_pkg('a', internal_deps=['b'])
        graph = _make_graph(a, b, c)
        sched = Scheduler.from_graph(graph, publishable={'a', 'b', 'c'})

        if sched.nodes['c'].remaining_deps != 0:
            raise AssertionError('c should have 0 remaining deps')
        if sched.nodes['b'].remaining_deps != 1:
            raise AssertionError('b should have 1 remaining dep (c)')
        if sched.nodes['a'].remaining_deps != 1:
            raise AssertionError('a should have 1 remaining dep (b)')

        if sched.nodes['c'].level != 0:
            raise AssertionError('c should be level 0')
        if sched.nodes['b'].level != 1:
            raise AssertionError('b should be level 1')
        if sched.nodes['a'].level != 2:
            raise AssertionError('a should be level 2')

    def test_diamond(self) -> None:
        """Diamond: D depends on B and C, both depend on A."""
        a = _make_pkg('a')
        b = _make_pkg('b', internal_deps=['a'])
        c = _make_pkg('c', internal_deps=['a'])
        d = _make_pkg('d', internal_deps=['b', 'c'])
        graph = _make_graph(a, b, c, d)
        sched = Scheduler.from_graph(graph, publishable={'a', 'b', 'c', 'd'})

        if sched.nodes['a'].remaining_deps != 0:
            raise AssertionError('a should have 0 remaining')
        if sched.nodes['b'].remaining_deps != 1:
            raise AssertionError('b should have 1 remaining')
        if sched.nodes['c'].remaining_deps != 1:
            raise AssertionError('c should have 1 remaining')
        if sched.nodes['d'].remaining_deps != 2:
            raise AssertionError('d should have 2 remaining')

    def test_non_publishable_deps_ignored(self) -> None:
        """Deps not in publishable set are not counted."""
        core = _make_pkg('core')
        plugin = _make_pkg('plugin', internal_deps=['core'])
        graph = _make_graph(core, plugin)
        # Only publish 'plugin', not 'core'.
        sched = Scheduler.from_graph(graph, publishable={'plugin'})
        if sched.nodes['plugin'].remaining_deps != 0:
            raise AssertionError('plugin should have 0 remaining (core not publishable)')


class TestSchedulerMarkDone:
    """Tests for Scheduler.mark_done (counter decrement + enqueue)."""

    def test_mark_done_enqueues_ready(self) -> None:
        """Marking A done enqueues B (B's only dep is A)."""
        nodes = {
            'a': PackageNode(name='a', remaining_deps=0, dependents=['b']),
            'b': PackageNode(name='b', remaining_deps=1, dependents=[]),
        }
        sched = Scheduler(nodes=nodes, concurrency=2)
        newly_ready = sched.mark_done('a')
        if newly_ready != ['b']:
            raise AssertionError(f'Expected ["b"], got {newly_ready}')

    def test_mark_done_partial(self) -> None:
        """Marking A done doesn't enqueue C (C has 2 deps, only 1 done)."""
        nodes = {
            'a': PackageNode(name='a', remaining_deps=0, dependents=['c']),
            'b': PackageNode(name='b', remaining_deps=0, dependents=['c']),
            'c': PackageNode(name='c', remaining_deps=2, dependents=[]),
        }
        sched = Scheduler(nodes=nodes, concurrency=2)
        newly_ready = sched.mark_done('a')
        if newly_ready:
            raise AssertionError(f'Expected [], got {newly_ready}')
        if sched.nodes['c'].remaining_deps != 1:
            raise AssertionError('c should have 1 remaining')

    def test_mark_done_diamond(self) -> None:
        """Diamond: D enqueued only after both B and C complete."""
        nodes = {
            'a': PackageNode(name='a', remaining_deps=0, dependents=['b', 'c']),
            'b': PackageNode(name='b', remaining_deps=1, dependents=['d']),
            'c': PackageNode(name='c', remaining_deps=1, dependents=['d']),
            'd': PackageNode(name='d', remaining_deps=2, dependents=[]),
        }
        sched = Scheduler(nodes=nodes, concurrency=2)
        # Complete A -> B and C become ready.
        sched.mark_done('a')
        # Complete B -> D not ready yet (needs C too).
        ready_after_b = sched.mark_done('b')
        if ready_after_b:
            raise AssertionError(f'D should not be ready yet: {ready_after_b}')
        # Complete C -> D is now ready.
        ready_after_c = sched.mark_done('c')
        if ready_after_c != ['d']:
            raise AssertionError(f'Expected ["d"], got {ready_after_c}')


class TestSchedulerRun:
    """Integration tests for Scheduler.run with async publish functions."""

    @pytest.mark.asyncio
    async def test_run_single_package(self) -> None:
        """Single package publishes successfully."""
        published: list[str] = []

        async def publish_fn(name: str) -> None:
            """Record the publish call."""
            published.append(name)

        pkg = _make_pkg('genkit')
        graph = _make_graph(pkg)
        sched = Scheduler.from_graph(graph, publishable={'genkit'}, concurrency=1)
        result = await sched.run(publish_fn)

        if not result.ok:
            raise AssertionError(f'Expected ok, got failures: {result.failed}')
        if result.published != ['genkit']:
            raise AssertionError(f'Expected ["genkit"], got {result.published}')

    @pytest.mark.asyncio
    async def test_run_linear_chain(self) -> None:
        """Linear A→B→C publishes in dependency order."""
        published: list[str] = []

        async def publish_fn(name: str) -> None:
            """Record the publish call."""
            published.append(name)

        c = _make_pkg('c')
        b = _make_pkg('b', internal_deps=['c'])
        a = _make_pkg('a', internal_deps=['b'])
        graph = _make_graph(a, b, c)
        sched = Scheduler.from_graph(
            graph,
            publishable={'a', 'b', 'c'},
            concurrency=1,
        )
        result = await sched.run(publish_fn)

        if not result.ok:
            raise AssertionError(f'Failures: {result.failed}')
        # With concurrency=1, order must be c, b, a.
        if published != ['c', 'b', 'a']:
            raise AssertionError(f'Expected ["c", "b", "a"], got {published}')

    @pytest.mark.asyncio
    async def test_run_diamond(self) -> None:
        """Diamond dependency: D publishes after both B and C."""
        published: list[str] = []

        async def publish_fn(name: str) -> None:
            """Record the publish call."""
            published.append(name)

        a = _make_pkg('a')
        b = _make_pkg('b', internal_deps=['a'])
        c = _make_pkg('c', internal_deps=['a'])
        d = _make_pkg('d', internal_deps=['b', 'c'])
        graph = _make_graph(a, b, c, d)
        sched = Scheduler.from_graph(
            graph,
            publishable={'a', 'b', 'c', 'd'},
            concurrency=2,
        )
        result = await sched.run(publish_fn)

        if not result.ok:
            raise AssertionError(f'Failures: {result.failed}')
        # 'a' must come first, 'd' must come last.
        if published[0] != 'a':
            raise AssertionError(f'Expected a first, got {published[0]}')
        if published[-1] != 'd':
            raise AssertionError(f'Expected d last, got {published[-1]}')
        if set(published) != {'a', 'b', 'c', 'd'}:
            raise AssertionError(f'Missing packages: {published}')

    @pytest.mark.asyncio
    async def test_run_failure_blocks_dependents(self) -> None:
        """If B fails, C (depends on B) is never published."""

        async def publish_fn(name: str) -> None:
            """Fail on package b."""
            if name == 'b':
                msg = 'Build failed'
                raise RuntimeError(msg)

        a = _make_pkg('a')
        b = _make_pkg('b', internal_deps=['a'])
        c = _make_pkg('c', internal_deps=['b'])
        graph = _make_graph(a, b, c)
        sched = Scheduler.from_graph(
            graph,
            publishable={'a', 'b', 'c'},
            concurrency=1,
        )
        result = await sched.run(publish_fn)

        if result.ok:
            raise AssertionError('Expected failure')
        if 'b' not in result.failed:
            raise AssertionError(f'Expected b to fail: {result.failed}')
        if 'a' not in result.published:
            raise AssertionError(f'Expected a published: {result.published}')
        # c should NOT be published (b failed, c depends on b).
        if 'c' in result.published:
            raise AssertionError('c should not be published (depends on failed b)')

    @pytest.mark.asyncio
    async def test_run_parallel_independent(self) -> None:
        """Independent packages run in parallel (verified by timing)."""
        published: list[str] = []

        async def publish_fn(name: str) -> None:
            """Simulate a short delay and record."""
            await asyncio.sleep(0.01)
            published.append(name)

        pkgs = [_make_pkg(f'pkg-{i}') for i in range(5)]
        graph = _make_graph(*pkgs)
        publishable = {p.name for p in pkgs}
        sched = Scheduler.from_graph(graph, publishable=publishable, concurrency=5)
        result = await sched.run(publish_fn)

        if not result.ok:
            raise AssertionError(f'Failures: {result.failed}')
        if len(result.published) != 5:
            raise AssertionError(f'Expected 5 published, got {len(result.published)}')

    @pytest.mark.asyncio
    async def test_run_empty_publishable(self) -> None:
        """Empty publishable set produces empty result."""

        async def publish_fn(name: str) -> None:
            """Should not be called."""
            raise AssertionError('Should not be called')

        pkg = _make_pkg('genkit')
        graph = _make_graph(pkg)
        sched = Scheduler.from_graph(graph, publishable=set(), concurrency=1)
        result = await sched.run(publish_fn)
        if result.published:
            raise AssertionError(f'Expected empty, got {result.published}')

    @pytest.mark.asyncio
    async def test_run_cancellation_returns_partial(self) -> None:
        """Cancelling the scheduler returns partial results."""
        published: list[str] = []
        cancel_after = 'b'

        async def publish_fn(name: str) -> None:
            """Publish and cancel the parent task after a specific package."""
            published.append(name)
            if name == cancel_after:
                # Cancel the task running scheduler.run() to simulate Ctrl+C.
                current = asyncio.current_task()
                if current is not None:
                    current.cancel()
                    # Yield control so the cancellation propagates.
                    await asyncio.sleep(0)

        c = _make_pkg('c')
        b = _make_pkg('b', internal_deps=['c'])
        a = _make_pkg('a', internal_deps=['b'])
        graph = _make_graph(a, b, c)
        sched = Scheduler.from_graph(
            graph,
            publishable={'a', 'b', 'c'},
            concurrency=1,
        )

        result = await sched.run(publish_fn)

        # 'c' should have been published before 'b' triggered cancel.
        if 'c' not in result.published:
            raise AssertionError(f'Expected c in published: {result.published}')
        # 'a' should NOT be published (cancelled before it ran).
        if 'a' in result.published:
            raise AssertionError('a should not be published after cancel')


class TestSchedulerDuplicateGuard:
    """Tests for duplicate-completion guard in mark_done."""

    def test_mark_done_idempotent(self) -> None:
        """Calling mark_done twice for the same package is a no-op."""
        nodes = {
            'a': PackageNode(name='a', remaining_deps=0, dependents=['b']),
            'b': PackageNode(name='b', remaining_deps=1, dependents=[]),
        }
        sched = Scheduler(nodes=nodes, concurrency=2)
        first = sched.mark_done('a')
        second = sched.mark_done('a')
        if first != ['b']:
            raise AssertionError(f'First call should return ["b"], got {first}')
        if second:
            raise AssertionError(f'Second call should return [], got {second}')
        # b's remaining_deps should be 0 (not -1).
        if sched.nodes['b'].remaining_deps != 0:
            raise AssertionError(f'Expected 0, got {sched.nodes["b"].remaining_deps}')


class TestSchedulerPauseResume:
    """Tests for suspend/resume functionality."""

    def test_pause_resume_state(self) -> None:
        """Pausing and resuming toggles is_paused."""
        sched = Scheduler(nodes={}, concurrency=1)
        if sched.is_paused:
            raise AssertionError('Should not be paused initially')
        sched.pause()
        if not sched.is_paused:
            raise AssertionError('Should be paused after pause()')
        sched.resume()
        if sched.is_paused:
            raise AssertionError('Should not be paused after resume()')

    @pytest.mark.asyncio
    async def test_pause_blocks_workers(self) -> None:
        """Paused scheduler does not start new packages until resumed."""
        published: list[str] = []

        async def publish_fn(name: str) -> None:
            """Record the publish call."""
            published.append(name)

        a = _make_pkg('a')
        b = _make_pkg('b')
        graph = _make_graph(a, b)
        sched = Scheduler.from_graph(
            graph,
            publishable={'a', 'b'},
            concurrency=2,
        )

        # Pause before running.
        sched.pause()

        # Start the scheduler in a background task.
        run_task = asyncio.create_task(sched.run(publish_fn))

        # Give workers time to start and hit the pause gate.
        await asyncio.sleep(0.05)
        if published:
            raise AssertionError(f'Should not publish while paused: {published}')

        # Resume and let it finish.
        sched.resume()
        result = await run_task

        if not result.ok:
            raise AssertionError(f'Failures: {result.failed}')
        if set(result.published) != {'a', 'b'}:
            raise AssertionError(f'Expected a and b, got {result.published}')


class TestSchedulerAlreadyPublished:
    """Tests for resume-after-crash via already_published."""

    def test_already_published_excluded_from_nodes(self) -> None:
        """Packages in already_published are not in the scheduler."""
        a = _make_pkg('a')
        b = _make_pkg('b', internal_deps=['a'])
        graph = _make_graph(a, b)
        sched = Scheduler.from_graph(
            graph,
            publishable={'a', 'b'},
            already_published={'a'},
        )
        if 'a' in sched.nodes:
            raise AssertionError('a should not be in nodes')
        if 'b' not in sched.nodes:
            raise AssertionError('b should be in nodes')
        # b's dep on a is satisfied (a is already done).
        if sched.nodes['b'].remaining_deps != 0:
            raise AssertionError(f'Expected 0, got {sched.nodes["b"].remaining_deps}')

    @pytest.mark.asyncio
    async def test_already_published_unlocks_dependents(self) -> None:
        """Dependents of already_published packages run immediately."""
        published: list[str] = []

        async def publish_fn(name: str) -> None:
            """Record the publish call."""
            published.append(name)

        a = _make_pkg('a')
        b = _make_pkg('b', internal_deps=['a'])
        c = _make_pkg('c', internal_deps=['b'])
        graph = _make_graph(a, b, c)
        sched = Scheduler.from_graph(
            graph,
            publishable={'a', 'b', 'c'},
            already_published={'a'},
            concurrency=1,
        )
        result = await sched.run(publish_fn)

        if not result.ok:
            raise AssertionError(f'Failures: {result.failed}')
        # Only b and c should be published (a was already done).
        if 'a' in result.published:
            raise AssertionError('a should not be re-published')
        if result.published != ['b', 'c']:
            raise AssertionError(f'Expected ["b", "c"], got {result.published}')

    @pytest.mark.asyncio
    async def test_all_already_published(self) -> None:
        """If everything is already published, result is empty."""

        async def publish_fn(name: str) -> None:
            """Should not be called."""
            raise AssertionError('Should not be called')

        a = _make_pkg('a')
        b = _make_pkg('b', internal_deps=['a'])
        graph = _make_graph(a, b)
        sched = Scheduler.from_graph(
            graph,
            publishable={'a', 'b'},
            already_published={'a', 'b'},
        )
        result = await sched.run(publish_fn)
        if result.published:
            raise AssertionError(f'Expected empty, got {result.published}')


class TestSchedulerRetry:
    """Tests for retry with exponential backoff."""

    @pytest.mark.asyncio
    async def test_retry_succeeds_after_transient_failure(self) -> None:
        """Package succeeds on second attempt after a transient error."""
        attempts: dict[str, int] = {}

        async def publish_fn(name: str) -> None:
            """Fail on first attempt, succeed on second."""
            attempts[name] = attempts.get(name, 0) + 1
            if name == 'a' and attempts[name] == 1:
                msg = 'Transient network error'
                raise RuntimeError(msg)

        pkg = _make_pkg('a')
        graph = _make_graph(pkg)
        sched = Scheduler.from_graph(
            graph,
            publishable={'a'},
            concurrency=1,
            max_retries=2,
            retry_base_delay=0.01,
        )
        result = await sched.run(publish_fn)

        if not result.ok:
            raise AssertionError(f'Expected ok, got failures: {result.failed}')
        if 'a' not in result.published:
            raise AssertionError(f'Expected a published: {result.published}')
        if attempts['a'] != 2:
            raise AssertionError(f'Expected 2 attempts, got {attempts["a"]}')

    @pytest.mark.asyncio
    async def test_retry_exhausted_records_failure(self) -> None:
        """Package fails after all retries are exhausted."""

        async def publish_fn(name: str) -> None:
            """Always fail."""
            msg = 'Permanent failure'
            raise RuntimeError(msg)

        pkg = _make_pkg('a')
        graph = _make_graph(pkg)
        sched = Scheduler.from_graph(
            graph,
            publishable={'a'},
            concurrency=1,
            max_retries=2,
            retry_base_delay=0.01,
        )
        result = await sched.run(publish_fn)

        if result.ok:
            raise AssertionError('Expected failure')
        if 'a' not in result.failed:
            raise AssertionError(f'Expected a to fail: {result.failed}')

    @pytest.mark.asyncio
    async def test_no_retry_by_default(self) -> None:
        """With max_retries=0, failure is immediate (no retry)."""
        attempts: dict[str, int] = {}

        async def publish_fn(name: str) -> None:
            """Always fail, count attempts."""
            attempts[name] = attempts.get(name, 0) + 1
            msg = 'Fail'
            raise RuntimeError(msg)

        pkg = _make_pkg('a')
        graph = _make_graph(pkg)
        sched = Scheduler.from_graph(
            graph,
            publishable={'a'},
            concurrency=1,
            max_retries=0,
        )
        result = await sched.run(publish_fn)

        if result.ok:
            raise AssertionError('Expected failure')
        if attempts['a'] != 1:
            raise AssertionError(f'Expected 1 attempt, got {attempts["a"]}')

    @pytest.mark.asyncio
    async def test_retry_unblocks_dependents_on_success(self) -> None:
        """Dependent runs after its dep succeeds on retry."""
        attempts: dict[str, int] = {}
        published: list[str] = []

        async def publish_fn(name: str) -> None:
            """Fail a on first try, then succeed."""
            attempts[name] = attempts.get(name, 0) + 1
            if name == 'a' and attempts[name] == 1:
                msg = 'Transient'
                raise RuntimeError(msg)
            published.append(name)

        a = _make_pkg('a')
        b = _make_pkg('b', internal_deps=['a'])
        graph = _make_graph(a, b)
        sched = Scheduler.from_graph(
            graph,
            publishable={'a', 'b'},
            concurrency=1,
            max_retries=1,
            retry_base_delay=0.01,
        )
        result = await sched.run(publish_fn)

        if not result.ok:
            raise AssertionError(f'Failures: {result.failed}')
        if set(result.published) != {'a', 'b'}:
            raise AssertionError(f'Expected a and b, got {result.published}')


class TestAddPackage:
    """Tests for Scheduler.add_package (live node insertion)."""

    def test_add_no_deps_enqueued_immediately(self) -> None:
        """Package with no deps is enqueued on add."""
        a = _make_pkg('a')
        graph = _make_graph(a)
        sched = Scheduler.from_graph(graph, publishable={'a'})

        added = sched.add_package('new-pkg')
        if not added:
            raise AssertionError('Expected add to succeed')
        if 'new-pkg' not in sched.nodes:
            raise AssertionError('New package should be in nodes')
        if sched._total != 2:
            raise AssertionError(f'Expected total=2, got {sched._total}')
        if 'new-pkg' not in sched._enqueued:
            raise AssertionError('Package with no deps should be enqueued')

    def test_add_with_pending_deps(self) -> None:
        """Package with unsatisfied deps waits for them."""
        a = _make_pkg('a')
        graph = _make_graph(a)
        sched = Scheduler.from_graph(graph, publishable={'a'})

        added = sched.add_package('new-pkg', deps=['a'], level=1)
        if not added:
            raise AssertionError('Expected add to succeed')
        if 'new-pkg' in sched._enqueued:
            raise AssertionError('Should wait until dep completes')
        # a should now list new-pkg as a dependent.
        if 'new-pkg' not in sched.nodes['a'].dependents:
            raise AssertionError('a should have new-pkg as dependent')

    def test_add_with_done_deps(self) -> None:
        """Package whose deps are already done is enqueued immediately."""
        a = _make_pkg('a')
        graph = _make_graph(a)
        sched = Scheduler.from_graph(graph, publishable={'a'})
        sched.mark_done('a')

        added = sched.add_package('new-pkg', deps=['a'], level=1)
        if not added:
            raise AssertionError('Expected add to succeed')
        if 'new-pkg' not in sched._enqueued:
            raise AssertionError('All deps done — should be enqueued')

    def test_add_with_unknown_deps_ignored(self) -> None:
        """Unknown deps are silently ignored (not counted)."""
        a = _make_pkg('a')
        graph = _make_graph(a)
        sched = Scheduler.from_graph(graph, publishable={'a'})

        added = sched.add_package('new-pkg', deps=['nonexistent'], level=0)
        if not added:
            raise AssertionError('Expected add to succeed')
        # Unknown dep → remaining_deps=0 → enqueued.
        if 'new-pkg' not in sched._enqueued:
            raise AssertionError('Unknown deps should be ignored')

    def test_add_duplicate_rejected(self) -> None:
        """Adding the same package twice returns False."""
        a = _make_pkg('a')
        graph = _make_graph(a)
        sched = Scheduler.from_graph(graph, publishable={'a'})

        if not sched.add_package('new-pkg'):
            raise AssertionError('First add should succeed')
        if sched.add_package('new-pkg'):
            raise AssertionError('Duplicate add should return False')

    def test_add_package_enqueued_after_dep_completes(self) -> None:
        """Dynamically added package is enqueued when its dep completes."""
        a = _make_pkg('a')
        graph = _make_graph(a)
        sched = Scheduler.from_graph(graph, publishable={'a'})

        sched.add_package('new-pkg', deps=['a'], level=1)
        if 'new-pkg' in sched._enqueued:
            raise AssertionError('Should not be enqueued yet')

        # Complete a — this should trigger new-pkg enqueue via mark_done.
        newly_ready = sched.mark_done('a')
        if 'new-pkg' not in newly_ready:
            raise AssertionError(f'Expected new-pkg in newly_ready: {newly_ready}')
        if 'new-pkg' not in sched._enqueued:
            raise AssertionError('Should be enqueued after dep completes')

    @pytest.mark.asyncio
    async def test_add_package_runs_in_live_scheduler(self) -> None:
        """Dynamically added package is published by a running scheduler."""
        published: list[str] = []

        async def publish_fn(name: str) -> None:
            """Publish fn."""
            published.append(name)
            # When 'a' completes, dynamically add 'dynamic' with no deps.
            if name == 'a':
                sched.add_package('dynamic', level=0)

        a = _make_pkg('a')
        graph = _make_graph(a)
        sched = Scheduler.from_graph(graph, publishable={'a'}, concurrency=1)
        result = await sched.run(publish_fn)

        if 'a' not in result.published:
            raise AssertionError(f'Expected a published: {result.published}')
        if 'dynamic' not in result.published:
            raise AssertionError(f'Expected dynamic published: {result.published}')


class TestRemovePackage:
    """Tests for Scheduler.remove_package (dynamic package removal)."""

    def test_remove_unknown_returns_false(self) -> None:
        """Removing non-existent package returns False."""
        a = _make_pkg('a')
        graph = _make_graph(a)
        sched = Scheduler.from_graph(graph, publishable={'a'})

        if sched.remove_package('nonexistent'):
            raise AssertionError('Expected False for unknown package')

    def test_remove_done_returns_false(self) -> None:
        """Removing already-completed package returns False."""
        a = _make_pkg('a')
        graph = _make_graph(a)
        sched = Scheduler.from_graph(graph, publishable={'a'})
        sched.mark_done('a')

        if sched.remove_package('a'):
            raise AssertionError('Expected False for done package')

    def test_remove_marks_cancelled(self) -> None:
        """Remove adds package to _cancelled set."""
        a = _make_pkg('a')
        b = _make_pkg('b', internal_deps=['a'])
        graph = _make_graph(a, b)
        sched = Scheduler.from_graph(graph, publishable={'a', 'b'})

        if not sched.remove_package('b'):
            raise AssertionError('Expected remove to succeed')
        if 'b' not in sched._cancelled:
            raise AssertionError('Should be in _cancelled set')

    def test_remove_unenqueued_marks_done(self) -> None:
        """Remove of a package that hasn't been enqueued yet marks it done."""
        a = _make_pkg('a')
        b = _make_pkg('b', internal_deps=['a'])
        graph = _make_graph(a, b)
        sched = Scheduler.from_graph(graph, publishable={'a', 'b'})

        # b has deps, so it shouldn't be enqueued yet.
        if 'b' in sched._enqueued:
            raise AssertionError('b should not be enqueued yet')

        sched.remove_package('b')
        if 'b' not in sched._done:
            raise AssertionError('Unenqueued removed package should be marked done')

    @pytest.mark.asyncio
    async def test_remove_skipped_on_dequeue(self) -> None:
        """Removed package is skipped when a worker dequeues it."""
        published: list[str] = []

        async def publish_fn(name: str) -> None:
            """Publish fn."""
            published.append(name)

        a = _make_pkg('a')
        b = _make_pkg('b')
        graph = _make_graph(a, b)
        sched = Scheduler.from_graph(graph, publishable={'a', 'b'}, concurrency=1)

        # Remove b (it's already seeded/enqueued since it has no deps).
        sched.remove_package('b', block_dependents=False)

        result = await sched.run(publish_fn)

        if 'b' in published:
            raise AssertionError('Removed package should not be published')
        if 'b' not in result.skipped:
            raise AssertionError(f'Expected b in skipped: {result.skipped}')
        if 'a' not in result.published:
            raise AssertionError(f'Expected a published: {result.published}')

    @pytest.mark.asyncio
    async def test_remove_blocks_dependents(self) -> None:
        """Remove with block_dependents=True blocks transitive dependents."""
        published: list[str] = []

        async def publish_fn(name: str) -> None:
            """Publish fn."""
            published.append(name)

        a = _make_pkg('a')
        b = _make_pkg('b', internal_deps=['a'])
        c = _make_pkg('c', internal_deps=['b'])
        graph = _make_graph(a, b, c)
        sched = Scheduler.from_graph(graph, publishable={'a', 'b', 'c'}, concurrency=1)

        # Remove b — should block c too.
        sched.remove_package('b', block_dependents=True)

        result = await sched.run(publish_fn)

        if 'a' not in result.published:
            raise AssertionError(f'Expected a published: {result.published}')
        if 'b' in result.published or 'c' in result.published:
            raise AssertionError(f'b and c should not be published: {result.published}')


class TestSchedulerNoSeeds:
    """Tests for scheduler with no seedable packages."""

    @pytest.mark.asyncio
    async def test_all_packages_have_unsatisfied_deps(self) -> None:
        """Scheduler returns immediately when no packages can be seeded."""
        # Create a cycle-like situation where all packages have deps
        # that are in the publishable set but none have 0 remaining deps.
        # We do this by manually constructing nodes.
        nodes = {
            'a': PackageNode(name='a', remaining_deps=1, dependents=['b']),
            'b': PackageNode(name='b', remaining_deps=1, dependents=['a']),
        }
        sched = Scheduler(nodes=nodes, concurrency=2)

        async def publish_fn(name: str) -> None:
            """Publish fn."""
            pass

        result = await sched.run(publish_fn)

        assert result.ok  # No failures, just nothing published.
        assert not result.published
        assert not result.failed


class TestSchedulerResultOk:
    """Tests for SchedulerResult.ok property."""

    def test_empty_result_is_ok(self) -> None:
        """Empty result is OK."""
        result = SchedulerResult()
        assert result.ok

    def test_result_with_failures_not_ok(self) -> None:
        """Result with failures is not OK."""
        result = SchedulerResult(failed={'a': 'boom'})
        assert not result.ok


class TestSchedulerObserverNotify:
    """Tests for scheduler observer notification helpers."""

    def test_notify_stage_with_observer(self) -> None:
        """_notify_stage calls observer.on_stage."""
        stages: list[tuple[str, PublishStage]] = []

        class SpyObserver(PublishObserver):
            def on_stage(self, name: str, stage: PublishStage) -> None:
                """On stage."""
                stages.append((name, stage))

        nodes = {'a': PackageNode(name='a', remaining_deps=0)}
        sched = Scheduler(nodes=nodes, observer=SpyObserver())
        sched._notify_stage('a', 'retrying')

        assert len(stages) == 1
        assert stages[0] == ('a', PublishStage.RETRYING)

    def test_notify_stage_without_observer(self) -> None:
        """_notify_stage is a no-op without observer."""
        nodes = {'a': PackageNode(name='a', remaining_deps=0)}
        sched = Scheduler(nodes=nodes, observer=None)
        # Should not raise.
        sched._notify_stage('a', 'retrying')

    def test_notify_scheduler_state_with_observer(self) -> None:
        """_notify_scheduler_state calls observer.on_scheduler_state."""
        states: list[SchedulerState] = []

        class SpyObserver(PublishObserver):
            def on_scheduler_state(self, state: SchedulerState) -> None:
                """On scheduler state."""
                states.append(state)

        nodes = {'a': PackageNode(name='a', remaining_deps=0)}
        sched = Scheduler(nodes=nodes, observer=SpyObserver())
        sched._notify_scheduler_state('paused')

        assert len(states) == 1
        assert states[0] == SchedulerState.PAUSED

    def test_notify_view_mode_with_observer(self) -> None:
        """_notify_view_mode calls observer.on_view_mode."""
        calls: list[tuple[ViewMode, DisplayFilter]] = []

        class SpyObserver(PublishObserver):
            def on_view_mode(self, mode: ViewMode, display_filter: DisplayFilter) -> None:
                """Record view mode change."""
                calls.append((mode, display_filter))

        nodes = {'a': PackageNode(name='a', remaining_deps=0)}
        sched = Scheduler(nodes=nodes, observer=SpyObserver())
        sched._notify_view_mode()

        assert len(calls) == 1
        assert calls[0] == (ViewMode.WINDOW, DisplayFilter.ALL)


class TestSchedulerBlockDependents:
    """Tests for _block_dependents recursion."""

    def test_block_dependents_recursive(self) -> None:
        """_block_dependents recursively blocks transitive dependents."""
        blocked: list[str] = []

        class SpyObserver(PublishObserver):
            def on_stage(self, name: str, stage: PublishStage) -> None:
                """On stage."""
                if stage == PublishStage.BLOCKED:
                    blocked.append(name)

        a = _make_pkg('a')
        b = _make_pkg('b', internal_deps=['a'])
        c = _make_pkg('c', internal_deps=['b'])
        graph = _make_graph(a, b, c)
        sched = Scheduler.from_graph(
            graph,
            publishable={'a', 'b', 'c'},
            concurrency=1,
            observer=SpyObserver(),
        )

        # Block dependents of 'a' — should block 'b' and 'c'.
        sched._block_dependents('a')

        assert 'b' in blocked
        assert 'c' in blocked

    def test_block_dependents_already_done_skipped(self) -> None:
        """_block_dependents skips already-done packages."""
        a = _make_pkg('a')
        b = _make_pkg('b', internal_deps=['a'])
        graph = _make_graph(a, b)
        sched = Scheduler.from_graph(graph, publishable={'a', 'b'}, concurrency=1)

        # Mark b as done first.
        sched._done.add('b')
        sched._completed += 1

        # Should not crash or double-count.
        sched._block_dependents('a')

    def test_block_dependents_unknown_node(self) -> None:
        """_block_dependents with unknown node is a no-op."""
        nodes = {'a': PackageNode(name='a', remaining_deps=0)}
        sched = Scheduler(nodes=nodes)
        # Should not raise.
        sched._block_dependents('nonexistent')


class TestSchedulerFromGraphEdgeCases:
    """Tests for from_graph edge cases."""

    def test_non_publishable_dependent_skipped(self) -> None:
        """Dependent not in publishable set is skipped during level computation."""
        a = _make_pkg('a')
        b = _make_pkg('b', internal_deps=['a'])
        graph = _make_graph(a, b)
        # Only 'a' is publishable — 'b' should be excluded from nodes.
        sched = Scheduler.from_graph(graph, publishable={'a'}, concurrency=1)
        assert 'a' in sched.nodes
        assert 'b' not in sched.nodes

    def test_mark_done_dependent_not_in_nodes(self) -> None:
        """mark_done skips dependents not present in nodes dict."""
        a = PackageNode(name='a', remaining_deps=0, dependents=['ghost'])
        sched = Scheduler(nodes={'a': a})
        # 'ghost' is not in nodes — should not raise.
        result = sched.mark_done('a')
        assert result == []


class TestSchedulerCancelledPackage:
    """Tests for cancelled/removed package handling in run."""

    @pytest.mark.asyncio
    async def test_removed_package_is_skipped(self) -> None:
        """Packages removed before dequeue are skipped."""
        a = _make_pkg('a')
        b = _make_pkg('b')
        graph = _make_graph(a, b)
        sched = Scheduler.from_graph(
            graph,
            publishable={'a', 'b'},
            concurrency=2,
        )

        published: list[str] = []

        async def fake_publish(name: str) -> None:
            """Fake publish."""
            published.append(name)

        # Remove 'b' before running.
        sched.remove_package('b')

        result = await sched.run(fake_publish)
        assert 'a' in published
        assert 'b' not in published
        assert 'b' in result.skipped

    @pytest.mark.asyncio
    async def test_keyboard_interrupt_during_run(self) -> None:
        """CancelledError during queue.join is handled gracefully."""
        a = _make_pkg('a')
        graph = _make_graph(a)
        sched = Scheduler.from_graph(
            graph,
            publishable={'a'},
            concurrency=1,
        )

        call_count = 0

        async def failing_publish(name: str) -> None:
            """Failing publish."""
            nonlocal call_count
            call_count += 1
            raise asyncio.CancelledError

        result = await sched.run(failing_publish)
        # The scheduler should complete without hanging.
        assert isinstance(result, SchedulerResult)
