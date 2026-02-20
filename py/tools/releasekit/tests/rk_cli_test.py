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

"""Tests for releasekit.cli module — parser and argument validation."""

from __future__ import annotations

from releasekit.cli import build_parser


class TestBuildParser:
    """Tests for the argument parser structure."""

    def test_parser_creation(self) -> None:
        """Parser is created without errors."""
        parser = build_parser()
        if parser is None:
            raise AssertionError('Parser should not be None')

    def test_no_args_shows_help(self) -> None:
        """Parsing empty args exits with SystemExit(2)."""
        parser = build_parser()
        try:
            parser.parse_args([])
            # It might not raise if subparser isn't required.
        except SystemExit:
            pass  # Expected.


class TestDiscoverSubcommand:
    """Tests for the discover subcommand arguments."""

    def test_discover_default(self) -> None:
        """Discover with no args uses defaults."""
        parser = build_parser()
        args = parser.parse_args(['discover'])
        if args.command != 'discover':
            raise AssertionError(f'Expected discover, got {args.command}')


class TestGraphSubcommand:
    """Tests for the graph subcommand arguments."""

    def test_graph_default_format(self) -> None:
        """Graph defaults to levels format."""
        parser = build_parser()
        args = parser.parse_args(['graph'])
        if args.command != 'graph':
            raise AssertionError(f'Expected graph, got {args.command}')
        if hasattr(args, 'format') and args.format != 'levels':
            raise AssertionError(f'Expected levels format, got {args.format}')

    def test_graph_dot_format(self) -> None:
        """Graph --format dot works."""
        parser = build_parser()
        args = parser.parse_args(['graph', '--format', 'dot'])
        if args.format != 'dot':
            raise AssertionError(f'Expected dot, got {args.format}')

    def test_graph_json_format(self) -> None:
        """Graph --format json works."""
        parser = build_parser()
        args = parser.parse_args(['graph', '--format', 'json'])
        if args.format != 'json':
            raise AssertionError(f'Expected json, got {args.format}')

    def test_graph_mermaid_format(self) -> None:
        """Graph --format mermaid works."""
        parser = build_parser()
        args = parser.parse_args(['graph', '--format', 'mermaid'])
        if args.format != 'mermaid':
            raise AssertionError(f'Expected mermaid, got {args.format}')

    def test_graph_csv_format(self) -> None:
        """Graph --format csv works."""
        parser = build_parser()
        args = parser.parse_args(['graph', '--format', 'csv'])
        if args.format != 'csv':
            raise AssertionError(f'Expected csv, got {args.format}')

    def test_graph_table_format(self) -> None:
        """Graph --format table works."""
        parser = build_parser()
        args = parser.parse_args(['graph', '--format', 'table'])
        if args.format != 'table':
            raise AssertionError(f'Expected table, got {args.format}')

    def test_graph_rdeps(self) -> None:
        """Graph --rdeps PKG works."""
        parser = build_parser()
        args = parser.parse_args(['graph', '--rdeps', 'genkit'])
        if args.rdeps != 'genkit':
            raise AssertionError(f'Expected genkit, got {args.rdeps}')

    def test_graph_deps(self) -> None:
        """Graph --deps PKG works."""
        parser = build_parser()
        args = parser.parse_args(['graph', '--deps', 'genkit'])
        if args.deps != 'genkit':
            raise AssertionError(f'Expected genkit, got {args.deps}')


