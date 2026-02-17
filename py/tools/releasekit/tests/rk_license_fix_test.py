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

"""Tests for releasekit.checks._license_fix."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import tomlkit
from releasekit.checks._license_fix import (
    FixAction,
    LicenseFixChoice,
    LicenseFixReport,
    apply_fixes,
    collect_fixable_deps,
    interactive_license_fix,
    prompt_for_fix,
)
from releasekit.checks._license_tree import (
    DepNode,
    DepStatus,
    LicenseTree,
    PackageTree,
)

# ── Helpers ──────────────────────────────────────────────────────────


def _parse_toml(text: str) -> dict[str, Any]:
    """Parse TOML text for test assertions (deep-converts tomlkit types)."""
    return json.loads(json.dumps(tomlkit.parse(text).unwrap()))


def _tree(
    *deps: tuple[str, str, DepStatus],
    project_license: str = 'Apache-2.0',
    parent: str = 'myapp',
) -> LicenseTree:
    """Build a minimal LicenseTree for testing."""
    nodes = [DepNode(name=n, license=lic, status=st) for n, lic, st in deps]
    pkg = PackageTree(name=parent, license=project_license, deps=nodes)
    return LicenseTree(project_license=project_license, packages=[pkg])


def _write_toml(path: Path, content: str) -> Path:
    """Write a TOML file and return its path."""
    path.write_text(content, encoding='utf-8')
    return path


# ── TestCollectFixableDeps ───────────────────────────────────────────


class TestCollectFixableDeps:
    """Tests for collect fixable deps."""

    def test_empty_tree(self) -> None:
        """Test empty tree."""
        tree = LicenseTree(project_license='MIT')
        assert collect_fixable_deps(tree) == []

    def test_all_ok(self) -> None:
        """Test all ok."""
        tree = _tree(('lib-a', 'MIT', DepStatus.OK), ('lib-b', 'BSD-3-Clause', DepStatus.ALLOWED))
        assert collect_fixable_deps(tree) == []

    def test_incompatible(self) -> None:
        """Test incompatible."""
        tree = _tree(('gpl-lib', 'GPL-3.0-only', DepStatus.INCOMPATIBLE))
        result = collect_fixable_deps(tree)
        assert len(result) == 1
        assert result[0][0] == 'myapp'
        assert result[0][1].name == 'gpl-lib'

    def test_denied(self) -> None:
        """Test denied."""
        tree = _tree(('bad-lib', 'AGPL-3.0-only', DepStatus.DENIED))
        result = collect_fixable_deps(tree)
        assert len(result) == 1
        assert result[0][1].status == DepStatus.DENIED

    def test_no_license(self) -> None:
        """Test no license."""
        tree = _tree(('mystery-lib', '', DepStatus.NO_LICENSE))
        result = collect_fixable_deps(tree)
        assert len(result) == 1

    def test_unresolved(self) -> None:
        """Test unresolved."""
        tree = _tree(('weird-lib', 'Custom-1.0', DepStatus.UNRESOLVED))
        result = collect_fixable_deps(tree)
        assert len(result) == 1

    def test_deduplicates_across_packages(self) -> None:
        """Test deduplicates across packages."""
        pkg1 = PackageTree(
            name='app-a',
            license='Apache-2.0',
            deps=[DepNode(name='gpl-lib', license='GPL-3.0-only', status=DepStatus.INCOMPATIBLE)],
        )
        pkg2 = PackageTree(
            name='app-b',
            license='Apache-2.0',
            deps=[DepNode(name='gpl-lib', license='GPL-3.0-only', status=DepStatus.INCOMPATIBLE)],
        )
        tree = LicenseTree(project_license='Apache-2.0', packages=[pkg1, pkg2])
        result = collect_fixable_deps(tree)
        assert len(result) == 1

    def test_mixed_statuses(self) -> None:
        """Test mixed statuses."""
        tree = _tree(
            ('ok-lib', 'MIT', DepStatus.OK),
            ('gpl-lib', 'GPL-3.0-only', DepStatus.INCOMPATIBLE),
            ('exempt-lib', '(exempt)', DepStatus.EXEMPT),
            ('bad-lib', 'AGPL-3.0-only', DepStatus.DENIED),
        )
        result = collect_fixable_deps(tree)
        assert len(result) == 2
        names = {r[1].name for r in result}
        assert names == {'gpl-lib', 'bad-lib'}


# ── TestPromptForFix ─────────────────────────────────────────────────


class TestPromptForFix:
    """Tests for prompt for fix."""

    def test_exempt(self) -> None:
        """Test exempt choice."""
        dep = DepNode(name='gpl-lib', license='GPL-3.0-only', status=DepStatus.INCOMPATIBLE)
        inputs = iter(['1'])
        output: list[str] = []
        choice = prompt_for_fix(
            'myapp',
            dep,
            'Apache-2.0',
            input_fn=lambda _prompt='': next(inputs),
            print_fn=output.append,
        )
        assert choice.action == FixAction.EXEMPT
        assert choice.dep_name == 'gpl-lib'

    def test_allow(self) -> None:
        """Test allow choice."""
        dep = DepNode(name='gpl-lib', license='GPL-3.0-only', status=DepStatus.INCOMPATIBLE)
        inputs = iter(['2'])
        choice = prompt_for_fix(
            'myapp',
            dep,
            'Apache-2.0',
            input_fn=lambda _prompt='': next(inputs),
            print_fn=lambda *_a: None,
        )
        assert choice.action == FixAction.ALLOW
        assert choice.dep_license == 'GPL-3.0-only'

    def test_deny(self) -> None:
        """Test deny choice."""
        dep = DepNode(name='bad-lib', license='AGPL-3.0-only', status=DepStatus.DENIED)
        inputs = iter(['3'])
        choice = prompt_for_fix(
            'myapp',
            dep,
            'Apache-2.0',
            input_fn=lambda _prompt='': next(inputs),
            print_fn=lambda *_a: None,
        )
        assert choice.action == FixAction.DENY

    def test_override(self) -> None:
        """Test override choice."""
        dep = DepNode(name='dual-lib', license='(unknown)', status=DepStatus.NO_LICENSE)
        inputs = iter(['4', 'MIT OR GPL-2.0-only'])
        choice = prompt_for_fix(
            'myapp',
            dep,
            'Apache-2.0',
            input_fn=lambda _prompt='': next(inputs),
            print_fn=lambda *_a: None,
        )
        assert choice.action == FixAction.OVERRIDE
        assert choice.override_value == 'MIT OR GPL-2.0-only'

    def test_skip(self) -> None:
        """Test skip choice."""
        dep = DepNode(name='gpl-lib', license='GPL-3.0-only', status=DepStatus.INCOMPATIBLE)
        inputs = iter(['5'])
        choice = prompt_for_fix(
            'myapp',
            dep,
            'Apache-2.0',
            input_fn=lambda _prompt='': next(inputs),
            print_fn=lambda *_a: None,
        )
        assert choice.action == FixAction.SKIP

    def test_invalid_then_valid(self) -> None:
        """Test invalid then valid input."""
        dep = DepNode(name='gpl-lib', license='GPL-3.0-only', status=DepStatus.INCOMPATIBLE)
        inputs = iter(['x', '99', '1'])
        output: list[str] = []
        choice = prompt_for_fix(
            'myapp',
            dep,
            'Apache-2.0',
            input_fn=lambda _prompt='': next(inputs),
            print_fn=output.append,
        )
        assert choice.action == FixAction.EXEMPT
        # Should have printed two "Invalid choice" messages.
        invalid_msgs = [m for m in output if 'Invalid choice' in str(m)]
        assert len(invalid_msgs) == 2

    def test_eof_returns_skip(self) -> None:
        """Test EOF returns skip."""
        dep = DepNode(name='gpl-lib', license='GPL-3.0-only', status=DepStatus.INCOMPATIBLE)

        def _raise_eof(_prompt: str = '') -> str:
            raise EOFError

        choice = prompt_for_fix(
            'myapp',
            dep,
            'Apache-2.0',
            input_fn=_raise_eof,
            print_fn=lambda *_a: None,
        )
        assert choice.action == FixAction.SKIP

    def test_keyboard_interrupt_propagates(self) -> None:
        """Test keyboard interrupt propagates (not caught)."""
        dep = DepNode(name='gpl-lib', license='GPL-3.0-only', status=DepStatus.INCOMPATIBLE)

        def _raise_ki(_prompt: str = '') -> str:
            raise KeyboardInterrupt

        with pytest.raises(KeyboardInterrupt):
            prompt_for_fix(
                'myapp',
                dep,
                'Apache-2.0',
                input_fn=_raise_ki,
                print_fn=lambda *_a: None,
            )

    def test_override_empty_then_valid(self) -> None:
        """Test override with empty input then valid."""
        dep = DepNode(name='dual-lib', license='(unknown)', status=DepStatus.NO_LICENSE)
        inputs = iter(['4', '', 'MIT'])
        output: list[str] = []
        choice = prompt_for_fix(
            'myapp',
            dep,
            'Apache-2.0',
            input_fn=lambda _prompt='': next(inputs),
            print_fn=output.append,
        )
        assert choice.action == FixAction.OVERRIDE
        assert choice.override_value == 'MIT'

    def test_override_eof_falls_back_to_skip(self) -> None:
        """Test override EOF falls back to skip."""
        dep = DepNode(name='dual-lib', license='(unknown)', status=DepStatus.NO_LICENSE)
        call_count = 0

        def _input(_prompt: str = '') -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return '4'
            raise EOFError

        choice = prompt_for_fix(
            'myapp',
            dep,
            'Apache-2.0',
            input_fn=_input,
            print_fn=lambda *_a: None,
        )
        assert choice.action == FixAction.SKIP


# ── TestApplyFixes ───────────────────────────────────────────────────


class TestApplyFixes:
    """Tests for apply fixes."""

    def test_no_actionable_choices(self, tmp_path: Path) -> None:
        """Test no actionable choices."""
        cfg = _write_toml(tmp_path / 'releasekit.toml', 'forge = "github"\n')
        report = apply_fixes(cfg, [LicenseFixChoice(dep_name='x', dep_license='MIT', parent_package='a')])
        assert not report.written

    def test_exempt(self, tmp_path: Path) -> None:
        """Test exempt adds to exempt_packages."""
        cfg = _write_toml(tmp_path / 'releasekit.toml', 'forge = "github"\n')
        choices = [
            LicenseFixChoice(
                dep_name='gpl-lib',
                dep_license='GPL-3.0-only',
                parent_package='myapp',
                action=FixAction.EXEMPT,
            )
        ]
        report = apply_fixes(cfg, choices)
        assert report.written
        doc = _parse_toml(cfg.read_text(encoding='utf-8'))
        assert 'gpl-lib' in doc['license']['exempt_packages']

    def test_allow(self, tmp_path: Path) -> None:
        """Test allow adds to allow_licenses."""
        cfg = _write_toml(tmp_path / 'releasekit.toml', 'forge = "github"\n')
        choices = [
            LicenseFixChoice(
                dep_name='lib',
                dep_license='GPL-3.0-only',
                parent_package='myapp',
                action=FixAction.ALLOW,
            )
        ]
        report = apply_fixes(cfg, choices)
        assert report.written
        doc = _parse_toml(cfg.read_text(encoding='utf-8'))
        assert 'GPL-3.0-only' in doc['license']['allow_licenses']

    def test_deny(self, tmp_path: Path) -> None:
        """Test deny adds to deny_licenses."""
        cfg = _write_toml(tmp_path / 'releasekit.toml', 'forge = "github"\n')
        choices = [
            LicenseFixChoice(
                dep_name='lib',
                dep_license='AGPL-3.0-only',
                parent_package='myapp',
                action=FixAction.DENY,
            )
        ]
        report = apply_fixes(cfg, choices)
        assert report.written
        doc = _parse_toml(cfg.read_text(encoding='utf-8'))
        assert 'AGPL-3.0-only' in doc['license']['deny_licenses']

    def test_override(self, tmp_path: Path) -> None:
        """Test override adds to overrides table."""
        cfg = _write_toml(tmp_path / 'releasekit.toml', 'forge = "github"\n')
        choices = [
            LicenseFixChoice(
                dep_name='dual-lib',
                dep_license='(unknown)',
                parent_package='myapp',
                action=FixAction.OVERRIDE,
                override_value='MIT',
            )
        ]
        report = apply_fixes(cfg, choices)
        assert report.written
        doc = _parse_toml(cfg.read_text(encoding='utf-8'))
        assert doc['license']['overrides']['dual-lib'] == 'MIT'

    def test_dry_run(self, tmp_path: Path) -> None:
        """Test dry run does not write."""
        cfg = _write_toml(tmp_path / 'releasekit.toml', 'forge = "github"\n')
        choices = [
            LicenseFixChoice(
                dep_name='gpl-lib',
                dep_license='GPL-3.0-only',
                parent_package='myapp',
                action=FixAction.EXEMPT,
            )
        ]
        report = apply_fixes(cfg, choices, dry_run=True)
        assert not report.written
        doc = _parse_toml(cfg.read_text(encoding='utf-8'))
        assert 'license' not in doc

    def test_idempotent(self, tmp_path: Path) -> None:
        """Test idempotent — adding same value twice does not duplicate."""
        cfg = _write_toml(tmp_path / 'releasekit.toml', '[license]\nexempt_packages = ["gpl-lib"]\n')
        choices = [
            LicenseFixChoice(
                dep_name='gpl-lib',
                dep_license='GPL-3.0-only',
                parent_package='myapp',
                action=FixAction.EXEMPT,
            )
        ]
        apply_fixes(cfg, choices)
        doc = _parse_toml(cfg.read_text(encoding='utf-8'))
        assert doc['license']['exempt_packages'].count('gpl-lib') == 1

    def test_preserves_existing_config(self, tmp_path: Path) -> None:
        """Test preserves existing config keys."""
        cfg = _write_toml(
            tmp_path / 'releasekit.toml',
            'forge = "github"\nrepo_owner = "firebase"\n\n[license]\nproject = "Apache-2.0"\n',
        )
        choices = [
            LicenseFixChoice(
                dep_name='gpl-lib',
                dep_license='GPL-3.0-only',
                parent_package='myapp',
                action=FixAction.EXEMPT,
            )
        ]
        apply_fixes(cfg, choices)
        doc = _parse_toml(cfg.read_text(encoding='utf-8'))
        assert doc['forge'] == 'github'
        assert doc['repo_owner'] == 'firebase'
        assert doc['license']['project'] == 'Apache-2.0'
        assert 'gpl-lib' in doc['license']['exempt_packages']

    def test_multiple_fixes(self, tmp_path: Path) -> None:
        """Test multiple fixes in one call."""
        cfg = _write_toml(tmp_path / 'releasekit.toml', 'forge = "github"\n')
        choices = [
            LicenseFixChoice(
                dep_name='gpl-lib',
                dep_license='GPL-3.0-only',
                parent_package='myapp',
                action=FixAction.EXEMPT,
            ),
            LicenseFixChoice(
                dep_name='agpl-lib',
                dep_license='AGPL-3.0-only',
                parent_package='myapp',
                action=FixAction.DENY,
            ),
            LicenseFixChoice(
                dep_name='dual-lib',
                dep_license='(unknown)',
                parent_package='myapp',
                action=FixAction.OVERRIDE,
                override_value='MIT',
            ),
            LicenseFixChoice(
                dep_name='skip-lib',
                dep_license='X',
                parent_package='myapp',
                action=FixAction.SKIP,
            ),
        ]
        report = apply_fixes(cfg, choices)
        assert report.written
        doc = _parse_toml(cfg.read_text(encoding='utf-8'))
        assert 'gpl-lib' in doc['license']['exempt_packages']
        assert 'AGPL-3.0-only' in doc['license']['deny_licenses']
        assert doc['license']['overrides']['dual-lib'] == 'MIT'


# ── TestInteractiveLicenseFix ────────────────────────────────────────


class TestInteractiveLicenseFix:
    """Tests for interactive license fix."""

    def test_no_issues(self, tmp_path: Path) -> None:
        """Test no issues to fix."""
        cfg = _write_toml(tmp_path / 'releasekit.toml', 'forge = "github"\n')
        tree = _tree(('ok-lib', 'MIT', DepStatus.OK))
        output: list[str] = []
        report = interactive_license_fix(tree, cfg, print_fn=output.append)
        assert not report.written
        assert any('No license issues' in str(m) for m in output)

    def test_exempt_one(self, tmp_path: Path) -> None:
        """Test exempt one dependency."""
        cfg = _write_toml(tmp_path / 'releasekit.toml', 'forge = "github"\n')
        tree = _tree(('gpl-lib', 'GPL-3.0-only', DepStatus.INCOMPATIBLE))
        inputs = iter(['1'])
        output: list[str] = []
        report = interactive_license_fix(
            tree,
            cfg,
            input_fn=lambda _prompt='': next(inputs),
            print_fn=output.append,
        )
        assert report.written
        assert len(report.choices) == 1
        assert report.choices[0].action == FixAction.EXEMPT
        doc = _parse_toml(cfg.read_text(encoding='utf-8'))
        assert 'gpl-lib' in doc['license']['exempt_packages']

    def test_skip_all(self, tmp_path: Path) -> None:
        """Test skip all issues."""
        cfg = _write_toml(tmp_path / 'releasekit.toml', 'forge = "github"\n')
        tree = _tree(('gpl-lib', 'GPL-3.0-only', DepStatus.INCOMPATIBLE))
        inputs = iter(['5'])
        output: list[str] = []
        report = interactive_license_fix(
            tree,
            cfg,
            input_fn=lambda _prompt='': next(inputs),
            print_fn=output.append,
        )
        assert not report.written
        assert any('skipped' in str(m) for m in output)

    def test_dry_run(self, tmp_path: Path) -> None:
        """Test dry run mode."""
        cfg = _write_toml(tmp_path / 'releasekit.toml', 'forge = "github"\n')
        tree = _tree(('gpl-lib', 'GPL-3.0-only', DepStatus.INCOMPATIBLE))
        inputs = iter(['1'])
        output: list[str] = []
        report = interactive_license_fix(
            tree,
            cfg,
            dry_run=True,
            input_fn=lambda _prompt='': next(inputs),
            print_fn=output.append,
        )
        assert not report.written
        assert any('dry-run' in str(m) for m in output)
        # File should be unchanged.
        doc = _parse_toml(cfg.read_text(encoding='utf-8'))
        assert 'license' not in doc

    def test_multiple_issues(self, tmp_path: Path) -> None:
        """Test multiple issues resolved."""
        cfg = _write_toml(tmp_path / 'releasekit.toml', 'forge = "github"\n')
        tree = _tree(
            ('gpl-lib', 'GPL-3.0-only', DepStatus.INCOMPATIBLE),
            ('agpl-lib', 'AGPL-3.0-only', DepStatus.DENIED),
        )
        inputs = iter(['1', '3'])
        report = interactive_license_fix(
            tree,
            cfg,
            input_fn=lambda _prompt='': next(inputs),
            print_fn=lambda *_a: None,
        )
        assert report.written
        assert len(report.choices) == 2
        doc = _parse_toml(cfg.read_text(encoding='utf-8'))
        assert 'gpl-lib' in doc['license']['exempt_packages']
        assert 'AGPL-3.0-only' in doc['license']['deny_licenses']

    def test_ctrl_c_aborts_immediately(self, tmp_path: Path) -> None:
        """Test Ctrl-C aborts the fix loop and applies choices made so far."""
        cfg = _write_toml(tmp_path / 'releasekit.toml', 'forge = "github"\n')
        tree = _tree(
            ('gpl-lib', 'GPL-3.0-only', DepStatus.INCOMPATIBLE),
            ('agpl-lib', 'AGPL-3.0-only', DepStatus.DENIED),
            ('mystery-lib', '(unknown)', DepStatus.NO_LICENSE),
        )
        call_count = 0

        def _input(_prompt: str = '') -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return '1'  # exempt gpl-lib
            raise KeyboardInterrupt  # abort on second dep

        output: list[str] = []
        report = interactive_license_fix(
            tree,
            cfg,
            input_fn=_input,
            print_fn=output.append,
        )
        # Only the first choice (exempt) should have been collected.
        assert len(report.choices) == 1
        assert report.choices[0].action == FixAction.EXEMPT
        assert report.written
        # "Aborted." should appear in output.
        assert any('Aborted' in str(m) for m in output)
        # Only gpl-lib should be in the config; agpl-lib and mystery-lib untouched.
        doc = _parse_toml(cfg.read_text(encoding='utf-8'))
        assert 'gpl-lib' in doc['license']['exempt_packages']


# ── TestLicenseFixReport ─────────────────────────────────────────────


class TestLicenseFixReport:
    """Tests for license fix report."""

    def test_defaults(self) -> None:
        """Test defaults."""
        report = LicenseFixReport()
        assert report.choices == []
        assert not report.written
        assert report.config_path is None

    def test_with_choices(self, tmp_path: Path) -> None:
        """Test with choices."""
        c = LicenseFixChoice(dep_name='x', dep_license='MIT', parent_package='a', action=FixAction.EXEMPT)
        report = LicenseFixReport(choices=[c], written=True, config_path=tmp_path / 'test.toml')
        assert len(report.choices) == 1
        assert report.written


# ── TestFixAction ────────────────────────────────────────────────────


class TestFixAction:
    """Tests for fix action constants."""

    def test_values(self) -> None:
        """Test values."""
        assert FixAction.EXEMPT == 'exempt'
        assert FixAction.ALLOW == 'allow'
        assert FixAction.DENY == 'deny'
        assert FixAction.OVERRIDE == 'override'
        assert FixAction.SKIP == 'skip'
