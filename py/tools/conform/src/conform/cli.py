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

    conform [--runtime NAME] [--specs-dir DIR] check-model [PLUGIN...] [-j N] [-v]
        Run model conformance tests in parallel (all plugins, all runtimes).

    conform [--runtime NAME] [--specs-dir DIR] test-model PLUGIN [--runtime NAME] [--use-cli]
        Run model conformance tests via the native runner.

    conform [--runtime NAME] [--specs-dir DIR] check-plugin
        Verify that every model plugin has conformance files.

    conform [--runtime NAME] [--specs-dir DIR] list
        List available plugins, their runtimes, and env-var readiness.

``--runtime`` and ``--specs-dir`` are global flags shared by all subcommands.
When ``--runtime`` is omitted, all configured runtimes are used.

When invoked with no subcommand, displays the help screen followed by
the plugin env-var readiness table.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import replace
from pathlib import Path

from rich import box
from rich.table import Table
from rich.text import Text

from conform.checker import check_model_conformance
from conform.config import ConformConfig, load_all_runtime_names, load_config
from conform.display import console, rust_error, stdout_console
from conform.plugins import check_env, discover_plugins, entry_point
from conform.runner import run_all
from conform.test_model import run_test_model
from conform.types import PluginResult, Status


def _resolve_runtime_names(runtime_arg: str | None) -> list[str]:
    """Resolve which runtimes to use.

    Args:
        runtime_arg: Explicit runtime name, or ``None`` for all configured.

    Returns:
        List of runtime names to operate on.
    """
    if runtime_arg is not None:
        return [runtime_arg]
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

    parser = argparse.ArgumentParser(
        prog='conform',
        description=(
            'Parallel model conformance test runner for Genkit plugins.\n\n'
            'Runs model conformance tests against multiple plugins and runtimes\n'
            'concurrently, collecting results and displaying a live progress table.'
        ),
        formatter_class=formatter_class,
    )

    parser.add_argument(
        '--runtime',
        default=None,
        metavar='NAME',
        help=('Runtime to use (e.g. python, js, go). If not specified, runs all configured runtimes.'),
    )
    parser.add_argument(
        '--specs-dir',
        default=None,
        metavar='DIR',
        help='Override the specs directory (default: from runtime config).',
    )

    subparsers = parser.add_subparsers(dest='command', help='Available subcommands')

    cm_parser = subparsers.add_parser(
        'check-model',
        help='Run model conformance tests in parallel.',
        description=(
            'Run genkit dev:test-model against one or more plugins concurrently.\n'
            'By default runs all plugins across all configured runtimes.\n'
            'Results are displayed in a live progress table with a final summary.'
        ),
        formatter_class=formatter_class,
    )
    cm_parser.add_argument(
        'plugins',
        nargs='*',
        default=[],
        metavar='PLUGIN',
        help='Optional plugin name(s) to test (default: all available).',
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

    tm_parser = subparsers.add_parser(
        'test-model',
        help='Run model conformance tests via the native runner.',
        description=(
            'Run model conformance tests by starting the entry point subprocess,\n'
            'communicating with the Genkit reflection server via async HTTP,\n'
            'and validating responses using the built-in validator protocols.\n\n'
            'This replaces ``genkit dev:test-model`` with a native Python\n'
            'implementation that works with all runtimes.'
        ),
        formatter_class=formatter_class,
    )
    tm_parser.add_argument(
        'plugin',
        metavar='PLUGIN',
        help='Plugin name to test (e.g. google-genai).',
    )
    tm_parser.add_argument(
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
    )

    subparsers.add_parser(
        'list',
        help='List available plugins and their env-var readiness.',
        description=(
            'Display a table of all plugins that have conformance specs,\n'
            'showing which runtimes and environment variables are available.'
        ),
        formatter_class=formatter_class,
    )

    return parser


def _cmd_check_model(args: argparse.Namespace, runtime_names: list[str]) -> int:
    """Handle ``conform check-model``.

    Runs tests across all specified runtimes.
    """
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
            f'[bold cyan]Running conformance tests[/bold cyan] '
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


def _cmd_test_model(args: argparse.Namespace, runtime_names: list[str]) -> int:
    """Handle ``conform test-model``.

    When multiple runtimes are active, discovers which ones have an entry
    point for the plugin and runs tests for each.
    """
    plugin = args.plugin
    use_cli = getattr(args, 'use_cli', False)
    specs_dir_override: str | None = getattr(args, 'specs_dir', None)

    # Filter to runtimes with entry points for this plugin.
    active_runtimes: list[str] = []
    for rt_name in runtime_names:
        rt_config = load_config(runtime_name=rt_name)
        ep = entry_point(plugin, rt_config)
        if ep.exists():
            active_runtimes.append(rt_name)

    if not active_runtimes:
        rust_error(
            'E0001',
            f'no runtime has an entry point for plugin `{plugin}`',
            hint='run `conform list` to see available plugins and runtimes',
        )
        return 1

    total_failures = 0

    for rt_name in active_runtimes:
        rt_config = load_config(
            runtime_name=rt_name,
            concurrency_override=getattr(args, 'concurrency', -1),
        )
        if specs_dir_override:
            new_rt = replace(
                rt_config.runtime,
                specs_dir=Path(specs_dir_override).resolve(),
            )
            rt_config = replace(rt_config, runtime=new_rt)

        available = discover_plugins(rt_config.runtime)
        if plugin not in available:
            continue

        missing = check_env(plugin, rt_config)
        if missing:
            if len(runtime_names) == 1:
                rust_error(
                    'E0002',
                    f'missing environment variables for `{plugin}`',
                    note=f'required: {", ".join(missing)}',
                    hint='set the missing variables and rerun',
                )
                return 1
            console.print(f'[yellow]Skipping {rt_name}:[/yellow] missing env vars: {", ".join(missing)}')
            continue

        console.print()

        if use_cli:
            console.print(
                f'[bold cyan]Running via genkit CLI[/bold cyan] \u2014 [dim]plugin={plugin}, runtime={rt_name}[/dim]'
            )
            results = asyncio.run(run_all([plugin], rt_config))
            r = results.get(plugin, PluginResult(plugin=plugin))
            if r.status in (Status.FAILED, Status.ERROR):
                total_failures += 1
        else:
            console.print(
                f'[bold cyan]Running model conformance tests[/bold cyan] '
                f'\u2014 [dim]plugin={plugin}, runtime={rt_name}[/dim]'
            )
            result = asyncio.run(run_test_model(plugin, rt_config))
            if result.total_failed > 0:
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
    elif args.command == 'test-model':
        sys.exit(_cmd_test_model(args, runtime_names))
    elif args.command == 'check-plugin':
        # check-plugin operates on one runtime config at a time.
        rt_name = runtime_names[0] if len(runtime_names) == 1 else 'python'
        config = load_config(runtime_name=rt_name)
        specs_dir: str | None = getattr(args, 'specs_dir', None)
        if specs_dir:
            new_rt = replace(config.runtime, specs_dir=Path(specs_dir).resolve())
            config = replace(config, runtime=new_rt)
        sys.exit(_cmd_check_plugin(config))
    elif args.command == 'list':
        sys.exit(_cmd_list(runtime_names))
    else:
        parser.print_help()
        sys.exit(0)
