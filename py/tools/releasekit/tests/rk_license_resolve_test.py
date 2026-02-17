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

"""Tests for the fuzzy SPDX license name resolver."""

from __future__ import annotations

import pytest
from releasekit.checks._license_graph import LicenseGraph
from releasekit.checks._license_resolve import LicenseResolver


@pytest.fixture()
def resolver() -> LicenseResolver:
    """Resolver."""
    graph = LicenseGraph.load()
    return LicenseResolver(graph)


# ── Stage 1: Exact match ────────────────────────────────────────────


class TestExactMatch:
    """Tests for exact Match."""

    def test_canonical_spdx_id(self, resolver: LicenseResolver) -> None:
        """Test canonical spdx id."""
        r = resolver.resolve('MIT')
        assert r.spdx_id == 'MIT'
        assert r.confidence == 1.0
        assert r.method == 'exact'
        assert r.resolved

    def test_hyphenated_id(self, resolver: LicenseResolver) -> None:
        """Test hyphenated id."""
        r = resolver.resolve('Apache-2.0')
        assert r.spdx_id == 'Apache-2.0'
        assert r.method == 'exact'

    def test_complex_id(self, resolver: LicenseResolver) -> None:
        """Test complex id."""
        r = resolver.resolve('GPL-3.0-only')
        assert r.spdx_id == 'GPL-3.0-only'
        assert r.method == 'exact'


# ── Stage 2: Alias match ────────────────────────────────────────────


class TestAliasMatch:
    """Tests for alias Match."""

    def test_common_name(self, resolver: LicenseResolver) -> None:
        """Test common name."""
        r = resolver.resolve('MIT License')
        assert r.spdx_id == 'MIT'
        assert r.confidence == 1.0
        assert r.method == 'alias'

    def test_the_prefix(self, resolver: LicenseResolver) -> None:
        """Test the prefix."""
        r = resolver.resolve('The MIT License')
        assert r.spdx_id == 'MIT'
        assert r.method == 'alias'

    def test_apache_short(self, resolver: LicenseResolver) -> None:
        """Test apache short."""
        r = resolver.resolve('Apache 2.0')
        assert r.spdx_id == 'Apache-2.0'
        assert r.method == 'alias'

    def test_asl_abbreviation(self, resolver: LicenseResolver) -> None:
        """Test asl abbreviation."""
        r = resolver.resolve('ASL 2.0')
        assert r.spdx_id == 'Apache-2.0'
        assert r.method == 'alias'

    def test_pypi_classifier(self, resolver: LicenseResolver) -> None:
        """Test pypi classifier."""
        r = resolver.resolve('License :: OSI Approved :: MIT License')
        assert r.spdx_id == 'MIT'
        assert r.method == 'alias'

    def test_gpl_abbreviation(self, resolver: LicenseResolver) -> None:
        """Test gpl abbreviation."""
        r = resolver.resolve('GPLv3')
        assert r.spdx_id == 'GPL-3.0-only'
        assert r.method == 'alias'

    def test_lgpl_abbreviation(self, resolver: LicenseResolver) -> None:
        """Test lgpl abbreviation."""
        r = resolver.resolve('LGPLv2.1')
        assert r.spdx_id == 'LGPL-2.1-only'
        assert r.method == 'alias'

    def test_bsd_license(self, resolver: LicenseResolver) -> None:
        """Test bsd license."""
        r = resolver.resolve('BSD License')
        assert r.spdx_id == 'BSD-3-Clause'
        assert r.method == 'alias'

    def test_case_insensitive(self, resolver: LicenseResolver) -> None:
        """Test case insensitive."""
        r = resolver.resolve('mit license')
        assert r.spdx_id == 'MIT'

    def test_boost(self, resolver: LicenseResolver) -> None:
        """Test boost."""
        r = resolver.resolve('Boost Software License')
        assert r.spdx_id == 'BSL-1.0'

    def test_unlicense(self, resolver: LicenseResolver) -> None:
        """Test unlicense."""
        r = resolver.resolve('The Unlicense')
        assert r.spdx_id == 'Unlicense'

    def test_mpl(self, resolver: LicenseResolver) -> None:
        """Test mpl."""
        r = resolver.resolve('MPL 2.0')
        assert r.spdx_id == 'MPL-2.0'


# ── Stage 3: Normalized match ────────────────────────────────────────


class TestNormalizedMatch:
    """Tests for normalized Match."""

    def test_extra_punctuation(self, resolver: LicenseResolver) -> None:
        """Test extra punctuation."""
        r = resolver.resolve('M.I.T.')
        assert r.spdx_id == 'MIT'
        assert r.method == 'normalized'
        assert r.confidence == pytest.approx(0.95)

    def test_extra_spaces(self, resolver: LicenseResolver) -> None:
        """Test extra spaces."""
        r = resolver.resolve('BSD  3  Clause')
        assert r.spdx_id == 'BSD-3-Clause'
        assert r.method == 'normalized'


