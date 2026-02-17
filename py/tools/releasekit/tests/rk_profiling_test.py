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

"""Tests for releasekit.profiling — pipeline step timing."""

from __future__ import annotations

import json
import time

from releasekit.profiling import PipelineProfile, StepRecord, StepTimer

# StepRecord


class TestStepRecord:
    """Tests for StepRecord dataclass."""

    def test_basic_fields(self) -> None:
        """All fields are stored correctly."""
        r = StepRecord(name='build', start=1.0, end=2.5, duration=1.5)
        assert r.name == 'build'
        assert r.start == 1.0
        assert r.end == 2.5
        assert r.duration == 1.5
        assert r.metadata == {}

    def test_metadata(self) -> None:
        """Metadata dict is preserved."""
        r = StepRecord(
            name='publish',
            start=0.0,
            end=1.0,
            duration=1.0,
            metadata={'package': 'genkit', 'level': 0},
        )
        assert r.metadata['package'] == 'genkit'
        assert r.metadata['level'] == 0

    def test_frozen(self) -> None:
        """StepRecord is immutable."""
        r = StepRecord(name='x', start=0.0, end=1.0, duration=1.0)
        try:
            r.name = 'y'  # type: ignore[misc]
            raise AssertionError('Should have raised')
        except AttributeError:
            pass


# PipelineProfile


class TestPipelineProfile:
    """Tests for PipelineProfile."""

    def _make_records(self) -> list[StepRecord]:
        """Make records."""
        return [
            StepRecord(name='step_a', start=10.0, end=11.0, duration=1.0),
            StepRecord(name='step_b', start=11.0, end=13.0, duration=2.0),
            StepRecord(name='publish:genkit', start=13.0, end=13.5, duration=0.5),
        ]

    def test_total_duration(self) -> None:
        """Sum of all step durations."""
        p = PipelineProfile(records=self._make_records())
        assert p.total_duration == 3.5

    def test_total_duration_empty(self) -> None:
        """Empty profile has zero duration."""
        assert PipelineProfile().total_duration == 0.0

    def test_critical_path(self) -> None:
        """Elapsed from first start to last end."""
        p = PipelineProfile(records=self._make_records())
        assert p.critical_path == 3.5

    def test_critical_path_empty(self) -> None:
        """Empty profile has zero critical path."""
        assert PipelineProfile().critical_path == 0.0

    def test_slowest(self) -> None:
        """Returns the step with the longest duration."""
        p = PipelineProfile(records=self._make_records())
        assert p.slowest is not None
        assert p.slowest.name == 'step_b'
        assert p.slowest.duration == 2.0

    def test_slowest_empty(self) -> None:
        """Empty profile returns None."""
        assert PipelineProfile().slowest is None

    def test_by_prefix(self) -> None:
        """Filters records by name prefix."""
        p = PipelineProfile(records=self._make_records())
        publish_records = p.by_prefix('publish:')
        assert len(publish_records) == 1
        assert publish_records[0].name == 'publish:genkit'

    def test_by_prefix_no_match(self) -> None:
        """Returns empty list when no records match."""
        p = PipelineProfile(records=self._make_records())
        assert p.by_prefix('nonexistent:') == []

    def test_summary(self) -> None:
        """Summary dict has expected keys and values."""
        p = PipelineProfile(records=self._make_records())
        s = p.summary()
        assert s['total_steps'] == 3
        assert s['total_duration_s'] == 3.5
        assert s['critical_path_s'] == 3.5
        assert s['slowest_step'] == 'step_b'
        assert s['slowest_duration_s'] == 2.0

    def test_summary_empty(self) -> None:
        """Empty profile summary has zero values."""
        s = PipelineProfile().summary()
        assert s['total_steps'] == 0
        assert s['slowest_step'] == ''
        assert s['slowest_duration_s'] == 0.0

    def test_to_json(self) -> None:
        """JSON output is valid and contains expected structure."""
        p = PipelineProfile(records=self._make_records())
        data = json.loads(p.to_json())
        assert 'summary' in data
        assert 'steps' in data
        assert len(data['steps']) == 3
        assert data['steps'][0]['name'] == 'step_a'

    def test_to_json_with_metadata(self) -> None:
        """Metadata is included in JSON output."""
        r = StepRecord(
            name='build',
            start=0.0,
            end=1.0,
            duration=1.0,
            metadata={'package': 'genkit'},
        )
        p = PipelineProfile(records=[r])
        data = json.loads(p.to_json())
        assert data['steps'][0]['package'] == 'genkit'

    def test_render(self) -> None:
        """Render produces a non-empty table string."""
        p = PipelineProfile(records=self._make_records())
        output = p.render()
        assert 'Pipeline Profile' in output
        assert 'step_a' in output
        assert 'step_b' in output
        assert 'Total steps: 3' in output

    def test_render_empty(self) -> None:
        """Empty profile renders a placeholder."""
        assert PipelineProfile().render() == '(no profiling data)'

    def test_render_top_n(self) -> None:
        """top_n limits to the N slowest steps."""
        p = PipelineProfile(records=self._make_records())
        output = p.render(top_n=1)
        assert 'step_b' in output
        # step_a (1.0s) should not appear since only top 1 shown.
        assert 'step_a' not in output

    def test_render_with_slowest_step(self) -> None:
        """Render includes the slowest step line."""
        p = PipelineProfile(records=self._make_records())
        output = p.render()
        assert 'Slowest:' in output


# StepTimer


class TestStepTimer:
    """Tests for StepTimer context manager."""

    def test_step_records_duration(self) -> None:
        """Step context manager records a positive duration."""
        timer = StepTimer()
        with timer.step('test_step'):
            time.sleep(0.01)

        assert len(timer.profile.records) == 1
        r = timer.profile.records[0]
        assert r.name == 'test_step'
        assert r.duration > 0
        assert r.metadata == {}

    def test_step_with_metadata(self) -> None:
        """Metadata kwargs are captured."""
        timer = StepTimer()
        with timer.step('build', package='genkit', level=0):
            pass

        r = timer.profile.records[0]
        assert r.metadata == {'package': 'genkit', 'level': 0}

    def test_multiple_steps(self) -> None:
        """Multiple steps are recorded in order."""
        timer = StepTimer()
        with timer.step('a'):
            pass
        with timer.step('b'):
            pass
        with timer.step('c'):
            pass

        names = [r.name for r in timer.profile.records]
        assert names == ['a', 'b', 'c']

    def test_step_records_on_exception(self) -> None:
        """Duration is recorded even when the step raises."""
        timer = StepTimer()
        try:
            with timer.step('failing'):
                raise ValueError('boom')
        except ValueError:
            pass

        assert len(timer.profile.records) == 1
        assert timer.profile.records[0].name == 'failing'
        assert timer.profile.records[0].duration >= 0

    def test_no_metadata_produces_empty_dict(self) -> None:
        """When no kwargs are passed, metadata is empty dict."""
        timer = StepTimer()
        with timer.step('plain'):
            pass
        assert timer.profile.records[0].metadata == {}
