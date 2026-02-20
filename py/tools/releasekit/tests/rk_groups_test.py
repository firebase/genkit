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

"""Tests for release group filtering."""

from __future__ import annotations

from pathlib import Path

import pytest
from releasekit.errors import ReleaseKitError
from releasekit.groups import filter_by_group, list_groups, validate_group
from releasekit.logging import configure_logging
from releasekit.workspace import Package

configure_logging(quiet=True)


def _pkg(name: str) -> Package:
    """Create a minimal Package for testing."""
    return Package(
        name=name,
        version='0.1.0',
        path=Path(f'/workspace/{name}'),
        manifest_path=Path(f'/workspace/{name}/pyproject.toml'),
    )


@pytest.fixture
def all_packages() -> list[Package]:
    """A realistic workspace with core, plugins, and samples."""
    return [
        _pkg('genkit'),
        _pkg('genkit-plugin-google-genai'),
        _pkg('genkit-plugin-vertex-ai'),
        _pkg('genkit-plugin-ollama'),
        _pkg('sample-chat'),
        _pkg('sample-rag'),
        _pkg('web-endpoints-hello'),
    ]


@pytest.fixture
def groups() -> dict[str, list[str]]:
    """Standard group definitions."""
    return {
        'core': ['genkit', 'genkit-plugin-*'],
        'samples': ['sample-*'],
        'web': ['web-*'],
        'all': ['*'],
    }


class TestFilterByGroup:
    """Tests for filter_by_group()."""

    def test_core_group_matches(
        self,
        all_packages: list[Package],
        groups: dict[str, list[str]],
    ) -> None:
        """Test core group matches."""
        result = filter_by_group(all_packages, groups=groups, group='core')
        names = [p.name for p in result]
        expected = ['genkit', 'genkit-plugin-google-genai', 'genkit-plugin-vertex-ai', 'genkit-plugin-ollama']
        if sorted(names) != sorted(expected):
            pytest.fail(f'Core group: expected {sorted(expected)}, got {sorted(names)}')

    def test_samples_group_matches(
        self,
        all_packages: list[Package],
        groups: dict[str, list[str]],
    ) -> None:
        """Test samples group matches."""
        result = filter_by_group(all_packages, groups=groups, group='samples')
        names = [p.name for p in result]
        expected = ['sample-chat', 'sample-rag']
        if sorted(names) != sorted(expected):
            pytest.fail(f'Samples group: expected {sorted(expected)}, got {sorted(names)}')

    def test_web_group_matches(
        self,
        all_packages: list[Package],
        groups: dict[str, list[str]],
    ) -> None:
        """Test web group matches."""
        result = filter_by_group(all_packages, groups=groups, group='web')
        names = [p.name for p in result]
        if names != ['web-endpoints-hello']:
            pytest.fail(f'Web group: expected ["web-endpoints-hello"], got {names}')

    def test_all_group_matches_everything(
        self,
        all_packages: list[Package],
        groups: dict[str, list[str]],
    ) -> None:
        """Test all group matches everything."""
        result = filter_by_group(all_packages, groups=groups, group='all')
        if len(result) != len(all_packages):
            pytest.fail(f'All group: expected {len(all_packages)}, got {len(result)}')

    def test_unknown_group_raises(
        self,
        all_packages: list[Package],
        groups: dict[str, list[str]],
    ) -> None:
        """Test unknown group raises."""
        with pytest.raises(ReleaseKitError, match="Unknown release group 'nonexistent'"):
            filter_by_group(all_packages, groups=groups, group='nonexistent')

    def test_empty_groups_raises(
        self,
        all_packages: list[Package],
    ) -> None:
        """Test empty groups raises."""
        with pytest.raises(ReleaseKitError, match="Unknown release group 'core'"):
            filter_by_group(all_packages, groups={}, group='core')

    def test_preserves_order(
        self,
        all_packages: list[Package],
        groups: dict[str, list[str]],
    ) -> None:
        """Filtered results preserve original list order."""
        result = filter_by_group(all_packages, groups=groups, group='core')
        names = [p.name for p in result]
        # The first should be 'genkit' since it comes first in the input.
        if names[0] != 'genkit':
            pytest.fail(f'Expected "genkit" first, got "{names[0]}"')

    def test_no_matches_returns_empty(
        self,
        all_packages: list[Package],
    ) -> None:
        """Test no matches returns empty."""
        groups = {'empty': ['nonexistent-*']}
        result = filter_by_group(all_packages, groups=groups, group='empty')
        if result:
            pytest.fail(f'Expected empty list, got {[p.name for p in result]}')

    def test_multiple_patterns_union(
        self,
        all_packages: list[Package],
    ) -> None:
        """Multiple patterns in a group are unioned (OR logic)."""
        groups = {'mixed': ['genkit', 'sample-*']}
        result = filter_by_group(all_packages, groups=groups, group='mixed')
        names = [p.name for p in result]
        expected = ['genkit', 'sample-chat', 'sample-rag']
        if sorted(names) != sorted(expected):
            pytest.fail(f'Mixed group: expected {sorted(expected)}, got {sorted(names)}')

    def test_exact_name_match(
        self,
        all_packages: list[Package],
    ) -> None:
        """Exact name (no glob) works as a pattern."""
        groups = {'single': ['genkit']}
        result = filter_by_group(all_packages, groups=groups, group='single')
        if len(result) != 1 or result[0].name != 'genkit':
            pytest.fail(f'Expected exactly [genkit], got {[p.name for p in result]}')


