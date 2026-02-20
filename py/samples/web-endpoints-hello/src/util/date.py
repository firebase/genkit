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

"""Date and time formatting utilities.

Provides deterministic, timezone-aware date/time formatting used by
Genkit tools and logging. All functions return strings — no datetime
objects leak across module boundaries.

These are intentionally simple wrappers so that:

1. The format string is defined in exactly one place.
2. Tests can freeze time and assert exact output.
3. Flows and tools import a named function instead of inlining
   ``datetime.now(tz=timezone.utc).strftime(...)``.
"""

from __future__ import annotations

from datetime import datetime, timezone

UTC_FORMAT = "%Y-%m-%d %H:%M UTC"
"""Default format string for UTC timestamps shown to users."""

ISO_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
"""ISO 8601 format with timezone offset for machine-readable timestamps."""


def utc_now_str(fmt: str = UTC_FORMAT) -> str:
    """Return the current UTC time as a formatted string.

    Args:
        fmt: ``strftime`` format string. Defaults to
            ``'%Y-%m-%d %H:%M UTC'`` (e.g. ``2026-02-07 22:15 UTC``).

    Returns:
        Formatted UTC timestamp string.
    """
    return datetime.now(tz=timezone.utc).strftime(fmt)


def format_utc(dt: datetime, fmt: str = UTC_FORMAT) -> str:
    """Format a datetime as a UTC string.

    If ``dt`` is naive (no tzinfo), it is assumed to be UTC.
    If ``dt`` has a timezone, it is converted to UTC first.

    Args:
        dt: The datetime to format.
        fmt: ``strftime`` format string.

    Returns:
        Formatted UTC timestamp string.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime(fmt)
