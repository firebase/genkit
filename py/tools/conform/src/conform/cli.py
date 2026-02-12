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

"""CLI entry point for the ``conform`` tool.

Provides subcommands::

    conform [GLOBAL FLAGS] check-model [PLUGIN...] [-j N] [-v] [--use-cli]
        Run model conformance tests (native runner, all runtimes).

    conform [GLOBAL FLAGS] check-plugin
        Verify that every model plugin has conformance files.

    conform [GLOBAL FLAGS] list
        List available plugins, their runtimes, and env-var readiness.

Global flags (apply to all subcommands)::

    --runtime NAME[,NAME,...]   Runtimes to use (default: all configured)
    --specs-dir DIR             Override the specs directory

When invoked with no subcommand, displays the help screen followed by
the plugin env-var readiness table.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from dataclasses import replace
from pathlib import Path

from rich import box
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.text import Text

from conform.checker import check_model_conformance
from conform.config import ConformConfig, load_all_runtime_names, load_config
from conform.display import (
    build_progress_table,
    build_summary_table,
    console,
    print_summary_footer,
    rust_error,
    rust_warning,
    stdout_console,
)
from conform.plugins import check_env, discover_plugins, entry_point
from conform.runner import run_all
from conform.types import PluginResult, Status
from conform.util_test_model import TestResult, run_test_model


def _resolve_runtime_names(runtime_arg: str | None) -> list[str]:
    """Resolve which runtimes to use.

    Args:
        runtime_arg: Comma-separated runtime name(s), or ``None`` for all
            configured.

    Returns:
        List of runtime names to operate on.
    """
    if runtime_arg:
        return [name.strip() for name in runtime_arg.split(',') if name.strip()]
    names = load_all_runtime_names()
    return names if names else ['python']


def _plugin_runtimes(plugin: str) -> list[str]:
    """Return the runtime names that have an entry point for *plugin*."""
    available: list[str] = []
    for rt_name in load_all_runtime_names():
        rt_config = load_config(runtime_name=rt_name)
        ep = entry_point(plugin, rt_config)
        if ep.exists():
            available.append(rt_name)
    return available


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser with rich-argparse formatting."""
    try:
        from rich_argparse import RichHelpFormatter

        RichHelpFormatter.styles['argparse.groups'] = 'yellow bold'
        RichHelpFormatter.styles['argparse.args'] = 'cyan'
        RichHelpFormatter.styles['argparse.metavar'] = 'dark_cyan'
        formatter_class: type[argparse.HelpFormatter] = RichHelpFormatter
    except ImportError:
        formatter_class = argparse.HelpFormatter

    # Shared parent parser for global flags — ensures they appear in
    # every subcommand's ``--help`` output.
    global_parser = argparse.ArgumentParser(add_help=False)
    global_parser.add_argument(
        '--runtime',
        default=None,
        metavar='NAME[,NAME,...]',
        help=(
            'Runtime(s) to use, comma-separated (e.g. python, python,js). '
            'If not specified, runs all configured runtimes.'
        ),
    )
    global_parser.add_argument(
        '--specs-dir',
        default=None,
        metavar='DIR',
        help='Override the specs directory (default: from runtime config).',
    )

    parser = argparse.ArgumentParser(
        prog='conform',
        description=(
            'Model conformance test runner for Genkit plugins.\n\n'
            'Runs model conformance tests against multiple plugins and runtimes\n'
            'concurrently, collecting results and displaying a unified table.'
        ),
        formatter_class=formatter_class,
        parents=[global_parser],
    )

    subparsers = parser.add_subparsers(dest='command', help='Available subcommands')

    cm_parser = subparsers.add_parser(
        'check-model',
        help='Run model conformance tests.',
        description=(
            'Run model conformance tests against one or more plugins using the\n'
            'native runner.  By default runs all plugins across all configured\n'
            'runtimes.  Results are displayed in a unified table.\n\n'
            'Use --use-cli to fall back to genkit dev:test-model subprocess.'
        ),
        formatter_class=formatter_class,
        parents=[global_parser],
    )
    cm_parser.add_argument(
        'plugins',
        nargs='*',
        default=[],
        metavar='PLUGIN',
        help='Plugin name(s) to test (default: all available).',
    )
    cm_parser.add_argument(
        '--concurrency',
        '-j',
        type=int,
        default=-1,
        metavar='N',
        help='Maximum concurrent plugins (overrides pyproject.toml).',
    )
    cm_parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Print full stdout/stderr for failed plugins.',
    )
    cm_parser.add_argument(
        '--use-cli',
        action='store_true',
        default=False,
        help='Use genkit CLI (genkit dev:test-model) instead of the native runner.',
    )

    subparsers.add_parser(
        'check-plugin',
        help='Check that every model plugin has conformance files.',
        description=(
            'Verify that every model plugin (identified by model_info.py or\n'
            'listed in [tool.conform.additional-model-plugins]) has both a\n'
            'model-conformance.yaml spec and a conformance_entry.py file.'
        ),
        formatter_class=formatter_class,
        parents=[global_parser],
    )

    subparsers.add_parser(
        'list',
        help='List available plugins and their env-var readiness.',
        description=(
            'Display a table of all plugins that have conformance specs,\n'
            'showing which runtimes and environment variables are available.'
        ),
        formatter_class=formatter_class,
        parents=[global_parser],
    )

    return parser


