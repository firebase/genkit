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
    │ _publish_one │───────────────▶│ UI implementations │
    │              │                │   (Rich / Log)     │
    └──────────────┘                └─────────┬─────────┘
                                              │
                          ┌───────────────────┼───────────────────┐
                          │                   │                   │
                  ┌───────┴───────┐   ┌───────┴───────┐   ┌──────┴──────┐
                  │ RichProgress  │   │ LogProgress   │   │ NullProgress│
                  │   UI (TTY)    │   │   UI (CI)     │   │  (tests)    │
                  └───────────────┘   └───────────────┘   └─────────────┘

    Types (PublishStage, SchedulerState, PublishObserver) live in
    observer.py to keep the dependency graph clean.

Sliding window::

    When total packages exceed terminal height, RichProgressUI shows
    only active + recently completed packages (sliding window), with
    a collapsed summary for waiting/completed packages.

Usage::

    from releasekit.ui import create_progress_ui
    from releasekit.observer import PublishStage

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
from dataclasses import dataclass, field
from types import TracebackType

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from releasekit.logging import get_logger
from releasekit.observer import DisplayFilter, PublishObserver, PublishStage, SchedulerState, ViewMode

logger = get_logger(__name__)


# Emoji and color for each stage.
_STAGE_DISPLAY: dict[PublishStage, tuple[str, str]] = {
    PublishStage.WAITING: ('⏳', 'dim'),
    PublishStage.PINNING: ('🔧', 'yellow'),
    PublishStage.BUILDING: ('🔨', 'yellow'),
    PublishStage.PUBLISHING: ('📤', 'cyan'),
    PublishStage.POLLING: ('🔍', 'cyan'),
    PublishStage.VERIFYING: ('🧪', 'magenta'),
    PublishStage.RETRYING: ('🔄', 'yellow bold'),
    PublishStage.PUBLISHED: ('✅', 'green'),
    PublishStage.FAILED: ('❌', 'red bold'),
    PublishStage.SKIPPED: ('⏭️ ', 'dim'),
    PublishStage.BLOCKED: ('🚫', 'red dim'),
}

# Progress fraction per stage (for the progress bar).
_STAGE_PROGRESS: dict[PublishStage, float] = {
    PublishStage.WAITING: 0.0,
    PublishStage.PINNING: 0.10,
    PublishStage.BUILDING: 0.30,
    PublishStage.PUBLISHING: 0.50,
    PublishStage.POLLING: 0.70,
    PublishStage.VERIFYING: 0.85,
    PublishStage.RETRYING: 0.50,
    PublishStage.PUBLISHED: 1.0,
    PublishStage.FAILED: 1.0,
    PublishStage.SKIPPED: 1.0,
    PublishStage.BLOCKED: 1.0,
}

# Terminal states that won't change.
_TERMINAL_STAGES = frozenset({
    PublishStage.PUBLISHED,
    PublishStage.FAILED,
    PublishStage.SKIPPED,
    PublishStage.BLOCKED,
})

# Maximum number of rows shown in the Rich table before switching to
# a sliding window that only displays active + recently completed rows.
_MAX_VISIBLE_ROWS = 30

