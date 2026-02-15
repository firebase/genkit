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

"""Tests for releasekit.utils.packaging — PEP 503/508 name helpers."""

from __future__ import annotations

import pytest
from releasekit.utils.packaging import normalize_name, parse_dep_name


class TestNormalizeName:
    """Tests for normalize_name()."""

    def test_lowercase(self) -> None:
        """Lowercases the name."""
        assert normalize_name('MyPackage') == 'mypackage'

    def test_underscores_to_hyphens(self) -> None:
        """Replaces underscores with hyphens."""
        assert normalize_name('my_package') == 'my-package'

    def test_mixed_case_and_underscores(self) -> None:
        """Handles both case and underscore normalization."""
        assert normalize_name('My_Cool_Package') == 'my-cool-package'

    def test_already_normalized(self) -> None:
        """Returns the same string if already normalized."""
        assert normalize_name('genkit') == 'genkit'

    def test_hyphens_preserved(self) -> None:
        """Hyphens are preserved as-is."""
        assert normalize_name('genkit-plugin-foo') == 'genkit-plugin-foo'

    def test_multiple_underscores(self) -> None:
        """Multiple underscores are each replaced."""
        assert normalize_name('a__b___c') == 'a--b---c'

    def test_empty_string(self) -> None:
        """Empty string returns empty string."""
        assert normalize_name('') == ''

    def test_all_uppercase(self) -> None:
        """All uppercase is lowercased."""
        assert normalize_name('GENKIT') == 'genkit'


class TestParseDepName:
    """Tests for parse_dep_name()."""

    def test_simple_name(self) -> None:
        """Parses a bare package name."""
        assert parse_dep_name('genkit') == 'genkit'

    def test_with_version_specifier(self) -> None:
        """Parses name from a version-pinned specifier."""
        assert parse_dep_name('genkit>=0.5.0') == 'genkit'

    def test_with_exact_version(self) -> None:
        """Parses name from an exact version pin."""
        assert parse_dep_name('genkit==1.0.0') == 'genkit'

    def test_with_extras(self) -> None:
        """Parses name from a specifier with extras."""
        assert parse_dep_name('genkit[dev]>=0.5.0') == 'genkit'

    def test_with_environment_marker(self) -> None:
        """Parses name from a specifier with environment markers."""
        assert parse_dep_name('genkit>=0.5.0; python_version>="3.10"') == 'genkit'

    def test_complex_specifier(self) -> None:
        """Parses name from a complex PEP 508 specifier."""
        assert parse_dep_name('genkit[all]>=0.5.0,<2.0; sys_platform=="linux"') == 'genkit'

    def test_lowercases_result(self) -> None:
        """Result is always lowercased."""
        assert parse_dep_name('MyPackage>=1.0') == 'mypackage'

    def test_hyphenated_name(self) -> None:
        """Parses hyphenated package names."""
        assert parse_dep_name('genkit-plugin-foo>=0.1.0') == 'genkit-plugin-foo'

    def test_underscored_name(self) -> None:
        """Parses underscored package names (lowercased but not normalized)."""
        assert parse_dep_name('genkit_plugin_foo>=0.1.0') == 'genkit_plugin_foo'

    def test_tilde_version(self) -> None:
        """Parses name from a tilde version specifier."""
        assert parse_dep_name('genkit~=0.5.0') == 'genkit'

    def test_not_equal_version(self) -> None:
        """Parses name from a not-equal version specifier."""
        assert parse_dep_name('genkit!=0.4.0') == 'genkit'

    def test_malformed_fallback(self) -> None:
        """Falls back to string splitting for malformed specifiers."""
        assert parse_dep_name('weird:package>=1.0') == 'weird:package'

    def test_empty_string(self) -> None:
        """Empty string returns empty string."""
        assert parse_dep_name('') == ''

    @pytest.mark.parametrize(
        ('spec', 'expected'),
        [
            ('requests>=2.28', 'requests'),
            ('httpx[http2]>=0.24', 'httpx'),
            ('pydantic>=2.0,<3.0', 'pydantic'),
            ('structlog', 'structlog'),
            ('tomlkit>=0.12.0', 'tomlkit'),
        ],
    )
    def test_common_dependencies(self, spec: str, expected: str) -> None:
        """Parses common real-world dependency specifiers."""
        assert parse_dep_name(spec) == expected