# ── Stage 4: Edit-distance match ─────────────────────────────────────


class TestEditDistanceMatch:
    """Tests for edit Distance Match."""

    def test_typo_in_apache(self, resolver: LicenseResolver) -> None:
        """Test typo in apache."""
        r = resolver.resolve('Apche-2.0')
        assert r.spdx_id == 'Apache-2.0'
        assert r.method == 'edit-distance'
        assert r.confidence > 0.5

    def test_typo_in_mit(self, resolver: LicenseResolver) -> None:
        """Test typo in mit."""
        r = resolver.resolve('MIt Licence')
        assert r.spdx_id == 'MIT'
        assert r.method in ('edit-distance', 'alias', 'normalized')

    def test_close_match_has_suggestions(self, resolver: LicenseResolver) -> None:
        """Test close match has suggestions."""
        r = resolver.resolve('Apche-2.0')
        # Should resolve but may have suggestions if ambiguous.
        assert r.resolved


# ── Stage 5: Unresolved ──────────────────────────────────────────────


class TestUnresolved:
    """Tests for unresolved."""

    def test_empty_string(self, resolver: LicenseResolver) -> None:
        """Test empty string."""
        r = resolver.resolve('')
        assert not r.resolved
        assert r.spdx_id == ''
        assert r.method == 'unresolved'
        assert r.confidence == 0.0

    def test_whitespace_only(self, resolver: LicenseResolver) -> None:
        """Test whitespace only."""
        r = resolver.resolve('   ')
        assert not r.resolved

    def test_gibberish(self, resolver: LicenseResolver) -> None:
        """Test gibberish."""
        r = resolver.resolve('xyzzy-foobar-9999')
        assert not r.resolved
        assert r.method == 'unresolved'


# ── ResolvedLicense properties ────────────────────────────────────────


class TestResolvedLicenseProperties:
    """Tests for resolved License Properties."""

    def test_resolved_true(self, resolver: LicenseResolver) -> None:
        """Test resolved true."""
        r = resolver.resolve('MIT')
        assert r.resolved is True

    def test_resolved_false(self, resolver: LicenseResolver) -> None:
        """Test resolved false."""
        r = resolver.resolve('xyzzy')
        assert r.resolved is False

    def test_original_preserved(self, resolver: LicenseResolver) -> None:
        """Test original preserved."""
        r = resolver.resolve('  MIT License  ')
        assert r.original == '  MIT License  '


# ── resolve_all() ────────────────────────────────────────────────────


class TestResolveAll:
    """Tests for resolve All."""

    def test_batch(self, resolver: LicenseResolver) -> None:
        """Test batch."""
        results = resolver.resolve_all(['MIT', 'Apache 2.0', 'xyzzy'])
        assert len(results) == 3
        assert results[0].spdx_id == 'MIT'
        assert results[1].spdx_id == 'Apache-2.0'
        assert not results[2].resolved

    def test_empty_list(self, resolver: LicenseResolver) -> None:
        """Test empty list."""
        assert resolver.resolve_all([]) == []


# ── Real-world license strings ───────────────────────────────────────


class TestRealWorldStrings:
    """Tests for real World Strings."""

    @pytest.mark.parametrize(
        'raw,expected',
        [
            ('MIT', 'MIT'),
            ('mit', 'MIT'),
            ('The MIT License (MIT)', 'MIT'),
            ('Apache License 2.0', 'Apache-2.0'),
            ('Apache License, Version 2.0', 'Apache-2.0'),
            ('Apache-2', 'Apache-2.0'),
            ('BSD-3-Clause', 'BSD-3-Clause'),
            ('Modified BSD License', 'BSD-3-Clause'),
            ('ISC License', 'ISC'),
            ('GPL-3.0-only', 'GPL-3.0-only'),
            ('GNU General Public License v3', 'GPL-3.0-only'),
            ('GPLv2', 'GPL-2.0-only'),
            ('LGPL-2.1-only', 'LGPL-2.1-only'),
            ('Mozilla Public License 2.0', 'MPL-2.0'),
            ('Unlicensed', 'Unlicense'),
            ('CC0', 'CC0-1.0'),
            ('Public Domain', 'CC0-1.0'),
            ('PSF License', 'Python-2.0'),
            ('Eclipse Public License 2.0', 'EPL-2.0'),
        ],
    )
    def test_resolves_correctly(self, resolver: LicenseResolver, raw: str, expected: str) -> None:
        """Test resolves correctly."""
        r = resolver.resolve(raw)
        assert r.spdx_id == expected, f'{raw!r} resolved to {r.spdx_id!r} via {r.method}, expected {expected!r}'