async def _run_native_check(
    plugins: list[str],
    runtime_names: list[str],
    concurrency: int,
    specs_dir_override: Path | None,
    verbose: bool,
) -> dict[str, PluginResult]:
    """Run native conformance tests for all (plugin, runtime) pairs.

    Creates a unified results dict keyed by ``plugin@runtime`` (or just
    ``plugin`` when only one runtime is active).  Uses an asyncio
    semaphore to bound concurrency.
    """
    single_rt = len(runtime_names) == 1
    results: dict[str, PluginResult] = {}
    tasks: list[tuple[str, str, str, ConformConfig]] = []

    for rt_name in runtime_names:
        rt_config = load_config(
            runtime_name=rt_name,
            concurrency_override=concurrency,
        )
        if specs_dir_override:
            new_rt = replace(
                rt_config.runtime,
                specs_dir=specs_dir_override,
            )
            rt_config = replace(rt_config, runtime=new_rt)

        available = discover_plugins(rt_config.runtime)

        if plugins:
            unknown = [p for p in plugins if p not in available]
            if unknown:
                for p in unknown:
                    rust_error(
                        'E0001',
                        f'unknown plugin `{p}` for runtime `{rt_name}`',
                        note=f'available: {", ".join(available)}',
                        hint='run `conform list` to see available plugins',
                    )
                return {}
            selected = plugins
        else:
            selected = available

        for plugin in selected:
            ep = entry_point(plugin, rt_config)
            if not ep.exists():
                continue
            key = plugin if single_rt else f'{plugin}@{rt_name}'
            result = PluginResult(plugin=plugin, runtime=rt_name)

            # Pre-flight: check env vars.
            missing = check_env(plugin, rt_config)
            if missing:
                result.status = Status.SKIPPED
                result.missing_env_vars = missing
                result.error_message = f'missing env: {", ".join(missing)}'
                results[key] = result
                continue

            results[key] = result
            tasks.append((key, plugin, rt_name, rt_config))

    if not tasks and not results:
        console.print('[yellow]No plugins found to test.[/yellow]')
        return results

    sem = asyncio.Semaphore(max(concurrency if concurrency > 0 else 4, 1))
    on_complete = asyncio.Event()

    # Mutable reference to the Live object so the inner function can
    # print log lines above the live table via live.console.print().
    live_ref: list[Live | None] = [None]

    async def _run_one(key: str, plugin: str, rt_name: str, config: ConformConfig) -> None:
        async with sem:
            result = results[key]
            result.status = Status.RUNNING
            on_complete.set()  # Trigger refresh to show RUNNING status.
            start = time.monotonic()

            def _on_test_done(tr: TestResult) -> None:
                """Update counts after each individual test."""
                if tr.passed:
                    result.tests_passed += 1
                else:
                    result.tests_failed += 1
                result.elapsed_s = time.monotonic() - start
                on_complete.set()

            try:
                run_result = await run_test_model(plugin, config, on_test_done=_on_test_done)
                result.elapsed_s = time.monotonic() - start
                result.tests_passed = run_result.total_passed
                result.tests_failed = run_result.total_failed
                if run_result.total_failed > 0:
                    result.status = Status.FAILED
                    result.error_message = f'{run_result.total_failed} test(s) failed'
                else:
                    result.status = Status.PASSED
            except Exception as exc:
                result.elapsed_s = time.monotonic() - start
                result.status = Status.ERROR
                result.error_message = str(exc)

            # Print a log line above the live table (or to console in
            # verbose mode).  Using live.console.print() ensures the
            # line renders above the pinned table.
            out = live_ref[0].console if live_ref[0] else console
            _log_native_result(plugin, rt_name, result, out)
            on_complete.set()  # Trigger refresh to show final status.

    coros = [_run_one(key, plugin, rt_name, cfg) for key, plugin, rt_name, cfg in tasks]

    if verbose:
        # Plain-text streaming mode (no live table).
        await asyncio.gather(*coros)

        # Summary counts.
        passed = sum(1 for r in results.values() if r.status == Status.PASSED)
        failed = sum(1 for r in results.values() if r.status in (Status.FAILED, Status.ERROR))
        skipped = sum(1 for r in results.values() if r.status == Status.SKIPPED)
        console.print()
        console.print(
            f'[bold]Done:[/bold] {passed} passed, {failed} failed, {skipped} skipped',
        )
    else:
        # Live Rich table pinned at the bottom, log lines scroll above.
        gather_task = asyncio.ensure_future(asyncio.gather(*coros))

        with Live(
            build_progress_table(results),
            console=console,
            refresh_per_second=4,
            transient=True,
        ) as live:
            live_ref[0] = live
            while not gather_task.done():
                on_complete.clear()
                try:
                    await asyncio.wait_for(on_complete.wait(), timeout=0.5)
                except TimeoutError:
                    pass
                live.update(build_progress_table(results))

            # Final refresh after all tasks complete.
            await gather_task
            live.update(build_progress_table(results))
            live_ref[0] = None

    return results


