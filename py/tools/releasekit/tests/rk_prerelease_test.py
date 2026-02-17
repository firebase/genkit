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

"""Tests for releasekit.prerelease — pre-release version management."""

from __future__ import annotations

import pytest
from releasekit.errors import ReleaseKitError
from releasekit.logging import configure_logging
from releasekit.prerelease import (
    PrereleaseInfo,
    apply_prerelease,
    escalate_prerelease,
    increment_prerelease,
    is_prerelease,
    parse_prerelease,
    prerelease_sort_key,
    promote_to_stable,
)

configure_logging(quiet=True)


# parse_prerelease


class TestParsePrerelease:
    """Tests for parse_prerelease()."""

    def test_semver_rc(self) -> None:
        """Parse semver RC version."""
        info = parse_prerelease('1.2.3-rc.1')
        assert info.major == 1
        assert info.minor == 2
        assert info.patch == 3
        assert info.label == 'rc'
        assert info.number == 1
        assert info.scheme == 'semver'
        assert info.is_prerelease is True

    def test_semver_alpha(self) -> None:
        """Parse semver alpha version."""
        info = parse_prerelease('0.5.0-alpha.3')
        assert info.label == 'alpha'
        assert info.number == 3

    def test_semver_beta(self) -> None:
        """Parse semver beta version."""
        info = parse_prerelease('2.0.0-beta.2')
        assert info.label == 'beta'
        assert info.number == 2

    def test_semver_dev(self) -> None:
        """Parse semver dev version."""
        info = parse_prerelease('1.0.0-dev.5')
        assert info.label == 'dev'
        assert info.number == 5

    def test_pep440_rc(self) -> None:
        """Parse PEP 440 RC version."""
        info = parse_prerelease('1.2.3rc1', scheme='pep440')
        assert info.label == 'rc'
        assert info.number == 1
        assert info.scheme == 'pep440'

    def test_pep440_alpha(self) -> None:
        """Parse PEP 440 alpha version."""
        info = parse_prerelease('1.2.3a2', scheme='pep440')
        assert info.label == 'alpha'
        assert info.number == 2

    def test_pep440_beta(self) -> None:
        """Parse PEP 440 beta version."""
        info = parse_prerelease('1.2.3b5', scheme='pep440')
        assert info.label == 'beta'
        assert info.number == 5

    def test_pep440_dev(self) -> None:
        """Parse PEP 440 dev version."""
        info = parse_prerelease('1.2.3.dev4', scheme='pep440')
        assert info.label == 'dev'
        assert info.number == 4

    def test_stable_version(self) -> None:
        """Parse a stable version (no pre-release)."""
        info = parse_prerelease('1.2.3')
        assert info.is_prerelease is False
        assert info.label == ''
        assert info.number == 0

    def test_auto_detect_semver(self) -> None:
        """Auto-detect semver scheme."""
        info = parse_prerelease('1.0.0-rc.1')
        assert info.scheme == 'semver'

    def test_auto_detect_pep440(self) -> None:
        """Auto-detect PEP 440 scheme."""
        info = parse_prerelease('1.0.0rc1')
        assert info.scheme == 'pep440'

    def test_invalid_version_raises(self) -> None:
        """Invalid version raises ReleaseKitError."""
        with pytest.raises(ReleaseKitError, match='Cannot parse version'):
            parse_prerelease('not-a-version')

    def test_base_version_property(self) -> None:
        """base_version strips pre-release suffix."""
        info = parse_prerelease('1.2.3-rc.5')
        assert info.base_version == '1.2.3'


# PrereleaseInfo.format


