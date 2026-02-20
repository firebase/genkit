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

"""Tests for src.util.date — date/time formatting utilities.

Run with::

    cd py/samples/web-endpoints-hello
    uv run pytest tests/util/date_test.py -v
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from src.util.date import ISO_FORMAT, UTC_FORMAT, format_utc, utc_now_str


class TestUtcNowStr:
    """Tests for `utc_now_str`."""

    def test_returns_string(self) -> None:
        """Verify the return value is a string."""
        result = utc_now_str()
        assert isinstance(result, str)

    def test_default_format_contains_utc(self) -> None:
        """Verify the default format ends with UTC."""
        result = utc_now_str()
        assert result.endswith("UTC")

    def test_default_format_matches_pattern(self) -> None:
        """Verify the default format matches ``YYYY-MM-DD HH:MM UTC``."""
        result = utc_now_str()
        # e.g. "2026-02-07 22:15 UTC"
        parts = result.split()
        assert len(parts) == 3
        assert len(parts[0]) == 10  # YYYY-MM-DD
        assert len(parts[1]) == 5  # HH:MM
        assert parts[2] == "UTC"

    def test_custom_format(self) -> None:
        """Verify a custom format string is respected."""
        result = utc_now_str(fmt="%Y")
        assert len(result) == 4
        assert result.isdigit()

    def test_frozen_time(self) -> None:
        """Verify output matches a frozen datetime."""
        frozen = datetime(2025, 6, 15, 10, 30, tzinfo=timezone.utc)
        with patch("src.util.date.datetime") as mock_dt:
            mock_dt.now.return_value = frozen
            mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)
            result = utc_now_str()
        assert result == "2025-06-15 10:30 UTC"

    def test_utc_format_constant(self) -> None:
        """Verify UTC_FORMAT contains expected directives."""
        assert "%Y" in UTC_FORMAT
        assert "%M" in UTC_FORMAT

    def test_iso_format_constant(self) -> None:
        """Verify ISO_FORMAT contains expected directives."""
        assert "%Y" in ISO_FORMAT
        assert "%z" in ISO_FORMAT


class TestFormatUtc:
    """Tests for `format_utc`."""

    def test_naive_datetime_assumed_utc(self) -> None:
        """Verify a naive datetime is treated as UTC."""
        dt = datetime(2025, 1, 1, 12, 0, 0)
        result = format_utc(dt)
        assert result == "2025-01-01 12:00 UTC"

    def test_utc_datetime(self) -> None:
        """Verify a UTC-aware datetime formats correctly."""
        dt = datetime(2025, 3, 15, 8, 45, tzinfo=timezone.utc)
        result = format_utc(dt)
        assert result == "2025-03-15 08:45 UTC"

    def test_non_utc_timezone_is_converted(self) -> None:
        """Verify a non-UTC datetime is converted to UTC."""
        est = timezone(timedelta(hours=-5))
        dt = datetime(2025, 1, 1, 12, 0, 0, tzinfo=est)
        result = format_utc(dt)
        # 12:00 EST = 17:00 UTC
        assert result == "2025-01-01 17:00 UTC"

    def test_custom_format(self) -> None:
        """Verify a custom format string is applied."""
        dt = datetime(2025, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
        result = format_utc(dt, fmt="%Y-%m-%d")
        assert result == "2025-06-01"

    def test_midnight(self) -> None:
        """Verify midnight formats as 00:00."""
        dt = datetime(2025, 12, 31, 0, 0, 0, tzinfo=timezone.utc)
        result = format_utc(dt)
        assert result == "2025-12-31 00:00 UTC"