def _log_native_result(
    plugin: str,
    rt_name: str,
    result: PluginResult,
    out: Console,
) -> None:
    """Print a single-line completion log.

    When called from within a ``Live`` context, *out* should be
    ``live.console`` so the line renders above the pinned table.
    """
    label = f'{plugin} ({rt_name})'
    elapsed = f'{result.elapsed_s:.1f}s' if result.elapsed_s else ''

    counts = ''
    if result.tests_passed or result.tests_failed:
        counts = f' ({result.tests_passed}/{result.tests_passed + result.tests_failed})'

    if result.status == Status.PASSED:
        out.print(f'  [green]✓[/green] {label} — [green]passed[/green]{counts} {elapsed}')
    elif result.status == Status.SKIPPED:
        out.print(
            f'  [yellow]⊘[/yellow] {label} — [yellow]skipped[/yellow] (missing: {", ".join(result.missing_env_vars)})',
        )
    elif result.status == Status.FAILED:
        out.print(f'  [red]✗[/red] {label} — [red]failed[/red]{counts} {elapsed}')
    elif result.status == Status.ERROR:
        out.print(
            f'  [red]![/red] {label} — [red]error[/red]: {result.error_message}',
        )


def _cmd_check_model(args: argparse.Namespace, runtime_names: list[str]) -> int:
    """Handle ``conform check-model``.

    Uses the native runner by default.  Falls back to the genkit CLI
    subprocess when ``--use-cli`` is specified.
    """
    specs_dir_raw: str | None = getattr(args, 'specs_dir', None)
    resolved_specs_dir: Path | None = Path(specs_dir_raw).resolve() if specs_dir_raw else None
    concurrency_override: int = getattr(args, 'concurrency', -1)
    use_cli = getattr(args, 'use_cli', False)
    verbose = getattr(args, 'verbose', False)

    if use_cli:
        return _cmd_check_model_cli(args, runtime_names)

    # Native runner path.
    results = asyncio.run(
        _run_native_check(
            plugins=args.plugins,
            runtime_names=runtime_names,
            concurrency=concurrency_override,
            specs_dir_override=resolved_specs_dir,
            verbose=verbose,
        )
    )

    if not results:
        return 1

    # Display unified results.
    console.print()
    console.print(build_summary_table(results))
    print_summary_footer(results)

    # Rust-style messages.
    for _key, result in results.items():
        if result.status == Status.SKIPPED:
            rust_warning(
                'W0001',
                f'skipping `{result.plugin}`: missing environment variables',
                note=', '.join(result.missing_env_vars),
            )
        elif result.status == Status.ERROR:
            rust_error(
                'E0002',
                f'internal error running `{result.plugin}`',
                note=result.error_message,
            )
        elif result.status == Status.FAILED:
            rust_error(
                'E0003',
                f'conformance tests failed for `{result.plugin}`',
                note=result.error_message,
                hint=f'run: conform check-model {result.plugin} -v',
            )

    failed = sum(1 for r in results.values() if r.status in (Status.FAILED, Status.ERROR))
    return 1 if failed > 0 else 0


