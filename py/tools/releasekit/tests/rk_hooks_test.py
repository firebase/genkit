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

"""Tests for releasekit.hooks — lifecycle hooks."""

from __future__ import annotations

from pathlib import Path

import pytest
from releasekit.config import HooksConfig
from releasekit.hooks import expand_template, merge_hooks, run_hooks
from releasekit.logging import configure_logging

configure_logging(quiet=True)


# ---------------------------------------------------------------------------
# expand_template
# ---------------------------------------------------------------------------


class TestExpandTemplate:
    """Tests for expand_template()."""

    def test_expands_version(self) -> None:
        """Expands ${version} placeholder."""
        assert expand_template('echo ${version}', {'version': '1.2.3'}) == 'echo 1.2.3'

    def test_expands_name(self) -> None:
        """Expands ${name} placeholder."""
        assert expand_template('deploy ${name}', {'name': 'my-pkg'}) == 'deploy my-pkg'

    def test_expands_tag(self) -> None:
        """Expands ${tag} placeholder."""
        assert expand_template('git tag ${tag}', {'tag': 'v1.2.3'}) == 'git tag v1.2.3'

    def test_expands_multiple(self) -> None:
        """Expands multiple placeholders in one command."""
        result = expand_template(
            './notify.sh ${name} ${version} ${tag}',
            {'name': 'core', 'version': '2.0.0', 'tag': 'core-v2.0.0'},
        )
        assert result == './notify.sh core 2.0.0 core-v2.0.0'

    def test_no_variables(self) -> None:
        """No variables leaves command unchanged."""
        assert expand_template('echo hello', {}) == 'echo hello'

    def test_unknown_variable_left_as_is(self) -> None:
        """Unknown variable placeholder is left as-is."""
        assert expand_template('echo ${unknown}', {'version': '1.0'}) == 'echo ${unknown}'


# ---------------------------------------------------------------------------
# merge_hooks
# ---------------------------------------------------------------------------


class TestMergeHooks:
    """Tests for merge_hooks()."""

    def test_concatenates_by_default(self) -> None:
        """Default merge concatenates root + workspace + package."""
        root = HooksConfig(before_publish=['./lint.sh'])
        ws = HooksConfig(before_publish=['./build-docs.sh'])
        pkg = HooksConfig(before_publish=['./validate.sh'])

        merged = merge_hooks(root, ws, pkg)
        assert merged.before_publish == ['./lint.sh', './build-docs.sh', './validate.sh']

    def test_concatenates_different_events(self) -> None:
        """Different events concatenate independently."""
        root = HooksConfig(before_publish=['./lint.sh'], after_tag=['./notify.sh'])
        ws = HooksConfig(before_prepare=['./check.sh'])

        merged = merge_hooks(root, ws)
        assert merged.before_publish == ['./lint.sh']
        assert merged.after_tag == ['./notify.sh']
        assert merged.before_prepare == ['./check.sh']

    def test_replace_uses_most_specific(self) -> None:
        """Replace mode uses package hooks when present."""
        root = HooksConfig(before_publish=['./lint.sh'])
        ws = HooksConfig(before_publish=['./ws-only.sh'])
        pkg = HooksConfig(before_publish=['./pkg-only.sh'])

        merged = merge_hooks(root, ws, pkg, replace=True)
        assert merged.before_publish == ['./pkg-only.sh']

    def test_replace_falls_back_to_workspace(self) -> None:
        """Replace mode falls back to workspace when no package hooks."""
        root = HooksConfig(before_publish=['./lint.sh'])
        ws = HooksConfig(before_publish=['./ws-only.sh'])

        merged = merge_hooks(root, ws, replace=True)
        assert merged.before_publish == ['./ws-only.sh']

    def test_replace_falls_back_to_root(self) -> None:
        """Replace mode falls back to root when no workspace/package hooks."""
        root = HooksConfig(before_publish=['./lint.sh'])

        merged = merge_hooks(root, replace=True)
        assert merged.before_publish == ['./lint.sh']

    def test_empty_hooks(self) -> None:
        """Empty hooks produce empty lists."""
        merged = merge_hooks(HooksConfig())
        assert merged.before_publish == []
        assert merged.after_publish == []

    def test_none_workspace_and_package(self) -> None:
        """None workspace and package are handled gracefully."""
        root = HooksConfig(after_publish=['./notify.sh'])
        merged = merge_hooks(root, None, None)
        assert merged.after_publish == ['./notify.sh']


# ---------------------------------------------------------------------------
# run_hooks
# ---------------------------------------------------------------------------


class TestRunHooks:
    """Tests for run_hooks()."""

    @pytest.mark.asyncio
    async def test_dry_run_does_not_execute(self) -> None:
        """Dry-run logs but does not execute."""
        hooks = HooksConfig(before_publish=['echo hello'])
        results = await run_hooks(hooks, 'before_publish', dry_run=True)
        assert len(results) == 1
        assert results[0].dry_run is True
        assert results[0].ok

    @pytest.mark.asyncio
    async def test_empty_hooks_returns_empty(self) -> None:
        """No commands returns empty list."""
        hooks = HooksConfig()
        results = await run_hooks(hooks, 'before_publish')
        assert results == []

    @pytest.mark.asyncio
    async def test_template_expansion_in_dry_run(self) -> None:
        """Template variables are expanded even in dry-run."""
        hooks = HooksConfig(after_tag=['echo ${version}'])
        results = await run_hooks(
            hooks,
            'after_tag',
            variables={'version': '1.2.3'},
            dry_run=True,
        )
        assert len(results) == 1
        assert results[0].command == ['echo', '1.2.3']

    @pytest.mark.asyncio
    async def test_invalid_event_raises(self) -> None:
        """Invalid event name raises ValueError."""
        hooks = HooksConfig()
        with pytest.raises(ValueError, match='Unknown hook event'):
            await run_hooks(hooks, 'invalid_event')

    @pytest.mark.asyncio
    async def test_executes_real_command(self, tmp_path: Path) -> None:
        """Real command creates a file."""
        marker = tmp_path / 'marker.txt'
        hooks = HooksConfig(before_publish=[f'touch {marker}'])
        results = await run_hooks(hooks, 'before_publish', cwd=tmp_path)
        assert len(results) == 1
        assert results[0].ok
        assert marker.exists()

    @pytest.mark.asyncio
    async def test_stops_on_failure(self) -> None:
        """Execution stops on first failed command."""
        hooks = HooksConfig(before_publish=['false', 'echo should-not-run'])
        results = await run_hooks(hooks, 'before_publish')
        assert len(results) == 1
        assert not results[0].ok
