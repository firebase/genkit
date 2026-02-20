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

"""String parsing utilities.

Pure functions for parsing configuration strings used across the
application. No I/O, no state, no framework dependencies — easy to
test in isolation.

- :func:`parse_rate` — Rate strings like ``"60/minute"`` →
  ``(capacity, period_seconds)``.
- :func:`split_comma_list` — Comma-separated strings →
  ``["a", "b", "c"]`` with whitespace trimming.
"""

from __future__ import annotations

PERIOD_MAP: dict[str, int] = {
    "second": 1,
    "minute": 60,
    "hour": 3600,
    "day": 86400,
}
"""Period name → seconds mapping for rate string parsing."""


def parse_rate(rate_str: str) -> tuple[int, int]:
    """Parse a rate string like ``60/minute`` into ``(capacity, period_seconds)``.

    Args:
        rate_str: Rate in ``<count>/<period>`` format. Supported periods:
            ``second``, ``minute``, ``hour``, ``day``.

    Returns:
        Tuple of (capacity, period_in_seconds).

    Raises:
        ValueError: If the format is invalid.

    Examples::

        >>> parse_rate('60/minute')
        (60, 60)
        >>> parse_rate('1000/hour')
        (1000, 3600)
        >>> parse_rate('10/second')
        (10, 1)
    """
    try:
        count_str, period_name = rate_str.strip().split("/", 1)
        count = int(count_str)
        period = PERIOD_MAP[period_name.strip().lower()]
    except (ValueError, KeyError) as exc:
        msg = f"Invalid rate format: '{rate_str}'. Expected '<count>/<period>' (e.g. '60/minute')."
        raise ValueError(msg) from exc
    return count, period


def split_comma_list(value: str) -> list[str]:
    """Split a comma-separated string into a list of trimmed, non-empty values.

    Useful for parsing environment variables like ``CORS_ALLOWED_ORIGINS``
    and ``TRUSTED_HOSTS``.

    Args:
        value: Comma-separated string (e.g. ``"a, b, c"``).

    Returns:
        List of stripped non-empty strings.

    Examples::

        >>> split_comma_list('a, b, c')
        ['a', 'b', 'c']
        >>> split_comma_list('  ')
        []
        >>> split_comma_list('*')
        ['*']
        >>> split_comma_list('')
        []
    """
    return [item.strip() for item in value.split(",") if item.strip()]