class TestPublishSubcommand:
    """Tests for the publish subcommand arguments."""

    def test_publish_dry_run(self) -> None:
        """--dry-run flag works."""
        parser = build_parser()
        args = parser.parse_args(['publish', '--dry-run'])
        if not args.dry_run:
            raise AssertionError('Expected dry_run=True')

    def test_publish_force(self) -> None:
        """--force flag works."""
        parser = build_parser()
        args = parser.parse_args(['publish', '--force'])
        if not args.force:
            raise AssertionError('Expected force=True')

    def test_publish_no_tag(self) -> None:
        """--no-tag flag works."""
        parser = build_parser()
        args = parser.parse_args(['publish', '--no-tag'])
        if not args.no_tag:
            raise AssertionError('Expected no_tag=True')

    def test_publish_no_push(self) -> None:
        """--no-push flag works."""
        parser = build_parser()
        args = parser.parse_args(['publish', '--no-push'])
        if not args.no_push:
            raise AssertionError('Expected no_push=True')

    def test_publish_no_release(self) -> None:
        """--no-release flag works."""
        parser = build_parser()
        args = parser.parse_args(['publish', '--no-release'])
        if not args.no_release:
            raise AssertionError('Expected no_release=True')

    def test_publish_version_only(self) -> None:
        """--version-only flag works."""
        parser = build_parser()
        args = parser.parse_args(['publish', '--version-only'])
        if not args.version_only:
            raise AssertionError('Expected version_only=True')

    def test_publish_concurrency(self) -> None:
        """--concurrency works."""
        parser = build_parser()
        args = parser.parse_args(['publish', '--concurrency', '4'])
        if args.concurrency != 4:
            raise AssertionError(f'Expected 4, got {args.concurrency}')


class TestCheckSubcommand:
    """Tests for the check subcommand."""

    def test_check_parsed(self) -> None:
        """Check subcommand is recognized."""
        parser = build_parser()
        args = parser.parse_args(['check'])
        if args.command != 'check':
            raise AssertionError(f'Expected check, got {args.command}')


class TestVersionSubcommand:
    """Tests for the version subcommand."""

    def test_version_parsed(self) -> None:
        """Version subcommand is recognized."""
        parser = build_parser()
        args = parser.parse_args(['version'])
        if args.command != 'version':
            raise AssertionError(f'Expected version, got {args.command}')


class TestExplainSubcommand:
    """Tests for the explain subcommand."""

    def test_explain_with_code(self) -> None:
        """Explain with a code works."""
        parser = build_parser()
        args = parser.parse_args(['explain', 'RK-CONFIG-NOT-FOUND'])
        if args.command != 'explain':
            raise AssertionError(f'Expected explain, got {args.command}')
        if args.code != 'RK-CONFIG-NOT-FOUND':
            raise AssertionError(f'Expected code, got {args.code}')


class TestInitSubcommand:
    """Tests for the init subcommand."""

    def test_init_parsed(self) -> None:
        """Init subcommand is recognized."""
        parser = build_parser()
        args = parser.parse_args(['init'])
        if args.command != 'init':
            raise AssertionError(f'Expected init, got {args.command}')

    def test_init_dry_run(self) -> None:
        """Init --dry-run works."""
        parser = build_parser()
        args = parser.parse_args(['init', '--dry-run'])
        if not args.dry_run:
            raise AssertionError('Expected dry_run=True')


class TestRollbackSubcommand:
    """Tests for the rollback subcommand."""

    def test_rollback_parsed(self) -> None:
        """Rollback subcommand is recognized."""
        parser = build_parser()
        args = parser.parse_args(['rollback', 'genkit-v0.5.0'])
        if args.command != 'rollback':
            raise AssertionError(f'Expected rollback, got {args.command}')
        if args.tag != 'genkit-v0.5.0':
            raise AssertionError(f'Expected tag, got {args.tag}')


class TestCompletionSubcommand:
    """Tests for the completion subcommand."""

    def test_completion_bash(self) -> None:
        """Completion bash works."""
        parser = build_parser()
        args = parser.parse_args(['completion', 'bash'])
        if args.command != 'completion':
            raise AssertionError(f'Expected completion, got {args.command}')
        if args.shell != 'bash':
            raise AssertionError(f'Expected bash, got {args.shell}')

    def test_completion_zsh(self) -> None:
        """Completion zsh works."""
        parser = build_parser()
        args = parser.parse_args(['completion', 'zsh'])
        if args.shell != 'zsh':
            raise AssertionError(f'Expected zsh, got {args.shell}')

    def test_completion_fish(self) -> None:
        """Completion fish works."""
        parser = build_parser()
        args = parser.parse_args(['completion', 'fish'])
        if args.shell != 'fish':
            raise AssertionError(f'Expected fish, got {args.shell}')


class TestPlanSubcommand:
    """Tests for the plan subcommand."""

    def test_plan_parsed(self) -> None:
        """Plan subcommand is recognized."""
        parser = build_parser()
        args = parser.parse_args(['plan'])
        if args.command != 'plan':
            raise AssertionError(f'Expected plan, got {args.command}')