class TestListGroups:
    """Tests for list_groups()."""

    def test_returns_sorted(self, groups: dict[str, list[str]]) -> None:
        """Test returns sorted."""
        result = list_groups(groups)
        names = [name for name, _ in result]
        if names != sorted(names):
            pytest.fail(f'Expected sorted order, got {names}')

    def test_empty_groups(self) -> None:
        """Test empty groups."""
        result = list_groups({})
        if result:
            pytest.fail(f'Expected empty list, got {result}')

    def test_includes_patterns(self, groups: dict[str, list[str]]) -> None:
        """Test includes patterns."""
        result = list_groups(groups)
        for name, patterns in result:
            if name == 'core':
                if patterns != ['genkit', 'genkit-plugin-*']:
                    pytest.fail(f"Core patterns: expected ['genkit', 'genkit-plugin-*'], got {patterns}")
                break
        else:
            pytest.fail('Core group not found in list_groups output')


class TestValidateGroup:
    """Tests for validate_group()."""

    def test_valid_group_no_warnings(
        self,
        all_packages: list[Package],
        groups: dict[str, list[str]],
    ) -> None:
        """Test valid group no warnings."""
        warnings = validate_group(groups, 'core', all_packages)
        if warnings:
            pytest.fail(f'Expected no warnings, got {warnings}')

    def test_unmatched_pattern_warns(
        self,
        all_packages: list[Package],
    ) -> None:
        """Test unmatched pattern warns."""
        groups = {'test': ['genkit', 'nonexistent-*']}
        warnings = validate_group(groups, 'test', all_packages)
        if len(warnings) != 1:
            pytest.fail(f'Expected 1 warning, got {len(warnings)}')
        if 'nonexistent-*' not in warnings[0]:
            pytest.fail(f"Expected mention of 'nonexistent-*', got: {warnings[0]}")

    def test_unknown_group_raises(
        self,
        all_packages: list[Package],
        groups: dict[str, list[str]],
    ) -> None:
        """Test unknown group raises."""
        with pytest.raises(ReleaseKitError, match='Unknown release group'):
            validate_group(groups, 'fake', all_packages)

    def test_all_patterns_unmatched(
        self,
        all_packages: list[Package],
    ) -> None:
        """Test all patterns unmatched."""
        groups = {'dead': ['zzz-*', 'xxx-*']}
        warnings = validate_group(groups, 'dead', all_packages)
        if len(warnings) != 2:
            pytest.fail(f'Expected 2 warnings, got {len(warnings)}')
