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

"""Pipeline profiling and step timing for releasekit.

Provides a :class:`StepTimer` that records wall-clock durations for
named pipeline steps. Useful for identifying bottlenecks in the
publish pipeline (e.g. slow registry polls, build steps).

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────┐
    │ Concept             │ Plain-English                                  │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ StepTimer           │ A stopwatch collection. Each named step gets  │
    │                     │ its own stopwatch that starts/stops.          │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ StepRecord          │ One completed measurement: name, start, end, │
    │                     │ duration, and optional metadata.              │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ PipelineProfile     │ The full collection of step records with      │
    │                     │ summary statistics and rendering.             │
    └─────────────────────┴────────────────────────────────────────────────┘

Usage::

    from releasekit.profiling import StepTimer

    timer = StepTimer()

    with timer.step('compute_bumps'):
        bumps = await compute_bumps(...)

    with timer.step('publish', package='genkit'):
        await publish(...)

    # Print a summary table.
    print(timer.profile.render())

    # Or get JSON for CI.
    print(timer.profile.to_json())
"""

from __future__ import annotations

import json
import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class StepRecord:
    """A single profiling measurement.

    Attributes:
        name: Step name (e.g. ``"compute_bumps"``, ``"publish:genkit"``).
        start: Monotonic start time (seconds).
        end: Monotonic end time (seconds).
        duration: Wall-clock duration in seconds.
        metadata: Optional key-value pairs (e.g. ``package``, ``level``).
    """

    name: str
    start: float
    end: float
    duration: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineProfile:
    """Collection of step timing records with summary statistics.

    Attributes:
        records: All recorded step timings, in order.
    """

    records: list[StepRecord] = field(default_factory=list)

    @property
    def total_duration(self) -> float:
        """Total wall-clock time across all steps (sum of durations)."""
        return sum(r.duration for r in self.records)

    @property
    def critical_path(self) -> float:
        """Elapsed time from first start to last end.

        This represents the actual wall-clock time of the pipeline,
        accounting for parallelism.
        """
        if not self.records:
            return 0.0
        return self.records[-1].end - self.records[0].start

    @property
    def slowest(self) -> StepRecord | None:
        """The step with the longest duration."""
        if not self.records:
            return None
        return max(self.records, key=lambda r: r.duration)

    def by_prefix(self, prefix: str) -> list[StepRecord]:
        """Filter records whose name starts with ``prefix``.

        Args:
            prefix: Name prefix to filter by (e.g. ``"publish:"``).

        Returns:
            Matching records in order.
        """
        return [r for r in self.records if r.name.startswith(prefix)]

    def summary(self) -> dict[str, Any]:
        """Return a summary dict suitable for structured logging.

        Returns:
            Dict with ``total_steps``, ``total_duration_s``,
            ``critical_path_s``, ``slowest_step``, and
            ``slowest_duration_s``.
        """
        slowest = self.slowest
        return {
            'total_steps': len(self.records),
            'total_duration_s': round(self.total_duration, 3),
            'critical_path_s': round(self.critical_path, 3),
            'slowest_step': slowest.name if slowest else '',
            'slowest_duration_s': round(slowest.duration, 3) if slowest else 0.0,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize the profile to JSON.

        Args:
            indent: JSON indentation level.

        Returns:
            JSON string with all records and summary.
        """
        return json.dumps(
            {
                'summary': self.summary(),
                'steps': [
                    {
                        'name': r.name,
                        'duration_s': round(r.duration, 3),
                        **r.metadata,
                    }
                    for r in self.records
                ],
            },
            indent=indent,
        )

    def render(self, *, top_n: int = 0) -> str:
        """Render a human-readable profiling table.

        Args:
            top_n: If > 0, only show the N slowest steps.

        Returns:
            A formatted string table.
        """
        if not self.records:
            return '(no profiling data)'

        records = self.records
        if top_n > 0:
            records = sorted(records, key=lambda r: r.duration, reverse=True)[:top_n]

        lines: list[str] = []
        lines.append('┌─ Pipeline Profile ─────────────────────────────────┐')

        # Header.
        lines.append(f'│ {"Step":<40s} {"Duration":>10s} │')
        lines.append('├────────────────────────────────────────┬───────────┤')

        for r in records:
            name = r.name[:40]
            dur = f'{r.duration:.3f}s'
            lines.append(f'│ {name:<40s} │ {dur:>9s} │')

        lines.append('├────────────────────────────────────────┴───────────┤')

        summary = self.summary()
        lines.append(f'│ Total steps: {summary["total_steps"]:<39d}│')
        lines.append(f'│ Sum of durations: {summary["total_duration_s"]:<34.3f}│')
        lines.append(f'│ Critical path:    {summary["critical_path_s"]:<34.3f}│')
        if summary['slowest_step']:
            lines.append(f'│ Slowest: {summary["slowest_step"]:<30s} {summary["slowest_duration_s"]:.3f}s │')
        lines.append('└────────────────────────────────────────────────────┘')

        return '\n'.join(lines)


class StepTimer:
    """Pipeline step timer that collects :class:`StepRecord` instances.

    Thread-safe for use with ``asyncio.gather`` — each ``step()``
    context manager captures its own start/end times independently.

    Attributes:
        profile: The collected :class:`PipelineProfile`.
    """

    def __init__(self) -> None:
        """Initialize a new step timer with an empty profile."""
        self.profile = PipelineProfile()

    @contextmanager
    def step(self, name: str, **metadata: Any) -> Generator[None, None, None]:  # noqa: ANN401
        """Time a named pipeline step.

        Args:
            name: Step name (e.g. ``"compute_bumps"``).
            **metadata: Optional key-value pairs attached to the record.

        Yields:
            Control to the caller. Duration is recorded on exit.

        Example::

            with timer.step('build', package='genkit'):
                await build_package(...)
        """
        start = time.monotonic()
        try:
            yield
        finally:
            end = time.monotonic()
            record = StepRecord(
                name=name,
                start=start,
                end=end,
                duration=end - start,
                metadata=dict(metadata) if metadata else {},
            )
            self.profile.records.append(record)


__all__ = [
    'PipelineProfile',
    'StepRecord',
    'StepTimer',
]
