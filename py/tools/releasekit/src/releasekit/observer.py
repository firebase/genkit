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

"""Observer protocol and enums for publish pipeline state.

Defines the stage/state enums and the observer interface that both
the scheduler and UI modules depend on. Extracted here to keep the
dependency graph clean::

    observer.py  ← PublishStage, SchedulerState, PublishObserver
      ↑              ↑
      │              │
    ui.py        scheduler.py
      ↑
    publisher.py

Stage indicators::

    ⏳ waiting  → 🔧 pinning → 🔨 building → 📤 publishing
    → 🔍 polling → 🧪 verifying → ✅ published / ❌ failed / ⏭️  skipped
    → 🔄 retrying (transient failure, backoff in progress)
    → 🚫 blocked (dependency failed, will not run)

Scheduler-level states::

    ▶ RUNNING  ⏸ PAUSED  ✖ CANCELLED

View modes::

    📋 ALL      show every package
    🪟 WINDOW   sliding window (active + recently completed + failed)
    📝 LOG      structured log lines (per-stage transitions)

Display filters::

    🔎 ALL      no filter
    🔎 ACTIVE   only active (non-terminal) packages
    🔎 FAILED   only failed + blocked packages
"""

from __future__ import annotations

from collections.abc import Sequence
from contextlib import AbstractContextManager
from enum import Enum
from types import TracebackType


class PublishStage(str, Enum):
    """Pipeline stage for a single package.

    Ordered by pipeline progression. Each package moves through
    these stages during publishing.
    """

    WAITING = 'waiting'
    PINNING = 'pinning'
    BUILDING = 'building'
    PUBLISHING = 'publishing'
    POLLING = 'polling'
    VERIFYING = 'verifying'
    RETRYING = 'retrying'
    PUBLISHED = 'published'
    FAILED = 'failed'
    SKIPPED = 'skipped'
    BLOCKED = 'blocked'


class SchedulerState(str, Enum):
    """Scheduler-level state.

    Represents the overall scheduler lifecycle, not per-package.
    """

    RUNNING = 'running'
    PAUSED = 'paused'
    CANCELLED = 'cancelled'


class ViewMode(str, Enum):
    """UI display mode — how many rows to show."""

    ALL = 'all'
    WINDOW = 'window'
    LOG = 'log'


class DisplayFilter(str, Enum):
    """UI display filter — which packages to include."""

    ALL = 'all'
    ACTIVE = 'active'
    FAILED = 'failed'


class PublishObserver(AbstractContextManager['PublishObserver']):
    """Protocol for receiving publish progress updates.

    Implementations must support the context manager protocol for
    setup/teardown of UI resources (e.g. Rich Live).
    """

    def init_packages(self, packages: Sequence[tuple[str, int, str]]) -> None:
        """Register all packages with their levels and versions.

        Args:
            packages: Sequence of ``(name, level, version)`` tuples,
                ordered by level then name.
        """

    def on_stage(self, name: str, stage: PublishStage) -> None:
        """Notify that a package has entered a new pipeline stage.

        Args:
            name: Package name.
            stage: The new stage.
        """

    def on_error(self, name: str, error: str) -> None:
        """Notify that a package has failed.

        Args:
            name: Package name.
            error: Error message.
        """

    def on_complete(self) -> None:
        """Notify that the entire publish run is complete."""

    def on_level_start(self, level: int, package_names: list[str]) -> None:
        """Notify that a level is starting.

        Args:
            level: Level index.
            package_names: Names of packages in this level.
        """

    def on_scheduler_state(self, state: SchedulerState) -> None:
        """Notify that the scheduler has changed state.

        Args:
            state: The new scheduler state (RUNNING, PAUSED, CANCELLED).
        """

    def on_view_mode(self, mode: ViewMode, display_filter: DisplayFilter) -> None:
        """Notify that the UI view mode or filter has changed.

        Args:
            mode: The new view mode (ALL or WINDOW).
            display_filter: The new display filter.
        """

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Clean up UI resources."""


__all__ = [
    'DisplayFilter',
    'PublishObserver',
    'PublishStage',
    'SchedulerState',
    'ViewMode',
]
