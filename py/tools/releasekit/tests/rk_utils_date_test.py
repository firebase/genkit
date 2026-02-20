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

"""Tests for releasekit.utils.date — UTC date/time helpers."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from unittest.mock import patch

from releasekit.utils.date import utc_iso, utc_now, utc_today


class TestUtcNow:
    """Tests for utc_now()."""

    def test_returns_datetime(self) -> None:
        """Returns a datetime instance."""
        result = utc_now()
        assert isinstance(result, datetime)

    def test_timezone_aware(self) -> None:
        """Returned datetime is timezone-aware (UTC)."""
        result = utc_now()
        assert result.tzinfo is not None
        assert result.tzinfo == timezone.utc

    def test_is_utc(self) -> None:
        """Returned datetime uses UTC timezone."""
        result = utc_now()
        assert result.utcoffset() is not None
        assert result.utcoffset().total_seconds() == 0  # type: ignore[union-attr]

    def test_deterministic_with_mock(self) -> None:
        """Returns the mocked time when datetime.now is patched."""
        fixed = datetime(2026, 3, 15, 12, 30, 45, tzinfo=timezone.utc)
        with patch('releasekit.utils.date.datetime') as mock_dt:
            mock_dt.now.return_value = fixed
            result = utc_now()
        assert result == fixed
        mock_dt.now.assert_called_once_with(tz=timezone.utc)


class TestUtcToday:
    """Tests for utc_today()."""

    def test_returns_string(self) -> None:
        """Returns a string."""
        result = utc_today()
        assert isinstance(result, str)

    def test_format_yyyy_mm_dd(self) -> None:
        """Returns date in YYYY-MM-DD format."""
        result = utc_today()
        assert re.fullmatch(r'\d{4}-\d{2}-\d{2}', result), f'Unexpected format: {result}'

    def test_deterministic_with_mock(self) -> None:
        """Returns the expected date string for a fixed time."""
        fixed = datetime(2026, 1, 5, 23, 59, 59, tzinfo=timezone.utc)
        with patch('releasekit.utils.date.datetime') as mock_dt:
            mock_dt.now.return_value = fixed
            result = utc_today()
        assert result == '2026-01-05'

    def test_zero_padded(self) -> None:
        """Month and day are zero-padded."""
        fixed = datetime(2026, 2, 3, 0, 0, 0, tzinfo=timezone.utc)
        with patch('releasekit.utils.date.datetime') as mock_dt:
            mock_dt.now.return_value = fixed
            result = utc_today()
        assert result == '2026-02-03'


class TestUtcIso:
    """Tests for utc_iso()."""

    def test_returns_string(self) -> None:
        """Returns a string."""
        result = utc_iso()
        assert isinstance(result, str)

    def test_iso_8601_parseable(self) -> None:
        """Returned string is parseable as ISO 8601."""
        result = utc_iso()
        parsed = datetime.fromisoformat(result)
        assert parsed.tzinfo is not None

    def test_contains_t_separator(self) -> None:
        """ISO string contains the T separator between date and time."""
        result = utc_iso()
        assert 'T' in result

    def test_deterministic_with_mock(self) -> None:
        """Returns the expected ISO string for a fixed time."""
        fixed = datetime(2026, 7, 4, 14, 30, 0, tzinfo=timezone.utc)
        with patch('releasekit.utils.date.datetime') as mock_dt:
            mock_dt.now.return_value = fixed
            result = utc_iso()
        assert result == '2026-07-04T14:30:00+00:00'
