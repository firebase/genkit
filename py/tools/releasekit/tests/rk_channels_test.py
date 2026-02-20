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

"""Tests for releasekit.channels — branch-to-channel mapping."""

from __future__ import annotations

from releasekit.channels import channel_to_dist_tag, channel_to_prerelease, resolve_channel
from releasekit.logging import configure_logging

configure_logging(quiet=True)


# resolve_channel


class TestResolveChannel:
    """Tests for resolve_channel()."""

    def test_exact_match(self) -> None:
        """Exact branch name matches."""
        branches = {'main': 'latest', 'next': 'next', 'beta': 'beta'}
        assert resolve_channel('main', branches) == 'latest'
        assert resolve_channel('next', branches) == 'next'
        assert resolve_channel('beta', branches) == 'beta'

    def test_glob_match(self) -> None:
        """Glob pattern matches branch."""
        branches = {'release/v1.*': 'v1-maintenance', 'main': 'latest'}
        assert resolve_channel('release/v1.5', branches) == 'v1-maintenance'
        assert resolve_channel('release/v1.0', branches) == 'v1-maintenance'

    def test_glob_no_match(self) -> None:
        """Glob pattern does not match different version."""
        branches = {'release/v1.*': 'v1-maintenance'}
        assert resolve_channel('release/v2.0', branches) == 'latest'

    def test_exact_takes_precedence_over_glob(self) -> None:
        """Exact match wins over glob."""
        branches = {'next': 'next', 'n*': 'nightly'}
        assert resolve_channel('next', branches) == 'next'

    def test_default_when_no_match(self) -> None:
        """Unmatched branch returns default."""
        branches = {'main': 'latest'}
        assert resolve_channel('feature/foo', branches) == 'latest'

    def test_custom_default(self) -> None:
        """Custom default is returned for unmatched branch."""
        branches = {'main': 'latest'}
        assert resolve_channel('feature/foo', branches, default='dev') == 'dev'

    def test_empty_branches(self) -> None:
        """Empty branches mapping returns default."""
        assert resolve_channel('main', {}) == 'latest'

    def test_empty_branches_custom_default(self) -> None:
        """Empty branches with custom default."""
        assert resolve_channel('main', {}, default='stable') == 'stable'


# channel_to_dist_tag


class TestChannelToDistTag:
    """Tests for channel_to_dist_tag()."""

    def test_latest_returns_none(self) -> None:
        """Latest channel means no dist-tag override."""
        assert channel_to_dist_tag('latest') is None

    def test_next_returns_next(self) -> None:
        """Next channel maps to next dist-tag."""
        assert channel_to_dist_tag('next') == 'next'

    def test_beta_returns_beta(self) -> None:
        """Beta channel maps to beta dist-tag."""
        assert channel_to_dist_tag('beta') == 'beta'

    def test_custom_channel(self) -> None:
        """Custom channel name used as dist-tag."""
        assert channel_to_dist_tag('v1-maintenance') == 'v1-maintenance'


# channel_to_prerelease


class TestChannelToPrerelease:
    """Tests for channel_to_prerelease()."""

    def test_latest_returns_empty(self) -> None:
        """Latest channel means stable (no prerelease)."""
        assert channel_to_prerelease('latest') == ''

    def test_next_returns_next(self) -> None:
        """Next channel maps to next prerelease label."""
        assert channel_to_prerelease('next') == 'next'

    def test_beta_returns_beta(self) -> None:
        """Beta channel maps to beta prerelease label."""
        assert channel_to_prerelease('beta') == 'beta'
