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

"""Rich Live progress table for publish operations.

Provides real-time visual feedback during ``releasekit publish`` with
per-package status, progress bars, and elapsed time. Degrades gracefully
to structured log lines in non-TTY environments (CI).

Architecture::

    publisher.py                    ui.py
    ┌──────────────┐    callback    ┌───────────────────┐
    │ _publish_one │───────────────▶│ PublishObserver    │ (protocol)
    │              │                │   on_stage()       │
    └──────────────┘                │   on_error()       │
                                    │   on_complete()    │
                                    └─────────┬─────────┘
                                              │
                          ┌───────────────────┼───────────────────┐
                          │                   │                   │
                  ┌───────┴───────┐   ┌───────┴───────┐   ┌──────┴──────┐
                  │ RichProgress  │   │ LogProgress   │   │ NullProgress│
                  │   UI (TTY)    │   │   UI (CI)     │   │  (tests)    │
                  └───────────────┘   └───────────────┘   └─────────────┘

Stage indicators::

    ⏳ waiting  → 🔧 pinning → 🔨 building → 📤 publishing
    → 🔍 polling → 🧪 verifying → ✅ published / ❌ failed / ⏭️  skipped

Usage::

    from releasekit.ui import create_progress_ui

    # Auto-detects TTY; returns RichProgressUI or LogProgressUI.
    ui = create_progress_ui(
        total_packages=12,
        total_levels=4,
        concurrency=5,
    )

    with ui:
        ui.on_stage('genkit', PublishStage.BUILDING)
        ui.on_stage('genkit', PublishStage.PUBLISHING)
        ui.on_stage('genkit', PublishStage.PUBLISHED)
        ui.on_error('genkit-plugin-x', 'Build failed: ...')
"""

from __future__ import annotations

import sys
import time
from collections.abc import Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from enum import Enum
from types import TracebackType

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from releasekit.logging import get_logger

logger = get_logger(__name__)


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
    PUBLISHED = 'published'
    FAILED = 'failed'
    SKIPPED = 'skipped'


# Emoji and color for each stage.
_STAGE_DISPLAY: dict[PublishStage, tuple[str, str]] = {
    PublishStage.WAITING: ('⏳', 'dim'),
    PublishStage.PINNING: ('🔧', 'yellow'),
    PublishStage.BUILDING: ('🔨', 'yellow'),
    PublishStage.PUBLISHING: ('📤', 'cyan'),
    PublishStage.POLLING: ('🔍', 'cyan'),
    PublishStage.VERIFYING: ('🧪', 'magenta'),
    PublishStage.PUBLISHED: ('✅', 'green'),
    PublishStage.FAILED: ('❌', 'red bold'),
    PublishStage.SKIPPED: ('⏭️ ', 'dim'),
}

# Progress fraction per stage (for the progress bar).
_STAGE_PROGRESS: dict[PublishStage, float] = {
    PublishStage.WAITING: 0.0,
    PublishStage.PINNING: 0.10,
    PublishStage.BUILDING: 0.30,
    PublishStage.PUBLISHING: 0.50,
    PublishStage.POLLING: 0.70,
    PublishStage.VERIFYING: 0.85,
    PublishStage.PUBLISHED: 1.0,
    PublishStage.FAILED: 1.0,
    PublishStage.SKIPPED: 1.0,
}

# Terminal states that won't change.
_TERMINAL_STAGES = frozenset({
    PublishStage.PUBLISHED,
    PublishStage.FAILED,
    PublishStage.SKIPPED,
})


