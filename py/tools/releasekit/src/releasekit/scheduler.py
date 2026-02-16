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

"""Dependency-triggered task scheduler for publish pipelines.

Replaces the level-based lockstep dispatch in :mod:`releasekit.publisher`
with a fine-grained, dependency-triggered queue. Packages start as soon
as all their dependencies complete — no waiting for an entire topological
level to finish.

Key Concepts (ELI5)::

    ┌─────────────────────────┬─────────────────────────────────────────────┐
    │ Concept                 │ Plain-English                               │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ PackageNode             │ One package with a countdown of how many    │
    │                         │ deps it still waits for.                    │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ Scheduler               │ Manages the queue and countdown. When a     │
    │                         │ dep finishes → decrements → enqueues when   │
    │                         │ countdown hits zero.                        │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ SchedulerResult         │ Collects published / failed / skipped.      │
    └─────────────────────────┴─────────────────────────────────────────────┘

Before (level-based lockstep)::

    Level 0: [A, B, C]  ─── all must finish ───▶  Level 1: [D, E, F]
                                                    ↑
                                          D waits for C even though
                                          D only depends on A

After (dependency-triggered queue)::

    A completes ──▶ D starts immediately (A is D's only dep)
    B completes ──▶ E starts immediately (B is E's only dep)
    C completes ──▶ F starts immediately (A + C are F's deps)

Worker pool architecture::

    ┌───────────────────────────────────────────────────────┐
    │                     Scheduler                         │
    │                                                       │
    │  from_graph() ──▶ seed level-0 ──▶ Queue              │
    │                                      │                │
    │         ┌────────────────────────────┼──────────┐     │
    │         │          Semaphore(N)      │          │     │
    │         │                            ▼          │     │
    │     ┌────────┐ ┌────────┐ ... ┌────────┐       │     │
    │     │Worker 0│ │Worker 1│     │Worker N│       │     │
    │     └───┬────┘ └───┬────┘     └───┬────┘       │     │
    │         │          │              │             │     │
    │         └──────────┴──────┬───────┘             │     │
    │                           │                     │     │
    │                     publish_fn(name)             │     │
    │                           │                     │     │
    │                    ┌──────┴──────┐              │     │
    │                    │  mark_done  │              │     │
    │                    └──────┬──────┘              │     │
    │                           │                     │     │
    │              decrement dependents' counters      │     │
    │              enqueue newly-ready packages        │     │
    │                           │                     │     │
    │                    ┌──────┴──────┐              │     │
    │                    │    Queue    │◀─────────────┘     │
    │                    └─────────────┘                    │
    └───────────────────────────────────────────────────────┘

Retry with exponential backoff + full jitter::

    publish_fn(name)
         │
         ├── success ──▶ mark_done ──▶ enqueue dependents
         │
         └── failure
              │
              ├── attempt < max_retries?
              │     │
              │     yes ──▶ sleep(uniform(0, base * 2^attempt)) ──▶ retry
              │     │          (capped at 60s)
              │     no  ──▶ record failure ──▶ block dependents
              │
              └── (dependents never enqueued on failure)

Lifecycle states::

    ┌──────────┐     resume()     ┌──────────┐
    │  PAUSED  │ ◀──────────────▶ │ RUNNING  │
    │          │     pause()      │          │
    └──────────┘                  └────┬─────┘
                                      │
                              Ctrl+C / cancel
                                      │
                                      ▼
                               ┌──────────┐
                               │CANCELLED │
                               │(partial  │
                               │ result)  │
                               └──────────┘

Usage::

    from releasekit.scheduler import Scheduler

    scheduler = Scheduler.from_graph(
        graph=graph,
        publishable={'genkit', 'genkit-plugin-foo', ...},
        concurrency=5,
        max_retries=2,
        retry_base_delay=1.0,
    )


    async def do_publish(name: str) -> None:
        '''Publish one package — called by the scheduler.'''
        ...


    result = await scheduler.run(do_publish)
"""

from __future__ import annotations

import asyncio
import os
import random
import select
import signal
import sys
import termios
import tty
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any

from releasekit.graph import DependencyGraph
from releasekit.logging import get_logger
from releasekit.observer import DisplayFilter, PublishObserver, PublishStage, SchedulerState, ViewMode

logger = get_logger(__name__)

# Type alias for the publish callback.
PublishFn = Callable[[str], Coroutine[Any, Any, None]]


