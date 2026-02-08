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

"""Tests for src.util.parse — string parsing utilities.

Run with::

    cd py/samples/web-endpoints-hello
    uv run pytest tests/util/parse_test.py -v
"""

import pytest

from src.util.parse import PERIOD_MAP, parse_rate, split_comma_list


class TestParseRate:
    """Tests for `parse_rate`."""

    def test_per_minute(self) -> None:
        """Verify per-minute rate is parsed correctly."""
        assert parse_rate("60/minute") == (60, 60)

    def test_per_second(self) -> None:
        """Verify per-second rate is parsed correctly."""
        assert parse_rate("10/second") == (10, 1)

    def test_per_hour(self) -> None:
        """Verify per-hour rate is parsed correctly."""
        assert parse_rate("1000/hour") == (1000, 3600)

    def test_per_day(self) -> None:
        """Verify per-day rate is parsed correctly."""
        assert parse_rate("5000/day") == (5000, 86400)

    def test_with_whitespace(self) -> None:
        """Verify surrounding whitespace is stripped."""
        assert parse_rate("  100 / minute  ") == (100, 60)

    def test_invalid_format(self) -> None:
        """Verify ValueError for invalid format string."""
        with pytest.raises(ValueError, match="Invalid rate format"):
            parse_rate("not-a-rate")

    def test_invalid_period(self) -> None:
        """Verify ValueError for unknown period name."""
        with pytest.raises(ValueError, match="Invalid rate format"):
            parse_rate("10/fortnight")

    def test_invalid_count(self) -> None:
        """Verify ValueError for non-numeric count."""
        with pytest.raises(ValueError, match="Invalid rate format"):
            parse_rate("abc/minute")

    def test_zero_count(self) -> None:
        """Verify zero count is accepted."""
        assert parse_rate("0/minute") == (0, 60)

    def test_large_count(self) -> None:
        """Verify large numeric count is accepted."""
        assert parse_rate("999999/second") == (999999, 1)

    def test_case_insensitive_period(self) -> None:
        """Verify period name matching is case-insensitive."""
        assert parse_rate("10/MINUTE") == (10, 60)
        assert parse_rate("10/Minute") == (10, 60)

    def test_empty_string_raises(self) -> None:
        """Verify ValueError for empty input."""
        with pytest.raises(ValueError):
            parse_rate("")


class TestSplitCommaList:
    """Tests for `split_comma_list`."""

    def test_basic_split(self) -> None:
        """Verify basic comma splitting."""
        assert split_comma_list("a,b,c") == ["a", "b", "c"]

    def test_with_whitespace(self) -> None:
        """Verify whitespace around items is stripped."""
        assert split_comma_list("a , b , c") == ["a", "b", "c"]

    def test_empty_string(self) -> None:
        """Verify empty string returns empty list."""
        assert split_comma_list("") == []

    def test_whitespace_only(self) -> None:
        """Verify whitespace-only string returns empty list."""
        assert split_comma_list("   ") == []

    def test_single_value(self) -> None:
        """Verify single value is returned as one-element list."""
        assert split_comma_list("*") == ["*"]

    def test_wildcard_origin(self) -> None:
        """Verify wildcard origin is returned as one-element list."""
        assert split_comma_list("*") == ["*"]

    def test_urls(self) -> None:
        """Verify URLs are split correctly."""
        result = split_comma_list("https://a.com, https://b.com")
        assert result == ["https://a.com", "https://b.com"]

    def test_trailing_comma(self) -> None:
        """Verify trailing comma does not produce empty element."""
        assert split_comma_list("a,b,") == ["a", "b"]

    def test_leading_comma(self) -> None:
        """Verify leading comma does not produce empty element."""
        assert split_comma_list(",a,b") == ["a", "b"]

    def test_multiple_empty_segments(self) -> None:
        """Verify consecutive commas are collapsed."""
        assert split_comma_list("a,,b,,,c") == ["a", "b", "c"]

    def test_preserves_internal_spaces(self) -> None:
        """Verify internal spaces within items are preserved."""
        result = split_comma_list("hello world, foo bar")
        assert result == ["hello world", "foo bar"]


class TestPeriodMap:
    """Tests for `PERIOD_MAP`."""

    def test_contains_expected_periods(self) -> None:
        """Verify all expected period names exist."""
        assert "second" in PERIOD_MAP
        assert "minute" in PERIOD_MAP
        assert "hour" in PERIOD_MAP
        assert "day" in PERIOD_MAP

    def test_values_are_seconds(self) -> None:
        """Verify period values are correct in seconds."""
        assert PERIOD_MAP["second"] == 1
        assert PERIOD_MAP["minute"] == 60
        assert PERIOD_MAP["hour"] == 3600
        assert PERIOD_MAP["day"] == 86400
