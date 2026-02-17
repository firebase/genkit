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

"""Tests for releasekit.calver — calendar versioning."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from releasekit.calver import compute_calver
from releasekit.logging import configure_logging

configure_logging(quiet=True)


def _utc(year: int, month: int, day: int) -> datetime:
    """Utc."""
    return datetime(year, month, day, 12, 0, tzinfo=timezone.utc)


# YYYY.MM.DD format


class TestDateFormat:
    """Tests for YYYY.MM.DD calver format."""

    def test_first_release(self) -> None:
        """First release uses date only."""
        assert compute_calver('YYYY.MM.DD', now=_utc(2026, 1, 15)) == '2026.1.15'

    def test_same_day_increments_micro(self) -> None:
        """Same-day release appends .1 micro suffix."""
        result = compute_calver(
            'YYYY.MM.DD',
            current_version='2026.1.15',
            now=_utc(2026, 1, 15),
        )
        assert result == '2026.1.15.1'

    def test_same_day_second_increment(self) -> None:
        """Second same-day release increments micro to .2."""
        result = compute_calver(
            'YYYY.MM.DD',
            current_version='2026.1.15.1',
            now=_utc(2026, 1, 15),
        )
        assert result == '2026.1.15.2'

    def test_new_day_resets(self) -> None:
        """New day drops micro suffix."""
        result = compute_calver(
            'YYYY.MM.DD',
            current_version='2026.1.15.3',
            now=_utc(2026, 1, 16),
        )
        assert result == '2026.1.16'

    def test_new_month(self) -> None:
        """New month resets day."""
        result = compute_calver(
            'YYYY.MM.DD',
            current_version='2026.1.31',
            now=_utc(2026, 2, 1),
        )
        assert result == '2026.2.1'

    def test_new_year(self) -> None:
        """New year resets month and day."""
        result = compute_calver(
            'YYYY.MM.DD',
            current_version='2025.12.31',
            now=_utc(2026, 1, 1),
        )
        assert result == '2026.1.1'

    def test_empty_current_version(self) -> None:
        """Empty current version produces base date."""
        assert compute_calver('YYYY.MM.DD', current_version='', now=_utc(2026, 3, 5)) == '2026.3.5'

    def test_invalid_current_version(self) -> None:
        """Invalid current version falls back to base date."""
        assert compute_calver('YYYY.MM.DD', current_version='not-a-version', now=_utc(2026, 3, 5)) == '2026.3.5'


# YYYY.MM.MICRO format


class TestMicroFormat:
    """Tests for YYYY.MM.MICRO calver format."""

    def test_first_release(self) -> None:
        """First release starts at micro 0."""
        assert compute_calver('YYYY.MM.MICRO', now=_utc(2026, 1, 15)) == '2026.1.0'

    def test_same_month_increments(self) -> None:
        """Same month increments micro."""
        result = compute_calver(
            'YYYY.MM.MICRO',
            current_version='2026.1.3',
            now=_utc(2026, 1, 20),
        )
        assert result == '2026.1.4'

    def test_new_month_resets(self) -> None:
        """New month resets micro to 0."""
        result = compute_calver(
            'YYYY.MM.MICRO',
            current_version='2026.1.7',
            now=_utc(2026, 2, 1),
        )
        assert result == '2026.2.0'

    def test_new_year_resets(self) -> None:
        """New year resets month and micro."""
        result = compute_calver(
            'YYYY.MM.MICRO',
            current_version='2025.12.5',
            now=_utc(2026, 1, 1),
        )
        assert result == '2026.1.0'

    def test_empty_current_version(self) -> None:
        """Empty current version starts at micro 0."""
        assert compute_calver('YYYY.MM.MICRO', current_version='', now=_utc(2026, 6, 1)) == '2026.6.0'

    def test_invalid_current_version(self) -> None:
        """Invalid current version falls back to micro 0."""
        assert compute_calver('YYYY.MM.MICRO', current_version='bad', now=_utc(2026, 6, 1)) == '2026.6.0'


# Invalid format


class TestInvalidFormat:
    """Tests for unknown calver format."""

    def test_unknown_format_raises(self) -> None:
        """Unknown format raises ValueError."""
        with pytest.raises(ValueError, match='Unknown calver format'):
            compute_calver('YYYY.WW.MICRO', now=_utc(2026, 1, 1))
