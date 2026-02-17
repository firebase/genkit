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

"""Tests for releasekit.schemas_ai."""

from __future__ import annotations

import json

import pytest
from releasekit.schemas_ai import ReleaseStats, ReleaseSummary


class TestReleaseStats:
    """Tests for the ReleaseStats Pydantic model."""

    def test_defaults(self) -> None:
        """Test defaults."""
        stats = ReleaseStats()
        assert stats.commit_count == 0
        assert stats.packages_changed == 0
        assert stats.files_changed == 0
        assert stats.days_since_last_release == 0

    def test_custom_values(self) -> None:
        """Test custom values."""
        stats = ReleaseStats(
            commit_count=42,
            packages_changed=23,
            files_changed=150,
            days_since_last_release=14,
        )
        assert stats.commit_count == 42
        assert stats.packages_changed == 23

    def test_non_negative_constraint(self) -> None:
        """Test non negative constraint."""
        with pytest.raises(Exception):  # noqa: B017
            ReleaseStats(commit_count=-1)  # pyrefly: ignore[bad-argument-type]

    def test_json_roundtrip(self) -> None:
        """Test json roundtrip."""
        stats = ReleaseStats(commit_count=10, packages_changed=5)
        data = json.loads(stats.model_dump_json())
        restored = ReleaseStats.model_validate(data)
        assert restored == stats


class TestReleaseSummary:
    """Tests for the ReleaseSummary Pydantic model."""

    def test_defaults(self) -> None:
        """Test defaults."""
        summary = ReleaseSummary()
        assert summary.overview == ''
        assert summary.highlights == []
        assert summary.breaking_changes == []
        assert summary.new_plugins == []
        assert summary.deprecations == []
        assert summary.security_fixes == []
        assert summary.package_summaries == {}
        assert summary.contributors == []
        assert isinstance(summary.stats, ReleaseStats)

    def test_full_summary(self) -> None:
        """Test full summary."""
        summary = ReleaseSummary(
            overview='Major release with new plugins.',
            highlights=['New Cloudflare plugin', 'Faster streaming'],
            breaking_changes=['Removed legacy_format param'],
            new_plugins=['genkit-plugin-cloudflare'],
            deprecations=['old_api() is deprecated'],
            security_fixes=['Fixed XSS in template rendering'],
            package_summaries={'genkit': 'Core improvements', 'genkit-plugin-ollama': 'Bug fixes'},
            contributors=['@user1', '@user2'],
            stats=ReleaseStats(commit_count=42, packages_changed=5),
        )
        assert len(summary.highlights) == 2
        assert summary.stats.commit_count == 42

    def test_json_roundtrip(self) -> None:
        """Test json roundtrip."""
        summary = ReleaseSummary(
            overview='Test release.',
            highlights=['Feature A'],
            package_summaries={'pkg-a': 'Updated'},
        )
        data = json.loads(summary.model_dump_json())
        restored = ReleaseSummary.model_validate(data)
        assert restored == summary

    def test_json_schema_export(self) -> None:
        """Test json schema export."""
        schema = ReleaseSummary.model_json_schema()
        assert 'properties' in schema
        assert 'overview' in schema['properties']
        assert 'highlights' in schema['properties']
        assert 'stats' in schema['properties']

    def test_partial_output_valid(self) -> None:
        """Models may only fill some fields — partial output must be valid."""
        data = {'overview': 'Quick fix release.'}
        summary = ReleaseSummary.model_validate(data)
        assert summary.overview == 'Quick fix release.'
        assert summary.highlights == []
