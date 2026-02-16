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

"""Release decision engine for ``releasekit should-release``.

Determines whether a release should happen based on four criteria:

1. **Releasable commits exist** — at least one conventional commit
   since the last release tag produces a non-NONE bump.
2. **Within release window** — current UTC time falls within the
   configured ``release_window`` (e.g. ``"14:00-16:00"``).
3. **Cooldown elapsed** — enough time has passed since the last
   release (``cooldown_minutes``).
4. **Minimum bump met** — the computed bump level meets or exceeds
   ``min_bump`` (e.g. skip if only ``chore:``/``docs:`` commits).

Designed for CI cron integration::

    releasekit should-release || exit 0
    releasekit publish --if-needed

Usage::

    from releasekit.should_release import should_release, ReleaseDecision

    decision = should_release(
        schedule=schedule_config,
        has_releasable_commits=True,
        max_bump_level='minor',
        last_release_time=datetime(2026, 1, 15, 14, 0),
        now=datetime(2026, 1, 15, 16, 30),
    )
    if decision.should:
        print('Release!')
    else:
        print(f'Skip: {decision.reason}')
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone

from releasekit.config import ScheduleConfig
from releasekit.logging import get_logger

log = get_logger('releasekit.should_release')

# Bump level ordering for min_bump comparison.
_BUMP_ORDER: dict[str, int] = {
    'patch': 1,
    'minor': 2,
    'major': 3,
}

# Day-of-week mapping for weekly cadence.
_WEEKDAY_MAP: dict[str, int] = {
    'monday': 0,
    'tuesday': 1,
    'wednesday': 2,
    'thursday': 3,
    'friday': 4,
}

# Regex to parse release_window format: "HH:MM-HH:MM"
_WINDOW_RE = re.compile(r'^(\d{2}):(\d{2})-(\d{2}):(\d{2})$')


@dataclass(frozen=True)
class ReleaseDecision:
    """Result of the should-release check.

    Attributes:
        should: Whether a release should proceed.
        reason: Human-readable explanation of the decision.
    """

    should: bool
    reason: str


def should_release(
    schedule: ScheduleConfig,
    *,
    has_releasable_commits: bool,
    max_bump_level: str = '',
    last_release_time: datetime | None = None,
    now: datetime | None = None,
) -> ReleaseDecision:
    """Determine whether a release should happen.

    Args:
        schedule: Schedule configuration from ``releasekit.toml``.
        has_releasable_commits: Whether any releasable commits exist
            since the last release tag.
        max_bump_level: The highest bump level among releasable commits
            (``"patch"``, ``"minor"``, ``"major"``, or ``""`` for none).
        last_release_time: UTC timestamp of the last release. ``None``
            means no previous release (always passes cooldown).
        now: Current UTC time. Defaults to ``datetime.now(timezone.utc)``.

    Returns:
        A :class:`ReleaseDecision` with the verdict and reason.
    """
    now = now or datetime.now(timezone.utc)

    # Check 1: Releasable commits.
    if not has_releasable_commits:
        return ReleaseDecision(
            should=False,
            reason='No releasable commits since last release.',
        )

    # Check 2: Minimum bump level.
    if schedule.min_bump and max_bump_level:
        required = _BUMP_ORDER.get(schedule.min_bump, 0)
        actual = _BUMP_ORDER.get(max_bump_level, 0)
        if actual < required:
            return ReleaseDecision(
                should=False,
                reason=(f"Bump level '{max_bump_level}' is below minimum '{schedule.min_bump}'."),
            )

    # Check 3: Cadence.
    cadence_ok = _check_cadence(schedule.cadence, now)
    if not cadence_ok.should:
        return cadence_ok

    # Check 4: Release window.
    if schedule.release_window:
        window_ok = _check_release_window(schedule.release_window, now)
        if not window_ok.should:
            return window_ok

    # Check 5: Cooldown.
    if schedule.cooldown_minutes > 0 and last_release_time is not None:
        cooldown_ok = _check_cooldown(
            schedule.cooldown_minutes,
            last_release_time,
            now,
        )
        if not cooldown_ok.should:
            return cooldown_ok

    log.info(
        'should_release',
        decision=True,
        bump=max_bump_level,
        cadence=schedule.cadence,
    )
    return ReleaseDecision(should=True, reason='All release criteria met.')


def _check_cadence(cadence: str, now: datetime) -> ReleaseDecision:
    """Check if the current time matches the cadence schedule."""
    if cadence == 'on-push':
        return ReleaseDecision(should=True, reason='Cadence is on-push.')

    if cadence == 'daily':
        return ReleaseDecision(should=True, reason='Cadence is daily.')

    if cadence.startswith('weekly:'):
        day_name = cadence.split(':', 1)[1]
        target_weekday = _WEEKDAY_MAP.get(day_name)
        if target_weekday is None:
            return ReleaseDecision(
                should=False,
                reason=f"Invalid weekly cadence day: '{day_name}'.",
            )
        if now.weekday() != target_weekday:
            return ReleaseDecision(
                should=False,
                reason=(f'Today is {_day_name(now.weekday())}, but cadence is weekly:{day_name}.'),
            )
        return ReleaseDecision(should=True, reason=f'Today is {day_name}.')

    if cadence == 'biweekly':
        # Biweekly: release on even ISO week numbers.
        iso_week = now.isocalendar()[1]
        if iso_week % 2 != 0:
            return ReleaseDecision(
                should=False,
                reason=f'ISO week {iso_week} is odd; biweekly releases on even weeks.',
            )
        return ReleaseDecision(
            should=True,
            reason=f'ISO week {iso_week} is even (biweekly).',
        )

    return ReleaseDecision(
        should=False,
        reason=f"Unknown cadence: '{cadence}'.",
    )


def _check_release_window(window: str, now: datetime) -> ReleaseDecision:
    """Check if the current UTC time is within the release window."""
    m = _WINDOW_RE.match(window)
    if not m:
        return ReleaseDecision(
            should=False,
            reason=f"Invalid release_window format: '{window}'.",
        )

    start_hour, start_min = int(m.group(1)), int(m.group(2))
    end_hour, end_min = int(m.group(3)), int(m.group(4))

    start_minutes = start_hour * 60 + start_min
    end_minutes = end_hour * 60 + end_min
    now_minutes = now.hour * 60 + now.minute

    if start_minutes <= end_minutes:
        # Normal window: e.g. 14:00-16:00
        in_window = start_minutes <= now_minutes <= end_minutes
    else:
        # Overnight window: e.g. 22:00-02:00
        in_window = now_minutes >= start_minutes or now_minutes <= end_minutes

    if not in_window:
        return ReleaseDecision(
            should=False,
            reason=(f'Current time {now.hour:02d}:{now.minute:02d} UTC is outside release window {window}.'),
        )

    return ReleaseDecision(
        should=True,
        reason=f'Within release window {window}.',
    )


def _check_cooldown(
    cooldown_minutes: int,
    last_release_time: datetime,
    now: datetime,
) -> ReleaseDecision:
    """Check if enough time has elapsed since the last release."""
    elapsed = now - last_release_time
    elapsed_minutes = elapsed.total_seconds() / 60

    if elapsed_minutes < cooldown_minutes:
        remaining = cooldown_minutes - elapsed_minutes
        return ReleaseDecision(
            should=False,
            reason=(
                f'Cooldown not elapsed: {elapsed_minutes:.0f}min since '
                f'last release, need {cooldown_minutes}min '
                f'({remaining:.0f}min remaining).'
            ),
        )

    return ReleaseDecision(
        should=True,
        reason=f'Cooldown elapsed ({elapsed_minutes:.0f}min >= {cooldown_minutes}min).',
    )


def _day_name(weekday: int) -> str:
    """Return the day name for a weekday number (0=Monday)."""
    names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    return names[weekday] if 0 <= weekday <= 6 else f'day-{weekday}'


__all__ = [
    'ReleaseDecision',
    'should_release',
]