def _cmd_check_model_cli(args: argparse.Namespace, runtime_names: list[str]) -> int:
    """Handle ``conform check-model --use-cli`` (legacy genkit CLI path)."""
    specs_dir_override: str | None = getattr(args, 'specs_dir', None)
    concurrency_override: int = getattr(args, 'concurrency', -1)
    total_failures = 0

    for rt_name in runtime_names:
        rt_config = load_config(
            runtime_name=rt_name,
            concurrency_override=concurrency_override,
        )
        if specs_dir_override:
            new_rt = replace(
                rt_config.runtime,
                specs_dir=Path(specs_dir_override).resolve(),
            )
            rt_config = replace(rt_config, runtime=new_rt)

        available = discover_plugins(rt_config.runtime)

        if args.plugins:
            unknown = [p for p in args.plugins if p not in available]
            if unknown:
                for p in unknown:
                    rust_error(
                        'E0001',
                        f'unknown plugin `{p}` for runtime `{rt_name}`',
                        note=f'available: {", ".join(available)}',
                        hint='run `conform list` to see available plugins',
                    )
                return 1
            plugins = args.plugins
        else:
            plugins = available

        if not plugins:
            continue

        console.print()
        console.print(
            f'[bold cyan]Running conformance tests (genkit CLI)[/bold cyan] '
            f'\u2014 [dim]{len(plugins)} plugin(s), '
            f'concurrency={rt_config.concurrency}, '
            f'runtime={rt_name}[/dim]'
        )
        console.print()

        results = asyncio.run(run_all(plugins, rt_config, verbose=args.verbose))

        failed = sum(1 for r in results.values() if r.status == Status.FAILED)
        errors = sum(1 for r in results.values() if r.status == Status.ERROR)
        if failed > 0 or errors > 0:
            total_failures += 1

    return 1 if total_failures > 0 else 0


def _cmd_check_plugin(config: ConformConfig) -> int:
    """Handle ``conform check-plugin``."""
    error_count = check_model_conformance(config)
    return 1 if error_count > 0 else 0


