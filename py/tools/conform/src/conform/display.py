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

"""Rich display helpers — progress tables, summary tables, and Rust-style messages.

All shared types (:class:`Status`, :class:`PluginResult`) live in
:mod:`conform.types` to avoid circular imports between this module
and :mod:`conform.runner`.
"""

from __future__ import annotations

from rich import box
from rich.console import Console
from rich.markup import escape
from rich.table import Table
from rich.text import Text

from conform.types import PluginResult, Status

# Status → (emoji, style) for the summary table.
_STATUS_DISPLAY: dict[Status, tuple[str, str]] = {
    Status.PENDING: ('◌', 'dim'),
    Status.RUNNING: ('⟳', 'bold blue'),
    Status.PASSED: ('✅', 'bold green'),
    Status.FAILED: ('❌', 'bold red'),
    Status.SKIPPED: ('⏭️ ', 'bold yellow'),
    Status.ERROR: ('⚠️ ', 'bold red'),
}

# Shared console instances.
#   console     → stderr (progress, errors, warnings)
#   stdout_console → stdout (tables, help-adjacent output)
console = Console(stderr=True)
stdout_console = Console()


# ---------------------------------------------------------------------------
# Rust-style messages
# ---------------------------------------------------------------------------


def rust_error(code: str, message: str, *, hint: str = '', note: str = '') -> None:
    """Print a Rust-style error message to stderr.

    Example output::

        error[E0001]: missing environment variable
          |
          = note: ANTHROPIC_API_KEY is not set
          = hint: export ANTHROPIC_API_KEY=sk-...
    """
    console.print(f'[bold red]error[/bold red]\\[[bold]{code}[/bold]]: {escape(message)}')
    if note:
        console.print('  [dim]|[/dim]')
        console.print(f'  [dim]=[/dim] [bold]note[/bold]: {escape(note)}')
    if hint:
        console.print(f'  [dim]=[/dim] [bold cyan]hint[/bold cyan]: {escape(hint)}')
    console.print()


def rust_warning(code: str, message: str, *, note: str = '') -> None:
    """Print a Rust-style warning message to stderr."""
    console.print(f'[bold yellow]warning[/bold yellow]\\[[bold]{code}[/bold]]: {escape(message)}')
    if note:
        console.print('  [dim]|[/dim]')
        console.print(f'  [dim]=[/dim] [bold]note[/bold]: {escape(note)}')
    console.print()


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def elapsed_str(secs: float) -> str:
    """Format elapsed seconds as ``Xm Ys`` or ``Ys``."""
    if secs <= 0:
        return '—'
    mins = int(secs) // 60
    sec = secs - mins * 60
    if mins > 0:
        return f'{mins}m {sec:.1f}s'
    return f'{sec:.1f}s'


def status_emoji(status: Status) -> str:
    """Return the emoji string for *status*."""
    return _STATUS_DISPLAY[status][0]


def status_style(status: Status) -> str:
    """Return the Rich style string for *status*."""
    return _STATUS_DISPLAY[status][1]


# ---------------------------------------------------------------------------
# Progress table (live-updated during ``conform check-model``)
# ---------------------------------------------------------------------------