class TestPrereleaseInfoFormat:
    """Tests for PrereleaseInfo.format()."""

    def test_format_semver_rc(self) -> None:
        """Format semver RC version."""
        info = PrereleaseInfo(1, 2, 3, 'rc', 1, 'semver')
        assert info.format() == '1.2.3-rc.1'

    def test_format_pep440_rc(self) -> None:
        """Format PEP 440 RC version."""
        info = PrereleaseInfo(1, 2, 3, 'rc', 1, 'pep440')
        assert info.format() == '1.2.3rc1'

    def test_format_pep440_alpha(self) -> None:
        """Format PEP 440 alpha version."""
        info = PrereleaseInfo(1, 2, 3, 'alpha', 2, 'pep440')
        assert info.format() == '1.2.3a2'

    def test_format_pep440_beta(self) -> None:
        """Format PEP 440 beta version."""
        info = PrereleaseInfo(1, 2, 3, 'beta', 3, 'pep440')
        assert info.format() == '1.2.3b3'

    def test_format_pep440_dev(self) -> None:
        """Format PEP 440 dev version."""
        info = PrereleaseInfo(1, 2, 3, 'dev', 4, 'pep440')
        assert info.format() == '1.2.3.dev4'

    def test_format_stable(self) -> None:
        """Format stable version (no label)."""
        info = PrereleaseInfo(1, 2, 3)
        assert info.format() == '1.2.3'


# apply_prerelease


class TestApplyPrerelease:
    """Tests for apply_prerelease()."""

    def test_apply_rc_semver(self) -> None:
        """Apply RC label to semver base version."""
        assert apply_prerelease('1.2.0', 'rc', scheme='semver') == '1.2.0-rc.1'

    def test_apply_alpha_pep440(self) -> None:
        """Apply alpha label to PEP 440 base version."""
        assert apply_prerelease('1.2.0', 'alpha', scheme='pep440') == '1.2.0a1'

    def test_apply_beta_semver(self) -> None:
        """Apply beta label to semver base version."""
        assert apply_prerelease('2.0.0', 'beta', scheme='semver') == '2.0.0-beta.1'

    def test_apply_dev_pep440(self) -> None:
        """Apply dev label to PEP 440 base version."""
        assert apply_prerelease('1.0.0', 'dev', scheme='pep440') == '1.0.0.dev1'

    def test_apply_custom_number(self) -> None:
        """Apply with custom starting number."""
        assert apply_prerelease('1.0.0', 'rc', scheme='semver', number=5) == '1.0.0-rc.5'

    def test_apply_replaces_existing(self) -> None:
        """Applying to an existing pre-release replaces it."""
        assert apply_prerelease('1.0.0-alpha.3', 'rc', scheme='semver') == '1.0.0-rc.1'

    def test_invalid_label_raises(self) -> None:
        """Invalid label raises ReleaseKitError."""
        with pytest.raises(ReleaseKitError, match='Invalid pre-release label'):
            apply_prerelease('1.0.0', 'gamma')


# increment_prerelease


class TestIncrementPrerelease:
    """Tests for increment_prerelease()."""

    def test_increment_semver_rc(self) -> None:
        """Increment semver RC counter."""
        assert increment_prerelease('1.2.0-rc.1') == '1.2.0-rc.2'

    def test_increment_semver_alpha(self) -> None:
        """Increment semver alpha counter."""
        assert increment_prerelease('1.0.0-alpha.3') == '1.0.0-alpha.4'

    def test_increment_pep440_rc(self) -> None:
        """Increment PEP 440 RC counter."""
        assert increment_prerelease('1.2.0rc1') == '1.2.0rc2'

    def test_increment_pep440_beta(self) -> None:
        """Increment PEP 440 beta counter."""
        assert increment_prerelease('1.0.0b2') == '1.0.0b3'

    def test_increment_stable_raises(self) -> None:
        """Incrementing a stable version raises."""
        with pytest.raises(ReleaseKitError, match='not a pre-release'):
            increment_prerelease('1.0.0')


# promote_to_stable


class TestPromoteToStable:
    """Tests for promote_to_stable()."""

    def test_promote_semver_rc(self) -> None:
        """Promote semver RC to stable."""
        assert promote_to_stable('1.2.0-rc.3') == '1.2.0'

    def test_promote_pep440_rc(self) -> None:
        """Promote PEP 440 RC to stable."""
        assert promote_to_stable('1.2.0rc3') == '1.2.0'

    def test_promote_semver_alpha(self) -> None:
        """Promote semver alpha to stable."""
        assert promote_to_stable('2.0.0-alpha.1') == '2.0.0'

    def test_promote_stable_raises(self) -> None:
        """Promoting a stable version raises."""
        with pytest.raises(ReleaseKitError, match='already stable'):
            promote_to_stable('1.0.0')


