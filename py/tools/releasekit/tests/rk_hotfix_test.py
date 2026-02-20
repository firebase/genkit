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

"""Tests for releasekit.hotfix — hotfix and maintenance branch support."""

from __future__ import annotations

from releasekit.config import WorkspaceConfig
from releasekit.hotfix import (
    CherryPickResult,
    HotfixContext,
    resolve_base_branch,
)
from releasekit.logging import configure_logging

configure_logging(quiet=True)


# resolve_base_branch


class TestResolveBaseBranch:
    """Tests for resolve_base_branch()."""

    def test_cli_override_wins(self) -> None:
        """CLI --base-branch overrides everything."""
        ws = WorkspaceConfig(publish_branch='release/1.x')
        result = resolve_base_branch(ws, cli_override='hotfix/1.2.3')
        assert result == 'hotfix/1.2.3'

    def test_config_publish_branch(self) -> None:
        """Config publish_branch is used when no CLI override."""
        ws = WorkspaceConfig(publish_branch='release/1.x')
        result = resolve_base_branch(ws)
        assert result == 'release/1.x'

    def test_default_branch_fallback(self) -> None:
        """Default branch is used when nothing else is set."""
        ws = WorkspaceConfig()
        result = resolve_base_branch(ws, default_branch='main')
        assert result == 'main'

    def test_custom_default_branch(self) -> None:
        """Custom default branch name."""
        ws = WorkspaceConfig()
        result = resolve_base_branch(ws, default_branch='develop')
        assert result == 'develop'


# CherryPickResult


class TestCherryPickResult:
    """Tests for CherryPickResult dataclass."""

    def test_ok_when_no_failures(self) -> None:
        """Result is ok when no failures."""
        result = CherryPickResult(applied=['abc123'])
        assert result.ok is True

    def test_not_ok_when_failures(self) -> None:
        """Result is not ok when there are failures."""
        result = CherryPickResult(failed={'abc123': 'conflict'})
        assert result.ok is False

    def test_summary_applied_only(self) -> None:
        """Summary shows applied count."""
        result = CherryPickResult(applied=['a', 'b'])
        assert '2 applied' in result.summary()

    def test_summary_with_failures(self) -> None:
        """Summary shows failure count."""
        result = CherryPickResult(applied=['a'], failed={'b': 'err'})
        assert '1 applied' in result.summary()
        assert '1 failed' in result.summary()

    def test_summary_with_skipped(self) -> None:
        """Summary shows skipped count."""
        result = CherryPickResult(applied=['a'], skipped=['b'])
        assert '1 skipped' in result.summary()

    def test_summary_dry_run(self) -> None:
        """Summary shows dry-run indicator."""
        result = CherryPickResult(applied=['a'], dry_run=True)
        assert 'dry-run' in result.summary()


# HotfixContext


class TestHotfixContext:
    """Tests for HotfixContext dataclass."""

    def test_maintenance_branch(self) -> None:
        """Maintenance branch context."""
        ctx = HotfixContext(base_branch='release/1.x', since_tag='v1.2.0', is_maintenance=True)
        assert ctx.is_maintenance is True
        assert ctx.base_branch == 'release/1.x'
        assert ctx.since_tag == 'v1.2.0'

    def test_default_branch(self) -> None:
        """Default branch context."""
        ctx = HotfixContext(base_branch='main')
        assert ctx.is_maintenance is False
        assert ctx.since_tag == ''