@dataclass
class _PackageRow:
    """Internal tracking for one package row in the progress table."""

    name: str
    level: int
    version: str
    stage: PublishStage = PublishStage.WAITING
    start_time: float | None = None
    end_time: float | None = None
    error: str = ''

    @property
    def elapsed(self) -> float | None:
        """Elapsed time in seconds, or None if not started."""
        if self.start_time is None:
            return None
        end = self.end_time if self.end_time is not None else time.monotonic()
        return end - self.start_time

    @property
    def elapsed_str(self) -> str:
        """Formatted elapsed time string."""
        elapsed = self.elapsed
        if elapsed is None:
            return '—'
        if elapsed < 60:
            return f'{elapsed:.1f}s'
        minutes = int(elapsed // 60)
        seconds = elapsed % 60
        return f'{minutes}m{seconds:.0f}s'


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

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Clean up UI resources."""


class NullProgressUI(PublishObserver):
    """No-op observer for testing and dry runs."""

    def __enter__(self) -> NullProgressUI:
        """Enter context manager."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit context manager."""


@dataclass
class LogProgressUI(PublishObserver):
    """Structured-log observer for non-TTY/CI environments.

    Emits one log line per state transition instead of a live table.
    """

    _packages: dict[str, _PackageRow] = field(default_factory=dict)

    def __enter__(self) -> LogProgressUI:
        """Enter context manager."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit context manager."""

    def init_packages(self, packages: Sequence[tuple[str, int, str]]) -> None:
        """Register packages."""
        for name, level, version in packages:
            self._packages[name] = _PackageRow(name=name, level=level, version=version)

    def on_stage(self, name: str, stage: PublishStage) -> None:
        """Log the stage transition."""
        row = self._packages.get(name)
        if row is None:
            return
        row.stage = stage
        if stage not in {PublishStage.WAITING, PublishStage.SKIPPED} and row.start_time is None:
            row.start_time = time.monotonic()
        if stage in _TERMINAL_STAGES:
            row.end_time = time.monotonic()
        logger.info(
            'stage_change',
            package=name,
            stage=stage.value,
            elapsed=row.elapsed_str,
        )

    def on_error(self, name: str, error: str) -> None:
        """Log the error."""
        row = self._packages.get(name)
        if row is not None:
            row.stage = PublishStage.FAILED
            row.error = error
            row.end_time = time.monotonic()
        logger.error('package_error', package=name, error=error)

    def on_complete(self) -> None:
        """Log completion summary."""
        published = sum(1 for r in self._packages.values() if r.stage == PublishStage.PUBLISHED)
        failed = sum(1 for r in self._packages.values() if r.stage == PublishStage.FAILED)
        skipped = sum(1 for r in self._packages.values() if r.stage == PublishStage.SKIPPED)
        logger.info(
            'publish_ui_complete',
            published=published,
            failed=failed,
            skipped=skipped,
            total=len(self._packages),
        )

    def on_level_start(self, level: int, package_names: list[str]) -> None:
        """Log level start."""
        logger.info('level_start', level=level, packages=package_names)


def _build_progress_bar(fraction: float, width: int = 10) -> Text:
    """Build a block-character progress bar.

    Args:
        fraction: Progress from 0.0 to 1.0.
        width: Total character width of the bar.

    Returns:
        A Rich :class:`Text` object with colored blocks.
    """
    filled = int(fraction * width)
    empty = width - filled
    bar = Text()
    if filled > 0:
        bar.append('█' * filled, style='green')
    if empty > 0:
        bar.append('░' * empty, style='dim')
    return bar


@dataclass
class RichProgressUI(PublishObserver):
    """Rich Live table observer for TTY environments.

    Renders a live-updating table showing per-package publish progress
    with stage indicators, progress bars, and elapsed time.
    """

    total_packages: int = 0
    total_levels: int = 0
    concurrency: int = 5
    _packages: dict[str, _PackageRow] = field(default_factory=dict)
    _package_order: list[str] = field(default_factory=list)
    _errors: list[tuple[str, str]] = field(default_factory=list)
    _console: Console = field(default_factory=lambda: Console(stderr=True))
    _live: Live | None = field(default=None, repr=False)
    _start_time: float = field(default_factory=time.monotonic)

    def __enter__(self) -> RichProgressUI:
        """Enter context manager and start the Rich Live display."""
        self._start_time = time.monotonic()
        self._live = Live(
            self._render(),
            console=self._console,
            refresh_per_second=4,
            transient=False,
        )
        self._live.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Stop the Rich Live display with a final render."""
        if self._live is not None:
            # Final render before closing.
            self._live.update(self._render())
            self._live.__exit__(exc_type, exc_val, exc_tb)
            self._live = None

    def init_packages(self, packages: Sequence[tuple[str, int, str]]) -> None:
        """Register packages and build display order."""
        self._package_order = []
        for name, level, version in packages:
            self._packages[name] = _PackageRow(name=name, level=level, version=version)
            self._package_order.append(name)
        self.total_packages = len(packages)
        if packages:
            self.total_levels = max(level for _, level, _ in packages) + 1
        self._refresh()

    def on_stage(self, name: str, stage: PublishStage) -> None:
        """Update a package's stage and refresh the display."""
        row = self._packages.get(name)
        if row is None:
            return
        row.stage = stage
        if stage not in {PublishStage.WAITING, PublishStage.SKIPPED} and row.start_time is None:
            row.start_time = time.monotonic()
        if stage in _TERMINAL_STAGES:
            row.end_time = time.monotonic()
        self._refresh()

    def on_error(self, name: str, error: str) -> None:
        """Mark a package as failed and record the error."""
        row = self._packages.get(name)
        if row is not None:
            row.stage = PublishStage.FAILED
            row.error = error
            row.end_time = time.monotonic()
        self._errors.append((name, error))
        self._refresh()

    def on_complete(self) -> None:
        """Final refresh."""
        self._refresh()

    def on_level_start(self, level: int, package_names: list[str]) -> None:
        """No-op for Rich UI (the table already shows level grouping)."""

    def _refresh(self) -> None:
        """Update the live display."""
        if self._live is not None:
            self._live.update(self._render())

    def _render(self) -> Panel:
        """Build the complete display panel."""
        # Header info.
        elapsed = time.monotonic() - self._start_time
        published = sum(1 for r in self._packages.values() if r.stage == PublishStage.PUBLISHED)
        failed = sum(1 for r in self._packages.values() if r.stage == PublishStage.FAILED)
        skipped = sum(1 for r in self._packages.values() if r.stage == PublishStage.SKIPPED)
        active = sum(
            1 for r in self._packages.values() if r.stage not in _TERMINAL_STAGES and r.stage != PublishStage.WAITING
        )
        waiting = sum(1 for r in self._packages.values() if r.stage == PublishStage.WAITING)

        # Build table.
        table = Table(
            show_header=True,
            header_style='bold',
            show_edge=False,
            pad_edge=False,
            expand=True,
        )
        table.add_column('Lvl', width=3, justify='right')
        table.add_column('Package', min_width=20, ratio=3)
        table.add_column('Version', min_width=8, ratio=1)
        table.add_column('Stage', min_width=14, ratio=2)
        table.add_column('Progress', width=12, justify='center')
        table.add_column('Time', width=8, justify='right')

        for name in self._package_order:
            row = self._packages[name]
            emoji, style = _STAGE_DISPLAY.get(row.stage, ('?', ''))
            stage_text = Text(f'{emoji} {row.stage.value}', style=style)
            progress = _STAGE_PROGRESS.get(row.stage, 0.0)
            bar = _build_progress_bar(progress)
            if row.stage in _TERMINAL_STAGES:
                # Use dash bar for terminal states.
                if row.stage == PublishStage.PUBLISHED:
                    bar = Text('██████████', style='green')
                elif row.stage == PublishStage.FAILED:
                    bar = Text('██████████', style='red')
                else:
                    bar = Text('──────────', style='dim')

            table.add_row(
                str(row.level),
                Text(row.name, style='bold' if row.stage not in _TERMINAL_STAGES else ''),
                row.version,
                stage_text,
                bar,
                row.elapsed_str,
            )

        # Summary footer.
        summary_parts = []
        if published:
            summary_parts.append(f'[green]✅ {published} published[/]')
        if active:
            summary_parts.append(f'[cyan]⚡ {active} active[/]')
        if waiting:
            summary_parts.append(f'[dim]⏳ {waiting} waiting[/]')
        if skipped:
            summary_parts.append(f'[dim]⏭️  {skipped} skipped[/]')
        if failed:
            summary_parts.append(f'[red]❌ {failed} failed[/]')

        summary = ' │ '.join(summary_parts) if summary_parts else 'Starting...'

        # ETA estimate.
        eta_str = ''
        if published > 0 and (waiting + active) > 0:
            avg_time = elapsed / published
            remaining = (waiting + active) * avg_time
            if remaining < 60:
                eta_str = f'  ETA: ~{remaining:.0f}s'
            else:
                eta_str = f'  ETA: ~{remaining / 60:.1f}m'

        elapsed_str = f'{elapsed:.1f}s' if elapsed < 60 else f'{elapsed / 60:.1f}m'
        footer = f'{summary}  │  Elapsed: {elapsed_str}{eta_str}'

        # Error panel (if any).
        content = table
        if self._errors:
            from rich.console import Group

            error_lines: list[str] = []
            for pkg_name, error_msg in self._errors[-5:]:  # Show last 5 errors.
                error_lines.append(f'[red bold]{pkg_name}[/]: {error_msg}')
            error_panel = Panel(
                '\n'.join(error_lines),
                title='[red]Errors[/]',
                border_style='red',
                expand=True,
            )
            content = Group(table, Text(''), error_panel)

        # Wrap in main panel.
        title = (
            f'releasekit publish — {self.total_packages} packages '
            f'across {self.total_levels} levels (concurrency: {self.concurrency})'
        )
        return Panel(
            content,
            title=f'[bold]{title}[/]',
            subtitle=footer,
            border_style='blue',
            expand=True,
        )


def create_progress_ui(
    *,
    total_packages: int = 0,
    total_levels: int = 0,
    concurrency: int = 5,
    force_tty: bool | None = None,
) -> PublishObserver:
    """Create the appropriate progress UI based on the environment.

    Auto-detects TTY. Returns :class:`RichProgressUI` for interactive
    terminals and :class:`LogProgressUI` for CI/non-TTY environments.

    Args:
        total_packages: Total number of packages in the run.
        total_levels: Total number of topological levels.
        concurrency: Max concurrent publishes per level.
        force_tty: Override TTY detection (``True``/``False``).
            ``None`` (default) auto-detects.

    Returns:
        A :class:`PublishObserver` instance.
    """
    is_tty = force_tty if force_tty is not None else sys.stderr.isatty()

    if is_tty:
        return RichProgressUI(
            total_packages=total_packages,
            total_levels=total_levels,
            concurrency=concurrency,
        )
    return LogProgressUI()


__all__ = [
    'LogProgressUI',
    'NullProgressUI',
    'PublishObserver',
    'PublishStage',
    'RichProgressUI',
    'create_progress_ui',
]