# Maximum number of log lines shown in the LOG view mode.
_MAX_LOG_LINES = 40


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
        blocked = sum(1 for r in self._packages.values() if r.stage == PublishStage.BLOCKED)
        logger.info(
            'publish_ui_complete',
            published=published,
            failed=failed,
            skipped=skipped,
            blocked=blocked,
            total=len(self._packages),
        )

    def on_level_start(self, level: int, package_names: list[str]) -> None:
        """Log level start."""
        logger.info('level_start', level=level, packages=package_names)

    def on_scheduler_state(self, state: SchedulerState) -> None:
        """Log scheduler state change."""
        logger.info('scheduler_state', state=state.value)


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

    For large workspaces (>30 packages), a sliding window shows only
    active and recently-completed packages. Waiting and finished
    packages are collapsed into summary counts.
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
    _scheduler_state: SchedulerState = SchedulerState.RUNNING
    _view_mode: ViewMode = ViewMode.WINDOW
    _display_filter: DisplayFilter = DisplayFilter.ALL
    _log_lines: list[str] = field(default_factory=list)

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
        # Append a log line for LOG view mode.
        emoji, _ = _STAGE_DISPLAY.get(stage, ('?', ''))
        self._log_lines.append(f'{emoji} {name}: {stage.value} ({row.elapsed_str})')
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

    def on_scheduler_state(self, state: SchedulerState) -> None:
        """Update scheduler state and refresh the display."""
        self._scheduler_state = state
        self._refresh()

    def on_view_mode(self, mode: ViewMode, display_filter: DisplayFilter) -> None:
        """Update view mode / filter and refresh the display."""
        self._view_mode = mode
        self._display_filter = display_filter
        self._refresh()

    def _refresh(self) -> None:
        """Update the live display."""
        if self._live is not None:
            if self._view_mode == ViewMode.LOG:
                self._live.update(self._render_log())
            else:
                self._live.update(self._render())

    def _visible_rows(self) -> list[str]:
        """Select which package rows to display.

        Respects both ViewMode (ALL vs WINDOW) and DisplayFilter
        (ALL vs ACTIVE vs FAILED).

        Returns:
            List of package names to display in the table.
        """
        # Apply display filter first.
        if self._display_filter == DisplayFilter.ACTIVE:
            candidates = [name for name in self._package_order if self._packages[name].stage not in _TERMINAL_STAGES]
        elif self._display_filter == DisplayFilter.FAILED:
            candidates = [
                name
                for name in self._package_order
                if self._packages[name].stage in {PublishStage.FAILED, PublishStage.BLOCKED}
            ]
        else:
            candidates = list(self._package_order)

        # ViewMode.ALL: show everything that passed the filter.
        if self._view_mode == ViewMode.ALL or len(candidates) <= _MAX_VISIBLE_ROWS:
            return candidates

        # ViewMode.WINDOW: sliding window — active + recently completed + failed.
        visible: list[str] = []
        for name in candidates:
            row = self._packages[name]
            if row.stage in {
                PublishStage.PINNING,
                PublishStage.BUILDING,
                PublishStage.PUBLISHING,
                PublishStage.POLLING,
                PublishStage.VERIFYING,
                PublishStage.RETRYING,
                PublishStage.FAILED,
                PublishStage.BLOCKED,
            }:
                visible.append(name)

        # Add recently completed (last 5 finished packages).
        completed = [
            name
            for name in candidates
            if self._packages[name].stage == PublishStage.PUBLISHED and self._packages[name].end_time is not None
        ]
        completed.sort(key=lambda n: self._packages[n].end_time or 0, reverse=True)
        for name in completed[:5]:
            if name not in visible:
                visible.append(name)

        # Add next few waiting packages (up to fill _MAX_VISIBLE_ROWS).
        remaining_slots = _MAX_VISIBLE_ROWS - len(visible)
        if remaining_slots > 0:
            for name in candidates:
                if self._packages[name].stage == PublishStage.WAITING and name not in visible:
                    visible.append(name)
                    remaining_slots -= 1
                    if remaining_slots <= 0:
                        break

        # Sort by original order for display stability.
        order_index = {name: i for i, name in enumerate(self._package_order)}
        visible.sort(key=lambda n: order_index.get(n, 0))
        return visible

    def _render(self) -> Panel:
        """Build the complete display panel."""
        stats = self._get_stats()

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

        visible_names = self._visible_rows()
        hidden_count = len(self._package_order) - len(visible_names)

        for name in visible_names:
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
                elif row.stage == PublishStage.BLOCKED:
                    bar = Text('██████████', style='red dim')
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

        # Collapsed row indicator for large workspaces.
        if hidden_count > 0:
            table.add_row(
                '',
                Text(f'  … {hidden_count} more (waiting/completed)', style='dim italic'),
                '',
                Text('', style='dim'),
                Text('', style='dim'),
                '',
            )

        # Summary footer.
        summary = self._format_summary(stats)

        # ETA estimate.
        eta_str = ''
        if stats['published'] > 0 and (stats['waiting'] + stats['active']) > 0:
            avg_time = stats['elapsed'] / stats['published']
            remaining = (stats['waiting'] + stats['active']) * avg_time
            if remaining < 60:
                eta_str = f'  ETA: ~{remaining:.0f}s'
            else:
                eta_str = f'  ETA: ~{remaining / 60:.1f}m'

        elapsed_str = self._format_elapsed(stats['elapsed'])

        # Control hint for keyboard shortcuts.
        control_hint = ''
        view_hint = ''
        if sys.stdin.isatty():
            if self._scheduler_state == SchedulerState.RUNNING:
                control_hint = '  │  [dim]p[/]=pause [dim]q[/]=quit'
            elif self._scheduler_state == SchedulerState.PAUSED:
                control_hint = '  │  [yellow]r[/]=resume [dim]q[/]=quit'

            # View mode and filter indicators.
            mode_label = '📋all' if self._view_mode == ViewMode.ALL else '🪟win'
            filter_label = self._display_filter.value
            view_hint = f'  │  [dim]l[/]=log [dim]a[/]/[dim]w[/]={mode_label} [dim]f[/]={filter_label}'

        footer = f'{summary}  │  Elapsed: {elapsed_str}{eta_str}{control_hint}{view_hint}'

        # Error panel (if any).
        content = table
        if self._errors:
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

        base_title = (
            f'releasekit publish — {self.total_packages} packages '
            f'across {self.total_levels} levels (concurrency: {self.concurrency})'
        )
        title, border_style = self._format_title_and_border(base_title)

        return Panel(
            content,
            title=f'[bold]{title}[/]',
            subtitle=footer,
            border_style=border_style,
            expand=True,
        )

    def _render_log(self) -> Panel:
        """Build a log-style panel showing recent stage transitions."""
        recent = self._log_lines[-_MAX_LOG_LINES:]
        stats = self._get_stats()
        summary = self._format_summary(stats)
        elapsed_str = self._format_elapsed(stats['elapsed'])

        # Control hints.
        control_hint = ''
        if sys.stdin.isatty():
            control_hint = '  │  [dim]l[/]=table'
            if self._scheduler_state == SchedulerState.RUNNING:
                control_hint += ' [dim]p[/]=pause [dim]q[/]=quit'
            elif self._scheduler_state == SchedulerState.PAUSED:
                control_hint += ' [yellow]r[/]=resume [dim]q[/]=quit'

        footer = f'{summary}  │  Elapsed: {elapsed_str}{control_hint}'

        # Build log content.
        if recent:
            log_text = Text('\n'.join(recent))
        else:
            log_text = Text('Waiting for events...', style='dim')

        base_title = f'releasekit publish — {self.total_packages} packages (📝 log view)'
        title, border_style = self._format_title_and_border(base_title)

        return Panel(
            log_text,
            title=f'[bold]{title}[/]',
            subtitle=footer,
            border_style=border_style,
            expand=True,
        )

    # -- Shared helpers ----------------------------------------------------

    def _get_stats(self) -> dict[str, int | float]:
        """Compute package statistics for rendering.

        Returns:
            Dict with keys: elapsed, published, failed, skipped, blocked,
            retrying, active, waiting.
        """
        return {
            'elapsed': time.monotonic() - self._start_time,
            'published': sum(1 for r in self._packages.values() if r.stage == PublishStage.PUBLISHED),
            'failed': sum(1 for r in self._packages.values() if r.stage == PublishStage.FAILED),
            'skipped': sum(1 for r in self._packages.values() if r.stage == PublishStage.SKIPPED),
            'blocked': sum(1 for r in self._packages.values() if r.stage == PublishStage.BLOCKED),
            'retrying': sum(1 for r in self._packages.values() if r.stage == PublishStage.RETRYING),
            'active': sum(
                1
                for r in self._packages.values()
                if r.stage not in _TERMINAL_STAGES and r.stage not in {PublishStage.WAITING, PublishStage.RETRYING}
            ),
            'waiting': sum(1 for r in self._packages.values() if r.stage == PublishStage.WAITING),
        }

    @staticmethod
    def _format_summary(stats: dict[str, int | float]) -> str:
        """Build the summary status string from stats."""
        parts: list[str] = []
        if stats['published']:
            parts.append(f'[green]✅ {stats["published"]} published[/]')
        if stats['active']:
            parts.append(f'[cyan]⚡ {stats["active"]} active[/]')
        if stats['retrying']:
            parts.append(f'[yellow]🔄 {stats["retrying"]} retrying[/]')
        if stats['waiting']:
            parts.append(f'[dim]⏳ {stats["waiting"]} waiting[/]')
        if stats['skipped']:
            parts.append(f'[dim]⏭️  {stats["skipped"]} skipped[/]')
        if stats['blocked']:
            parts.append(f'[red dim]🚫 {stats["blocked"]} blocked[/]')
        if stats['failed']:
            parts.append(f'[red]❌ {stats["failed"]} failed[/]')
        return ' │ '.join(parts) if parts else 'Starting...'

    @staticmethod
    def _format_elapsed(elapsed: int | float) -> str:
        """Format elapsed time as a human-readable string."""
        return f'{elapsed:.1f}s' if elapsed < 60 else f'{elapsed / 60:.1f}m'

    def _format_title_and_border(self, base_title: str) -> tuple[str, str]:
        """Append scheduler state banner and return (title, border_style)."""
        title = base_title
        border_style = 'blue'
        if self._scheduler_state == SchedulerState.PAUSED:
            title += '  [yellow bold]⏸ PAUSED[/]'
            border_style = 'yellow'
        elif self._scheduler_state == SchedulerState.CANCELLED:
            title += '  [red bold]✖ CANCELLED[/]'
            border_style = 'red'
        return title, border_style


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
    'SchedulerState',
    'create_progress_ui',
]
