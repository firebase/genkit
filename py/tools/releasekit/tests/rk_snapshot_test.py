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

"""Tests for releasekit.snapshot — snapshot release version generation."""

from __future__ import annotations

from releasekit.logging import configure_logging
from releasekit.snapshot import (
    SnapshotConfig,
    apply_snapshot_versions,
    compute_snapshot_version,
)
from releasekit.versions import PackageVersion

configure_logging(quiet=True)


# ---------------------------------------------------------------------------
# compute_snapshot_version
# ---------------------------------------------------------------------------


class TestComputeSnapshotVersion:
    """Tests for compute_snapshot_version()."""

    def test_semver_with_sha(self) -> None:
        """Semver snapshot with git SHA identifier."""
        cfg = SnapshotConfig(identifier='abc1234')
        v = compute_snapshot_version(cfg, scheme='semver')
        assert v == '0.0.0-dev.abc1234'

    def test_semver_with_pr_number(self) -> None:
        """Semver snapshot with PR number."""
        cfg = SnapshotConfig(identifier='abc1234', pr_number='42')
        v = compute_snapshot_version(cfg, scheme='semver')
        assert v == '0.0.0-dev.pr-42.abc1234'

    def test_semver_custom_prefix(self) -> None:
        """Semver snapshot with custom prefix."""
        cfg = SnapshotConfig(prefix='snapshot', identifier='abc1234')
        v = compute_snapshot_version(cfg, scheme='semver')
        assert v == '0.0.0-snapshot.abc1234'

    def test_semver_custom_base_version(self) -> None:
        """Semver snapshot with custom base version."""
        cfg = SnapshotConfig(identifier='abc1234', base_version='1.0.0')
        v = compute_snapshot_version(cfg, scheme='semver')
        assert v == '1.0.0-dev.abc1234'

    def test_pep440_with_numeric_identifier(self) -> None:
        """PEP 440 snapshot with numeric identifier."""
        cfg = SnapshotConfig(identifier='20260215')
        v = compute_snapshot_version(cfg, scheme='pep440')
        assert v == '0.0.0.dev20260215'

    def test_pep440_non_numeric_uses_timestamp(self) -> None:
        """PEP 440 snapshot with non-numeric identifier falls back to timestamp."""
        cfg = SnapshotConfig(identifier='abc1234')
        v = compute_snapshot_version(cfg, scheme='pep440')
        assert v.startswith('0.0.0.dev')
        # Should be numeric after .dev
        dev_part = v.split('.dev')[1]
        assert dev_part.isdigit()

    def test_semver_no_identifier_no_timestamp(self) -> None:
        """Semver snapshot with no identifier defaults to 'snapshot'."""
        cfg = SnapshotConfig()
        v = compute_snapshot_version(cfg, scheme='semver')
        assert v == '0.0.0-dev.snapshot'

    def test_semver_timestamp_mode(self) -> None:
        """Semver snapshot with timestamp mode."""
        cfg = SnapshotConfig(timestamp=True)
        v = compute_snapshot_version(cfg, scheme='semver')
        assert v.startswith('0.0.0-dev.')
        # Timestamp format: YYYYMMDDTHHMM
        ts_part = v.split('dev.')[1]
        assert 'T' in ts_part


# ---------------------------------------------------------------------------
# apply_snapshot_versions
# ---------------------------------------------------------------------------


class TestApplySnapshotVersions:
    """Tests for apply_snapshot_versions()."""

    def test_replaces_bumped_versions(self) -> None:
        """Bumped packages get snapshot version."""
        versions = [
            PackageVersion(name='a', old_version='1.0.0', new_version='1.1.0', bump='minor'),
            PackageVersion(name='b', old_version='2.0.0', new_version='2.0.1', bump='patch'),
        ]
        result = apply_snapshot_versions(versions, '0.0.0-dev.abc1234')
        assert result[0].new_version == '0.0.0-dev.abc1234'
        assert result[0].bump == 'snapshot'
        assert result[1].new_version == '0.0.0-dev.abc1234'

    def test_skipped_packages_stay_skipped(self) -> None:
        """Skipped packages remain unchanged."""
        versions = [
            PackageVersion(name='a', old_version='1.0.0', new_version='1.0.0', skipped=True),
            PackageVersion(name='b', old_version='2.0.0', new_version='2.0.1', bump='patch'),
        ]
        result = apply_snapshot_versions(versions, '0.0.0-dev.abc1234')
        assert result[0].skipped is True
        assert result[0].new_version == '1.0.0'
        assert result[1].new_version == '0.0.0-dev.abc1234'

    def test_snapshot_tags_are_empty(self) -> None:
        """Snapshot versions don't get git tags."""
        versions = [
            PackageVersion(name='a', old_version='1.0.0', new_version='1.1.0', bump='minor', tag='a-v1.1.0'),
        ]
        result = apply_snapshot_versions(versions, '0.0.0-dev.abc1234')
        assert result[0].tag == ''

    def test_empty_list(self) -> None:
        """Empty version list returns empty."""
        result = apply_snapshot_versions([], '0.0.0-dev.abc1234')
        assert result == []
