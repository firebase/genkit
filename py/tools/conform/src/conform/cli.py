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

Provides three subcommands::

    conform check-model [PLUGIN...] [--all] [-j N] [-v] [--runtime NAME]
        Run model conformance tests in parallel.

    conform check-plugin
        Verify that every model plugin has conformance files.

    conform list
        List available plugins and their env-var readiness.

When invoked with no subcommand, displays the help screen followed by
the plugin env-var readiness table.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from rich import box
from rich.table import Table
from rich.text import Text

from conform.checker import check_model_conformance
from conform.config import ConformConfig, load_config
from conform.display import console, rust_error, stdout_console
from conform.plugins import check_env, discover_plugins
from conform.runner import run_all
from conform.types import Status


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
            'Runs genkit dev:test-model against multiple plugins concurrently,\n'
            'collecting results as they arrive and displaying a live progress table.'
        ),
        formatter_class=formatter_class,
    )
    subparsers = parser.add_subparsers(dest='command', help='Available subcommands')

    # --- check-model ---
    cm_parser = subparsers.add_parser(
        'check-model',
        help='Run model conformance tests in parallel.',
        description=(
            'Run genkit dev:test-model against one or more plugins concurrently.\n'
            'Results are displayed in a live progress table with a final summary.'
        ),
        formatter_class=formatter_class,
    )

    cm_group = cm_parser.add_mutually_exclusive_group()
    cm_group.add_argument(
        'plugins',
        nargs='*',
        default=[],
        metavar='PLUGIN',
        help='Plugin name(s) to test (e.g. anthropic deepseek).',
    )
    cm_group.add_argument(
        '--all',
        action='store_true',
        dest='all_plugins',
        help='Test all available plugins.',
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
        '--runtime',
        default='python',
        metavar='NAME',
        help='Runtime to use (default: python). See [tool.conform.runtimes.*].',
    )

    # --- check-plugin ---
    cp_parser = subparsers.add_parser(
        'check-plugin',
        help='Check that every model plugin has conformance files.',
        description=(
            'Verify that every model plugin (identified by model_info.py or\n'
            'listed in [tool.conform.additional-model-plugins]) has both a\n'
            'model-conformance.yaml spec and a conformance_entry.py file.'
        ),
        formatter_class=formatter_class,
    )
    cp_parser.add_argument(
        '--runtime',
        default='python',
        metavar='NAME',
        help='Runtime to use (default: python). See [tool.conform.runtimes.*].',
    )

    # --- list ---
    list_parser = subparsers.add_parser(
        'list',
        help='List available plugins and their env-var readiness.',
        description=(
            'Display a table of all plugins that have conformance specs,\n'
            'showing which environment variables are set and which are missing.'
        ),
        formatter_class=formatter_class,
    )
    list_parser.add_argument(
        '--runtime',
        default='python',
        metavar='NAME',
        help='Runtime to use (default: python). See [tool.conform.runtimes.*].',
    )

    return parser


def _cmd_check_model(args: argparse.Namespace, config: ConformConfig) -> int:
    """Handle ``conform check-model``."""
    available = discover_plugins(config.runtime)

    if args.all_plugins:
        plugins = available
    elif args.plugins:
        unknown = [p for p in args.plugins if p not in available]
        if unknown:
            for p in unknown:
                rust_error(
                    'E0001',
                    f'unknown plugin `{p}`',
                    note=f'available: {", ".join(available)}',
                    hint='run `conform list` to see available plugins',
                )
            return 1
        plugins = args.plugins
    else:
        console.print('[yellow]No plugins specified.[/yellow] Use --all or name plugins.')
        console.print('Run `conform check-model --help` for usage.')
        return 0

    if not plugins:
        console.print('[yellow]No plugins to test.[/yellow]')
        return 0

    console.print()
    console.print(
        f'[bold cyan]Running conformance tests[/bold cyan] '
        f'— [dim]{len(plugins)} plugin(s), '
        f'concurrency={config.concurrency}, '
        f'runtime={config.runtime.name}[/dim]'
    )
    console.print()

    results = asyncio.run(run_all(plugins, config, verbose=args.verbose))

    failed = sum(1 for r in results.values() if r.status == Status.FAILED)
    errors = sum(1 for r in results.values() if r.status == Status.ERROR)

    if failed > 0 or errors > 0:
        return 1
    return 0


def _cmd_check_plugin(config: ConformConfig) -> int:
    """Handle ``conform check-plugin``."""
    error_count = check_model_conformance(config)
    return 1 if error_count > 0 else 0


def _cmd_list(config: ConformConfig) -> int:
    """Handle ``conform list``."""
    plugins = discover_plugins(config.runtime)

    table = Table(
        title=f'Available Plugins ({config.runtime.name})',
        box=box.ROUNDED,
        title_style='bold cyan',
        border_style='dim',
        header_style='bold',
        show_lines=False,
    )
    table.add_column('', width=2, justify='center')
    table.add_column('Plugin', style='bold', min_width=24)
    table.add_column('Environment Variables', ratio=1)

    for plugin in plugins:
        required = config.env.get(plugin, [])
        missing = check_env(plugin, config)

        if not required:
            ready = Text('●', style='bold green')
            env_text = Text('(no credentials needed)', style='dim')
        elif not missing:
            ready = Text('●', style='bold green')
            parts: list[Text | str] = []
            for v in required:
                if parts:
                    parts.append('  ')
                parts.append(Text(v, style='blue'))
            env_text = Text.assemble(*parts)
        else:
            ready = Text('○', style='bold red')
            parts = []
            for v in required:
                if parts:
                    parts.append('  ')
                style = 'blue' if v not in missing else 'red'
                parts.append(Text(v, style=style))
            env_text = Text.assemble(*parts)

        table.add_row(ready, plugin, env_text)

    # Print to stdout so ordering matches argparse help output.
    stdout_console.print()
    stdout_console.print(table)
    stdout_console.print()
    stdout_console.print(
        '[bold]Legend:[/bold]  '
        '[green]●[/green] Ready  '
        '[red]○[/red] Missing env vars  '
        '[blue]VAR[/blue] Set  '
        '[red]VAR[/red] Not set'
    )
    stdout_console.print()
    return 0


def main() -> None:
    """Entry point for the ``conform`` CLI."""
    parser = _build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        # Also show the plugin env-var readiness table so users
        # immediately see what's configured.
        config = load_config()
        _cmd_list(config)
        sys.exit(0)

    # Load config from pyproject.toml, applying CLI overrides.
    concurrency_override: int = getattr(args, 'concurrency', -1)
    runtime_name: str = getattr(args, 'runtime', 'python')
    config = load_config(
        concurrency_override=concurrency_override,
        runtime_name=runtime_name,
    )

    if args.command == 'check-model':
        sys.exit(_cmd_check_model(args, config))
    elif args.command == 'check-plugin':
        sys.exit(_cmd_check_plugin(config))
    elif args.command == 'list':
        sys.exit(_cmd_list(config))
    else:
        parser.print_help()
        sys.exit(0)