# escalate_prerelease


class TestEscalatePrerelease:
    """Tests for escalate_prerelease()."""

    def test_alpha_to_beta(self) -> None:
        """Escalate alpha to beta."""
        assert escalate_prerelease('1.0.0-alpha.3', 'beta') == '1.0.0-beta.1'

    def test_beta_to_rc(self) -> None:
        """Escalate beta to RC."""
        assert escalate_prerelease('1.0.0-beta.2', 'rc') == '1.0.0-rc.1'

    def test_dev_to_alpha(self) -> None:
        """Escalate dev to alpha."""
        assert escalate_prerelease('1.0.0-dev.5', 'alpha') == '1.0.0-alpha.1'

    def test_pep440_alpha_to_rc(self) -> None:
        """Escalate PEP 440 alpha to RC."""
        assert escalate_prerelease('1.0.0a3', 'rc') == '1.0.0rc1'

    def test_downgrade_raises(self) -> None:
        """Downgrading raises ReleaseKitError."""
        with pytest.raises(ReleaseKitError, match='not a higher stage'):
            escalate_prerelease('1.0.0-rc.1', 'alpha')

    def test_same_label_raises(self) -> None:
        """Same label raises ReleaseKitError."""
        with pytest.raises(ReleaseKitError, match='not a higher stage'):
            escalate_prerelease('1.0.0-beta.1', 'beta')

    def test_stable_raises(self) -> None:
        """Escalating a stable version raises."""
        with pytest.raises(ReleaseKitError, match='stable'):
            escalate_prerelease('1.0.0', 'rc')


# is_prerelease


class TestIsPrerelease:
    """Tests for is_prerelease()."""

    def test_semver_rc_is_prerelease(self) -> None:
        """Semver RC is a pre-release."""
        assert is_prerelease('1.0.0-rc.1') is True

    def test_pep440_alpha_is_prerelease(self) -> None:
        """PEP 440 alpha is a pre-release."""
        assert is_prerelease('1.0.0a1') is True

    def test_stable_is_not_prerelease(self) -> None:
        """Stable version is not a pre-release."""
        assert is_prerelease('1.0.0') is False

    def test_invalid_returns_false(self) -> None:
        """Invalid version returns False (no exception)."""
        assert is_prerelease('not-a-version') is False


# prerelease_sort_key


class TestPrereleaseSortKey:
    """Tests for prerelease_sort_key()."""

    def test_sort_order(self) -> None:
        """Pre-releases sort before stable, in label order."""
        versions = [
            '1.0.0',
            '1.0.0-rc.1',
            '1.0.0-beta.1',
            '1.0.0-alpha.1',
            '1.0.0-dev.1',
        ]
        sorted_versions = sorted(versions, key=prerelease_sort_key)
        assert sorted_versions == [
            '1.0.0-dev.1',
            '1.0.0-alpha.1',
            '1.0.0-beta.1',
            '1.0.0-rc.1',
            '1.0.0',
        ]

    def test_same_label_sorts_by_number(self) -> None:
        """Same label sorts by counter number."""
        versions = ['1.0.0-rc.3', '1.0.0-rc.1', '1.0.0-rc.2']
        sorted_versions = sorted(versions, key=prerelease_sort_key)
        assert sorted_versions == ['1.0.0-rc.1', '1.0.0-rc.2', '1.0.0-rc.3']

    def test_different_base_versions(self) -> None:
        """Different base versions sort by major.minor.patch."""
        versions = ['2.0.0-rc.1', '1.0.0-rc.1', '1.1.0-rc.1']
        sorted_versions = sorted(versions, key=prerelease_sort_key)
        assert sorted_versions == ['1.0.0-rc.1', '1.1.0-rc.1', '2.0.0-rc.1']
