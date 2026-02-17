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

"""Tests for releasekit.should_release — release decision engine."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from releasekit.config import ScheduleConfig
from releasekit.logging import configure_logging
from releasekit.should_release import should_release

configure_logging(quiet=True)


def _utc(year: int, month: int, day: int, hour: int = 12, minute: int = 0) -> datetime:
    """Create a UTC datetime."""
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


# No releasable commits


class TestNoReleasableCommits:
    """should_release returns False when no releasable commits exist."""

    def test_no_commits(self) -> None:
        """No releasable commits means no release."""
        decision = should_release(
            ScheduleConfig(),
            has_releasable_commits=False,
            now=_utc(2026, 1, 15),
        )
        assert not decision.should
        assert 'No releasable commits' in decision.reason


# Minimum bump level


class TestMinBump:
    """should_release respects min_bump setting."""

    def test_patch_below_minor(self) -> None:
        """Patch bump is below min_bump=minor."""
        decision = should_release(
            ScheduleConfig(min_bump='minor'),
            has_releasable_commits=True,
            max_bump_level='patch',
            now=_utc(2026, 1, 15),
        )
        assert not decision.should
        assert 'below minimum' in decision.reason

    def test_minor_meets_minor(self) -> None:
        """Minor bump meets min_bump=minor."""
        decision = should_release(
            ScheduleConfig(min_bump='minor'),
            has_releasable_commits=True,
            max_bump_level='minor',
            now=_utc(2026, 1, 15),
        )
        assert decision.should

    def test_major_exceeds_minor(self) -> None:
        """Major bump exceeds min_bump=minor."""
        decision = should_release(
            ScheduleConfig(min_bump='minor'),
            has_releasable_commits=True,
            max_bump_level='major',
            now=_utc(2026, 1, 15),
        )
        assert decision.should

    def test_no_min_bump_allows_patch(self) -> None:
        """No min_bump allows any bump level."""
        decision = should_release(
            ScheduleConfig(),
            has_releasable_commits=True,
            max_bump_level='patch',
            now=_utc(2026, 1, 15),
        )
        assert decision.should


# Cadence


class TestCadence:
    """should_release respects cadence setting."""

    def test_on_push_always_releases(self) -> None:
        """on-push cadence always allows release."""
        decision = should_release(
            ScheduleConfig(cadence='on-push'),
            has_releasable_commits=True,
            now=_utc(2026, 1, 15),
        )
        assert decision.should

    def test_daily_always_releases(self) -> None:
        """Daily cadence always allows release."""
        decision = should_release(
            ScheduleConfig(cadence='daily'),
            has_releasable_commits=True,
            now=_utc(2026, 1, 15),
        )
        assert decision.should

    def test_weekly_correct_day(self) -> None:
        """weekly:monday allows release on Monday."""
        # 2026-01-19 is a Monday.
        decision = should_release(
            ScheduleConfig(cadence='weekly:monday'),
            has_releasable_commits=True,
            now=_utc(2026, 1, 19),
        )
        assert decision.should

    def test_weekly_wrong_day(self) -> None:
        """weekly:monday blocks release on Tuesday."""
        # 2026-01-20 is a Tuesday.
        decision = should_release(
            ScheduleConfig(cadence='weekly:monday'),
            has_releasable_commits=True,
            now=_utc(2026, 1, 20),
        )
        assert not decision.should
        assert 'tuesday' in decision.reason.lower()

    def test_biweekly_even_week(self) -> None:
        """Biweekly releases on even ISO weeks."""
        # Find a date in an even ISO week.
        dt = _utc(2026, 1, 5)  # ISO week 2 (even).
        decision = should_release(
            ScheduleConfig(cadence='biweekly'),
            has_releasable_commits=True,
            now=dt,
        )
        assert decision.should

    def test_biweekly_odd_week(self) -> None:
        """Biweekly blocks on odd ISO weeks."""
        # ISO week 1 is odd.
        dt = _utc(2026, 1, 1)
        decision = should_release(
            ScheduleConfig(cadence='biweekly'),
            has_releasable_commits=True,
            now=dt,
        )
        assert not decision.should
        assert 'odd' in decision.reason.lower()


# Release window


class TestReleaseWindow:
    """should_release respects release_window setting."""

    def test_within_window(self) -> None:
        """Time within window allows release."""
        decision = should_release(
            ScheduleConfig(release_window='14:00-16:00'),
            has_releasable_commits=True,
            now=_utc(2026, 1, 15, 15, 0),
        )
        assert decision.should

    def test_outside_window(self) -> None:
        """Time outside window blocks release."""
        decision = should_release(
            ScheduleConfig(release_window='14:00-16:00'),
            has_releasable_commits=True,
            now=_utc(2026, 1, 15, 10, 0),
        )
        assert not decision.should
        assert 'outside release window' in decision.reason

    def test_at_window_start(self) -> None:
        """Exact window start time is inclusive."""
        decision = should_release(
            ScheduleConfig(release_window='14:00-16:00'),
            has_releasable_commits=True,
            now=_utc(2026, 1, 15, 14, 0),
        )
        assert decision.should

    def test_at_window_end(self) -> None:
        """Exact window end time is inclusive."""
        decision = should_release(
            ScheduleConfig(release_window='14:00-16:00'),
            has_releasable_commits=True,
            now=_utc(2026, 1, 15, 16, 0),
        )
        assert decision.should

    def test_overnight_window_before_midnight(self) -> None:
        """Overnight window works before midnight."""
        decision = should_release(
            ScheduleConfig(release_window='22:00-02:00'),
            has_releasable_commits=True,
            now=_utc(2026, 1, 15, 23, 0),
        )
        assert decision.should

    def test_overnight_window_after_midnight(self) -> None:
        """Overnight window works after midnight."""
        decision = should_release(
            ScheduleConfig(release_window='22:00-02:00'),
            has_releasable_commits=True,
            now=_utc(2026, 1, 16, 1, 0),
        )
        assert decision.should

    def test_no_window_always_passes(self) -> None:
        """No release_window means any time is OK."""
        decision = should_release(
            ScheduleConfig(),
            has_releasable_commits=True,
            now=_utc(2026, 1, 15, 3, 0),
        )
        assert decision.should


# Cooldown


class TestCooldown:
    """should_release respects cooldown_minutes setting."""

    def test_cooldown_not_elapsed(self) -> None:
        """Release blocked when cooldown has not elapsed."""
        now = _utc(2026, 1, 15, 14, 30)
        last = now - timedelta(minutes=30)
        decision = should_release(
            ScheduleConfig(cooldown_minutes=120),
            has_releasable_commits=True,
            last_release_time=last,
            now=now,
        )
        assert not decision.should
        assert 'Cooldown not elapsed' in decision.reason

    def test_cooldown_elapsed(self) -> None:
        """Release allowed when cooldown has elapsed."""
        now = _utc(2026, 1, 15, 14, 30)
        last = now - timedelta(minutes=150)
        decision = should_release(
            ScheduleConfig(cooldown_minutes=120),
            has_releasable_commits=True,
            last_release_time=last,
            now=now,
        )
        assert decision.should

    def test_no_previous_release_skips_cooldown(self) -> None:
        """No previous release skips cooldown check."""
        decision = should_release(
            ScheduleConfig(cooldown_minutes=120),
            has_releasable_commits=True,
            last_release_time=None,
            now=_utc(2026, 1, 15),
        )
        assert decision.should

    def test_zero_cooldown_always_passes(self) -> None:
        """Zero cooldown never blocks."""
        now = _utc(2026, 1, 15, 14, 30)
        last = now - timedelta(seconds=1)
        decision = should_release(
            ScheduleConfig(cooldown_minutes=0),
            has_releasable_commits=True,
            last_release_time=last,
            now=now,
        )
        assert decision.should


# Combined checks


class TestCombined:
    """should_release with multiple criteria."""

    def test_all_criteria_met(self) -> None:
        """All criteria met produces should=True."""
        now = _utc(2026, 1, 19, 15, 0)  # Monday, 15:00 UTC
        last = now - timedelta(hours=3)
        decision = should_release(
            ScheduleConfig(
                cadence='weekly:monday',
                release_window='14:00-16:00',
                cooldown_minutes=120,
                min_bump='patch',
            ),
            has_releasable_commits=True,
            max_bump_level='minor',
            last_release_time=last,
            now=now,
        )
        assert decision.should
        assert 'All release criteria met' in decision.reason

    def test_cadence_blocks_despite_commits(self) -> None:
        """Cadence blocks even when commits exist."""
        # Tuesday but cadence is weekly:monday.
        now = _utc(2026, 1, 20, 15, 0)
        decision = should_release(
            ScheduleConfig(cadence='weekly:monday'),
            has_releasable_commits=True,
            max_bump_level='major',
            now=now,
        )
        assert not decision.should