def build_progress_table(results: dict[str, PluginResult]) -> Table:
    """Build a Rich table showing current status of all plugins."""
    table = Table(
        title='⏳ Model Conformance Tests',
        box=box.ROUNDED,
        title_style='bold cyan',
        border_style='dim',
        header_style='bold',
        expand=False,
        pad_edge=True,
        show_lines=False,
    )
    table.add_column('', width=3, justify='center')
    table.add_column('Plugin', style='bold', min_width=24)
    table.add_column('Status', min_width=10)
    table.add_column('Tests', justify='right', min_width=8)
    table.add_column('Time', justify='right', min_width=10)
    table.add_column('Details', ratio=1)

    for _plugin, result in results.items():
        emoji = status_emoji(result.status)
        style = status_style(result.status)

        status_text = Text(
            result.status.value.upper() if result.status != Status.RUNNING else 'running…',
            style=style,
        )

        # Show test counts if available.
        total = result.tests_passed + result.tests_failed
        if total > 0:
            if result.tests_failed == 0:
                tests_text = Text(f'{result.tests_passed}/{total}', style='green')
            else:
                tests_text = Text(f'{result.tests_passed}/{total}', style='red')
        else:
            tests_text = Text('—', style='dim')

        detail = ''
        if result.status == Status.SKIPPED and result.missing_env_vars:
            detail = f'missing: {", ".join(result.missing_env_vars)}'
        elif result.status in (Status.FAILED, Status.ERROR) and result.error_message:
            detail = result.error_message[:80]

        table.add_row(
            emoji,
            result.plugin,
            status_text,
            tests_text,
            elapsed_str(result.elapsed_s),
            Text(detail, style='dim'),
        )

    return table


# ---------------------------------------------------------------------------
# Summary table (printed once after ``conform check-model`` completes)
# ---------------------------------------------------------------------------


def build_summary_table(results: dict[str, PluginResult]) -> Table:
    """Build a final summary table with emojis, printed after all tests complete."""
    table = Table(
        title='📊 Conformance Results',
        box=box.HEAVY_HEAD,
        title_style='bold cyan',
        border_style='bright_black',
        header_style='bold white',
        expand=False,
        pad_edge=True,
        show_lines=False,
    )
    table.add_column('', width=3, justify='center')
    table.add_column('Plugin', style='bold', min_width=24)
    table.add_column('Result', min_width=12)
    table.add_column('Tests', justify='right', min_width=8)
    table.add_column('Time', justify='right', min_width=10)
    table.add_column('Details', ratio=1, style='dim')

    for _plugin, result in results.items():
        emoji = status_emoji(result.status)
        style = status_style(result.status)
        label = result.status.value.upper()

        # Show test counts if available.
        total = result.tests_passed + result.tests_failed
        if total > 0:
            if result.tests_failed == 0:
                tests_text = Text(f'{result.tests_passed}/{total}', style='green')
            else:
                tests_text = Text(f'{result.tests_passed}/{total}', style='red')
        else:
            tests_text = Text('—', style='dim')

        detail = ''
        if result.status == Status.SKIPPED and result.missing_env_vars:
            detail = f'missing: {", ".join(result.missing_env_vars)}'
        elif result.status in (Status.FAILED, Status.ERROR) and result.error_message:
            detail = result.error_message[:100]

        table.add_row(
            emoji,
            result.plugin,
            Text(label, style=style),
            tests_text,
            elapsed_str(result.elapsed_s),
            detail,
        )

    return table


def print_summary_footer(results: dict[str, PluginResult]) -> None:
    """Print the aggregated pass/fail/skip/error counts with emojis."""
    passed = sum(1 for r in results.values() if r.status == Status.PASSED)
    failed = sum(1 for r in results.values() if r.status == Status.FAILED)
    errors = sum(1 for r in results.values() if r.status == Status.ERROR)
    skipped = sum(1 for r in results.values() if r.status == Status.SKIPPED)
    total_time = max(
        (r.elapsed_s for r in results.values()),
        default=0.0,
    )

    parts: list[str] = []
    if passed:
        parts.append(f'[bold green]✅ {passed} passed[/bold green]')
    if failed:
        parts.append(f'[bold red]❌ {failed} failed[/bold red]')
    if errors:
        parts.append(f'[bold red]⚠️  {errors} error(s)[/bold red]')
    if skipped:
        parts.append(f'[bold yellow]⏭️  {skipped} skipped[/bold yellow]')

    console.print()
    console.print(f'  {" · ".join(parts)}  [dim]({elapsed_str(total_time)} wall time)[/dim]')
    console.print()
