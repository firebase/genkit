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

"""Tests for releasekit.plan module."""

from __future__ import annotations

import json
from pathlib import Path

from releasekit.plan import (
    ExecutionPlan,
    PlanEntry,
    PlanStatus,
    build_plan,
)
from releasekit.versions import PackageVersion
from releasekit.workspace import Package


def _make_packages() -> list[Package]:
    """Create a minimal package set for testing."""
    return [
        Package(
            name='genkit',
            version='0.5.0',
            path=Path('/ws/packages/genkit'),
            pyproject_path=Path('/ws/packages/genkit/pyproject.toml'),
        ),
        Package(
            name='genkit-plugin-foo',
            version='0.5.0',
            path=Path('/ws/plugins/foo'),
            pyproject_path=Path('/ws/plugins/foo/pyproject.toml'),
            internal_deps=['genkit'],
        ),
        Package(
            name='sample-hello',
            version='0.1.0',
            path=Path('/ws/samples/hello'),
            pyproject_path=Path('/ws/samples/hello/pyproject.toml'),
            internal_deps=['genkit', 'genkit-plugin-foo'],
        ),
    ]


class TestPlanStatus:
    """Tests for PlanStatus enum."""

    def test_values(self) -> None:
        """All expected statuses exist."""
        expected = {'included', 'skipped', 'excluded', 'already_published', 'dependency_only'}
        got = {s.value for s in PlanStatus}
        if got != expected:
            msg = f'Expected {expected}, got {got}'
            raise AssertionError(msg)


class TestPlanEntry:
    """Tests for PlanEntry dataclass."""

    def test_defaults(self) -> None:
        """Default entry is INCLUDED with empty fields."""
        entry = PlanEntry(name='genkit')
        if entry.status != PlanStatus.INCLUDED:
            raise AssertionError(f'Expected INCLUDED, got {entry.status}')
        if entry.bump != 'none':
            raise AssertionError(f'Expected bump=none, got {entry.bump}')

    def test_all_fields(self) -> None:
        """All fields are settable."""
        entry = PlanEntry(
            name='genkit',
            level=0,
            current_version='0.5.0',
            next_version='0.6.0',
            status=PlanStatus.INCLUDED,
            bump='minor',
            reason='changed',
            order=1,
        )
        if entry.next_version != '0.6.0':
            raise AssertionError(f'Wrong next_version: {entry.next_version}')
        if entry.bump != 'minor':
            raise AssertionError(f'Wrong bump: {entry.bump}')


class TestExecutionPlan:
    """Tests for ExecutionPlan."""

    def _make_plan(self) -> ExecutionPlan:
        """Create a plan with mixed statuses."""
        return ExecutionPlan(
            entries=[
                PlanEntry(
                    name='genkit',
                    level=0,
                    current_version='0.5.0',
                    next_version='0.6.0',
                    status=PlanStatus.INCLUDED,
                    bump='minor',
                ),
                PlanEntry(
                    name='genkit-plugin-foo',
                    level=1,
                    current_version='0.5.0',
                    next_version='0.6.0',
                    status=PlanStatus.INCLUDED,
                    bump='minor',
                ),
                PlanEntry(
                    name='sample-hello',
                    level=2,
                    current_version='0.1.0',
                    status=PlanStatus.SKIPPED,
                    reason='no changes',
                ),
                PlanEntry(
                    name='sample-excluded',
                    level=2,
                    current_version='0.1.0',
                    status=PlanStatus.EXCLUDED,
                    reason='excluded by config',
                ),
            ],
            git_sha='abc123',
        )

    def test_included(self) -> None:
        """included() returns only INCLUDED entries."""
        plan = self._make_plan()
        included = plan.included
        if len(included) != 2:
            raise AssertionError(f'Expected 2 included, got {len(included)}')
        names = [e.name for e in included]
        if 'genkit' not in names or 'genkit-plugin-foo' not in names:
            raise AssertionError(f'Wrong names: {names}')

    def test_skipped(self) -> None:
        """Skipped returns SKIPPED and ALREADY_PUBLISHED entries."""
        plan = self._make_plan()
        skipped = plan.skipped
        if len(skipped) != 1:
            raise AssertionError(f'Expected 1 skipped, got {len(skipped)}')
        if skipped[0].name != 'sample-hello':
            raise AssertionError(f'Wrong name: {skipped[0].name}')

    def test_summary(self) -> None:
        """summary() returns counts by status value."""
        plan = self._make_plan()
        summary = plan.summary()
        if summary.get('included') != 2:
            raise AssertionError(f'Wrong included count: {summary}')
        if summary.get('excluded') != 1:
            raise AssertionError(f'Wrong excluded count: {summary}')
        if summary.get('skipped') != 1:
            raise AssertionError(f'Wrong skipped count: {summary}')

    def test_format_table(self) -> None:
        """format_table() returns a non-empty string."""
        plan = self._make_plan()
        table = plan.format_table()
        if not table:
            raise AssertionError('Empty table')
        if 'genkit' not in table:
            raise AssertionError(f'genkit not in table: {table[:200]}')

    def test_format_json(self) -> None:
        """format_json() returns valid JSON."""
        plan = self._make_plan()
        output = plan.format_json()

        data = json.loads(output)
        if 'entries' not in data:
            raise AssertionError(f'Missing entries key: {list(data.keys())}')
        if len(data['entries']) != 4:
            raise AssertionError(f'Expected 3 entries, got {len(data["entries"])}')

    def test_format_csv(self) -> None:
        """format_csv() returns CSV with header."""
        plan = self._make_plan()
        output = plan.format_csv()

        lines = output.strip().split('\n')
        if len(lines) < 2:
            raise AssertionError(f'Expected header + rows, got {len(lines)} lines')
        # Header should have column names.
        header = lines[0]
        if 'name' not in header:
            raise AssertionError(f'Missing name in header: {header}')

    def test_empty_plan(self) -> None:
        """An empty plan produces empty results."""
        plan = ExecutionPlan(entries=[], git_sha='x')
        if plan.included:
            raise AssertionError('Expected no included')
        if plan.skipped:
            raise AssertionError('Expected no skipped')