@dataclass
class PackageNode:
    """A node in the dependency-aware scheduler.

    Tracks how many dependencies remain before this package can be
    enqueued for publishing.

    Attributes:
        name: Package name.
        remaining_deps: Count of deps not yet published. Starts at
            the number of publishable internal deps. Decremented by
            :meth:`Scheduler.mark_done`. Enqueued when it hits zero.
        dependents: Names of packages that depend on *this* package.
            Used to notify downstream packages when this one completes.
        level: Topological level (0 = no deps). Preserved for observer
            compatibility and logging.
    """

    name: str
    remaining_deps: int
    dependents: list[str] = field(default_factory=list)
    level: int = 0


@dataclass(frozen=True)
class SchedulerResult:
    """Result of a scheduler run.

    Attributes:
        published: Names of successfully published packages, in
            completion order.
        failed: Mapping of failed package names to error messages.
        skipped: Names of packages that were skipped (not publishable).
    """

    published: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)
    skipped: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """Return True if no packages failed."""
        return not self.failed


# Maximum backoff delay (seconds) to prevent excessively long waits.
_MAX_BACKOFF_SECONDS = 60.0


class Scheduler:
    """Dependency-triggered task scheduler.

    Enqueues packages as their dependencies complete, rather than
    waiting for an entire topological level to finish. A semaphore
    controls maximum concurrency.

    The scheduler does **not** call ``_publish_one`` directly — it
    invokes a caller-provided ``publish_fn(name)`` coroutine. This
    keeps the scheduler decoupled from publish-specific logic and
    makes it testable with simple stubs.

    Thread safety:
        This class is designed for **single-event-loop** use. All shared
        state (``_completed``, ``_result``, ``_done``, ``_enqueued``,
        ``_nodes``) is mutated only in coroutines on the same loop.
        Asyncio's cooperative scheduling guarantees no interleaving
        between ``await`` points, so no locks are needed.

        The underlying primitives (``asyncio.Queue``, ``asyncio.Event``,
        ``asyncio.Semaphore``) are **NOT thread-safe**. If you need to
        call ``pause()``/``resume()`` from a different thread (e.g., a
        signal handler), use ``loop.call_soon_threadsafe(scheduler.pause)``.

        **Multiple event loops are not supported.** The scheduler is
        bound to the loop it was created on. This is intentional:

        - Python's ``asyncio.run()`` creates a single loop per call —
          the standard pattern for CLI tools and server workers alike.
        - Supporting multiple loops would require thread-safe primitives
          (``threading.Lock``), which block the event loop, or a
          message-passing layer between loops — both add complexity
          with no benefit for a CLI publish pipeline.
        - For cross-process coordination (e.g., parallel releasekit
          invocations), use the existing ``release_lock()`` file lock
          instead of multi-loop scheduling.

    Attributes:
        _nodes: All tracked nodes (publishable + skipped).
        _queue: Packages ready to publish (all deps satisfied).
        _semaphore: Concurrency limiter.
        _total: Total number of publishable packages (for progress).
        _completed: Count of finished packages (published + failed).
        _resume_event: Gate for suspend/resume. Workers await this
            before processing each item.
        _done: Set of packages already completed (duplicate guard).
        _max_retries: Max retry attempts per package (0 = no retries).
        _retry_base_delay: Base delay in seconds for exponential backoff.
    """

    def __init__(
        self,
        nodes: dict[str, PackageNode],
        concurrency: int = 5,
        max_retries: int = 0,
        retry_base_delay: float = 1.0,
        task_timeout: float | None = None,
        observer: PublishObserver | None = None,
    ) -> None:
        """Initialize the scheduler.

        Args:
            nodes: Mapping of package name to :class:`PackageNode`.
                Only publishable packages should be included.
            concurrency: Maximum number of concurrent publish tasks.
            max_retries: Number of retry attempts per package before
                recording a failure. Set to 0 (default) to disable.
            retry_base_delay: Base delay in seconds for exponential
                backoff between retries. Actual delay is
                ``base * 2**attempt``, capped at 60s.
            task_timeout: Maximum seconds per publish attempt. If the
                publish callback does not complete within this time,
                a :class:`TimeoutError` is raised and the attempt is
                treated as a retryable failure. ``None`` (default)
                means no timeout.
            observer: Optional UI observer for stage/state callbacks.
        """
        self._nodes = nodes
        self._queue: asyncio.Queue[PackageNode] = asyncio.Queue()
        self._semaphore = asyncio.Semaphore(concurrency)
        self._total = len(nodes)
        self._completed = 0
        self._result = SchedulerResult()
        self._max_retries = max_retries
        self._retry_base_delay = retry_base_delay
        self._task_timeout = task_timeout
        self._observer = observer
        # Track which nodes have been enqueued to avoid double-enqueue.
        self._enqueued: set[str] = set()
        # Track completed packages to prevent double-completion.
        self._done: set[str] = set()
        # Gate for suspend/resume. Set = running, cleared = paused.
        self._resume_event = asyncio.Event()
        self._resume_event.set()
        # Packages cancelled via remove_package(). Workers skip on dequeue.
        self._cancelled: set[str] = set()
        # Current view mode / filter (keyboard toggles).
        self._view_mode = ViewMode.WINDOW
        self._previous_view_mode = ViewMode.WINDOW
        self._display_filter = DisplayFilter.ALL

    @classmethod
    def from_graph(
        cls,
        graph: DependencyGraph,
        publishable: set[str],
        concurrency: int = 5,
        already_published: set[str] | None = None,
        max_retries: int = 0,
        retry_base_delay: float = 1.0,
        task_timeout: float | None = None,
        observer: PublishObserver | None = None,
    ) -> Scheduler:
        """Build a scheduler from a dependency graph.

        Only packages in ``publishable`` are scheduled. Dependencies
        outside ``publishable`` are ignored (their counters are not
        counted).

        Packages in ``already_published`` are treated as completed:
        they are excluded from scheduling, and their dependents'
        ``remaining_deps`` counters are pre-decremented. This enables
        resume-after-crash — the caller reads which packages were
        already published from the saved run-state and passes them in.

        Args:
            graph: The workspace dependency graph.
            publishable: Set of package names that should be published.
            concurrency: Maximum concurrent publish tasks.
            already_published: Optional set of packages that were
                published in a prior (interrupted) run and should
                not be re-published.
            max_retries: Number of retry attempts per package (0 = no
                retries). On transient failures, the worker retries
                with exponential backoff before recording a failure.
            retry_base_delay: Base delay in seconds for exponential
                backoff. Actual delay is ``base * 2**attempt``,
                capped at 60s.
            task_timeout: Maximum seconds per publish attempt. If the
                publish callback does not complete within this time,
                a :class:`TimeoutError` is raised and the attempt is
                treated as a retryable failure. ``None`` (default)
                means no timeout.
            observer: Optional UI observer for stage/state callbacks.

        Returns:
            A ready-to-run :class:`Scheduler`.
        """
        done = already_published or set()
        remaining = publishable - done

        if done:
            logger.info(
                'scheduler_skip_already_published',
                count=len(done),
                packages=sorted(done),
            )

        # Compute topological levels for each package (for observer compat).
        # Use the full publishable set for level computation so levels
        # stay stable regardless of which packages are already done.
        in_degree: dict[str, int] = {}
        for name in publishable:
            deps = [d for d in graph.edges.get(name, []) if d in publishable]
            in_degree[name] = len(deps)

        # BFS to assign levels.
        levels: dict[str, int] = {}
        queue: list[str] = [n for n, d in in_degree.items() if d == 0]
        current_level = 0
        while queue:
            for n in queue:
                levels[n] = current_level
            next_queue: list[str] = []
            for n in queue:
                for dependent in graph.reverse_edges.get(n, []):
                    if dependent not in publishable:
                        continue
                    if dependent not in levels:
                        in_degree[dependent] -= 1
                        if in_degree[dependent] == 0:
                            next_queue.append(dependent)
            queue = sorted(next_queue)
            current_level += 1

        # Build nodes only for packages that still need publishing.
        nodes: dict[str, PackageNode] = {}
        for name in remaining:
            # Count only deps that are also remaining (not already done).
            deps = [d for d in graph.edges.get(name, []) if d in remaining]
            dependents = [d for d in graph.reverse_edges.get(name, []) if d in remaining]
            nodes[name] = PackageNode(
                name=name,
                remaining_deps=len(deps),
                dependents=sorted(dependents),
                level=levels.get(name, 0),
            )

        return cls(
            nodes=nodes,
            concurrency=concurrency,
            max_retries=max_retries,
            retry_base_delay=retry_base_delay,
            task_timeout=task_timeout,
            observer=observer,
        )

    def _seed_queue(self) -> int:
        """Enqueue all packages with zero remaining deps.

        Returns:
            Number of packages seeded.
        """
        seeded = 0
        for node in sorted(self._nodes.values(), key=lambda n: n.name):
            if node.remaining_deps == 0 and node.name not in self._enqueued:
                self._queue.put_nowait(node)
                self._enqueued.add(node.name)
                seeded += 1
                logger.debug(
                    'scheduler_seed',
                    package=node.name,
                    level=node.level,
                )
        return seeded

    def mark_done(self, name: str) -> list[str]:
        """Mark a package as published and enqueue ready dependents.

        Decrements the ``remaining_deps`` counter for each dependent.
        When a counter hits zero, that dependent is enqueued.

        Duplicate calls for the same ``name`` are silently ignored.

        Args:
            name: Name of the completed package.

        Returns:
            List of dependent names that were newly enqueued.
        """
        if name in self._done:
            logger.debug('scheduler_duplicate_done', package=name)
            return []
        self._done.add(name)

        node = self._nodes[name]
        newly_ready: list[str] = []
        for dep_name in node.dependents:
            dep_node = self._nodes.get(dep_name)
            if dep_node is None:
                continue
            dep_node.remaining_deps -= 1
            if dep_node.remaining_deps == 0 and dep_name not in self._enqueued:
                self._queue.put_nowait(dep_node)
                self._enqueued.add(dep_name)
                newly_ready.append(dep_name)
                logger.debug(
                    'scheduler_enqueue',
                    package=dep_name,
                    triggered_by=name,
                    level=dep_node.level,
                )
        return newly_ready

    def add_package(
        self,
        name: str,
        *,
        deps: list[str] | None = None,
        level: int = 0,
    ) -> bool:
        """Add a package to a running scheduler.

        Inserts a new node into the live scheduler. If all of the node's
        dependencies are already completed, the node is enqueued for
        immediate processing. Otherwise it waits until ``mark_done``
        decrements its counter to zero.

        This method is safe to call while ``run()`` is active because
        asyncio's cooperative scheduling guarantees no interleaving
        between ``await`` points on the same event loop. All mutations
        (``_nodes``, ``_total``, ``_enqueued``, ``_done``) happen
        atomically from the caller's perspective.

        Use case: an HTTP server process accepts new packages at runtime
        and feeds them into the running scheduler via this method.

        Args:
            name: Package name. Must not already exist in the scheduler.
            deps: Names of packages this one depends on. Only deps that
                are *also in the scheduler* are counted. Unknown deps
                are silently ignored (same behavior as ``from_graph``).
            level: Topological level hint for display purposes.

        Returns:
            ``True`` if the package was added, ``False`` if it already
            exists (duplicate addition is a no-op).
        """
        if name in self._nodes:
            logger.debug('scheduler_add_duplicate', package=name)
            return False

        deps = deps or []

        # Count only deps that exist in the scheduler and are not yet done.
        remaining = 0
        for dep_name in deps:
            dep_node = self._nodes.get(dep_name)
            if dep_node is None:
                # Unknown dep — either external or not in the scheduler.
                continue
            if dep_name in self._done:
                # Already completed — don't count.
                continue
            remaining += 1

        node = PackageNode(
            name=name,
            remaining_deps=remaining,
            dependents=[],
            level=level,
        )
        self._nodes[name] = node
        self._total += 1

        # Wire up: add this node as a dependent of each of its deps.
        for dep_name in deps:
            dep_node = self._nodes.get(dep_name)
            if dep_node is not None and dep_name != name:
                dep_node.dependents.append(name)

        # If all deps are satisfied, enqueue immediately.
        if remaining == 0 and name not in self._enqueued:
            self._queue.put_nowait(node)
            self._enqueued.add(name)
            logger.info(
                'scheduler_add_enqueue',
                package=name,
                level=level,
                reason='all deps satisfied or no deps',
            )
        else:
            logger.info(
                'scheduler_add_waiting',
                package=name,
                level=level,
                remaining_deps=remaining,
            )

        return True

    def remove_package(
        self,
        name: str,
        *,
        block_dependents: bool = True,
    ) -> bool:
        """Remove a package from the scheduler.

        If the package is queued but not yet being processed, it will be
        skipped when a worker dequeues it. If it is currently being
        processed, it cannot be interrupted — only future dequeues are
        affected.

        ``asyncio.Queue`` does not support arbitrary removal, so this
        method adds the name to a ``_cancelled`` set. Workers check
        this set after dequeue and skip cancelled nodes.

        By default, all dependents of the removed package are also
        blocked (same behavior as a failed package). Set
        ``block_dependents=False`` to leave dependents untouched.

        Use case: an HTTP server receives a "skip this package" request
        (e.g., a known-broken package that should not delay the rest).

        Args:
            name: Package name to remove.
            block_dependents: Whether to recursively block dependents.

        Returns:
            ``True`` if the package was marked for removal, ``False``
            if it was not found or already completed.
        """
        if name not in self._nodes:
            logger.debug('scheduler_remove_unknown', package=name)
            return False

        if name in self._done:
            logger.debug('scheduler_remove_already_done', package=name)
            return False

        self._cancelled.add(name)
        logger.info('scheduler_remove', package=name)

        # If the package hasn't been enqueued yet (waiting on deps),
        # mark it done immediately so dependents get blocked and the
        # total counter stays accurate.
        if name not in self._enqueued:
            self._done.add(name)
            self._completed += 1
            self._notify_stage(name, 'blocked')

        if block_dependents:
            self._block_dependents(name)

        return True

    def pause(self) -> None:
        """Suspend the scheduler.

        Workers finish their current package but won't start new ones
        until :meth:`resume` is called.
        """
        self._resume_event.clear()
        logger.info('scheduler_paused')
        self._notify_scheduler_state('paused')

    def resume(self) -> None:
        """Resume a suspended scheduler."""
        self._resume_event.set()
        logger.info('scheduler_resumed')
        self._notify_scheduler_state('running')

    @property
    def is_paused(self) -> bool:
        """Return True if the scheduler is currently paused."""
        return not self._resume_event.is_set()

    async def run(self, publish_fn: PublishFn) -> SchedulerResult:
        """Run the scheduler until all packages are processed.

        Spawns a pool of workers that consume from the queue. Each
        worker acquires the semaphore, calls ``publish_fn(name)``,
        and marks the package as done (triggering dependents).

        If ``publish_fn`` raises, the package is recorded as failed
        but dependents are **not** enqueued (fail-fast for the
        dependency chain).

        Args:
            publish_fn: Async callable that publishes a single package
                by name. Should raise on failure.

        Returns:
            A :class:`SchedulerResult` with published/failed/skipped.
        """
        # Seed initial packages (those with no deps).
        seeded = self._seed_queue()
        if seeded == 0 and self._total > 0:
            logger.warning(
                'scheduler_no_seeds',
                hint='All packages have unsatisfied deps. Check for cycles.',
            )
            return self._result

        logger.info(
            'scheduler_start',
            total=self._total,
            seeded=seeded,
            concurrency=self._semaphore._value,  # noqa: SLF001 - internal semaphore value for logging
        )

        # Install signal handlers for pause/resume from another terminal.
        loop = asyncio.get_running_loop()
        self._install_signal_handlers(loop)

        # Sentinel to signal workers to stop.
        done_event = asyncio.Event()

        async def worker(worker_id: int) -> None:
            """Worker coroutine — pulls from queue and publishes."""
            while not done_event.is_set():
                # Honor suspend/resume gate before pulling work.
                await self._resume_event.wait()

                try:
                    node = await asyncio.wait_for(
                        self._queue.get(),
                        timeout=1.0,
                    )
                except TimeoutError:
                    if self._completed >= self._total:
                        break
                    continue

                # Skip removed packages. The node is already in the
                # queue (asyncio.Queue has no remove), so we check the
                # _cancelled set on dequeue instead.
                if node.name in self._cancelled:
                    self._result.skipped.append(node.name)
                    self._done.add(node.name)
                    self._completed += 1
                    self._queue.task_done()
                    logger.info(
                        'scheduler_skip_cancelled',
                        package=node.name,
                        worker=worker_id,
                    )
                    continue

                # Ensure task_done() is always called, even if the
                # worker is cancelled. CancelledError is a BaseException
                # and not caught by the except Exception block below,
                # so without this finally, _queue.join() would hang.
                try:
                    async with self._semaphore:
                        last_exc: Exception | None = None
                        for attempt in range(1 + self._max_retries):
                            try:
                                logger.info(
                                    'scheduler_publish_start',
                                    package=node.name,
                                    worker=worker_id,
                                    level=node.level,
                                    attempt=attempt + 1,
                                    max_attempts=1 + self._max_retries,
                                )
                                if self._task_timeout is not None:
                                    await asyncio.wait_for(
                                        publish_fn(node.name),
                                        timeout=self._task_timeout,
                                    )
                                else:
                                    await publish_fn(node.name)
                                self._result.published.append(node.name)
                                self.mark_done(node.name)
                                logger.info(
                                    'scheduler_publish_done',
                                    package=node.name,
                                    worker=worker_id,
                                )
                                last_exc = None
                                break
                            except Exception as exc:
                                last_exc = exc
                                if attempt < self._max_retries:
                                    max_delay = min(
                                        self._retry_base_delay * (2**attempt),
                                        _MAX_BACKOFF_SECONDS,
                                    )
                                    delay = random.uniform(0, max_delay)  # noqa: S311 - jitter, not crypto
                                    logger.warning(
                                        'scheduler_publish_retry',
                                        package=node.name,
                                        attempt=attempt + 1,
                                        max_retries=self._max_retries,
                                        delay=delay,
                                        error=str(exc),
                                        worker=worker_id,
                                    )
                                    self._notify_stage(node.name, 'retrying')
                                    await asyncio.sleep(delay)

                        if last_exc is not None:
                            self._result.failed[node.name] = str(last_exc)
                            logger.error(
                                'scheduler_publish_failed',
                                package=node.name,
                                error=str(last_exc),
                                worker=worker_id,
                                attempts=1 + self._max_retries,
                            )
                            # Don't mark_done — dependents won't be enqueued.
                            # Mark all direct dependents as BLOCKED.
                            self._block_dependents(node.name)
                finally:
                    self._completed += 1
                    self._queue.task_done()

        # Spawn workers.
        worker_count = min(self._semaphore._value, self._total)  # noqa: SLF001 - need count for worker pool
        workers = [asyncio.create_task(worker(i), name=f'scheduler-worker-{i}') for i in range(worker_count)]

        # Start keyboard listener (p=pause, r=resume, q=cancel).
        key_task = asyncio.create_task(
            self._key_listener(done_event),
            name='scheduler-key-listener',
        )

        try:
            # Wait for all items to be processed.
            await self._queue.join()
        except (asyncio.CancelledError, KeyboardInterrupt):
            logger.warning(
                'scheduler_cancelled',
                published=len(self._result.published),
                failed=len(self._result.failed),
                remaining=self._total - self._completed,
            )
            self._notify_scheduler_state('cancelled')
        finally:
            done_event.set()

            key_task.cancel()
            for w in workers:
                w.cancel()

            # Suppress CancelledError from cancelled workers.
            await asyncio.gather(*workers, key_task, return_exceptions=True)

            # Remove signal handlers.
            self._uninstall_signal_handlers(loop)

        logger.info(
            'scheduler_complete',
            published=len(self._result.published),
            failed=len(self._result.failed),
        )
        return self._result

    # -- Keyboard shortcuts ------------------------------------------------

    async def _key_listener(self, done_event: asyncio.Event) -> None:
        """Listen for keyboard shortcuts (p=pause, r=resume, q=cancel, l=log).

        Puts stdin into cbreak mode for single-keystroke reads without
        requiring Enter. Only active when stdin is a TTY on Unix.
        Restores terminal settings on exit.

        Uses ``select()`` with a timeout to avoid blocking the thread
        pool executor indefinitely (which would prevent clean shutdown).

        Args:
            done_event: Set when the scheduler is done (stops listener).
        """
        if sys.platform == 'win32' or not sys.stdin.isatty():
            return

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)

        def _read_key() -> str | None:
            """Read a single key with 0.5s timeout. Returns None on timeout."""
            readable, _, _ = select.select([fd], [], [], 0.5)
            if readable:
                return sys.stdin.read(1)
            return None

        loop = asyncio.get_running_loop()

        try:
            tty.setcbreak(fd)

            while not done_event.is_set():
                char = await loop.run_in_executor(None, _read_key)
                if done_event.is_set():
                    break
                if char is None:
                    continue
                if char == 'p':
                    self.pause()
                elif char == 'r':
                    self.resume()
                elif char == 'q':
                    logger.info('scheduler_quit_requested')
                    raise asyncio.CancelledError
                elif char == 'a':
                    self._view_mode = ViewMode.ALL
                    self._notify_view_mode()
                elif char == 'w':
                    self._view_mode = ViewMode.WINDOW
                    self._notify_view_mode()
                elif char == 'f':
                    # Cycle: ALL → ACTIVE → FAILED → ALL.
                    filters = list(DisplayFilter)
                    idx = filters.index(self._display_filter)
                    self._display_filter = filters[(idx + 1) % len(filters)]
                    self._notify_view_mode()
                elif char == 'l':
                    # Toggle between LOG and the previous table mode.
                    if self._view_mode == ViewMode.LOG:
                        self._view_mode = self._previous_view_mode
                    else:
                        self._previous_view_mode = self._view_mode
                        self._view_mode = ViewMode.LOG
                    self._notify_view_mode()
        except asyncio.CancelledError:
            raise
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    # -- Observer helpers --------------------------------------------------

    def _notify_stage(self, name: str, stage_value: str) -> None:
        """Notify the observer of a per-package stage change.

        Args:
            name: Package name.
            stage_value: Stage enum value string (e.g. 'retrying').
        """
        if self._observer is not None:
            self._observer.on_stage(name, PublishStage(stage_value))

    def _notify_scheduler_state(self, state_value: str) -> None:
        """Notify the observer of a scheduler-level state change.

        Args:
            state_value: SchedulerState enum value string.
        """
        if self._observer is not None:
            self._observer.on_scheduler_state(SchedulerState(state_value))

    def _notify_view_mode(self) -> None:
        """Notify the observer that the view mode or filter changed."""
        if self._observer is not None:
            self._observer.on_view_mode(self._view_mode, self._display_filter)

    def _block_dependents(self, failed_name: str) -> None:
        """Recursively mark all transitive dependents of a failed package as BLOCKED.

        When a package fails, none of its dependents can ever run.
        This walks the dependency tree and marks each as BLOCKED in the
        observer, and increments ``_completed`` so the scheduler doesn't
        hang waiting for them.

        Args:
            failed_name: Name of the package that failed.
        """
        node = self._nodes.get(failed_name)
        if node is None:
            return

        for dep_name in node.dependents:
            if dep_name in self._done:
                continue
            # Mark as blocked (completed without publishing).
            self._done.add(dep_name)
            self._completed += 1
            self._notify_stage(dep_name, 'blocked')
            logger.info(
                'scheduler_package_blocked',
                package=dep_name,
                blocked_by=failed_name,
            )
            # Mark a sentinel on the queue so join() doesn't hang.
            # We need task_done for each blocked package that was
            # never dequeued; put + immediate task_done won't work.
            # Instead, just treat them as completed via the counter.
            #
            # Recurse to block transitive dependents.
            self._block_dependents(dep_name)

    # -- Signal handlers ---------------------------------------------------

    def _install_signal_handlers(self, loop: asyncio.AbstractEventLoop) -> None:
        """Register SIGUSR1 (pause) and SIGUSR2 (resume) signal handlers.

        Only available on Unix. Silently skipped on Windows.
        """
        if sys.platform == 'win32':
            return

        try:
            loop.add_signal_handler(signal.SIGUSR1, self.pause)
            loop.add_signal_handler(signal.SIGUSR2, self.resume)
            logger.debug(
                'scheduler_signals_installed',
                pause='SIGUSR1 (kill -USR1 <pid>)',
                resume='SIGUSR2 (kill -USR2 <pid>)',
                pid=os.getpid(),
            )
        except (ValueError, OSError):
            # Not running in main thread, or platform doesn't support it.
            logger.debug('scheduler_signals_skipped', reason='not main thread or unsupported')

    def _uninstall_signal_handlers(self, loop: asyncio.AbstractEventLoop) -> None:
        """Remove signal handlers registered by _install_signal_handlers."""
        if sys.platform == 'win32':
            return

        try:
            loop.remove_signal_handler(signal.SIGUSR1)
            loop.remove_signal_handler(signal.SIGUSR2)
        except (ValueError, OSError):
            pass

    @property
    def nodes(self) -> dict[str, PackageNode]:
        """Return the node map (read-only access for inspection)."""
        return self._nodes


__all__ = [
    'PackageNode',
    'Scheduler',
    'SchedulerResult',
]
