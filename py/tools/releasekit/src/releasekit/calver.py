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

"""Calendar-based versioning (CalVer) for releasekit.

Supports two formats:

- ``YYYY.MM.DD`` — Date-based, one release per day. If a second
  release happens on the same day, a micro suffix is appended
  (e.g. ``2026.01.15.1``).
- ``YYYY.MM.MICRO`` — Year-month with an auto-incrementing micro
  counter (e.g. ``2026.1.0``, ``2026.1.1``, ``2026.2.0``).

Usage::

    from releasekit.calver import compute_calver

    version = compute_calver(
        fmt='YYYY.MM.MICRO',
        current_version='2026.1.3',
    )
    # => '2026.1.4' (same month) or '2026.2.0' (new month)
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from releasekit.logging import get_logger

log = get_logger('releasekit.calver')

# Regex to parse YYYY.MM.DD[.micro] versions.
_DATE_RE = re.compile(r'^(\d{4})\.(\d{1,2})\.(\d{1,2})(?:\.(\d+))?$')

# Regex to parse YYYY.MM.MICRO versions.
_MICRO_RE = re.compile(r'^(\d{4})\.(\d{1,2})\.(\d+)$')


def compute_calver(
    fmt: str,
    *,
    current_version: str = '',
    now: datetime | None = None,
) -> str:
    """Compute the next calendar version.

    Args:
        fmt: CalVer format string: ``"YYYY.MM.DD"`` or
            ``"YYYY.MM.MICRO"``.
        current_version: The current version string. Used to determine
            whether to increment the micro counter or reset it.
        now: Current UTC time. Defaults to ``datetime.now(timezone.utc)``.

    Returns:
        The next version string.

    Raises:
        ValueError: If ``fmt`` is not a recognized CalVer format.
    """
    now = now or datetime.now(timezone.utc)

    if fmt == 'YYYY.MM.DD':
        return _compute_date_version(current_version, now)
    if fmt == 'YYYY.MM.MICRO':
        return _compute_micro_version(current_version, now)

    msg = f"Unknown calver format: '{fmt}'. Use 'YYYY.MM.DD' or 'YYYY.MM.MICRO'."
    raise ValueError(msg)


def _compute_date_version(current_version: str, now: datetime) -> str:
    """Compute YYYY.MM.DD version, appending .micro if same day."""
    year = now.year
    month = now.month
    day = now.day
    base = f'{year}.{month}.{day}'

    if not current_version:
        return base

    m = _DATE_RE.match(current_version)
    if not m:
        return base

    cur_year, cur_month, cur_day = int(m.group(1)), int(m.group(2)), int(m.group(3))
    cur_micro = int(m.group(4)) if m.group(4) else 0

    if cur_year == year and cur_month == month and cur_day == day:
        # Same day: increment micro suffix.
        return f'{base}.{cur_micro + 1}'

    return base


def _compute_micro_version(current_version: str, now: datetime) -> str:
    """Compute YYYY.MM.MICRO version."""
    year = now.year
    month = now.month

    if not current_version:
        return f'{year}.{month}.0'

    m = _MICRO_RE.match(current_version)
    if not m:
        return f'{year}.{month}.0'

    cur_year, cur_month, cur_micro = int(m.group(1)), int(m.group(2)), int(m.group(3))

    if cur_year == year and cur_month == month:
        # Same month: increment micro.
        return f'{year}.{month}.{cur_micro + 1}'

    # New month (or year): reset micro.
    return f'{year}.{month}.0'


__all__ = [
    'compute_calver',
]