class TestBuildPlan:
    """Tests for the build_plan() function."""

    def test_basic_build(self) -> None:
        """build_plan produces entries for all packages."""
        packages = _make_packages()
        versions = [
            PackageVersion(name='genkit', old_version='0.5.0', new_version='0.6.0', bump='minor'),
            PackageVersion(name='genkit-plugin-foo', old_version='0.5.0', new_version='0.6.0', bump='minor'),
            PackageVersion(name='sample-hello', old_version='0.1.0', new_version='0.1.1', bump='patch'),
        ]
        levels = [
            [packages[0]],
            [packages[1]],
            [packages[2]],
        ]

        plan = build_plan(versions, levels)
        if len(plan.entries) != 3:
            raise AssertionError(f'Expected 3 entries, got {len(plan.entries)}')

    def test_exclude_names(self) -> None:
        """Excluded packages get EXCLUDED status."""
        packages = _make_packages()
        versions = [
            PackageVersion(name='genkit', old_version='0.5.0', new_version='0.6.0', bump='minor'),
            PackageVersion(name='genkit-plugin-foo', old_version='0.5.0', new_version='0.6.0', bump='minor'),
            PackageVersion(name='sample-hello', old_version='0.1.0', new_version='0.1.1', bump='patch'),
        ]
        levels = [
            [packages[0]],
            [packages[1]],
            [packages[2]],
        ]

        plan = build_plan(versions, levels, exclude_names=['sample-hello'])
        excluded = [e for e in plan.entries if e.status == PlanStatus.EXCLUDED]
        if len(excluded) != 1:
            raise AssertionError(f'Expected 1 excluded, got {len(excluded)}')
        if excluded[0].name != 'sample-hello':
            raise AssertionError(f'Wrong excluded: {excluded[0].name}')

    def test_already_published(self) -> None:
        """Already-published packages are marked accordingly."""
        packages = _make_packages()
        versions = [
            PackageVersion(name='genkit', old_version='0.5.0', new_version='0.5.0', bump='none'),
            PackageVersion(name='genkit-plugin-foo', old_version='0.5.0', new_version='0.6.0', bump='minor'),
            PackageVersion(name='sample-hello', old_version='0.1.0', new_version='0.1.1', bump='patch'),
        ]
        levels = [
            [packages[0]],
            [packages[1]],
            [packages[2]],
        ]

        plan = build_plan(versions, levels, already_published={'genkit'})
        genkit = next(e for e in plan.entries if e.name == 'genkit')
        if genkit.status != PlanStatus.ALREADY_PUBLISHED:
            raise AssertionError(f'Expected ALREADY_PUBLISHED, got {genkit.status}')

    def test_git_sha_propagated(self) -> None:
        """git_sha is propagated to the plan."""
        plan = build_plan([], [], git_sha='sha256abc')
        if plan.git_sha != 'sha256abc':
            raise AssertionError(f'Wrong SHA: {plan.git_sha}')