def _cmd_list(runtime_names: list[str]) -> int:
    """Handle ``conform list``.

    Shows all plugins across all active runtimes with a column indicating
    which runtimes have entry points.
    """
    # Collect the union of all plugins across runtimes.
    all_plugins: dict[str, ConformConfig] = {}
    for rt_name in runtime_names:
        rt_config = load_config(runtime_name=rt_name)
        for plugin in discover_plugins(rt_config.runtime):
            if plugin not in all_plugins:
                all_plugins[plugin] = rt_config

    if not all_plugins:
        stdout_console.print('[yellow]No plugins found.[/yellow]')
        return 0

    all_rt_names = load_all_runtime_names()

    table = Table(
        title='Available Plugins',
        box=box.ROUNDED,
        title_style='bold cyan',
        border_style='dim',
        header_style='bold',
        show_lines=False,
    )
    table.add_column('', width=2, justify='center')
    table.add_column('Plugin', style='bold', min_width=20)
    table.add_column('Runtimes', min_width=12)
    table.add_column('Environment Variables', ratio=1)

    for plugin in sorted(all_plugins):
        config = all_plugins[plugin]
        required = config.env.get(plugin, [])
        missing = check_env(plugin, config)

        # Readiness indicator.
        if not required:
            ready = Text('\u25cf', style='bold green')
            env_text = Text('(no credentials needed)', style='dim')
        elif not missing:
            ready = Text('\u25cf', style='bold green')
            parts: list[Text | str] = []
            for v in required:
                if parts:
                    parts.append('  ')
                parts.append(Text(v, style='blue'))
            env_text = Text.assemble(*parts)
        else:
            ready = Text('\u25cb', style='bold red')
            parts = []
            for v in required:
                if parts:
                    parts.append('  ')
                style = 'blue' if v not in missing else 'red'
                parts.append(Text(v, style=style))
            env_text = Text.assemble(*parts)

        # Runtime availability.
        runtimes = _plugin_runtimes(plugin)
        rt_parts: list[Text | str] = []
        for rt in all_rt_names:
            if rt_parts:
                rt_parts.append(' ')
            if rt in runtimes:
                rt_parts.append(Text(rt, style='green'))
            else:
                rt_parts.append(Text(rt, style='dim'))
        rt_text = Text.assemble(*rt_parts)

        table.add_row(ready, plugin, rt_text, env_text)

    stdout_console.print()
    stdout_console.print(table)
    stdout_console.print()
    stdout_console.print(
        '[bold]Legend:[/bold]  '
        '[green]\u25cf[/green] Ready  '
        '[red]\u25cb[/red] Missing env vars  '
        '[blue]VAR[/blue] Set  '
        '[red]VAR[/red] Not set  '
        '[green]runtime[/green] Available  '
        '[dim]runtime[/dim] Not available'
    )
    stdout_console.print()
    return 0


def main() -> None:
    """Entry point for the ``conform`` CLI."""
    parser = _build_parser()
    args = parser.parse_args()

    runtime_arg: str | None = getattr(args, 'runtime', None)

    if args.command is None:
        parser.print_help()
        _cmd_list(_resolve_runtime_names(runtime_arg))
        sys.exit(0)

    runtime_names = _resolve_runtime_names(runtime_arg)

    if args.command == 'check-model':
        sys.exit(_cmd_check_model(args, runtime_names))
    elif args.command == 'check-plugin':
        exit_code = 0
        specs_dir: str | None = getattr(args, 'specs_dir', None)
        for rt_name in runtime_names:
            config = load_config(runtime_name=rt_name)
            if specs_dir:
                new_rt = replace(config.runtime, specs_dir=Path(specs_dir).resolve())
                config = replace(config, runtime=new_rt)
            if _cmd_check_plugin(config) != 0:
                exit_code = 1
        sys.exit(exit_code)
    elif args.command == 'list':
        sys.exit(_cmd_list(runtime_names))
    else:
        parser.print_help()
        sys.exit(0)
